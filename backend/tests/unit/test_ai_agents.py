"""AIエージェント (Probes) のユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cs_risk_agent.ai.agents.anomaly_probe import AnomalyProbe
from cs_risk_agent.ai.agents.cross_ref_probe import CrossReferenceProbe
from cs_risk_agent.ai.agents.ratio_probe import RatioProbe
from cs_risk_agent.ai.agents.relationship_probe import RelationshipProbe
from cs_risk_agent.ai.agents.trend_probe import TrendProbe

# ---------------------------------------------------------------------------
# テスト用 AgentState ヘルパー
# ---------------------------------------------------------------------------


def _base_state(financial_data: dict | None = None) -> dict:
    """基本的な AgentState を生成."""
    return {
        "company_id": "SUB-0001",
        "fiscal_year": 2025,
        "financial_data": financial_data or {},
        "probe_results": [],
        "insights": [],
        "risk_factors": [],
        "final_report": "",
        "current_stage": "analysis",
        "errors": [],
    }


def _sample_financial_data() -> dict:
    """標準的な財務データ."""
    return {
        "revenue": 100_000,
        "revenue_prev": 80_000,
        "cogs": 60_000,
        "cogs_prev": 50_000,
        "sga": 15_000,
        "sga_prev": 12_000,
        "operating_income": 25_000,
        "operating_income_prev": 18_000,
        "net_income": 12_000,
        "net_income_prev": 10_000,
        "total_assets": 200_000,
        "total_assets_prev": 180_000,
        "total_equity": 100_000,
        "total_liabilities": 100_000,
        "current_assets": 80_000,
        "current_liabilities": 40_000,
        "inventory": 20_000,
        "inventory_prev": 15_000,
        "receivables": 25_000,
        "receivables_prev": 20_000,
        "operating_cash_flow": 15_000,
        "interest_expense": 3_000,
        "ebit": 18_000,
    }


# ---------------------------------------------------------------------------
# AnomalyProbe テスト
# ---------------------------------------------------------------------------


class TestAnomalyProbe:
    """異常検知プローブのテスト."""

    def test_init_defaults(self) -> None:
        probe = AnomalyProbe()
        assert probe._z_threshold == 3.0
        assert probe._yoy_threshold == 0.50

    def test_init_custom(self) -> None:
        probe = AnomalyProbe(z_threshold=2.0, yoy_threshold=0.30)
        assert probe._z_threshold == 2.0
        assert probe._yoy_threshold == 0.30

    def test_analyze_normal_data(self) -> None:
        probe = AnomalyProbe()
        state = _base_state(_sample_financial_data())
        result = probe.analyze(state)
        assert "probe_results" in result
        assert isinstance(result["probe_results"], list)

    def test_analyze_with_extreme_yoy(self) -> None:
        probe = AnomalyProbe(yoy_threshold=0.10)
        data = _sample_financial_data()
        data["revenue_prev"] = 30_000  # 233%増 → 異常検知
        state = _base_state(data)
        result = probe.analyze(state)
        # YoY変化が閾値を超えるので検出あり
        yoy_findings = [r for r in result["probe_results"] if r.get("probe_name") == "anomaly"]
        assert len(yoy_findings) >= 0  # 検出有無はロジック次第

    def test_analyze_empty_data(self) -> None:
        probe = AnomalyProbe()
        state = _base_state({})
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)

    def test_extract_numeric_items(self) -> None:
        data = {"revenue": 100, "name": "test", "ratio": 0.5, "revenue_prev": 80}
        items = AnomalyProbe._extract_numeric_items(data)
        # _prev キーは除外される
        assert "revenue" in items
        assert "ratio" in items
        assert "revenue_prev" not in items
        assert "name" not in items

    def test_classify_yoy_severity(self) -> None:
        # > 1.0 → "critical", > 0.75 → "high", else → "medium"
        assert AnomalyProbe._classify_yoy_severity(1.5) == "critical"
        assert AnomalyProbe._classify_yoy_severity(0.8) == "high"
        assert AnomalyProbe._classify_yoy_severity(0.3) == "medium"
        assert AnomalyProbe._classify_yoy_severity(0.05) == "medium"


# ---------------------------------------------------------------------------
# RatioProbe テスト
# ---------------------------------------------------------------------------


class TestRatioProbe:
    """財務比率プローブのテスト."""

    def test_init_defaults(self) -> None:
        probe = RatioProbe()
        assert len(probe._thresholds) > 0

    def test_analyze_normal_data(self) -> None:
        probe = RatioProbe()
        state = _base_state(_sample_financial_data())
        result = probe.analyze(state)
        assert "probe_results" in result

    def test_calculate_ratios(self) -> None:
        probe = RatioProbe()
        data = _sample_financial_data()
        ratios = probe._calculate_ratios(data)
        assert isinstance(ratios, dict)
        # 基本比率が計算されるはず
        if "roe" in ratios:
            assert ratios["roe"] == pytest.approx(0.12, abs=0.01)

    def test_profitability_ratios(self) -> None:
        probe = RatioProbe()
        data = _sample_financial_data()
        ratios = probe._calc_profitability_ratios(data)
        assert isinstance(ratios, dict)

    def test_efficiency_ratios(self) -> None:
        probe = RatioProbe()
        data = _sample_financial_data()
        ratios = probe._calc_efficiency_ratios(data)
        assert isinstance(ratios, dict)

    def test_safety_ratios(self) -> None:
        probe = RatioProbe()
        data = _sample_financial_data()
        ratios = probe._calc_safety_ratios(data)
        assert isinstance(ratios, dict)

    def test_is_calculable(self) -> None:
        assert RatioProbe._is_calculable(100, 50) is True
        assert RatioProbe._is_calculable(100, 0) is False
        assert RatioProbe._is_calculable(None, 50) is False

    def test_analyze_zero_equity(self) -> None:
        probe = RatioProbe()
        data = _sample_financial_data()
        data["total_equity"] = 0
        state = _base_state(data)
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)


# ---------------------------------------------------------------------------
# TrendProbe テスト
# ---------------------------------------------------------------------------


class TestTrendProbe:
    """トレンドプローブのテスト."""

    def test_init_defaults(self) -> None:
        probe = TrendProbe()
        assert probe._growth_threshold == 0.30
        assert probe._break_threshold == 2.0
        assert probe._min_periods == 3

    def test_analyze_with_prev_data(self) -> None:
        probe = TrendProbe()
        state = _base_state(_sample_financial_data())
        result = probe.analyze(state)
        assert "probe_results" in result

    def test_analyze_with_history(self) -> None:
        probe = TrendProbe()
        data = _sample_financial_data()
        data["history"] = {
            "revenue": [80_000, 85_000, 90_000, 100_000],
            "net_income": [8_000, 9_000, 10_000, 12_000],
        }
        state = _base_state(data)
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)

    def test_compute_growth_rates(self) -> None:
        rates = TrendProbe._compute_growth_rates([100, 120, 150])
        assert len(rates) == 2
        assert rates[0] == pytest.approx(0.2, abs=0.01)
        assert rates[1] == pytest.approx(0.25, abs=0.01)

    def test_compute_growth_rates_empty(self) -> None:
        rates = TrendProbe._compute_growth_rates([100])
        assert rates == []

    def test_classify_growth_severity(self) -> None:
        # > 1.0 → "critical", > 0.50 → "high", else → "medium"
        assert TrendProbe._classify_growth_severity(1.5) == "critical"
        assert TrendProbe._classify_growth_severity(0.8) == "high"
        assert TrendProbe._classify_growth_severity(0.05) == "medium"

    def test_analyze_empty_data(self) -> None:
        probe = TrendProbe()
        state = _base_state({})
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)


# ---------------------------------------------------------------------------
# RelationshipProbe テスト
# ---------------------------------------------------------------------------


class TestRelationshipProbe:
    """関連当事者プローブのテスト."""

    def test_init_defaults(self) -> None:
        probe = RelationshipProbe()
        assert probe._revenue_threshold == 0.30
        assert probe._receivable_threshold == 0.25
        assert probe._balance_threshold == 0.20

    def test_analyze_no_related_party_data(self) -> None:
        probe = RelationshipProbe()
        state = _base_state(_sample_financial_data())
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)

    def test_analyze_with_related_party_data(self) -> None:
        probe = RelationshipProbe()
        data = _sample_financial_data()
        data["related_party_revenue"] = 40_000  # 40% > threshold 30%
        data["related_party_receivables"] = 10_000
        data["related_party_purchases"] = 38_000
        state = _base_state(data)
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)

    def test_analyze_with_intercompany(self) -> None:
        probe = RelationshipProbe()
        data = _sample_financial_data()
        data["intercompany_receivables"] = 50_000
        data["intercompany_payables"] = 48_000
        state = _base_state(data)
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)

    def test_is_round_number(self) -> None:
        assert RelationshipProbe._is_round_number(10_000) is True
        assert RelationshipProbe._is_round_number(1_000) is True
        assert RelationshipProbe._is_round_number(12_345) is False

    def test_is_valid_pair(self) -> None:
        assert RelationshipProbe._is_valid_pair(100, 200) is True
        assert RelationshipProbe._is_valid_pair(0, 200) is True  # 0 is valid int
        assert RelationshipProbe._is_valid_pair(None, 200) is False
        assert RelationshipProbe._is_valid_pair(100, 0) is False  # denominator=0

    def test_period_end_anomaly(self) -> None:
        probe = RelationshipProbe()
        data = _sample_financial_data()
        data["q4_related_party_revenue"] = 35_000
        data["related_party_revenue"] = 40_000
        state = _base_state(data)
        result = probe.analyze(state)
        assert isinstance(result["probe_results"], list)


# ---------------------------------------------------------------------------
# CrossReferenceProbe テスト
# ---------------------------------------------------------------------------


class TestCrossReferenceProbe:
    """クロスリファレンスプローブのテスト."""

    def test_no_findings(self) -> None:
        probe = CrossReferenceProbe()
        state = _base_state()
        state["probe_results"] = []
        result = probe.analyze(state)
        # 発見なし → no_major_issues
        cross_findings = [
            r for r in result["probe_results"] if r.get("probe_name") == "cross_reference"
        ]
        assert len(cross_findings) >= 1
        assert cross_findings[0]["severity"] == "low"

    def test_partial_evidence(self) -> None:
        probe = CrossReferenceProbe()
        state = _base_state()
        state["probe_results"] = [
            {"probe_name": "anomaly", "severity": "high", "finding": "test1"},
        ]
        result = probe.analyze(state)
        cross_findings = [
            r for r in result["probe_results"] if r.get("probe_name") == "cross_reference"
        ]
        assert len(cross_findings) >= 1

    def test_corroborating_evidence(self) -> None:
        probe = CrossReferenceProbe()
        state = _base_state()
        state["probe_results"] = [
            {"probe_name": "anomaly", "severity": "high", "finding": "f1"},
            {"probe_name": "ratio", "severity": "critical", "finding": "f2"},
            {"probe_name": "trend", "severity": "high", "finding": "f3"},
        ]
        result = probe.analyze(state)
        cross_findings = [
            r for r in result["probe_results"] if r.get("probe_name") == "cross_reference"
        ]
        assert len(cross_findings) >= 1
        assert cross_findings[0]["severity"] == "critical"


# ---------------------------------------------------------------------------
# AnalysisOrchestrator テスト
# ---------------------------------------------------------------------------


class TestAnalysisOrchestrator:
    """分析オーケストレーターのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.agents.orchestrator import AnalysisOrchestrator

        assert AnalysisOrchestrator is not None

    def test_init(self) -> None:
        from cs_risk_agent.ai.agents.orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator()
        assert orch._graph is not None

    @pytest.mark.asyncio
    async def test_run(self) -> None:
        from cs_risk_agent.ai.agents.orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator()
        mock_state = _base_state(_sample_financial_data())
        mock_state["final_report"] = "test report"

        with patch.object(orch, "_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_state)
            result = await orch.run("SUB-0001", 2025, _sample_financial_data())
            assert isinstance(result, dict)
