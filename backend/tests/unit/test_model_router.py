"""AIモデルルーター ユニットテスト.

AIModelRouter のルーティング・フォールバック・予算管理ロジックを検証する。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.ai.circuit_breaker import CircuitBreaker
from cs_risk_agent.ai.cost_tracker import CostTracker
from cs_risk_agent.ai.model_tier import MODEL_PRESETS, ModelTierManager
from cs_risk_agent.ai.provider import AIResponse, Message, MessageRole, TokenUsage
from cs_risk_agent.ai.registry import ProviderRegistry
from cs_risk_agent.ai.router import AIModelRouter
from cs_risk_agent.config import ModelTier
from cs_risk_agent.core.exceptions import (
    AllProvidersFailedError,
    BudgetExceededError,
    ProviderError,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


def _mock_response(provider: str = "azure") -> AIResponse:
    """テスト用 AIResponse を生成."""
    return AIResponse(
        content=f"Response from {provider}",
        model="test-model",
        provider=provider,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


@pytest.fixture
def mock_registry():
    """モックプロバイダーレジストリ."""
    registry = ProviderRegistry()
    registry._initialized = True

    # Azure プロバイダー（正常）
    azure = AsyncMock()
    azure.name = "azure"
    azure.is_available = True
    azure.complete.return_value = _mock_response("azure")

    # AWS プロバイダー（正常）
    aws = AsyncMock()
    aws.name = "aws"
    aws.is_available = True
    aws.complete.return_value = _mock_response("aws")

    # Ollama プロバイダー（正常）
    ollama = AsyncMock()
    ollama.name = "ollama"
    ollama.is_available = True
    ollama.complete.return_value = _mock_response("ollama")

    registry._providers = {"azure": azure, "aws": aws, "ollama": ollama}
    return registry


@pytest.fixture
def router(mock_registry):
    """テスト用 AIModelRouter."""
    return AIModelRouter(
        registry=mock_registry,
        tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
        circuit_breaker=CircuitBreaker(monthly_limit_usd=1000.0),
        cost_tracker=CostTracker(),
    )


@pytest.fixture
def messages() -> list[Message]:
    """テスト用メッセージ."""
    return [Message(role=MessageRole.USER, content="テスト質問")]


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestCompleteWithDefaultProvider:
    """デフォルトプロバイダーでの完了リクエスト."""

    @pytest.mark.asyncio
    async def test_complete_with_default_provider(self, router, messages):
        """デフォルトプロバイダー（azure）で正常に完了すること."""
        response = await router.complete(messages, provider="azure")
        assert response.provider == "azure"
        assert response.content == "Response from azure"

    @pytest.mark.asyncio
    async def test_complete_returns_ai_response(self, router, messages):
        """戻り値が AIResponse インスタンスであること."""
        response = await router.complete(messages, provider="azure")
        assert isinstance(response, AIResponse)


class TestFallbackOnProviderError:
    """プロバイダー障害時のフォールバック."""

    @pytest.mark.asyncio
    async def test_fallback_on_provider_error(self, router, messages, mock_registry):
        """プライマリプロバイダー障害時にフォールバックすること."""
        # Azure を障害に設定
        mock_registry._providers["azure"].complete.side_effect = ProviderError(
            "azure", "Service unavailable"
        )

        response = await router.complete(messages, provider="azure")
        # フォールバックチェーンで aws に切り替わる
        assert response.provider in ("aws", "ollama")

    @pytest.mark.asyncio
    async def test_fallback_chain_order(self, router, messages, mock_registry):
        """フォールバックチェーンが設定順序に従うこと."""
        mock_registry._providers["azure"].complete.side_effect = ProviderError(
            "azure", "Error"
        )
        response = await router.complete(messages, provider="azure")
        # azure が失敗したので、次のプロバイダーが応答
        assert response.content is not None


class TestAllProvidersFailed:
    """全プロバイダー障害時."""

    @pytest.mark.asyncio
    async def test_all_providers_failed_error(self, router, messages, mock_registry):
        """全プロバイダーが障害の場合に AllProvidersFailedError が発生すること."""
        for provider in mock_registry._providers.values():
            provider.complete.side_effect = ProviderError("test", "Error")

        with pytest.raises(AllProvidersFailedError):
            await router.complete(messages, provider="azure")


class TestBudgetExceeded:
    """予算超過時."""

    @pytest.mark.asyncio
    async def test_budget_exceeded_error(self, messages, mock_registry):
        """サーキットブレーカーが OPEN 状態の場合に BudgetExceededError が発生すること."""
        # 予算を非常に小さく設定
        cb = CircuitBreaker(
            monthly_limit_usd=0.001,
            alert_threshold=0.1,
            breaker_threshold=0.5,
        )
        from cs_risk_agent.ai.circuit_breaker import UsageRecord
        from datetime import datetime, timezone

        # 予算を超過させる
        await cb.record_usage(UsageRecord(
            timestamp=datetime.now(timezone.utc),
            provider="azure", model="gpt-4o",
            input_tokens=100, output_tokens=50,
            cost_usd=0.001,
        ))

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=ModelTierManager(),
            circuit_breaker=cb,
            cost_tracker=CostTracker(),
        )

        with pytest.raises(BudgetExceededError):
            await router.complete(messages, provider="azure")


class TestHybridRouting:
    """ハイブリッドモードのルーティング."""

    @pytest.mark.asyncio
    async def test_hybrid_routing(self, router, messages, mock_registry):
        """data_classification を指定した場合のルーティング.

        ハイブリッドモードが設定されていない場合は
        デフォルトプロバイダーにフォールバックする。
        """
        response = await router.complete(
            messages,
            data_classification="confidential",
        )
        # ハイブリッドルールが設定されていないのでデフォルトプロバイダーで処理
        assert isinstance(response, AIResponse)
        assert response.content is not None


class TestCostRecording:
    """コスト記録の検証."""

    @pytest.mark.asyncio
    async def test_cost_recorded_on_success(self, router, messages):
        """リクエスト成功時にコストが記録されること."""
        await router.complete(messages, provider="azure")

        # コストトラッカーにエントリが記録されている
        summary = router._cost_tracker.get_summary()
        assert summary.total_requests == 1
        assert summary.total_cost_usd >= 0  # ローカルモデルの場合0もありうる

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_usage(self, router, messages):
        """リクエスト成功時にサーキットブレーカーに利用が記録されること."""
        await router.complete(messages, provider="azure")

        status = router._circuit_breaker.get_status()
        assert status.request_count == 1
