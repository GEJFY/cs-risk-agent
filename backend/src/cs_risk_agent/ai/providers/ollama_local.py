"""Ollama ローカルLLMプロバイダー実装.

ローカル環境で動作するOllamaに接続し、オンプレミスでのLLM推論を実現する。
機密データ処理時のハイブリッドモードで使用。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import structlog
from ollama import AsyncClient

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIProvider,
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)
from cs_risk_agent.config import OllamaSettings, get_settings
from cs_risk_agent.core.exceptions import ProviderError

logger = structlog.get_logger(__name__)


def _to_ollama_messages(messages: list[Message]) -> list[dict[str, str]]:
    """Message リストを Ollama 形式に変換."""
    return [{"role": msg.role.value, "content": msg.content} for msg in messages]


class OllamaLocalProvider(AIProvider):
    """Ollama ローカルLLMプロバイダー."""

    def __init__(self, settings: OllamaSettings | None = None) -> None:
        self._settings = settings or get_settings().ollama
        self._client: AsyncClient | None = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        return True  # ローカルなので常に設定上は利用可能

    def _get_client(self) -> AsyncClient:
        """Ollamaクライアント取得."""
        if self._client is None:
            self._client = AsyncClient(host=self._settings.base_url)
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
        """Ollama での同期チャット完了."""
        client = self._get_client()
        model_id = model or self._settings.cost_effective_model
        ollama_msgs = _to_ollama_messages(messages)

        try:
            response = await client.chat(
                model=model_id,
                messages=ollama_msgs,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            # トークン使用量の推定
            usage = TokenUsage(
                prompt_tokens=response.get("prompt_eval_count", 0),
                completion_tokens=response.get("eval_count", 0),
                total_tokens=(
                    response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
                ),
            )

            return AIResponse(
                content=response["message"]["content"],
                model=model_id,
                provider=self.name,
                usage=usage,
                finish_reason="stop",
            )

        except Exception as e:
            logger.error("ollama.complete.error", error=str(e), model=model_id)
            raise ProviderError("ollama", str(e)) from e

    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """Ollama でのストリーミングチャット完了."""
        client = self._get_client()
        model_id = model or self._settings.cost_effective_model
        ollama_msgs = _to_ollama_messages(messages)

        try:
            stream = await client.chat(
                model=model_id,
                messages=ollama_msgs,
                stream=True,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            async for chunk in stream:
                content = chunk["message"]["content"]
                if content:
                    yield AIChunk(
                        content=content,
                        model=model_id,
                        provider=self.name,
                        finish_reason="stop" if chunk.get("done") else None,
                    )

        except Exception as e:
            logger.error("ollama.stream.error", error=str(e), model=model_id)
            raise ProviderError("ollama", str(e)) from e

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Ollama での埋め込み生成."""
        client = self._get_client()
        embed_model = model or "nomic-embed-text"

        try:
            embeddings: list[list[float]] = []
            for text in texts:
                response = await client.embeddings(model=embed_model, prompt=text)
                embeddings.append(response["embedding"])

            return EmbeddingResponse(
                embeddings=embeddings,
                model=embed_model,
                provider=self.name,
                usage=TokenUsage(),
            )

        except Exception as e:
            logger.error("ollama.embed.error", error=str(e), model=embed_model)
            raise ProviderError("ollama", str(e)) from e

    async def health_check(self) -> bool:
        """Ollama ヘルスチェック."""
        try:
            client = self._get_client()
            await client.list()
            return True
        except Exception:
            return False
