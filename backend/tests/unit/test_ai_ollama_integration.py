"""Ollama プロバイダー統合テスト + AIルーター LOCAL モード テスト.

Ollama ローカルLLM接続を模擬した統合的なテスト。
実際のOllama接続は不要（全てモック）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.ai.provider import (
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)


class TestOllamaProviderIntegration:
    """Ollama プロバイダーの統合テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.base_url = "http://localhost:11434"
        settings.cost_effective_model = "llama3.1:8b"
        from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider

        return OllamaLocalProvider(settings=settings)

    @pytest.mark.asyncio
    async def test_risk_analysis_prompt(self) -> None:
        """リスク分析プロンプトの処理テスト."""
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value={
                "message": {
                    "content": "売掛金の急増は架空売上のリスクを示唆します。"
                },
                "prompt_eval_count": 150,
                "eval_count": 50,
            }
        )
        p._client = mock_client

        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="あなたは連結子会社リスク分析AIアシスタントです。",
            ),
            Message(
                role=MessageRole.USER,
                content="売掛金が前年比233%増加した子会社のリスクを分析してください。",
            ),
        ]

        result = await p.complete(messages, model="llama3.1:8b", temperature=0.3)
        assert "売掛金" in result.content
        assert result.provider == "ollama"
        assert result.usage.total_tokens == 200

        # Ollama クライアントに正しいパラメータが渡されたか
        call_kwargs = mock_client.chat.call_args
        assert call_kwargs.kwargs["model"] == "llama3.1:8b"
        assert call_kwargs.kwargs["options"]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self) -> None:
        """マルチターン会話テスト."""
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value={
                "message": {"content": "フォローアップ回答です。"},
                "prompt_eval_count": 200,
                "eval_count": 30,
            }
        )
        p._client = mock_client

        messages = [
            Message(role=MessageRole.SYSTEM, content="分析アシスタント"),
            Message(role=MessageRole.USER, content="上海子会社のリスクは？"),
            Message(
                role=MessageRole.ASSISTANT,
                content="売掛金が急増しています。",
            ),
            Message(
                role=MessageRole.USER,
                content="具体的な対応策は？",
            ),
        ]

        result = await p.complete(messages, model="llama3.1:8b")
        assert result.content == "フォローアップ回答です。"

        # 全メッセージが Ollama に送信されたか
        call_kwargs = mock_client.chat.call_args
        ollama_msgs = call_kwargs.kwargs["messages"]
        assert len(ollama_msgs) == 4
        assert ollama_msgs[0]["role"] == "system"
        assert ollama_msgs[3]["role"] == "user"

    @pytest.mark.asyncio
    async def test_embedding_for_rag(self) -> None:
        """RAG 用埋め込みテスト."""
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.embeddings = AsyncMock(
            side_effect=[
                {"embedding": [0.1] * 768},
                {"embedding": [0.2] * 768},
            ]
        )
        p._client = mock_client

        result = await p.embed(
            ["売掛金の前年比分析", "ベンフォード分析の結果"],
            model="nomic-embed-text",
        )
        assert len(result.embeddings) == 2
        assert len(result.embeddings[0]) == 768
        assert result.model == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_streaming_analysis(self) -> None:
        """ストリーミング分析テスト."""
        p = self._make_provider()

        async def _stream():
            yield {"message": {"content": "リスク"}, "done": False}
            yield {"message": {"content": "分析"}, "done": False}
            yield {"message": {"content": "結果"}, "done": True}

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=_stream())
        p._client = mock_client

        chunks = []
        async for chunk in p.stream(
            [Message(role=MessageRole.USER, content="分析して")],
            model="llama3.1:8b",
        ):
            chunks.append(chunk)

        assert len(chunks) == 3
        full_text = "".join(c.content for c in chunks)
        assert full_text == "リスク分析結果"
        assert chunks[-1].finish_reason == "stop"


class TestAIRouterLocalMode:
    """AIルーター LOCAL モードのテスト."""

    @pytest.mark.asyncio
    async def test_local_mode_routes_to_ollama(self) -> None:
        """LOCAL モードで Ollama にルーティングされるか."""
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.config import ModelTier

        mock_registry = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.name = "ollama"
        mock_provider.complete = AsyncMock(
            return_value=AIResponse(
                content="回答",
                model="llama3.1:8b",
                provider="ollama",
                usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        )
        mock_registry.get.return_value = mock_provider

        mock_settings = MagicMock()
        mock_settings.ai.mode.value = "local"
        from cs_risk_agent.config import AIMode

        mock_settings.ai.mode = AIMode.LOCAL
        mock_settings.ai.default_provider = "azure"
        mock_settings.ai.fallback_providers = ["azure", "ollama"]

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "llama3.1:8b"

        mock_cb = AsyncMock()
        mock_cb.check_budget = AsyncMock()

        mock_cost = MagicMock()
        mock_cost.record.return_value = MagicMock(cost_usd=0.0)

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )
        router._settings = mock_settings

        messages = [Message(role=MessageRole.USER, content="テスト")]
        result = await router.complete(messages, tier=ModelTier.COST_EFFECTIVE)

        # LOCAL モードなので Ollama が使われる
        mock_registry.get.assert_called_with("ollama")
        assert result.provider == "ollama"

    @pytest.mark.asyncio
    async def test_hybrid_mode_routes_by_classification(self) -> None:
        """HYBRID モードでデータ分類に基づくルーティング."""
        from cs_risk_agent.ai.router import AIModelRouter
        from cs_risk_agent.config import ModelTier

        mock_registry = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.name = "ollama"
        mock_provider.complete = AsyncMock(
            return_value=AIResponse(
                content="機密データ分析結果",
                model="llama3.1:8b",
                provider="ollama",
                usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        )
        mock_registry.get.return_value = mock_provider

        mock_settings = MagicMock()
        from cs_risk_agent.config import AIMode

        mock_settings.ai.mode = AIMode.HYBRID
        mock_settings.ai.default_provider = "azure"
        mock_settings.ai.fallback_providers = ["azure", "ollama"]

        # ハイブリッドルール: confidential → ollama
        mock_rule = MagicMock()
        mock_rule.data_classification = "confidential"
        mock_rule.provider = "ollama"
        mock_settings.hybrid_rules = [mock_rule]

        mock_tier = MagicMock()
        mock_tier.get_model_id.return_value = "llama3.1:8b"

        mock_cb = AsyncMock()
        mock_cb.check_budget = AsyncMock()

        mock_cost = MagicMock()
        mock_cost.record.return_value = MagicMock(cost_usd=0.0)

        router = AIModelRouter(
            registry=mock_registry,
            tier_manager=mock_tier,
            circuit_breaker=mock_cb,
            cost_tracker=mock_cost,
        )
        router._settings = mock_settings

        messages = [Message(role=MessageRole.USER, content="機密データ分析")]
        result = await router.complete(
            messages,
            tier=ModelTier.COST_EFFECTIVE,
            data_classification="confidential",
        )

        # confidential データは Ollama にルーティング
        mock_registry.get.assert_called_with("ollama")
        assert result.content == "機密データ分析結果"


class TestAIInsightsFallback:
    """AI Insights API のフォールバック応答テスト."""

    def test_fallback_response_with_company(self) -> None:
        """企業指定時のフォールバック応答."""
        from cs_risk_agent.api.v1.ai_insights import _fallback_response

        with patch("cs_risk_agent.api.v1.ai_insights.DemoData") as mock_demo:
            mock_data = MagicMock()
            mock_data.get_risk_score_by_entity.return_value = {
                "total_score": 85,
                "risk_level": "critical",
                "da_score": 78,
                "fraud_score": 82,
                "rule_score": 90,
                "benford_score": 88,
                "risk_factors": ["売掛金急増", "CF逆相関"],
            }
            mock_data.get_entity_by_id.return_value = {
                "name": "テスト子会社",
                "country": "JP",
            }
            mock_demo.get.return_value = mock_data

            response = _fallback_response("リスク分析", "ENT001")
            assert response.provider == "demo"
            assert "85" in response.response
            assert "テスト子会社" in response.response

    def test_fallback_response_generic(self) -> None:
        """汎用フォールバック応答."""
        from cs_risk_agent.api.v1.ai_insights import _fallback_response

        with patch("cs_risk_agent.api.v1.ai_insights.DemoData") as mock_demo:
            mock_data = MagicMock()
            mock_data.get_risk_summary.return_value = {
                "total_companies": 15,
                "by_level": {"critical": 2, "high": 3, "medium": 5, "low": 5},
                "avg_score": 45.5,
            }
            mock_demo.get.return_value = mock_data

            response = _fallback_response("こんにちは", None)
            assert response.provider == "demo"
            assert "15" in response.response

    def test_fallback_response_shanghai_keyword(self) -> None:
        """上海キーワード検出時のフォールバック."""
        from cs_risk_agent.api.v1.ai_insights import _fallback_response

        with patch("cs_risk_agent.api.v1.ai_insights.DemoData") as mock_demo:
            mock_data = MagicMock()
            mock_data.get_risk_score_by_entity.return_value = None
            mock_data.get_entity_by_id.return_value = None
            mock_demo.get.return_value = mock_data

            response = _fallback_response("上海子会社の分析", None)
            assert "CRITICAL" in response.response
            assert "上海" in response.response
