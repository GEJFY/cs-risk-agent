"""fraud_prediction.py / trend_probe.py 残りカバレッジテスト."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from cs_risk_agent.core.exceptions import AnalysisError


# ---------------------------------------------------------------------------
# FraudPredictor - train / predict / _score_to_level / _get_feature_importance
# ---------------------------------------------------------------------------


def _make_sample_df(n: int = 100, fraud_ratio: float = 0.1) -> tuple:
    """テスト用の財務データとラベルを生成."""
    rng = np.random.default_rng(42)
    data = {
        "receivables": rng.uniform(1e6, 1e8, n),
        "revenue": rng.uniform(1e7, 1e9, n),
        "receivables_prior": rng.uniform(1e6, 1e8, n),
        "revenue_prior": rng.uniform(1e7, 1e9, n),
        "cogs": rng.uniform(1e6, 5e8, n),
        "cogs_prior": rng.uniform(1e6, 5e8, n),
        "current_assets": rng.uniform(1e7, 5e8, n),
        "ppe": rng.uniform(1e6, 1e8, n),
        "total_assets": rng.uniform(1e8, 1e10, n),
        "current_assets_prior": rng.uniform(1e7, 5e8, n),
        "ppe_prior": rng.uniform(1e6, 1e8, n),
        "total_assets_prior": rng.uniform(1e8, 1e10, n),
        "depreciation": rng.uniform(1e5, 1e7, n),
        "depreciation_prior": rng.uniform(1e5, 1e7, n),
        "sga": rng.uniform(1e6, 1e8, n),
        "sga_prior": rng.uniform(1e6, 1e8, n),
        "long_term_debt": rng.uniform(1e6, 5e8, n),
        "current_liabilities": rng.uniform(1e7, 3e8, n),
        "long_term_debt_prior": rng.uniform(1e6, 5e8, n),
        "current_liabilities_prior": rng.uniform(1e7, 3e8, n),
        "net_income": rng.uniform(-1e7, 1e8, n),
        "operating_cash_flow": rng.uniform(-1e7, 1e8, n),
        "retained_earnings": rng.uniform(1e6, 1e9, n),
        "ebit": rng.uniform(1e6, 1e8, n),
        "total_equity": rng.uniform(1e7, 5e9, n),
        "total_liabilities": rng.uniform(1e7, 5e9, n),
    }
    df = pd.DataFrame(data)
    n_fraud = int(n * fraud_ratio)
    y = pd.Series([1] * n_fraud + [0] * (n - n_fraud))
    return df, y


class TestFraudPredictorTrain:
    """FraudPredictor.train テスト."""

    def test_train_success(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, y = _make_sample_df(50, fraud_ratio=0.2)
        metrics = predictor.train(df, y)
        assert "auc" in metrics
        assert "recall" in metrics
        assert "cv_auc_mean" in metrics
        assert predictor.is_trained is True

    def test_train_empty_data(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        with pytest.raises(AnalysisError, match="学習データが空"):
            predictor.train(pd.DataFrame(), pd.Series(dtype=int))

    def test_train_no_fraud_labels(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, _ = _make_sample_df(20)
        y = pd.Series([0] * 20)
        with pytest.raises(AnalysisError, match="正例"):
            predictor.train(df, y)


class TestFraudPredictorPredict:
    """FraudPredictor.predict テスト."""

    def test_predict_rule_based(self) -> None:
        """モデル未学習: ルールベース予測."""
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, _ = _make_sample_df(5)
        results = predictor.predict(df)
        assert len(results) == 5
        for r in results:
            assert r.risk_level in ("critical", "high", "medium", "low")

    def test_predict_with_trained_model(self) -> None:
        """モデル学習済み: アンサンブル予測."""
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, y = _make_sample_df(50, fraud_ratio=0.2)
        predictor.train(df, y)
        results = predictor.predict(df.head(3))
        assert len(results) == 3
        assert results[0].feature_importance  # non-empty dict

    def test_predict_empty(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        with pytest.raises(AnalysisError, match="予測対象データが空"):
            predictor.predict(pd.DataFrame())


class TestScoreToLevel:
    """_score_to_level テスト."""

    def test_critical(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        assert FraudPredictor._score_to_level(85.0) == "critical"

    def test_high(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        assert FraudPredictor._score_to_level(65.0) == "high"

    def test_medium(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        assert FraudPredictor._score_to_level(45.0) == "medium"

    def test_low(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        assert FraudPredictor._score_to_level(20.0) == "low"


class TestFeatureImportance:
    """_get_feature_importance テスト."""

    def test_no_model(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        assert predictor._get_feature_importance() == {}

    def test_with_trained_model(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, y = _make_sample_df(50, fraud_ratio=0.2)
        predictor.train(df, y)
        importance = predictor._get_feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0


class TestFeatureNames:
    """feature_names プロパティテスト."""

    def test_feature_names(self) -> None:
        from cs_risk_agent.analysis.fraud_prediction import FraudPredictor

        predictor = FraudPredictor()
        df, y = _make_sample_df(50, fraud_ratio=0.2)
        predictor.train(df, y)
        names = predictor.feature_names
        assert "DSRI" in names
        assert len(names) == 13


# ---------------------------------------------------------------------------
# TrendProbe
# ---------------------------------------------------------------------------


class TestTrendProbe:
    """TrendProbe テスト."""

    def _make_agent(self):
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        return TrendProbe()

    def _make_state(self, financial_data=None) -> dict:
        return {
            "company_id": "TEST001",
            "current_stage": "",
            "financial_data": financial_data or {},
            "probe_results": [],
            "risk_factors": [],
            "errors": [],
        }

    def test_analyze_no_time_series(self) -> None:
        """時系列データが空の場合 data_limitation finding."""
        agent = self._make_agent()
        # financial_data は空でないが時系列にならない
        state = self._make_state({"single_value": 123})
        state = agent.analyze(state)
        findings = [f for f in state["probe_results"] if f["finding_type"] == "data_limitation"]
        assert len(findings) == 1

    def test_analyze_empty_financial_data(self) -> None:
        """financial_data が空の場合はエラー追加."""
        agent = self._make_agent()
        state = self._make_state({})
        state = agent.analyze(state)
        assert any("財務データが空" in e for e in state["errors"])

    def test_analyze_with_prev_pairs(self) -> None:
        """_prev ペアから時系列を抽出し分析."""
        agent = self._make_agent()
        state = self._make_state({
            "revenue": 100_000_000,
            "revenue_prev": 50_000_000,  # 100% growth → anomaly
        })
        state = agent.analyze(state)
        # 高い成長率 → growth_anomaly findings
        anomalies = [
            f for f in state["probe_results"] if f["finding_type"] == "growth_anomaly"
        ]
        assert len(anomalies) >= 1

    def test_analyze_with_history(self) -> None:
        """history リストパターンのテスト."""
        agent = self._make_agent()
        state = self._make_state({
            "history": [
                {"fiscal_year": 2022, "revenue": 100, "cogs": 50},
                {"fiscal_year": 2023, "revenue": 200, "cogs": 60},
                {"fiscal_year": 2024, "revenue": 150, "cogs": 70},
                {"fiscal_year": 2025, "revenue": 300, "cogs": 80},
            ]
        })
        state = agent.analyze(state)
        assert len(state["probe_results"]) > 0

    def test_extract_time_series_history(self) -> None:
        agent = self._make_agent()
        data = {
            "history": [
                {"fiscal_year": 2023, "revenue": 100, "profit": 10},
                {"fiscal_year": 2024, "revenue": 200, "profit": 20},
            ]
        }
        ts = agent._extract_time_series(data)
        assert "revenue" in ts
        assert ts["revenue"] == [100.0, 200.0]

    def test_extract_time_series_prev_pairs(self) -> None:
        agent = self._make_agent()
        data = {"revenue": 200, "revenue_prev": 100}
        ts = agent._extract_time_series(data)
        assert ts["revenue"] == [100.0, 200.0]

    def test_compute_growth_rates(self) -> None:
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        rates = TrendProbe._compute_growth_rates([100, 150, 120])
        assert len(rates) == 2
        assert abs(rates[0] - 0.5) < 1e-6

    def test_compute_growth_rates_zero_value(self) -> None:
        """ゼロ値がある場合はスキップ."""
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        rates = TrendProbe._compute_growth_rates([0, 100, 200])
        assert len(rates) == 1  # 最初のペアはスキップ

    def test_detect_structural_breaks(self) -> None:
        """構造変化検出."""
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        agent = TrendProbe(break_threshold=1.0)  # 低しきい値
        state = self._make_state()
        ts = {"metric_a": [100.0, 100.0, 100.0, 500.0]}
        agent._detect_structural_breaks(state, ts)
        breaks = [
            f for f in state["probe_results"] if f["finding_type"] == "structural_break"
        ]
        assert len(breaks) >= 1

    def test_detect_structural_breaks_short_series(self) -> None:
        """min_periods 未満の場合はスキップ."""
        agent = self._make_agent()
        state = self._make_state()
        ts = {"metric_a": [100.0, 110.0]}  # < min_periods(3)
        agent._detect_structural_breaks(state, ts)
        assert len(state["probe_results"]) == 0

    def test_detect_trend_reversals_peak(self) -> None:
        """ピーク（増加→減少）検出."""
        agent = self._make_agent()
        state = self._make_state()
        ts = {"metric_a": [100.0, 200.0, 150.0]}
        agent._detect_trend_reversals(state, ts)
        reversals = [
            f for f in state["probe_results"] if f["finding_type"] == "trend_reversal"
        ]
        assert any(r["evidence"]["reversal_type"] == "peak" for r in reversals)

    def test_detect_trend_reversals_bottom(self) -> None:
        """ボトム（減少→増加）検出."""
        agent = self._make_agent()
        state = self._make_state()
        ts = {"metric_a": [200.0, 100.0, 150.0]}
        agent._detect_trend_reversals(state, ts)
        reversals = [
            f for f in state["probe_results"] if f["finding_type"] == "trend_reversal"
        ]
        assert any(r["evidence"]["reversal_type"] == "bottom" for r in reversals)

    def test_revenue_expense_divergence_cogs(self) -> None:
        """売上・原価トレンド乖離."""
        agent = self._make_agent()
        state = self._make_state()
        data = {
            "revenue": 100, "revenue_prev": 100,  # 0% growth
            "cost_of_goods_sold": 80, "cost_of_goods_sold_prev": 50,  # +60% growth
        }
        agent._check_revenue_expense_divergence(state, data)
        divs = [
            f for f in state["probe_results"]
            if f["finding_type"] == "revenue_expense_divergence"
        ]
        assert len(divs) >= 1

    def test_revenue_expense_divergence_sga(self) -> None:
        """売上減少下の販管費増加."""
        agent = self._make_agent()
        state = self._make_state()
        data = {
            "revenue": 80, "revenue_prev": 100,  # -20%
            "sga_expense": 60, "sga_expense_prev": 40,  # +50%
        }
        agent._check_revenue_expense_divergence(state, data)
        divs = [
            f for f in state["probe_results"]
            if f["finding_type"] == "revenue_expense_divergence"
        ]
        assert len(divs) >= 1
        assert len(state["risk_factors"]) >= 1

    def test_revenue_expense_divergence_no_revenue(self) -> None:
        """売上データ欠落."""
        agent = self._make_agent()
        state = self._make_state()
        agent._check_revenue_expense_divergence(state, {})
        assert len(state["probe_results"]) == 0

    def test_check_growth_acceleration(self) -> None:
        """成長率急変検出."""
        agent = self._make_agent()
        state = self._make_state()
        # growth_threshold=0.30 → acceleration threshold=0.60
        growth_rates = [0.1, 0.8]  # acceleration = 0.7 > 0.60
        agent._check_growth_acceleration(state, "revenue", growth_rates)
        accs = [
            f for f in state["probe_results"]
            if f["finding_type"] == "growth_acceleration_anomaly"
        ]
        assert len(accs) >= 1

    def test_analyze_error_handling(self) -> None:
        """analyze 内で例外が発生した場合."""
        agent = self._make_agent()
        state = self._make_state({"revenue": 100, "revenue_prev": 50})
        # _extract_time_series にパッチして例外を発生させる
        with patch.object(agent, "_extract_time_series", side_effect=RuntimeError("boom")):
            result = agent.analyze(state)
        assert len(result["errors"]) >= 1

    def test_classify_growth_severity(self) -> None:
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        assert TrendProbe._classify_growth_severity(0.6) in (
            "medium", "high", "critical"
        )

    def test_analyze_growth_rates_short(self) -> None:
        """値が1つの場合はスキップ."""
        agent = self._make_agent()
        state = self._make_state()
        ts = {"metric_a": [100.0]}  # 1値のみ
        agent._analyze_growth_rates(state, ts)
        assert len(state["probe_results"]) == 0

    def test_analyze_growth_rates_no_growth(self) -> None:
        """成長率がゼロの値ペア (0始まり)."""
        agent = self._make_agent()
        state = self._make_state()
        ts = {"metric_a": [0.0, 100.0]}
        agent._analyze_growth_rates(state, ts)
        # growth rate from 0 is skipped
        assert len(state["probe_results"]) == 0


# ---------------------------------------------------------------------------
# Repository list_all
# ---------------------------------------------------------------------------


class TestRepositoryListAll:
    """CompanyRepository.list_all テスト."""

    @pytest.mark.asyncio
    async def test_list_all_no_filter(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        # count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3
        # data query
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [
            MagicMock(), MagicMock(), MagicMock()
        ]
        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        repo = CompanyRepository(mock_session)
        items, total = await repo.list_all(page=1, per_page=20)
        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_industry_filter(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        repo = CompanyRepository(mock_session)
        items, total = await repo.list_all(
            page=1, per_page=10, industry_code="3700"
        )
        assert total == 1
        assert len(items) == 1
