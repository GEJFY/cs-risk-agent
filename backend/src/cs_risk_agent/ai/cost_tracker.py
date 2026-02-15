"""コスト追跡・予算管理モジュール.

AIリクエストごとのトークン消費・コストを追跡し、
プロバイダー/モデル/ユーザー別の利用統計を提供する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from cs_risk_agent.ai.model_tier import ModelTierManager
from cs_risk_agent.config import ModelTier

logger = structlog.get_logger(__name__)


@dataclass
class CostEntry:
    """コストエントリ."""

    timestamp: datetime
    provider: str
    model: str
    tier: ModelTier
    input_tokens: int
    output_tokens: int
    cost_usd: float
    user_id: str = ""
    request_id: str = ""
    operation: str = "complete"


@dataclass
class CostSummary:
    """コストサマリー."""

    total_cost_usd: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    by_provider: dict[str, float]
    by_model: dict[str, float]
    by_tier: dict[str, float]
    by_user: dict[str, float]
    period_start: datetime
    period_end: datetime


class CostTracker:
    """コスト追跡マネージャー.

    全AIリクエストのコストを記録し、集計・分析を提供する。
    """

    def __init__(self, tier_manager: ModelTierManager | None = None) -> None:
        self._tier_manager = tier_manager or ModelTierManager()
        self._entries: list[CostEntry] = []

    def calculate_cost(
        self,
        provider: str,
        tier: ModelTier,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """コスト計算.

        Args:
            provider: プロバイダー名
            tier: モデルティア
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数

        Returns:
            float: 概算コスト（USD）
        """
        return self._tier_manager.estimate_cost(provider, tier, input_tokens, output_tokens)

    def record(
        self,
        provider: str,
        model: str,
        tier: ModelTier,
        input_tokens: int,
        output_tokens: int,
        user_id: str = "",
        request_id: str = "",
        operation: str = "complete",
    ) -> CostEntry:
        """コストを記録.

        Args:
            provider: プロバイダー名
            model: モデルID
            tier: モデルティア
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            user_id: ユーザーID
            request_id: リクエストID
            operation: 操作種別

        Returns:
            CostEntry: 記録されたエントリ
        """
        cost = self.calculate_cost(provider, tier, input_tokens, output_tokens)

        entry = CostEntry(
            timestamp=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            tier=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            user_id=user_id,
            request_id=request_id,
            operation=operation,
        )
        self._entries.append(entry)

        logger.info(
            "cost_tracker.recorded",
            provider=provider,
            model=model,
            tier=tier.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            user_id=user_id,
        )

        return entry

    def get_summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> CostSummary:
        """コストサマリー取得.

        Args:
            since: 集計開始日時
            until: 集計終了日時

        Returns:
            CostSummary: 集計結果
        """
        now = datetime.now(timezone.utc)
        start = since or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = until or now

        filtered = [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]

        by_provider: dict[str, float] = {}
        by_model: dict[str, float] = {}
        by_tier: dict[str, float] = {}
        by_user: dict[str, float] = {}
        total_input = 0
        total_output = 0

        for entry in filtered:
            by_provider[entry.provider] = by_provider.get(entry.provider, 0) + entry.cost_usd
            by_model[entry.model] = by_model.get(entry.model, 0) + entry.cost_usd
            by_tier[entry.tier.value] = by_tier.get(entry.tier.value, 0) + entry.cost_usd
            if entry.user_id:
                by_user[entry.user_id] = by_user.get(entry.user_id, 0) + entry.cost_usd
            total_input += entry.input_tokens
            total_output += entry.output_tokens

        return CostSummary(
            total_cost_usd=sum(e.cost_usd for e in filtered),
            total_requests=len(filtered),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            by_provider=by_provider,
            by_model=by_model,
            by_tier=by_tier,
            by_user=by_user,
            period_start=start,
            period_end=end,
        )

    def to_dict(self) -> dict[str, Any]:
        """API応答用辞書変換."""
        summary = self.get_summary()
        return {
            "total_cost_usd": round(summary.total_cost_usd, 4),
            "total_requests": summary.total_requests,
            "total_input_tokens": summary.total_input_tokens,
            "total_output_tokens": summary.total_output_tokens,
            "by_provider": {k: round(v, 4) for k, v in summary.by_provider.items()},
            "by_model": {k: round(v, 4) for k, v in summary.by_model.items()},
            "by_tier": {k: round(v, 4) for k, v in summary.by_tier.items()},
        }
