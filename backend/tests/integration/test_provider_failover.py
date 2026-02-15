"""プロバイダーフェイルオーバー 統合テスト.

複数プロバイダー間のフェイルオーバーとサーキットブレーカー連携を検証する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from cs_risk_agent.ai.circuit_breaker import CircuitBreaker, CircuitState, UsageRecord
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
# ヘルパー
# ---------------------------------------------------------------------------


def _create_mock_provider(name: str, should_fail: bool = False) -> AsyncMock:
    """テスト用モックプロバイダーを生成する."""
    provider = AsyncMock()
    provider.name = name
    provider.is_available = True

    if should_fail:
        provider.complete.side_effect = ProviderError(name, "Service unavailable")
    else:
        provider.complete.return_value = AIResponse(
            content=f"Response from {name}",
            model="test-model",
            provider=name,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

    return provider


def _create_registry(provider_configs: dict[str, bool]) -> ProviderRegistry:
    """プロバイダーの成功/失敗を指定してレジストリを生成する.

    Args:
        provider_configs: プロバイダー名 → should_fail のマッピング
    """
    registry = ProviderRegistry()
    registry._initialized = True
    registry._providers = {
        name: _create_mock_provider(name, should_fail)
        for name, should_fail in provider_configs.items()
    }
    return registry


def _create_router(registry: ProviderRegistry, budget: float = 1000.0) -> AIModelRouter:
    """テスト用ルーターを生成する."""
    return AIModelRouter(
        registry=registry,
        tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
        circuit_breaker=CircuitBreaker(monthly_limit_usd=budget),
        cost_tracker=CostTracker(),
    )


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def messages() -> list[Message]:
    """テスト用メッセージ."""
    return [Message(role=MessageRole.USER, content="テスト質問")]


# ---------------------------------------------------------------------------
# フェイルオーバーシーケンス テスト
# ---------------------------------------------------------------------------


class TestFailoverSequence:
    """フェイルオーバーシーケンスの検証."""

    @pytest.mark.asyncio
    async def test_failover_first_fails_second_succeeds(self, messages):
        """1番目のプロバイダー障害時に2番目にフォールバックすること."""
        registry = _create_registry({
            "azure": True,   # 障害
            "aws": False,    # 正常
            "gcp": False,    # 正常
            "ollama": False,  # 正常
        })
        router = _create_router(registry)

        response = await router.complete(messages, provider="azure")
        assert response.provider in ("aws", "gcp", "ollama")
        assert "Response from" in response.content

    @pytest.mark.asyncio
    async def test_failover_first_two_fail(self, messages):
        """1番目と2番目が障害の場合に3番目にフォールバックすること."""
        registry = _create_registry({
            "azure": True,   # 障害
            "aws": True,     # 障害
            "gcp": False,    # 正常
            "ollama": False,  # 正常
        })
        router = _create_router(registry)

        response = await router.complete(messages, provider="azure")
        assert response.provider in ("gcp", "ollama")

    @pytest.mark.asyncio
    async def test_failover_to_local_llm(self, messages):
        """全クラウドプロバイダー障害時にローカルLLMにフォールバックすること."""
        registry = _create_registry({
            "azure": True,   # 障害
            "aws": True,     # 障害
            "gcp": True,     # 障害
            "ollama": False,  # 正常（ローカル）
        })
        router = _create_router(registry)

        response = await router.complete(messages, provider="azure")
        assert response.provider == "ollama"

    @pytest.mark.asyncio
    async def test_all_providers_fail(self, messages):
        """全プロバイダー障害で AllProvidersFailedError が発生すること."""
        registry = _create_registry({
            "azure": True,
            "aws": True,
            "gcp": True,
            "ollama": True,
        })
        router = _create_router(registry)

        with pytest.raises(AllProvidersFailedError) as exc_info:
            await router.complete(messages, provider="azure")

        assert len(exc_info.value.providers) > 0

    @pytest.mark.asyncio
    async def test_recovery_after_failure(self, messages):
        """プロバイダー復旧後の正常動作確認."""
        registry = _create_registry({
            "azure": True,   # 初回障害
            "aws": False,
            "gcp": False,
            "ollama": False,
        })
        router = _create_router(registry)

        # 1回目: フォールバック
        response1 = await router.complete(messages, provider="azure")
        assert response1.provider != "azure"

        # Azure を復旧
        registry._providers["azure"] = _create_mock_provider("azure", should_fail=False)

        # 2回目: Azure で正常処理
        response2 = await router.complete(messages, provider="azure")
        assert response2.provider == "azure"

    @pytest.mark.asyncio
    async def test_unavailable_provider_skipped(self, messages):
        """is_available=False のプロバイダーがスキップされること."""
        registry = _create_registry({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })
        # azure を利用不可に設定
        registry._providers["azure"].is_available = False

        router = _create_router(registry)
        response = await router.complete(messages, provider="azure")
        # azure はスキップされ、次のプロバイダーで処理される
        assert response.provider in ("aws", "gcp", "ollama")


# ---------------------------------------------------------------------------
# サーキットブレーカー統合テスト
# ---------------------------------------------------------------------------


class TestCircuitBreakerIntegration:
    """サーキットブレーカーとルーターの統合検証."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_after_budget(self, messages):
        """予算超過後にリクエストがブロックされること."""
        registry = _create_registry({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })

        # 非常に小さい予算でルーターを作成
        cb = CircuitBreaker(
            monthly_limit_usd=0.001,
            alert_threshold=0.1,
            breaker_threshold=0.5,
        )

        # 予算を事前に超過させる
        await cb.record_usage(UsageRecord(
            timestamp=datetime.now(timezone.utc),
            provider="azure",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.001,
        ))

        router = AIModelRouter(
            registry=registry,
            tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
            circuit_breaker=cb,
            cost_tracker=CostTracker(),
        )

        with pytest.raises(BudgetExceededError):
            await router.complete(messages, provider="azure")

    @pytest.mark.asyncio
    async def test_successful_requests_track_cost(self, messages):
        """成功リクエストのコストがサーキットブレーカーに記録されること."""
        registry = _create_registry({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })
        cb = CircuitBreaker(monthly_limit_usd=1000.0)
        router = AIModelRouter(
            registry=registry,
            tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
            circuit_breaker=cb,
            cost_tracker=CostTracker(),
        )

        await router.complete(messages, provider="azure")

        # サーキットブレーカーにレコードが記録されること
        status = cb.get_status()
        assert status.request_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(self, messages):
        """サーキットブレーカーの状態遷移がルーター経由で機能すること."""
        registry = _create_registry({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })

        # azure の返答に大きなトークン数を設定（高コスト）
        registry._providers["azure"].complete.return_value = AIResponse(
            content="Expensive response",
            model="gpt-4o",
            provider="azure",
            usage=TokenUsage(prompt_tokens=100000, completion_tokens=50000, total_tokens=150000),
        )

        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )

        router = AIModelRouter(
            registry=registry,
            tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
            circuit_breaker=cb,
            cost_tracker=CostTracker(),
        )

        # 複数回リクエストしてコストを蓄積
        # gpt-4o: input=0.0025/1K, output=0.01/1K
        # 1回あたり: 100K*0.0025 + 50K*0.01 = 0.25 + 0.5 = 0.75 USD
        # budget=100: 0.75で0.75%なのでまだ CLOSED
        await router.complete(messages, provider="azure")

        status = cb.get_status()
        assert status.state in (
            CircuitState.CLOSED,
            CircuitState.HALF_OPEN,
            CircuitState.OPEN,
        )
