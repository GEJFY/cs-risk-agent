"""AI Provider 抽象インターフェース - Provider Pattern 実装.

全てのAIプロバイダー（Azure, AWS, GCP, Ollama, vLLM）が
準拠すべき統一インターフェースを定義する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


class MessageRole(str, Enum):
    """メッセージロール."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """チャットメッセージ."""

    role: MessageRole
    content: str


@dataclass
class AIResponse:
    """AI応答レスポンス."""

    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIChunk:
    """ストリーミング応答チャンク."""

    content: str
    model: str
    provider: str
    finish_reason: str | None = None


@dataclass
class TokenUsage:
    """トークン使用量."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        """概算コスト（USD）- プロバイダー別に上書き可能."""
        return 0.0


@dataclass
class EmbeddingResponse:
    """埋め込みレスポンス."""

    embeddings: list[list[float]]
    model: str
    provider: str
    usage: TokenUsage


class AIProvider(ABC):
    """AIプロバイダー抽象基底クラス.

    全プロバイダーはこのインターフェースを実装する。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """プロバイダー名."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """プロバイダーが利用可能か."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AIResponse:
        """同期的にチャット完了リクエストを送信.

        Args:
            messages: チャットメッセージリスト
            model: 使用するモデルID
            temperature: 生成温度
            max_tokens: 最大トークン数
            **kwargs: プロバイダー固有パラメータ

        Returns:
            AIResponse: 応答
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """ストリーミングでチャット完了リクエストを送信.

        Args:
            messages: チャットメッセージリスト
            model: 使用するモデルID
            temperature: 生成温度
            max_tokens: 最大トークン数
            **kwargs: プロバイダー固有パラメータ

        Yields:
            AIChunk: 応答チャンク
        """
        ...

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """テキスト埋め込みベクトルを生成.

        Args:
            texts: 埋め込み対象テキストリスト
            model: 埋め込みモデルID
            **kwargs: プロバイダー固有パラメータ

        Returns:
            EmbeddingResponse: 埋め込みレスポンス
        """
        ...

    async def health_check(self) -> bool:
        """プロバイダーヘルスチェック."""
        try:
            response = await self.complete(
                messages=[Message(role=MessageRole.USER, content="ping")],
                model="",  # デフォルトモデル使用
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False
