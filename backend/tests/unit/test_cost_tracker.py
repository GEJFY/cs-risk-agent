"""コストトラッカー ユニットテスト.

CostTracker のコスト計算・記録・集計ロジックを検証する。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cs_risk_agent.ai.cost_tracker import CostEntry, CostSummary, CostTracker
from cs_risk_agent.ai.model_tier import MODEL_PRESETS, ModelTierManager
from cs_risk_agent.config import ModelTier


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def tier_manager() -> ModelTierManager:
    """テスト用 ModelTierManager（デフォルトプリセット）."""
    return ModelTierManager(presets=MODEL_PRESETS.copy())


@pytest.fixture
def tracker(tier_manager) -> CostTracker:
    """テスト用 CostTracker."""
    return CostTracker(tier_manager=tier_manager)


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestCalculateCost:
    """コスト計算の検証."""

    def test_calculate_cost_azure_sota(self, tracker):
        """Azure SOTA モデルのコスト計算が正しいこと."""
        # gpt-4o: input=0.0025/1k, output=0.01/1k
        cost = tracker.calculate_cost(
            provider="azure",
            tier=ModelTier.SOTA,
            input_tokens=1000,
            output_tokens=500,
        )
        expected = (1000 / 1000) * 0.0025 + (500 / 1000) * 0.01
        assert cost == pytest.approx(expected)

    def test_calculate_cost_azure_cost_effective(self, tracker):
        """Azure 高コスパモデルのコスト計算が正しいこと."""
        # gpt-4o-mini: input=0.00015/1k, output=0.0006/1k
        cost = tracker.calculate_cost(
            provider="azure",
            tier=ModelTier.COST_EFFECTIVE,
            input_tokens=2000,
            output_tokens=1000,
        )
        expected = (2000 / 1000) * 0.00015 + (1000 / 1000) * 0.0006
        assert cost == pytest.approx(expected)

    def test_calculate_cost_ollama_free(self, tracker):
        """Ollama ローカルモデルのコストが 0 であること."""
        cost = tracker.calculate_cost(
            provider="ollama",
            tier=ModelTier.SOTA,
            input_tokens=5000,
            output_tokens=2000,
        )
        assert cost == 0.0

    def test_calculate_cost_zero_tokens(self, tracker):
        """トークン数0のコストが0であること."""
        cost = tracker.calculate_cost(
            provider="azure",
            tier=ModelTier.SOTA,
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0


class TestRecordEntry:
    """コスト記録の検証."""

    def test_record_entry(self, tracker):
        """record でエントリが正しく記録されること."""
        entry = tracker.record(
            provider="azure",
            model="gpt-4o",
            tier=ModelTier.SOTA,
            input_tokens=1000,
            output_tokens=500,
            user_id="user-001",
            request_id="req-001",
        )

        assert isinstance(entry, CostEntry)
        assert entry.provider == "azure"
        assert entry.model == "gpt-4o"
        assert entry.tier == ModelTier.SOTA
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.user_id == "user-001"
        assert entry.cost_usd > 0

    def test_record_multiple_entries(self, tracker):
        """複数エントリの記録が蓄積されること."""
        for i in range(5):
            tracker.record(
                provider="azure",
                model="gpt-4o",
                tier=ModelTier.SOTA,
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
            )
        summary = tracker.get_summary()
        assert summary.total_requests == 5


class TestGetSummary:
    """コストサマリー取得の検証."""

    def test_get_summary(self, tracker):
        """get_summary が正しいサマリーを返すこと."""
        tracker.record(
            provider="azure",
            model="gpt-4o",
            tier=ModelTier.SOTA,
            input_tokens=1000,
            output_tokens=500,
        )
        tracker.record(
            provider="aws",
            model="claude-sonnet",
            tier=ModelTier.SOTA,
            input_tokens=2000,
            output_tokens=800,
        )

        summary = tracker.get_summary()
        assert isinstance(summary, CostSummary)
        assert summary.total_requests == 2
        assert summary.total_cost_usd > 0
        assert summary.total_input_tokens == 3000
        assert summary.total_output_tokens == 1300

    def test_summary_empty(self, tracker):
        """記録がない場合のサマリーが空であること."""
        summary = tracker.get_summary()
        assert summary.total_requests == 0
        assert summary.total_cost_usd == 0.0


class TestSummaryByProvider:
    """プロバイダー別集計の検証."""

    def test_summary_by_provider(self, tracker):
        """プロバイダー別のコスト集計が正しいこと."""
        tracker.record(
            provider="azure", model="gpt-4o",
            tier=ModelTier.SOTA, input_tokens=1000, output_tokens=500,
        )
        tracker.record(
            provider="aws", model="claude",
            tier=ModelTier.SOTA, input_tokens=1000, output_tokens=500,
        )

        summary = tracker.get_summary()
        assert "azure" in summary.by_provider
        assert "aws" in summary.by_provider
        assert len(summary.by_provider) == 2


class TestSummaryByTier:
    """ティア別集計の検証."""

    def test_summary_by_tier(self, tracker):
        """ティア別のコスト集計が正しいこと."""
        tracker.record(
            provider="azure", model="gpt-4o",
            tier=ModelTier.SOTA, input_tokens=1000, output_tokens=500,
        )
        tracker.record(
            provider="azure", model="gpt-4o-mini",
            tier=ModelTier.COST_EFFECTIVE, input_tokens=1000, output_tokens=500,
        )

        summary = tracker.get_summary()
        assert ModelTier.SOTA.value in summary.by_tier
        assert ModelTier.COST_EFFECTIVE.value in summary.by_tier

    def test_to_dict_format(self, tracker):
        """to_dict が正しい辞書形式を返すこと."""
        tracker.record(
            provider="azure", model="gpt-4o",
            tier=ModelTier.SOTA, input_tokens=1000, output_tokens=500,
        )
        result = tracker.to_dict()
        assert "total_cost_usd" in result
        assert "total_requests" in result
        assert "by_provider" in result
        assert "by_model" in result
        assert "by_tier" in result
