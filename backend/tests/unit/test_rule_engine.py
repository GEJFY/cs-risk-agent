"""ルールエンジン ユニットテスト.

RuleEngine の評価・スコアリングロジックを検証する。
"""

from __future__ import annotations

import pytest

from cs_risk_agent.analysis.rule_engine import (
    SEVERITY_WEIGHTS,
    RuleCategory,
    RuleDefinition,
    RuleEngine,
    RuleEngineResult,
    RuleResult,
    Severity,
)
from cs_risk_agent.core.exceptions import AnalysisError


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> RuleEngine:
    """テスト用 RuleEngine."""
    return RuleEngine()


@pytest.fixture
def risky_data() -> dict:
    """複数ルールが発火するリスクの高い財務データ."""
    return {
        "revenue": 100000,
        "revenue_prior": 90000,
        "cogs": 60000,
        "cogs_prior": 50000,
        "sga": 16000,
        "sga_prior": 14000,
        "net_income": 12000,
        "operating_cash_flow": -5000,  # 営業CF赤字 → R006発火
        "total_assets": 200000,
        "total_assets_prior": 180000,
        "current_assets": 30000,
        "current_assets_prior": 70000,
        "ppe": 50000,
        "ppe_prior": 45000,
        "receivables": 40000,  # 大幅増加 → R001発火
        "receivables_prior": 12000,
        "inventory": 8000,
        "inventory_prior": 5000,
        "depreciation": 5000,
        "depreciation_prior": 4500,
        "total_liabilities": 350000,  # 高レバレッジ → R003発火
        "total_equity": 100000,
        "current_liabilities": 40000,
        "current_liabilities_prior": 35000,
        "long_term_debt": 30000,
        "long_term_debt_prior": 28000,
        "retained_earnings": 60000,
        "ebit": 18000,
    }


@pytest.fixture
def safe_data() -> dict:
    """ルールがほぼ発火しない健全な財務データ."""
    return {
        "revenue": 100000,
        "revenue_prior": 95000,
        "cogs": 60000,
        "cogs_prior": 57000,
        "sga": 14000,
        "sga_prior": 14500,
        "net_income": 12000,
        "operating_cash_flow": 15000,
        "total_assets": 200000,
        "total_assets_prior": 190000,
        "current_assets": 80000,
        "current_assets_prior": 75000,
        "ppe": 50000,
        "ppe_prior": 48000,
        "receivables": 13000,
        "receivables_prior": 12000,
        "inventory": 8000,
        "inventory_prior": 7800,
        "depreciation": 5000,
        "depreciation_prior": 4800,
        "total_liabilities": 80000,
        "total_equity": 120000,
        "current_liabilities": 30000,
        "current_liabilities_prior": 28000,
        "long_term_debt": 20000,
        "long_term_debt_prior": 19000,
        "retained_earnings": 70000,
        "ebit": 20000,
    }


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestEvaluateAllRules:
    """全ルール評価の検証."""

    def test_evaluate_all_rules(self, engine, risky_data):
        """全26ルールが評価され結果が返ること."""
        results = engine.evaluate(risky_data)
        assert len(results) == 26

        # 各結果が RuleResult 型であること
        for r in results:
            assert isinstance(r, RuleResult)
            assert r.rule_id.startswith("R")

    def test_some_rules_triggered(self, engine, risky_data):
        """リスクデータで一部ルールが発火すること."""
        results = engine.evaluate(risky_data)
        triggered = [r for r in results if r.triggered]
        assert len(triggered) > 0, "リスクデータなのに1つもルールが発火しません"

    def test_safe_data_fewer_triggers(self, engine, safe_data):
        """健全データではルール発火数が少ないこと."""
        results = engine.evaluate(safe_data)
        triggered = [r for r in results if r.triggered]
        # 完全にゼロにはならないかもしれないが、少ないはず
        assert len(triggered) < 10


class TestCalculateTotalScore:
    """総合スコア算出の検証."""

    def test_calculate_total_score(self, engine, risky_data):
        """総合スコアが0〜100の範囲であること."""
        results = engine.evaluate(risky_data)
        score = engine.calculate_total_score(results)
        assert 0.0 <= score <= 100.0

    def test_risky_data_higher_score(self, engine, risky_data, safe_data):
        """リスクデータの方が健全データよりスコアが高いこと."""
        risky_results = engine.evaluate(risky_data)
        safe_results = engine.evaluate(safe_data)

        risky_score = engine.calculate_total_score(risky_results)
        safe_score = engine.calculate_total_score(safe_results)

        assert risky_score > safe_score

    def test_empty_results_return_zero(self, engine):
        """空の結果リストでスコアが0になること."""
        score = engine.calculate_total_score([])
        assert score == 0.0


class TestHighSeverityRules:
    """高重大度ルールの検証."""

    def test_high_severity_rules(self, engine):
        """CRITICAL/HIGH 重大度ルールが存在すること."""
        critical_rules = engine.get_rules_by_severity(Severity.CRITICAL)
        high_rules = engine.get_rules_by_severity(Severity.HIGH)

        assert len(critical_rules) > 0, "CRITICAL ルールが存在しません"
        assert len(high_rules) > 0, "HIGH ルールが存在しません"

    def test_critical_rule_negative_ocf_positive_ni(self, engine):
        """R006: 営業CF赤字+純利益黒字で発火すること."""
        data = {
            "operating_cash_flow": -5000,
            "net_income": 10000,
        }
        results = engine.evaluate(data)
        r006 = next(r for r in results if r.rule_id == "R006")
        assert r006.triggered is True

    def test_critical_rule_auditor_change(self, engine):
        """R025: 監査法人変更で発火すること."""
        data = {"auditor_changed": True}
        results = engine.evaluate(data)
        r025 = next(r for r in results if r.rule_id == "R025")
        assert r025.triggered is True

    def test_severity_weights(self, engine, risky_data):
        """発火ルールのスコアが重大度ウェイトと一致すること."""
        results = engine.evaluate(risky_data)
        for r in results:
            if r.triggered:
                expected_weight = SEVERITY_WEIGHTS.get(r.severity, 0.0)
                assert r.score == pytest.approx(expected_weight)


class TestEmptyData:
    """空データの検証."""

    def test_empty_data(self, engine):
        """空辞書で AnalysisError が発生すること."""
        with pytest.raises(AnalysisError):
            engine.evaluate({})

    def test_none_values_handled(self, engine):
        """None値を含むデータでエラーが発生しないこと."""
        data = {
            "revenue": None,
            "revenue_prior": None,
            "total_assets": 100000,
        }
        results = engine.evaluate(data)
        assert len(results) == 26  # エラーなく全ルール評価される


class TestScoreRange:
    """スコア範囲の検証."""

    def test_score_range_0_100(self, engine, risky_data):
        """evaluate_and_score のスコアが0〜100の範囲であること."""
        result = engine.evaluate_and_score(risky_data)
        assert isinstance(result, RuleEngineResult)
        assert 0.0 <= result.total_score <= 100.0

    def test_evaluate_and_score_structure(self, engine, risky_data):
        """evaluate_and_score の結果構造が正しいこと."""
        result = engine.evaluate_and_score(risky_data)
        assert result.total_rules == 26
        assert result.triggered_count >= 0
        assert result.max_possible_score > 0
        assert isinstance(result.category_scores, dict)
        assert isinstance(result.severity_distribution, dict)


class TestCustomRules:
    """カスタムルールの検証."""

    def test_add_rule(self, engine):
        """カスタムルールを追加できること."""
        custom_rule = RuleDefinition(
            rule_id="R999",
            name="custom_test",
            description="テスト用カスタムルール",
            severity=Severity.LOW,
            category=RuleCategory.GOVERNANCE,
            check_fn=lambda d: True,
        )
        engine.add_rule(custom_rule)
        assert engine.rule_count == 27

    def test_add_duplicate_rule_raises_error(self, engine):
        """重複ルールIDの追加で AnalysisError が発生すること."""
        custom_rule = RuleDefinition(
            rule_id="R001",  # 既存と重複
            name="duplicate",
            description="重複テスト",
            severity=Severity.LOW,
            category=RuleCategory.GOVERNANCE,
            check_fn=lambda d: True,
        )
        with pytest.raises(AnalysisError):
            engine.add_rule(custom_rule)

    def test_remove_rule(self, engine):
        """ルールを削除できること."""
        assert engine.remove_rule("R001") is True
        assert engine.rule_count == 25

    def test_remove_nonexistent_rule(self, engine):
        """存在しないルールの削除がFalseを返すこと."""
        assert engine.remove_rule("R999") is False
