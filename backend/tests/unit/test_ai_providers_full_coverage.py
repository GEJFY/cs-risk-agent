"""AI Providers 全メソッド カバレッジテスト."""

from __future__ import annotations

import json
from io import BytesIO
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


# ---------------------------------------------------------------------------
# AWS Bedrock
# ---------------------------------------------------------------------------


class TestAWSBedrock:
    """AWSBedrockProvider テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.is_configured = True
        settings.region = "us-east-1"
        settings.access_key_id = "AKID"
        settings.secret_access_key = "secret"
        settings.bedrock_sota_model = "anthropic.claude-v2"
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider

        return AWSBedrockProvider(settings=settings)

    def test_name_and_available(self) -> None:
        p = self._make_provider()
        assert p.name == "aws"
        assert p.is_available is True

    def test_get_client_unavailable(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider
        from cs_risk_agent.core.exceptions import ProviderUnavailableError

        settings = MagicMock()
        settings.is_configured = False
        p = AWSBedrockProvider(settings=settings)
        with pytest.raises(ProviderUnavailableError):
            p._get_client()

    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    def test_get_client_creates_once(self, mock_boto3) -> None:
        p = self._make_provider()
        c1 = p._get_client()
        c2 = p._get_client()
        assert c1 is c2
        mock_boto3.client.assert_called_once()

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_complete(self, mock_boto3) -> None:
        p = self._make_provider()
        body_content = json.dumps({
            "content": [{"text": "Hello"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "stop_reason": "end_turn",
        }).encode()
        mock_response = {"body": BytesIO(body_content)}
        mock_boto3.client.return_value.invoke_model.return_value = mock_response

        msgs = [
            Message(role=MessageRole.SYSTEM, content="Be helpful"),
            Message(role=MessageRole.USER, content="Hi"),
        ]
        result = await p.complete(msgs, model="")
        assert isinstance(result, AIResponse)
        assert result.content == "Hello"
        assert result.usage.prompt_tokens == 10

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_complete_error(self, mock_boto3) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_boto3.client.return_value.invoke_model.side_effect = RuntimeError("boom")

        with pytest.raises(ProviderError, match="aws"):
            await p.complete(
                [Message(role=MessageRole.USER, content="Hi")], model="m"
            )

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_stream(self, mock_boto3) -> None:
        p = self._make_provider()

        # content_block_delta イベント
        delta_event = {
            "chunk": {
                "bytes": json.dumps({
                    "type": "content_block_delta",
                    "delta": {"text": "Hi"},
                }).encode()
            }
        }
        stop_event = {
            "chunk": {
                "bytes": json.dumps({"type": "message_stop"}).encode()
            }
        }
        mock_boto3.client.return_value.invoke_model_with_response_stream.return_value = {
            "body": [delta_event, stop_event]
        }

        msgs = [Message(role=MessageRole.USER, content="Hello")]
        chunks = []
        async for chunk in p.stream(msgs, model=""):
            chunks.append(chunk)
        assert len(chunks) == 2
        assert chunks[0].content == "Hi"
        assert chunks[1].finish_reason == "stop"

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_stream_error(self, mock_boto3) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_boto3.client.return_value.invoke_model_with_response_stream.side_effect = (
            RuntimeError("stream fail")
        )
        with pytest.raises(ProviderError):
            async for _ in p.stream(
                [Message(role=MessageRole.USER, content="Hi")], model="m"
            ):
                pass

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_embed(self, mock_boto3) -> None:
        p = self._make_provider()
        body1 = json.dumps({"embedding": [0.1, 0.2], "inputTextTokenCount": 3}).encode()
        body2 = json.dumps({"embedding": [0.3, 0.4], "inputTextTokenCount": 4}).encode()

        mock_client = mock_boto3.client.return_value
        mock_client.invoke_model.side_effect = [
            {"body": BytesIO(body1)},
            {"body": BytesIO(body2)},
        ]

        result = await p.embed(["hello", "world"], model="")
        assert isinstance(result, EmbeddingResponse)
        assert len(result.embeddings) == 2
        assert result.usage.prompt_tokens == 7

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.aws_bedrock.boto3")
    async def test_embed_error(self, mock_boto3) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_boto3.client.return_value.invoke_model.side_effect = RuntimeError("err")
        with pytest.raises(ProviderError):
            await p.embed(["text"], model="m")


# ---------------------------------------------------------------------------
# GCP Vertex AI
# ---------------------------------------------------------------------------


class TestGCPVertex:
    """GCPVertexProvider テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.is_configured = True
        settings.project_id = "proj-123"
        settings.location = "us-central1"
        settings.sota_model = "gemini-1.5-pro"
        from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider

        return GCPVertexProvider(settings=settings)

    def test_name_and_available(self) -> None:
        p = self._make_provider()
        assert p.name == "gcp"
        assert p.is_available is True

    def test_ensure_initialized_unavailable(self) -> None:
        from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider
        from cs_risk_agent.core.exceptions import ProviderUnavailableError

        settings = MagicMock()
        settings.is_configured = False
        p = GCPVertexProvider(settings=settings)
        with pytest.raises(ProviderUnavailableError):
            p._ensure_initialized()

    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    def test_ensure_initialized_once(self, mock_aip) -> None:
        p = self._make_provider()
        p._ensure_initialized()
        p._ensure_initialized()
        mock_aip.init.assert_called_once()

    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    def test_get_model_with_system(self, mock_gm, mock_aip) -> None:
        p = self._make_provider()
        p._get_model("gemini", system_instruction="Be helpful")
        mock_gm.assert_called_once_with("gemini", system_instruction="Be helpful")

    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    def test_get_model_without_system(self, mock_gm, mock_aip) -> None:
        p = self._make_provider()
        p._get_model("gemini", system_instruction=None)
        mock_gm.assert_called_once_with("gemini")

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    async def test_complete(self, mock_gm_cls, mock_aip) -> None:
        p = self._make_provider()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Answer"
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=10, candidates_token_count=5, total_token_count=15
        )
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_gm_cls.return_value = mock_model

        msgs = [
            Message(role=MessageRole.SYSTEM, content="Sys"),
            Message(role=MessageRole.USER, content="Q"),
            Message(role=MessageRole.ASSISTANT, content="A"),
        ]
        result = await p.complete(msgs, model="")
        assert result.content == "Answer"
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    async def test_complete_error(self, mock_gm_cls, mock_aip) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(side_effect=RuntimeError("err"))
        mock_gm_cls.return_value = mock_model

        with pytest.raises(ProviderError):
            await p.complete(
                [Message(role=MessageRole.USER, content="Q")], model=""
            )

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    async def test_stream(self, mock_gm_cls, mock_aip) -> None:
        p = self._make_provider()
        mock_model = MagicMock()

        # async iterator for stream
        async def _stream():
            for text in ["Hello", " World"]:
                chunk = MagicMock()
                chunk.text = text
                yield chunk

        mock_model.generate_content_async = AsyncMock(return_value=_stream())
        mock_gm_cls.return_value = mock_model

        chunks = []
        async for c in p.stream(
            [Message(role=MessageRole.USER, content="Q")], model=""
        ):
            chunks.append(c)
        assert len(chunks) == 2

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    @patch("cs_risk_agent.ai.providers.gcp_vertex.GenerativeModel")
    async def test_stream_error(self, mock_gm_cls, mock_aip) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(side_effect=RuntimeError("err"))
        mock_gm_cls.return_value = mock_model

        with pytest.raises(ProviderError):
            async for _ in p.stream(
                [Message(role=MessageRole.USER, content="Q")], model=""
            ):
                pass

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    async def test_embed(self, mock_aip) -> None:
        p = self._make_provider()
        p._initialized = True  # skip init

        mock_emb_model = MagicMock()
        mock_result = [MagicMock(values=[0.1, 0.2]), MagicMock(values=[0.3, 0.4])]
        mock_emb_model.get_embeddings.return_value = mock_result

        with patch(
            "vertexai.language_models.TextEmbeddingModel"
        ) as mock_tem:
            mock_tem.from_pretrained.return_value = mock_emb_model
            result = await p.embed(["a", "b"], model="")
            assert len(result.embeddings) == 2

    @pytest.mark.asyncio
    @patch("cs_risk_agent.ai.providers.gcp_vertex.aiplatform")
    async def test_embed_error(self, mock_aip) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        p._initialized = True

        with patch(
            "vertexai.language_models.TextEmbeddingModel"
        ) as mock_tem:
            mock_tem.from_pretrained.side_effect = RuntimeError("err")
            with pytest.raises(ProviderError):
                await p.embed(["a"], model="")


# ---------------------------------------------------------------------------
# vLLM Local
# ---------------------------------------------------------------------------


class TestVLLMLocal:
    """VLLMLocalProvider テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.base_url = "http://localhost:8080"
        settings.model = "llama-3"
        from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider

        return VLLMLocalProvider(settings=settings)

    def test_name_and_available(self) -> None:
        p = self._make_provider()
        assert p.name == "vllm"
        assert p.is_available is True

    def test_get_client_creates_once(self) -> None:
        p = self._make_provider()
        c1 = p._get_client()
        c2 = p._get_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        p = self._make_provider()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client

        result = await p.complete(
            [Message(role=MessageRole.USER, content="Q")], model=""
        )
        assert result.content == "Hi"
        assert result.usage.total_tokens == 8

    @pytest.mark.asyncio
    async def test_complete_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("fail"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            await p.complete(
                [Message(role=MessageRole.USER, content="Q")], model="m"
            )

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        p = self._make_provider()

        class FakeStreamResponse:
            async def aiter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"Hel"},"finish_reason":null}]}'
                yield 'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}'
                yield "data: [DONE]"

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=FakeStreamResponse())
        p._client = mock_client

        chunks = []
        async for c in p.stream(
            [Message(role=MessageRole.USER, content="Q")], model=""
        ):
            chunks.append(c)
        assert len(chunks) == 2
        assert chunks[0].content == "Hel"

    @pytest.mark.asyncio
    async def test_stream_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            async for _ in p.stream(
                [Message(role=MessageRole.USER, content="Q")], model=""
            ):
                pass

    @pytest.mark.asyncio
    async def test_embed(self) -> None:
        p = self._make_provider()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1]}, {"embedding": [0.2]}],
            "usage": {"prompt_tokens": 4, "total_tokens": 4},
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        p._client = mock_client

        result = await p.embed(["a", "b"], model="")
        assert len(result.embeddings) == 2
        assert result.usage.prompt_tokens == 4

    @pytest.mark.asyncio
    async def test_embed_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            await p.embed(["a"], model="m")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        p._client = mock_client
        await p.close()
        mock_client.aclose.assert_awaited_once()
        assert p._client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self) -> None:
        p = self._make_provider()
        await p.close()  # no error


# ---------------------------------------------------------------------------
# Ollama Local
# ---------------------------------------------------------------------------


class TestOllamaLocal:
    """OllamaLocalProvider テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.base_url = "http://localhost:11434"
        settings.cost_effective_model = "llama3.1:8b"
        from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider

        return OllamaLocalProvider(settings=settings)

    def test_name_and_available(self) -> None:
        p = self._make_provider()
        assert p.name == "ollama"
        assert p.is_available is True

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value={
            "message": {"content": "Answer"},
            "prompt_eval_count": 10,
            "eval_count": 5,
        })
        p._client = mock_client

        result = await p.complete(
            [Message(role=MessageRole.USER, content="Q")], model=""
        )
        assert result.content == "Answer"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            await p.complete(
                [Message(role=MessageRole.USER, content="Q")], model="m"
            )

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        p = self._make_provider()

        async def _stream_response():
            yield {"message": {"content": "Hello"}, "done": False}
            yield {"message": {"content": " World"}, "done": True}

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=_stream_response())
        p._client = mock_client

        chunks = []
        async for c in p.stream(
            [Message(role=MessageRole.USER, content="Q")], model=""
        ):
            chunks.append(c)
        assert len(chunks) == 2
        assert chunks[0].finish_reason is None
        assert chunks[1].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            async for _ in p.stream(
                [Message(role=MessageRole.USER, content="Q")], model=""
            ):
                pass

    @pytest.mark.asyncio
    async def test_embed(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.embeddings = AsyncMock(
            side_effect=[
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]},
            ]
        )
        p._client = mock_client

        result = await p.embed(["a", "b"], model="")
        assert len(result.embeddings) == 2

    @pytest.mark.asyncio
    async def test_embed_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.embeddings = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            await p.embed(["a"], model="m")

    @pytest.mark.asyncio
    async def test_health_check_ok(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.list = AsyncMock(return_value={"models": []})
        p._client = mock_client

        assert await p.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_fail(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.list = AsyncMock(side_effect=RuntimeError("down"))
        p._client = mock_client

        assert await p.health_check() is False


# ---------------------------------------------------------------------------
# Azure Foundry
# ---------------------------------------------------------------------------


class TestAzureFoundry:
    """AzureFoundryProvider テスト."""

    def _make_provider(self):
        settings = MagicMock()
        settings.is_configured = True
        settings.endpoint = "https://test.openai.azure.com"
        settings.api_key = "test-key"
        settings.sota_deployment = "gpt-4o"
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider

        return AzureFoundryProvider(settings=settings)

    def test_name_and_available(self) -> None:
        p = self._make_provider()
        assert p.name == "azure"
        assert p.is_available is True

    def test_get_client_unavailable(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.core.exceptions import ProviderUnavailableError

        settings = MagicMock()
        settings.is_configured = False
        p = AzureFoundryProvider(settings=settings)
        with pytest.raises(ProviderUnavailableError):
            p._get_client()

    @patch("cs_risk_agent.ai.providers.azure_foundry.ChatCompletionsClient")
    @patch("cs_risk_agent.ai.providers.azure_foundry.AzureKeyCredential")
    def test_get_client_creates_once(self, mock_cred, mock_cc) -> None:
        p = self._make_provider()
        c1 = p._get_client()
        c2 = p._get_client()
        assert c1 is c2
        mock_cc.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.model = "gpt-4o"
        mock_choice = MagicMock()
        mock_choice.message.content = "Result"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_client.complete = AsyncMock(return_value=mock_response)
        p._client = mock_client

        msgs = [
            Message(role=MessageRole.SYSTEM, content="Sys"),
            Message(role=MessageRole.USER, content="Q"),
            Message(role=MessageRole.ASSISTANT, content="A"),
        ]
        result = await p.complete(msgs, model="")
        assert result.content == "Result"
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            await p.complete(
                [Message(role=MessageRole.USER, content="Q")], model="m"
            )

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        p = self._make_provider()

        async def _updates():
            u1 = MagicMock()
            u1.choices = [MagicMock()]
            u1.choices[0].delta.content = "Hello"
            u1.choices[0].finish_reason = None
            yield u1
            u2 = MagicMock()
            u2.choices = [MagicMock()]
            u2.choices[0].delta.content = " World"
            u2.choices[0].finish_reason = "stop"
            yield u2

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=_updates())
        p._client = mock_client

        chunks = []
        async for c in p.stream(
            [Message(role=MessageRole.USER, content="Q")], model=""
        ):
            chunks.append(c)
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_stream_error(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=RuntimeError("err"))
        p._client = mock_client

        with pytest.raises(ProviderError):
            async for _ in p.stream(
                [Message(role=MessageRole.USER, content="Q")], model=""
            ):
                pass

    @pytest.mark.asyncio
    async def test_embed_raises(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderError

        p = self._make_provider()
        with pytest.raises(ProviderError, match="Embedding not yet implemented"):
            await p.embed(["a"], model="m")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        p = self._make_provider()
        mock_client = AsyncMock()
        p._client = mock_client
        await p.close()
        mock_client.close.assert_awaited_once()
        assert p._client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self) -> None:
        p = self._make_provider()
        await p.close()  # no error


# ---------------------------------------------------------------------------
# Helper function coverage
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """ヘルパー関数テスト."""

    def test_to_bedrock_messages(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import _to_bedrock_messages

        msgs = [
            Message(role=MessageRole.SYSTEM, content="sys"),
            Message(role=MessageRole.USER, content="hi"),
            Message(role=MessageRole.ASSISTANT, content="hello"),
        ]
        sys_prompt, bedrock_msgs = _to_bedrock_messages(msgs)
        assert sys_prompt == "sys"
        assert len(bedrock_msgs) == 2

    def test_to_vertex_contents(self) -> None:
        from cs_risk_agent.ai.providers.gcp_vertex import _to_vertex_contents

        msgs = [
            Message(role=MessageRole.SYSTEM, content="sys"),
            Message(role=MessageRole.USER, content="hi"),
            Message(role=MessageRole.ASSISTANT, content="hello"),
        ]
        sys_instr, contents = _to_vertex_contents(msgs)
        assert sys_instr == "sys"
        assert len(contents) == 2

    def test_to_ollama_messages(self) -> None:
        from cs_risk_agent.ai.providers.ollama_local import _to_ollama_messages

        msgs = [Message(role=MessageRole.USER, content="hi")]
        result = _to_ollama_messages(msgs)
        assert result == [{"role": "user", "content": "hi"}]

    def test_to_azure_message(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import _to_azure_message

        sys_msg = _to_azure_message(Message(role=MessageRole.SYSTEM, content="s"))
        user_msg = _to_azure_message(Message(role=MessageRole.USER, content="u"))
        asst_msg = _to_azure_message(Message(role=MessageRole.ASSISTANT, content="a"))
        assert sys_msg is not None
        assert user_msg is not None
        assert asst_msg is not None
