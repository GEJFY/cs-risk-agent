"""統合リスクスコアラー ユニットテスト.

IntegratedRiskScorer の統合スコア算出・リスクレベル判定を検証する。
"""

from __future__ import annotations

import pytest

from cs_risk_agent.analysis.risk_scorer import (
    DEFAULT_WEIGHTS,
    RISK_LEVEL_THRESHOLDS,
    IntegratedRiskResult,
    IntegratedRiskScorer,
    RiskComponent,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def scorer() -> IntegratedRiskScorer:
    """テスト用 IntegratedRiskScorer（デフォルト重み）."""
    return IntegratedRiskScorer()


@pytest.fixture
def custom_scorer() -> IntegratedRiskScorer:
    """カスタム重みのスコアラー."""
    return IntegratedRiskScorer(weights={
        "rule_engine": 0.5,
        "fraud_prediction": 0.5,
    })


# ---------------------------------------------------------------------------
# 統合スコア算出テスト
# ---------------------------------------------------------------------------


class TestCalculateIntegratedScore:
    """統合スコア算出の検証."""

    def test_calculate_integrated_score(self, scorer):
        """統合スコアが正しく算出されること."""
        scores = {
            "rule_engine": 70.0,
            "discretionary_accruals": 50.0,
            "fraud_prediction": 60.0,
            "benford": 30.0,
        }
        result = scorer.calculate_integrated_score(scores)

        # 手計算: 70*0.3 + 50*0.25 + 60*0.25 + 30*0.2 = 21 + 12.5 + 15 + 6 = 54.5
        assert result == pytest.approx(54.5, abs=0.1)

    def test_all_hundred_scores(self, scorer):
        """全コンポーネント100点で100点になること."""
        scores = {
            "rule_engine": 100.0,
            "discretionary_accruals": 100.0,
            "fraud_prediction": 100.0,
            "benford": 100.0,
        }
        result = scorer.calculate_integrated_score(scores)
        assert result == pytest.approx(100.0)

    def test_missing_components_treated_as_zero(self, scorer):
        """未提供コンポーネントが0点として扱われること."""
        scores = {"rule_engine": 100.0}
        result = scorer.calculate_integrated_score(scores)
        # rule_engine のみ100 * 0.3 = 30
        assert result == pytest.approx(30.0, abs=0.1)

    def test_score_clamped_to_100(self, scorer):
        """スコアが100を超えないこと."""
        scores = {
            "rule_engine": 200.0,
            "discretionary_accruals": 200.0,
            "fraud_prediction": 200.0,
            "benford": 200.0,
        }
        result = scorer.calculate_integrated_score(scores)
        assert result <= 100.0

    def test_negative_scores_clamped_to_zero(self, scorer):
        """負のスコアが0にクランプされること."""
        scores = {
            "rule_engine": -50.0,
            "discretionary_accruals": -30.0,
            "fraud_prediction": -20.0,
            "benford": -10.0,
        }
        result = scorer.calculate_integrated_score(scores)
        assert result >= 0.0


# ---------------------------------------------------------------------------
# リスクレベル判定テスト
# ---------------------------------------------------------------------------


class TestRiskLevelThresholds:
    """リスクレベル閾値の検証."""

    def test_critical_level(self):
        """80点以上が critical であること."""
        assert IntegratedRiskScorer.get_risk_level(80.0) == "critical"
        assert IntegratedRiskScorer.get_risk_level(95.0) == "critical"

    def test_high_level(self):
        """60-79点が high であること."""
        assert IntegratedRiskScorer.get_risk_level(60.0) == "high"
        assert IntegratedRiskScorer.get_risk_level(79.9) == "high"

    def test_medium_level(self):
        """40-59点が medium であること."""
        assert IntegratedRiskScorer.get_risk_level(40.0) == "medium"
        assert IntegratedRiskScorer.get_risk_level(59.9) == "medium"

    def test_low_level(self):
        """39点以下が low であること."""
        assert IntegratedRiskScorer.get_risk_level(39.9) == "low"
        assert IntegratedRiskScorer.get_risk_level(0.0) == "low"

    def test_boundary_values(self):
        """閾値境界値が正しく分類されること."""
        assert IntegratedRiskScorer.get_risk_level(80.0) == "critical"
        assert IntegratedRiskScorer.get_risk_level(60.0) == "high"
        assert IntegratedRiskScorer.get_risk_level(40.0) == "medium"


# ---------------------------------------------------------------------------
# コンポーネント重み検証テスト
# ---------------------------------------------------------------------------


class TestComponentWeights:
    """コンポーネント重みの検証."""

    def test_default_weights_sum_to_one(self):
        """デフォルト重みの合計が1.0であること."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_custom_weights_normalized(self, custom_scorer):
        """カスタム重みが正規化されること."""
        total = sum(custom_scorer.weights.values())
        assert total == pytest.approx(1.0)

    def test_custom_weights_score(self, custom_scorer):
        """カスタム重みが計算に反映されること."""
        scores = {
            "rule_engine": 80.0,
            "fraud_prediction": 40.0,
        }
        result = custom_scorer.calculate_integrated_score(scores)
        # 80*0.5 + 40*0.5 = 60.0
        assert result == pytest.approx(60.0, abs=0.1)


# ---------------------------------------------------------------------------
# 日本語サマリー生成テスト
# ---------------------------------------------------------------------------


class TestGenerateRiskSummaryJapanese:
    """日本語サマリー生成の検証."""

    def test_generate_risk_summary_japanese(self, scorer):
        """日本語サマリーが生成されること."""
        scores = {
            "rule_engine": 85.0,
            "discretionary_accruals": 70.0,
            "fraud_prediction": 60.0,
            "benford": 30.0,
        }
        result = scorer.evaluate(scores)
        assert isinstance(result, IntegratedRiskResult)
        assert "統合リスクスコア" in result.summary_ja
        assert "リスクレベル" in result.summary_ja

    def test_high_risk_components_in_summary(self, scorer):
        """高リスクコンポーネントがサマリーに含まれること."""
        scores = {
            "rule_engine": 85.0,
            "discretionary_accruals": 20.0,
            "fraud_prediction": 20.0,
            "benford": 20.0,
        }
        result = scorer.evaluate(scores)
        assert "高リスク要因" in result.summary_ja
        assert "ルールエンジン" in result.summary_ja

    def test_recommendations_generated(self, scorer):
        """推奨アクションが生成されること."""
        scores = {
            "rule_engine": 85.0,
            "discretionary_accruals": 85.0,
            "fraud_prediction": 85.0,
            "benford": 85.0,
        }
        result = scorer.evaluate(scores)
        assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# 全ゼロスコアテスト
# ---------------------------------------------------------------------------


class TestAllZeroScores:
    """全コンポーネントゼロスコアの検証."""

    def test_all_zero_scores(self, scorer):
        """全コンポーネント0点で統合スコアも0になること."""
        scores = {
            "rule_engine": 0.0,
            "discretionary_accruals": 0.0,
            "fraud_prediction": 0.0,
            "benford": 0.0,
        }
        result = scorer.calculate_integrated_score(scores)
        assert result == 0.0

    def test_all_zero_risk_level(self, scorer):
        """全コンポーネント0点でリスクレベルがlowであること."""
        scores = {
            "rule_engine": 0.0,
            "discretionary_accruals": 0.0,
            "fraud_prediction": 0.0,
            "benford": 0.0,
        }
        result = scorer.evaluate(scores)
        assert result.risk_level == "low"
        assert result.integrated_score == 0.0

    def test_empty_scores(self, scorer):
        """空スコアで0点になること."""
        result = scorer.calculate_integrated_score({})
        assert result == 0.0

    def test_evaluate_returns_all_components(self, scorer):
        """evaluate が全コンポーネントを含む結果を返すこと."""
        scores = {}
        result = scorer.evaluate(scores)
        assert len(result.components) == len(scorer.weights)
        for comp in result.components:
            assert isinstance(comp, RiskComponent)
            assert comp.score == 0.0
