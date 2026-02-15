"""AI Provider インターフェースおよび各プロバイダーのカバレッジテスト."""

from __future__ import annotations

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
# データクラステスト
# ---------------------------------------------------------------------------


class TestMessageRole:
    """MessageRole 列挙型テスト."""

    def test_values(self) -> None:
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"


class TestMessage:
    """Message データクラステスト."""

    def test_create(self) -> None:
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"


class TestTokenUsage:
    """TokenUsage データクラステスト."""

    def test_defaults(self) -> None:
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom(self) -> None:
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.total_tokens == 150

    def test_cost_usd(self) -> None:
        usage = TokenUsage()
        assert usage.cost_usd == 0.0


class TestAIResponse:
    """AIResponse データクラステスト."""

    def test_create(self) -> None:
        usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        response = AIResponse(
            content="Hello!",
            model="gpt-4o",
            provider="azure",
            usage=usage,
        )
        assert response.content == "Hello!"
        assert response.finish_reason == "stop"
        assert response.metadata == {}

    def test_with_metadata(self) -> None:
        usage = TokenUsage()
        response = AIResponse(
            content="test",
            model="m",
            provider="p",
            usage=usage,
            finish_reason="length",
            metadata={"key": "value"},
        )
        assert response.finish_reason == "length"
        assert response.metadata == {"key": "value"}


class TestAIChunk:
    """AIChunk データクラステスト."""

    def test_create(self) -> None:
        chunk = AIChunk(content="Hi", model="m", provider="p")
        assert chunk.content == "Hi"
        assert chunk.finish_reason is None

    def test_with_finish(self) -> None:
        chunk = AIChunk(content="", model="m", provider="p", finish_reason="stop")
        assert chunk.finish_reason == "stop"


class TestEmbeddingResponse:
    """EmbeddingResponse データクラステスト."""

    def test_create(self) -> None:
        usage = TokenUsage()
        resp = EmbeddingResponse(
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            model="text-embed",
            provider="azure",
            usage=usage,
        )
        assert len(resp.embeddings) == 2
        assert resp.model == "text-embed"


# ---------------------------------------------------------------------------
# Azure Foundry プロバイダーテスト
# ---------------------------------------------------------------------------


class TestAzureFoundryProvider:
    """Azure AI Foundry プロバイダーのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider

        assert AzureFoundryProvider is not None

    def test_name(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings

        provider = AzureFoundryProvider(AzureSettings())
        assert provider.name == "azure"

    def test_not_available_without_config(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings

        provider = AzureFoundryProvider(AzureSettings(endpoint="", api_key=""))
        assert provider.is_available is False

    def test_available_with_config(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings

        provider = AzureFoundryProvider(
            AzureSettings(endpoint="https://test.openai.azure.com", api_key="test-key")
        )
        assert provider.is_available is True

    def test_get_client_raises_when_unavailable(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings
        from cs_risk_agent.core.exceptions import ProviderUnavailableError

        provider = AzureFoundryProvider(AzureSettings())
        with pytest.raises(ProviderUnavailableError):
            provider._get_client()

    def test_to_azure_message(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import _to_azure_message

        sys_msg = _to_azure_message(Message(role=MessageRole.SYSTEM, content="system"))
        user_msg = _to_azure_message(Message(role=MessageRole.USER, content="hello"))
        asst_msg = _to_azure_message(Message(role=MessageRole.ASSISTANT, content="hi"))
        assert sys_msg is not None
        assert user_msg is not None
        assert asst_msg is not None

    @pytest.mark.asyncio
    async def test_embed_not_implemented(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings
        from cs_risk_agent.core.exceptions import ProviderError

        provider = AzureFoundryProvider(
            AzureSettings(endpoint="https://test.openai.azure.com", api_key="key")
        )
        with pytest.raises(ProviderError, match="Embedding not yet implemented"):
            await provider.embed(["text"], "model")

    @pytest.mark.asyncio
    async def test_close_no_client(self) -> None:
        from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
        from cs_risk_agent.config import AzureSettings

        provider = AzureFoundryProvider(AzureSettings())
        await provider.close()  # should not raise


# ---------------------------------------------------------------------------
# Ollama プロバイダーテスト
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    """Ollama ローカル LLM プロバイダーのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider

        assert OllamaLocalProvider is not None

    def test_name(self) -> None:
        from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider
        from cs_risk_agent.config import OllamaSettings

        provider = OllamaLocalProvider(OllamaSettings())
        assert provider.name == "ollama"

    def test_always_available(self) -> None:
        from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider
        from cs_risk_agent.config import OllamaSettings

        provider = OllamaLocalProvider(OllamaSettings())
        assert provider.is_available is True

    def test_to_ollama_messages(self) -> None:
        from cs_risk_agent.ai.providers.ollama_local import _to_ollama_messages

        messages = [
            Message(role=MessageRole.SYSTEM, content="Be helpful"),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        result = _to_ollama_messages(messages)
        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "Be helpful"}
        assert result[1] == {"role": "user", "content": "Hello"}


# ---------------------------------------------------------------------------
# AWS Bedrock プロバイダーテスト
# ---------------------------------------------------------------------------


class TestAWSBedrockProvider:
    """AWS Bedrock プロバイダーのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider

        assert AWSBedrockProvider is not None

    def test_name(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider
        from cs_risk_agent.config import AWSSettings

        provider = AWSBedrockProvider(AWSSettings())
        assert provider.name == "aws"

    def test_not_available_without_keys(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider
        from cs_risk_agent.config import AWSSettings

        provider = AWSBedrockProvider(AWSSettings())
        assert provider.is_available is False

    def test_available_with_keys(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider
        from cs_risk_agent.config import AWSSettings

        provider = AWSBedrockProvider(
            AWSSettings(access_key_id="AKIA...", secret_access_key="secret")
        )
        assert provider.is_available is True

    def test_to_bedrock_messages(self) -> None:
        from cs_risk_agent.ai.providers.aws_bedrock import _to_bedrock_messages

        messages = [
            Message(role=MessageRole.SYSTEM, content="system prompt"),
            Message(role=MessageRole.USER, content="hello"),
            Message(role=MessageRole.ASSISTANT, content="hi"),
        ]
        system, bedrock_msgs = _to_bedrock_messages(messages)
        assert system == "system prompt"
        assert len(bedrock_msgs) == 2


# ---------------------------------------------------------------------------
# GCP Vertex プロバイダーテスト
# ---------------------------------------------------------------------------


class TestGCPVertexProvider:
    """GCP Vertex AI プロバイダーのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider

        assert GCPVertexProvider is not None

    def test_name(self) -> None:
        from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider
        from cs_risk_agent.config import GCPSettings

        provider = GCPVertexProvider(GCPSettings())
        assert provider.name == "gcp"

    def test_not_available_without_project(self) -> None:
        from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider
        from cs_risk_agent.config import GCPSettings

        provider = GCPVertexProvider(GCPSettings(project_id=""))
        assert provider.is_available is False


# ---------------------------------------------------------------------------
# vLLM プロバイダーテスト
# ---------------------------------------------------------------------------


class TestVLLMProvider:
    """vLLM プロバイダーのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider

        assert VLLMLocalProvider is not None

    def test_name(self) -> None:
        from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider
        from cs_risk_agent.config import VLLMSettings

        provider = VLLMLocalProvider(VLLMSettings())
        assert provider.name == "vllm"

    def test_always_available(self) -> None:
        from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider
        from cs_risk_agent.config import VLLMSettings

        provider = VLLMLocalProvider(VLLMSettings())
        assert provider.is_available is True

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider
        from cs_risk_agent.config import VLLMSettings

        provider = VLLMLocalProvider(VLLMSettings())
        await provider.close()  # should not raise
