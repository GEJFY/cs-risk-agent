"""AWS Bedrock プロバイダー実装.

boto3 bedrock-runtime を使用して AWS Bedrock に接続する。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import boto3
import structlog

from cs_risk_agent.ai.provider import (
    AIChunk,
    AIProvider,
    AIResponse,
    EmbeddingResponse,
    Message,
    MessageRole,
    TokenUsage,
)
from cs_risk_agent.config import AWSSettings, get_settings
from cs_risk_agent.core.exceptions import ProviderError, ProviderUnavailableError

logger = structlog.get_logger(__name__)


def _to_bedrock_messages(messages: list[Message]) -> tuple[str | None, list[dict[str, str]]]:
    """Message リストを Bedrock 形式に変換.

    Returns:
        (system_prompt, messages) のタプル
    """
    system_prompt: str | None = None
    bedrock_msgs: list[dict[str, str]] = []

    for msg in messages:
        if msg.role == MessageRole.SYSTEM:
            system_prompt = msg.content
        else:
            bedrock_msgs.append({
                "role": msg.role.value,
                "content": [{"type": "text", "text": msg.content}],
            })

    return system_prompt, bedrock_msgs


class AWSBedrockProvider(AIProvider):
    """AWS Bedrock プロバイダー."""

    def __init__(self, settings: AWSSettings | None = None) -> None:
        self._settings = settings or get_settings().aws
        self._client = None

    @property
    def name(self) -> str:
        return "aws"

    @property
    def is_available(self) -> bool:
        return self._settings.is_configured

    def _get_client(self) -> Any:
        """Bedrock Runtime クライアント取得."""
        if not self.is_available:
            raise ProviderUnavailableError("aws", "AWS credentials not configured")
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._settings.region,
                aws_access_key_id=self._settings.access_key_id,
                aws_secret_access_key=self._settings.secret_access_key,
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
        """AWS Bedrock での同期チャット完了."""
        client = self._get_client()
        model_id = model or self._settings.bedrock_sota_model
        system_prompt, bedrock_msgs = _to_bedrock_messages(messages)

        try:
            request_body: dict[str, Any] = {
                "messages": bedrock_msgs,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "anthropic_version": "bedrock-2023-05-31",
            }
            if system_prompt:
                request_body["system"] = system_prompt

            response = client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            result = json.loads(response["body"].read())
            content = ""
            if result.get("content"):
                content = result["content"][0].get("text", "")

            usage_data = result.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=(
                    usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
                ),
            )

            return AIResponse(
                content=content,
                model=model_id,
                provider=self.name,
                usage=usage,
                finish_reason=result.get("stop_reason", "stop"),
            )

        except Exception as e:
            logger.error("aws.complete.error", error=str(e), model=model_id)
            raise ProviderError("aws", str(e)) from e

    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """AWS Bedrock でのストリーミングチャット完了."""
        client = self._get_client()
        model_id = model or self._settings.bedrock_sota_model
        system_prompt, bedrock_msgs = _to_bedrock_messages(messages)

        try:
            request_body: dict[str, Any] = {
                "messages": bedrock_msgs,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "anthropic_version": "bedrock-2023-05-31",
            }
            if system_prompt:
                request_body["system"] = system_prompt

            response = client.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        data = json.loads(chunk["bytes"].decode())
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("text"):
                                yield AIChunk(
                                    content=delta["text"],
                                    model=model_id,
                                    provider=self.name,
                                )
                        elif data.get("type") == "message_stop":
                            yield AIChunk(
                                content="",
                                model=model_id,
                                provider=self.name,
                                finish_reason="stop",
                            )

        except Exception as e:
            logger.error("aws.stream.error", error=str(e), model=model_id)
            raise ProviderError("aws", str(e)) from e

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """AWS Bedrock での埋め込み生成."""
        client = self._get_client()
        embed_model = model or "amazon.titan-embed-text-v2:0"

        try:
            embeddings: list[list[float]] = []
            total_tokens = 0

            for text in texts:
                response = client.invoke_model(
                    modelId=embed_model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps({"inputText": text}),
                )
                result = json.loads(response["body"].read())
                embeddings.append(result["embedding"])
                total_tokens += result.get("inputTextTokenCount", 0)

            return EmbeddingResponse(
                embeddings=embeddings,
                model=embed_model,
                provider=self.name,
                usage=TokenUsage(prompt_tokens=total_tokens, total_tokens=total_tokens),
            )

        except Exception as e:
            logger.error("aws.embed.error", error=str(e), model=embed_model)
            raise ProviderError("aws", str(e)) from e
