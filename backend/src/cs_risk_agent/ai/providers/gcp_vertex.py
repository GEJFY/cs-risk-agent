"""GCP Vertex AI プロバイダー実装.

google-cloud-aiplatform を使用して Vertex AI に接続する。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import structlog
from google.cloud import aiplatform
from vertexai.generative_models import (
    Content,
    GenerativeModel,
    Part,
)

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIProvider,
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)
from cs_risk_agent.config import GCPSettings, get_settings
from cs_risk_agent.core.exceptions import ProviderError, ProviderUnavailableError

logger = structlog.get_logger(__name__)


def _to_vertex_contents(messages: list[Message]) -> tuple[str | None, list[Content]]:
    """Message リストを Vertex AI Content 形式に変換."""
    system_instruction: str | None = None
    contents: list[Content] = []

    for msg in messages:
        if msg.role == MessageRole.SYSTEM:
            system_instruction = msg.content
        elif msg.role == MessageRole.USER:
            contents.append(Content(role="user", parts=[Part.from_text(msg.content)]))
        elif msg.role == MessageRole.ASSISTANT:
            contents.append(Content(role="model", parts=[Part.from_text(msg.content)]))

    return system_instruction, contents


class GCPVertexProvider(AIProvider):
    """GCP Vertex AI プロバイダー."""

    def __init__(self, settings: GCPSettings | None = None) -> None:
        self._settings = settings or get_settings().gcp
        self._initialized = False

    @property
    def name(self) -> str:
        return "gcp"

    @property
    def is_available(self) -> bool:
        return self._settings.is_configured

    def _ensure_initialized(self) -> None:
        """Vertex AI 初期化."""
        if not self.is_available:
            raise ProviderUnavailableError("gcp", "GCP project not configured")
        if not self._initialized:
            aiplatform.init(
                project=self._settings.project_id,
                location=self._settings.location,
            )
            self._initialized = True

    def _get_model(self, model: str, system_instruction: str | None = None) -> GenerativeModel:
        """GenerativeModel インスタンス取得."""
        self._ensure_initialized()
        model_id = model or self._settings.sota_model
        kwargs: dict[str, Any] = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        return GenerativeModel(model_id, **kwargs)

    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AIResponse:
        """Vertex AI での同期チャット完了."""
        model_id = model or self._settings.sota_model
        system_instruction, contents = _to_vertex_contents(messages)

        try:
            gen_model = self._get_model(model_id, system_instruction)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            response = await gen_model.generate_content_async(
                contents,
                generation_config=generation_config,
            )

            # 使用量取得
            usage_metadata = getattr(response, "usage_metadata", None)
            usage = TokenUsage(
                prompt_tokens=getattr(usage_metadata, "prompt_token_count", 0),
                completion_tokens=getattr(usage_metadata, "candidates_token_count", 0),
                total_tokens=getattr(usage_metadata, "total_token_count", 0),
            )

            return AIResponse(
                content=response.text,
                model=model_id,
                provider=self.name,
                usage=usage,
                finish_reason="stop",
            )

        except Exception as e:
            logger.error("gcp.complete.error", error=str(e), model=model_id)
            raise ProviderError("gcp", str(e)) from e

    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """Vertex AI でのストリーミングチャット完了."""
        model_id = model or self._settings.sota_model
        system_instruction, contents = _to_vertex_contents(messages)

        try:
            gen_model = self._get_model(model_id, system_instruction)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            response = await gen_model.generate_content_async(
                contents,
                generation_config=generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield AIChunk(
                        content=chunk.text,
                        model=model_id,
                        provider=self.name,
                    )

        except Exception as e:
            logger.error("gcp.stream.error", error=str(e), model=model_id)
            raise ProviderError("gcp", str(e)) from e

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Vertex AI での埋め込み生成."""
        from vertexai.language_models import TextEmbeddingModel

        self._ensure_initialized()
        embed_model_id = model or "text-embedding-005"

        try:
            embed_model = TextEmbeddingModel.from_pretrained(embed_model_id)
            embeddings_result = embed_model.get_embeddings(texts)

            embeddings = [e.values for e in embeddings_result]

            return EmbeddingResponse(
                embeddings=embeddings,
                model=embed_model_id,
                provider=self.name,
                usage=TokenUsage(),
            )

        except Exception as e:
            logger.error("gcp.embed.error", error=str(e), model=embed_model_id)
            raise ProviderError("gcp", str(e)) from e
