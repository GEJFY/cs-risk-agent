"""AI Router + Provider カバレッジテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)
from cs_risk_agent.config import ModelTier


# --- AIModelRouter ---


class TestAIModelRouterResolve:
    """_resolve_provider_name テスト."""

    def _make_router(self, **kwargs):
        from cs_risk_agent.ai.router import AIModelRouter

        mock_registry = MagicMock()
        mock_tier = MagicMock()
        mock_cb = MagicMock()
        mock_cost = MagicMock()
        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )
        return router

    def test_explicit_provider(self) -> None:
        router = self._make_router()
        assert router._resolve_provider_name(provider="azure") == "azure"

    def test_default_provider(self) -> None:
        router = self._make_router()
        assert router._resolve_provider_name() == router._settings.ai.default_provider

    def test_local_mode(self) -> None:
        from cs_risk_agent.config import AIMode

        router = self._make_router()
        router._settings = MagicMock()
        router._settings.ai.mode = AIMode.LOCAL
        assert router._resolve_provider_name() == "ollama"

    def test_hybrid_mode_routing(self) -> None:
        from cs_risk_agent.config import AIMode

        router = self._make_router()
        router._settings = MagicMock()
        router._settings.ai.mode = AIMode.HYBRID

        mock_rule = MagicMock()
        mock_rule.data_classification = "confidential"
        mock_rule.provider = "ollama"
        router._settings.hybrid_rules = [mock_rule]

        result = router._resolve_provider_name(data_classification="confidential")
        assert result == "ollama"


class TestAIModelRouterFallback:
    """_get_fallback_chain テスト."""

    def _make_router(self):
        from cs_risk_agent.ai.router import AIModelRouter

        router = AIModelRouter(
            registry=MagicMock(),
            tier_manager=MagicMock(),
            circuit_breaker=MagicMock(),
            cost_tracker=MagicMock(),
        )
        return router

    def test_primary_in_chain(self) -> None:
        router = self._make_router()
        router._settings = MagicMock()
        router._settings.ai.fallback_providers = ["azure", "ollama", "aws"]

        chain = router._get_fallback_chain("azure")
        assert chain[0] == "azure"
        assert "ollama" in chain

    def test_primary_not_in_chain(self) -> None:
        router = self._make_router()
        router._settings = MagicMock()
        router._settings.ai.fallback_providers = ["ollama"]

        chain = router._get_fallback_chain("azure")
        assert chain[0] == "azure"
        assert "ollama" in chain


class TestAIModelRouterComplete:
    """complete メソッドテスト."""

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter

        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.complete.return_value = AIResponse(
            content="Hello",
            provider="ollama",
            model="llama3",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "llama3"

        mock_cb = AsyncMock()
        mock_cb.check_budget = AsyncMock()
        mock_cb.record_usage = AsyncMock()

        mock_cost = MagicMock()
        mock_cost.record.return_value = MagicMock(cost_usd=0.001)

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )

        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = await router.complete(messages)
        assert result.content == "Hello"
        mock_cb.check_budget.assert_awaited_once()
        mock_cb.record_usage.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_provider_unavailable_fallback(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter

        mock_unavailable = MagicMock()
        mock_unavailable.is_available = False

        mock_available = AsyncMock()
        mock_available.is_available = True
        mock_available.complete.return_value = AIResponse(
            content="Fallback",
            provider="ollama",
            model="llama3",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
        )

        mock_registry = MagicMock()
        mock_registry.get.side_effect = [mock_unavailable, mock_available]

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "llama3"

        mock_cb = AsyncMock()
        mock_cost = MagicMock()
        mock_cost.record.return_value = MagicMock(cost_usd=0.0)

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )
        router._settings = MagicMock()
        router._settings.ai.default_provider = "azure"
        router._settings.ai.fallback_providers = ["azure", "ollama"]
        router._settings.ai.mode = MagicMock(value="cloud")

        messages = [Message(role=MessageRole.USER, content="test")]
        result = await router.complete(messages, provider="azure")
        assert result.content == "Fallback"

    @pytest.mark.asyncio
    async def test_complete_all_fail(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.core.exceptions import AllProvidersFailedError

        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.complete.side_effect = RuntimeError("error")

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "model"

        mock_cb = AsyncMock()
        mock_cost = MagicMock()

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )
        router._settings = MagicMock()
        router._settings.ai.default_provider = "ollama"
        router._settings.ai.fallback_providers = ["ollama"]
        router._settings.ai.mode = MagicMock(value="local")

        messages = [Message(role=MessageRole.USER, content="test")]
        with pytest.raises(AllProvidersFailedError):
            await router.complete(messages)

    @pytest.mark.asyncio
    async def test_complete_budget_exceeded(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.core.exceptions import BudgetExceededError

        mock_cb = AsyncMock()
        mock_cb.check_budget.side_effect = BudgetExceededError(100.0, 50.0)

        router = AIModelRouter(
            registry=MagicMock(),
            tier_manager=MagicMock(),
            circuit_breaker=mock_cb,
            cost_tracker=MagicMock(),
        )

        messages = [Message(role=MessageRole.USER, content="test")]
        with pytest.raises(BudgetExceededError):
            await router.complete(messages)


class TestAIModelRouterStream:
    """stream メソッドテスト."""

    @pytest.mark.asyncio
    async def test_stream_success(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter

        async def mock_stream(*args, **kwargs):
            yield AIChunk(content="chunk1", provider="ollama", model="llama3")
            yield AIChunk(content="chunk2", provider="ollama", model="llama3")

        mock_provider = MagicMock()
        mock_provider.is_available = True
        mock_provider.stream = mock_stream

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "llama3"

        mock_cb = AsyncMock()
        mock_cost = MagicMock()

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )

        messages = [Message(role=MessageRole.USER, content="test")]
        chunks = []
        async for chunk in router.stream(messages):
            chunks.append(chunk)
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_stream_all_fail(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.core.exceptions import AllProvidersFailedError

        async def bad_stream(*args, **kwargs):
            raise RuntimeError("fail")
            yield  # noqa: RET503 - make it a generator

        mock_provider = MagicMock()
        mock_provider.is_available = True
        mock_provider.stream = bad_stream

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "model"

        mock_cb = AsyncMock()

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=MagicMock(),
        )
        router._settings = MagicMock()
        router._settings.ai.default_provider = "ollama"
        router._settings.ai.fallback_providers = ["ollama"]
        router._settings.ai.mode = MagicMock(value="local")

        messages = [Message(role=MessageRole.USER, content="test")]
        with pytest.raises(AllProvidersFailedError):
            async for _ in router.stream(messages):
                pass


class TestAIModelRouterEmbed:
    """embed メソッドテスト."""

    @pytest.mark.asyncio
    async def test_embed_success(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter

        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.embed.return_value = EmbeddingResponse(
            embeddings=[[0.1, 0.2, 0.3]],
            model="embed-model",
            provider="ollama",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5),
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=MagicMock(),
            circuit_breaker=MagicMock(),
            cost_tracker=MagicMock(),
        )

        result = await router.embed(["test text"])
        assert len(result.embeddings) == 1

    @pytest.mark.asyncio
    async def test_embed_all_fail(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.core.exceptions import AllProvidersFailedError

        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.embed.side_effect = RuntimeError("fail")

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_provider

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=MagicMock(),
            circuit_breaker=MagicMock(),
            cost_tracker=MagicMock(),
        )
        router._settings = MagicMock()
        router._settings.ai.default_provider = "ollama"
        router._settings.ai.fallback_providers = ["ollama"]
        router._settings.ai.mode = MagicMock(value="local")

        with pytest.raises(AllProvidersFailedError):
            await router.embed(["test"])


class TestAIModelRouterStatus:
    """get_status テスト."""

    def test_get_status(self) -> None:
        from cs_risk_agent.ai.router import AIModelRouter

        mock_registry = MagicMock()
        mock_registry.to_dict.return_value = {}

        mock_cb = MagicMock()
        mock_cb.to_dict.return_value = {}

        mock_cost = MagicMock()
        mock_cost.to_dict.return_value = {}

        mock_tier = MagicMock()
        mock_tier.to_dict.return_value = {}

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )

        status = router.get_status()
        assert "mode" in status
        assert "providers" in status
        assert "budget" in status
        assert "cost" in status
