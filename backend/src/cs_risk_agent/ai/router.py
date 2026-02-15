"""Intelligent Model Router - フォールバック付きモデルルーティング.

デフォルトプロバイダーへのリクエストを試行し、失敗時にフォールバックチェーンに従って
次のプロバイダーに自動切り替えする。ハイブリッドモードではデータ分類に基づいて
ローカル/クラウドプロバイダーを選択する。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import structlog

from cs_risk_agent.ai.circuit_breaker import CircuitBreaker, UsageRecord
from cs_risk_agent.ai.cost_tracker import CostTracker
from cs_risk_agent.ai.model_tier import ModelTierManager
from cs_risk_agent.ai.provider import AIChunk, AIResponse, EmbeddingResponse, Message
from cs_risk_agent.ai.registry import ProviderRegistry, get_provider_registry
from cs_risk_agent.config import AIMode, ModelTier, get_settings
from cs_risk_agent.core.exceptions import (
    AllProvidersFailedError,
    BudgetExceededError,
    ProviderError,
)

logger = structlog.get_logger(__name__)


class AIModelRouter:
    """インテリジェントAIモデルルーター.

    機能:
    - デフォルトプロバイダーへのリクエスト送信
    - フォールバックチェーンによる自動切り替え
    - ハイブリッドモードでのデータ分類ベースルーティング
    - サーキットブレーカーによる予算管理
    - コスト追跡
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        tier_manager: ModelTierManager | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self._registry = registry or get_provider_registry()
        self._tier_manager = tier_manager or ModelTierManager()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._cost_tracker = cost_tracker or CostTracker(self._tier_manager)
        self._settings = get_settings()

    def _resolve_provider_name(
        self,
        provider: str | None = None,
        data_classification: str | None = None,
    ) -> str:
        """使用するプロバイダー名を決定.

        Args:
            provider: 明示的に指定されたプロバイダー名
            data_classification: データ分類（ハイブリッドモード用）

        Returns:
            str: 使用するプロバイダー名
        """
        if provider:
            return provider

        # ハイブリッドモード: データ分類に基づいてルーティング
        if self._settings.ai.mode == AIMode.HYBRID and data_classification:
            for rule in self._settings.hybrid_rules:
                if rule.data_classification == data_classification:
                    logger.info(
                        "router.hybrid_routing",
                        classification=data_classification,
                        routed_to=rule.provider,
                    )
                    return rule.provider

        # ローカルモード: ローカルプロバイダーのみ使用
        if self._settings.ai.mode == AIMode.LOCAL:
            return "ollama"

        return self._settings.ai.default_provider

    def _get_fallback_chain(self, primary: str) -> list[str]:
        """フォールバックチェーンを取得（primary を先頭に）."""
        chain = self._settings.ai.fallback_providers
        if primary in chain:
            chain = [primary] + [p for p in chain if p != primary]
        else:
            chain = [primary] + chain
        return chain

    async def complete(
        self,
        messages: list[Message],
        *,
        provider: str | None = None,
        tier: ModelTier = ModelTier.SOTA,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        data_classification: str | None = None,
        user_id: str = "",
        **kwargs: Any,
    ) -> AIResponse:
        """チャット完了 - フォールバック付き.

        Args:
            messages: チャットメッセージ
            provider: プロバイダー名（省略時はルーティングロジックで決定）
            tier: モデルティア
            model: 明示的モデル指定（省略時はティアから解決）
            temperature: 生成温度
            max_tokens: 最大トークン数
            data_classification: データ分類（ハイブリッド用）
            user_id: ユーザーID
            **kwargs: プロバイダー固有パラメータ

        Returns:
            AIResponse: 応答

        Raises:
            BudgetExceededError: 予算超過
            AllProvidersFailedError: 全プロバイダー失敗
        """
        # 予算チェック
        await self._circuit_breaker.check_budget()

        primary = self._resolve_provider_name(provider, data_classification)
        chain = self._get_fallback_chain(primary)
        request_id = str(uuid.uuid4())
        errors: list[str] = []

        for provider_name in chain:
            try:
                ai_provider = self._registry.get(provider_name)
                if not ai_provider.is_available:
                    logger.debug("router.provider_unavailable", provider=provider_name)
                    continue

                # モデルID解決
                model_id = model or self._tier_manager.get_model_id(provider_name, tier)

                logger.info(
                    "router.attempting",
                    provider=provider_name,
                    model=model_id,
                    tier=tier.value,
                    request_id=request_id,
                )

                response = await ai_provider.complete(
                    messages=messages,
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                # コスト記録
                cost_entry = self._cost_tracker.record(
                    provider=provider_name,
                    model=model_id,
                    tier=tier,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    user_id=user_id,
                    request_id=request_id,
                )

                # サーキットブレーカーに記録
                await self._circuit_breaker.record_usage(
                    UsageRecord(
                        timestamp=datetime.now(timezone.utc),
                        provider=provider_name,
                        model=model_id,
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                        cost_usd=cost_entry.cost_usd,
                        request_id=request_id,
                    )
                )

                logger.info(
                    "router.success",
                    provider=provider_name,
                    model=model_id,
                    tokens=response.usage.total_tokens,
                    cost_usd=cost_entry.cost_usd,
                    request_id=request_id,
                )

                return response

            except BudgetExceededError:
                raise
            except (ProviderError, Exception) as e:
                error_msg = f"{provider_name}: {e}"
                errors.append(error_msg)
                logger.warning(
                    "router.provider_failed",
                    provider=provider_name,
                    error=str(e),
                    request_id=request_id,
                    remaining_providers=len(chain) - chain.index(provider_name) - 1,
                )
                continue

        raise AllProvidersFailedError(chain)

    async def stream(
        self,
        messages: list[Message],
        *,
        provider: str | None = None,
        tier: ModelTier = ModelTier.SOTA,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        data_classification: str | None = None,
        user_id: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[AIChunk]:
        """ストリーミングチャット完了 - フォールバック付き."""
        await self._circuit_breaker.check_budget()

        primary = self._resolve_provider_name(provider, data_classification)
        chain = self._get_fallback_chain(primary)
        request_id = str(uuid.uuid4())

        for provider_name in chain:
            try:
                ai_provider = self._registry.get(provider_name)
                if not ai_provider.is_available:
                    continue

                model_id = model or self._tier_manager.get_model_id(provider_name, tier)

                logger.info(
                    "router.stream.attempting",
                    provider=provider_name,
                    model=model_id,
                    request_id=request_id,
                )

                async for chunk in ai_provider.stream(
                    messages=messages,
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ):
                    yield chunk

                return

            except BudgetExceededError:
                raise
            except (ProviderError, Exception) as e:
                logger.warning(
                    "router.stream.provider_failed",
                    provider=provider_name,
                    error=str(e),
                    request_id=request_id,
                )
                continue

        raise AllProvidersFailedError(chain)

    async def embed(
        self,
        texts: list[str],
        *,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """埋め込み生成 - フォールバック付き."""
        primary = self._resolve_provider_name(provider)
        chain = self._get_fallback_chain(primary)

        for provider_name in chain:
            try:
                ai_provider = self._registry.get(provider_name)
                if not ai_provider.is_available:
                    continue
                return await ai_provider.embed(texts, model=model or "", **kwargs)
            except (ProviderError, Exception) as e:
                logger.warning("router.embed.failed", provider=provider_name, error=str(e))
                continue

        raise AllProvidersFailedError(chain)

    def get_status(self) -> dict[str, Any]:
        """ルーター全体のステータス取得."""
        return {
            "mode": self._settings.ai.mode.value,
            "default_provider": self._settings.ai.default_provider,
            "fallback_chain": self._settings.ai.fallback_providers,
            "providers": self._registry.to_dict(),
            "budget": self._circuit_breaker.to_dict(),
            "cost": self._cost_tracker.to_dict(),
            "model_tiers": self._tier_manager.to_dict(),
        }


# シングルトンインスタンス
_router: AIModelRouter | None = None


def get_ai_router() -> AIModelRouter:
    """AIModelRouterシングルトン取得."""
    global _router
    if _router is None:
        _router = AIModelRouter()
    return _router
