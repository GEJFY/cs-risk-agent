"""フェイルオーバーデモスクリプト.

特定プロバイダーの障害時に即座に別プロバイダーへ切り替わることを実演する。
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, patch

# パス追加
sys.path.insert(0, str(__file__).replace("scripts/demo_failover.py", "backend/src"))

from cs_risk_agent.ai.provider import AIResponse, Message, MessageRole, TokenUsage
from cs_risk_agent.ai.circuit_breaker import CircuitBreaker
from cs_risk_agent.ai.cost_tracker import CostTracker
from cs_risk_agent.ai.model_tier import ModelTierManager
from cs_risk_agent.ai.registry import ProviderRegistry
from cs_risk_agent.ai.router import AIModelRouter
from cs_risk_agent.core.exceptions import ProviderError


class MockProvider:
    """テスト用モックプロバイダー."""

    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return True

    async def complete(self, messages, model, **kwargs) -> AIResponse:
        if self._should_fail:
            raise ProviderError(self._name, "Service unavailable (simulated)")
        return AIResponse(
            content=f"[{self._name}] 応答成功: リクエストを正常に処理しました。",
            model=model or "mock-model",
            provider=self._name,
            usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        )

    async def stream(self, messages, model, **kwargs):
        if self._should_fail:
            raise ProviderError(self._name, "Service unavailable (simulated)")
        yield type("Chunk", (), {"content": f"[{self._name}] stream chunk", "model": model, "provider": self._name, "finish_reason": "stop"})()

    async def embed(self, texts, model, **kwargs):
        raise ProviderError(self._name, "Not implemented")

    async def health_check(self) -> bool:
        return not self._should_fail


async def demo_failover():
    """フェイルオーバーデモ実行."""
    print("=" * 70)
    print("  クラウド・フェイルオーバー デモ")
    print("  特定プロバイダー障害時の即時切り替え")
    print("=" * 70)

    # レジストリにモックプロバイダーを登録
    registry = ProviderRegistry()
    registry._initialized = True

    # Scenario 1: Azure障害 → AWSフォールバック
    print("\n--- シナリオ1: Azureプロバイダー障害 ---")
    registry._providers = {
        "azure": MockProvider("azure", should_fail=True),
        "aws": MockProvider("aws", should_fail=False),
        "gcp": MockProvider("gcp", should_fail=False),
        "ollama": MockProvider("ollama", should_fail=False),
    }

    router = AIModelRouter(
        registry=registry,
        tier_manager=ModelTierManager(),
        circuit_breaker=CircuitBreaker(monthly_limit_usd=1000),
        cost_tracker=CostTracker(),
    )

    messages = [Message(role=MessageRole.USER, content="連結子会社のリスク分析を実行してください")]

    print("  リクエスト送信: Azure (default) → 障害発生")
    try:
        response = await router.complete(messages, provider="azure")
        print(f"  フォールバック成功: {response.provider}")
        print(f"  応答: {response.content}")
    except Exception as e:
        print(f"  エラー: {e}")

    # Scenario 2: Azure + AWS障害 → GCPフォールバック
    print("\n--- シナリオ2: Azure + AWS 同時障害 ---")
    registry._providers["aws"] = MockProvider("aws", should_fail=True)

    try:
        response = await router.complete(messages, provider="azure")
        print(f"  フォールバック成功: {response.provider}")
        print(f"  応答: {response.content}")
    except Exception as e:
        print(f"  エラー: {e}")

    # Scenario 3: 全クラウド障害 → ローカルLLMフォールバック
    print("\n--- シナリオ3: 全クラウド障害 → ローカルLLM ---")
    registry._providers["gcp"] = MockProvider("gcp", should_fail=True)

    try:
        response = await router.complete(messages, provider="azure")
        print(f"  フォールバック成功: {response.provider}")
        print(f"  応答: {response.content}")
    except Exception as e:
        print(f"  エラー: {e}")

    # Scenario 4: 全プロバイダー障害
    print("\n--- シナリオ4: 全プロバイダー障害 ---")
    registry._providers["ollama"] = MockProvider("ollama", should_fail=True)

    try:
        response = await router.complete(messages, provider="azure")
        print(f"  応答: {response.content}")
    except Exception as e:
        print(f"  全プロバイダー失敗（期待通り）: {e}")

    # Scenario 5: 復旧確認
    print("\n--- シナリオ5: Azure復旧後の正常動作 ---")
    registry._providers["azure"] = MockProvider("azure", should_fail=False)

    try:
        response = await router.complete(messages, provider="azure")
        print(f"  復旧確認: {response.provider}")
        print(f"  応答: {response.content}")
    except Exception as e:
        print(f"  エラー: {e}")

    print("\n" + "=" * 70)
    print("  フェイルオーバーデモ完了")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_failover())
