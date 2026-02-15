"""vLLM ローカルLLMプロバイダー実装.

OpenAI互換APIを持つvLLMサーバーに接続する。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
import structlog

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIProvider,
    AIResponse,
    EmbeddingResponse,
    Message,
    TokenUsage,
)
from cs_risk_agent.config import VLLMSettings, get_settings
from cs_risk_agent.core.exceptions import ProviderError

logger = structlog.get_logger(__name__)


class VLLMLocalProvider(AIProvider):
    """vLLM ローカルLLMプロバイダー (OpenAI互換API)."""

    def __init__(self, settings: VLLMSettings | None = None) -> None:
        self._settings = settings or get_settings().vllm
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "vllm"

    @property
    def is_available(self) -> bool:
        return True

    def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアント取得."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=120.0,
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
        """vLLM での同期チャット完了 (OpenAI互換)."""
        client = self._get_client()
        model_id = model or self._settings.model

        payload = {
            "model": model_id,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=model_id,
                provider=self.name,
                usage=usage,
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
            )

        except Exception as e:
            logger.error("vllm.complete.error", error=str(e), model=model_id)
            raise ProviderError("vllm", str(e)) from e

    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """vLLM でのストリーミングチャット完了."""
        client = self._get_client()
        model_id = model or self._settings.model

        payload = {
            "model": model_id,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with client.stream("POST", "/v1/chat/completions", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield AIChunk(
                                content=content,
                                model=model_id,
                                provider=self.name,
                                finish_reason=data["choices"][0].get("finish_reason"),
                            )

        except Exception as e:
            logger.error("vllm.stream.error", error=str(e), model=model_id)
            raise ProviderError("vllm", str(e)) from e

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """vLLM での埋め込み生成."""
        client = self._get_client()
        embed_model = model or self._settings.model

        try:
            response = await client.post(
                "/v1/embeddings",
                json={"model": embed_model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()

            embeddings = [item["embedding"] for item in data["data"]]
            usage_data = data.get("usage", {})

            return EmbeddingResponse(
                embeddings=embeddings,
                model=embed_model,
                provider=self.name,
                usage=TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                ),
            )

        except Exception as e:
            logger.error("vllm.embed.error", error=str(e), model=embed_model)
            raise ProviderError("vllm", str(e)) from e

    async def close(self) -> None:
        """クライアントをクローズ."""
        if self._client:
            await self._client.aclose()
            self._client = None
