"""Azure AI Foundry プロバイダー実装.

Azure AI Inference SDK を使用して Azure OpenAI Service に接続する。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import structlog
from azure.ai.inference.aio import ChatCompletionsClient
from azure.ai.inference.models import (
    ChatCompletions,
    ChatRequestMessage,
    StreamingChatCompletionsUpdate,
    SystemMessage,
    UserMessage,
    AssistantMessage,
)
from azure.core.credentials import AzureKeyCredential

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIProvider,
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)
from cs_risk_agent.config import AzureSettings, get_settings
from cs_risk_agent.core.exceptions import ProviderError, ProviderUnavailableError

logger = structlog.get_logger(__name__)


def _to_azure_message(msg: Message) -> ChatRequestMessage:
    """Message -> Azure ChatRequestMessage 変換."""
    if msg.role == MessageRole.SYSTEM:
        return SystemMessage(content=msg.content)
    elif msg.role == MessageRole.ASSISTANT:
        return AssistantMessage(content=msg.content)
    else:
        return UserMessage(content=msg.content)


class AzureFoundryProvider(AIProvider):
    """Azure AI Foundry プロバイダー."""

    def __init__(self, settings: AzureSettings | None = None) -> None:
        self._settings = settings or get_settings().azure
        self._client: ChatCompletionsClient | None = None

    @property
    def name(self) -> str:
        return "azure"

    @property
    def is_available(self) -> bool:
        return self._settings.is_configured

    def _get_client(self) -> ChatCompletionsClient:
        """クライアントを取得（遅延初期化）."""
        if not self.is_available:
            raise ProviderUnavailableError("azure", "API key or endpoint not configured")
        if self._client is None:
            self._client = ChatCompletionsClient(
                endpoint=self._settings.endpoint,
                credential=AzureKeyCredential(self._settings.api_key),
            )
        return self._client

    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AIResponse:
        """Azure AI での同期チャット完了."""
        client = self._get_client()
        azure_messages = [_to_azure_message(m) for m in messages]

        try:
            response: ChatCompletions = await client.complete(
                messages=azure_messages,
                model=model or self._settings.sota_deployment,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

            return AIResponse(
                content=response.choices[0].message.content or "",
                model=response.model or model,
                provider=self.name,
                usage=usage,
                finish_reason=response.choices[0].finish_reason or "stop",
            )

        except Exception as e:
            logger.error("azure.complete.error", error=str(e), model=model)
            raise ProviderError("azure", str(e)) from e

    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """Azure AI でのストリーミングチャット完了."""
        client = self._get_client()
        azure_messages = [_to_azure_message(m) for m in messages]

        try:
            response = await client.complete(
                messages=azure_messages,
                model=model or self._settings.sota_deployment,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for update in response:
                if update.choices and update.choices[0].delta.content:
                    yield AIChunk(
                        content=update.choices[0].delta.content,
                        model=model,
                        provider=self.name,
                        finish_reason=update.choices[0].finish_reason,
                    )

        except Exception as e:
            logger.error("azure.stream.error", error=str(e), model=model)
            raise ProviderError("azure", str(e)) from e

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Azure AI での埋め込み生成（未実装プレースホルダー）."""
        raise ProviderError("azure", "Embedding not yet implemented for Azure Foundry")

    async def close(self) -> None:
        """クライアントをクローズ."""
        if self._client:
            await self._client.close()
            self._client = None
