"""FinOps サーキットブレーカー - 予算超過時のリクエスト遮断.

月間予算に対する利用量を監視し、閾値超過時にリクエストを遮断する。
アラート閾値でのWarningログ出力にも対応。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from cs_risk_agent.config import get_settings
from cs_risk_agent.core.exceptions import BudgetExceededError

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """サーキットブレーカー状態."""

    CLOSED = "closed"        # 正常稼働
    HALF_OPEN = "half_open"  # アラート閾値超過
    OPEN = "open"            # 遮断中


@dataclass
class UsageRecord:
    """利用記録."""

    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    request_id: str = ""


@dataclass
class BudgetStatus:
    """予算ステータス."""

    monthly_limit_usd: float
    current_spend_usd: float
    remaining_usd: float
    usage_ratio: float
    state: CircuitState
    alert_threshold: float
    breaker_threshold: float
    period_start: datetime
    period_end: datetime
    request_count: int


class CircuitBreaker:
    """FinOps サーキットブレーカー.

    月間予算に基づいてAIリクエストの許可/遮断を制御する。

    状態遷移:
        CLOSED -> HALF_OPEN: 利用率がアラート閾値を超過
        HALF_OPEN -> OPEN: 利用率がブレーカー閾値を超過
        OPEN -> CLOSED: 月が変わった場合（自動リセット）
    """

    def __init__(
        self,
        monthly_limit_usd: float | None = None,
        alert_threshold: float | None = None,
        breaker_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        self._monthly_limit = monthly_limit_usd or settings.ai.monthly_budget_usd
        self._alert_threshold = alert_threshold or settings.ai.budget_alert_threshold
        self._breaker_threshold = breaker_threshold or settings.ai.circuit_breaker_threshold
        self._records: list[UsageRecord] = []
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
        self._current_month: str = self._get_current_month()

    @staticmethod
    def _get_current_month() -> str:
        """現在の年月文字列."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _maybe_reset_month(self) -> None:
        """月が変わった場合に記録をリセット."""
        current = self._get_current_month()
        if current != self._current_month:
            logger.info(
                "circuit_breaker.monthly_reset",
                old_month=self._current_month,
                new_month=current,
                total_records=len(self._records),
            )
            self._records.clear()
            self._state = CircuitState.CLOSED
            self._current_month = current

    @property
    def current_spend(self) -> float:
        """当月の累計コスト."""
        self._maybe_reset_month()
        return sum(r.cost_usd for r in self._records)

    @property
    def usage_ratio(self) -> float:
        """予算利用率 (0.0 - 1.0+)."""
        if self._monthly_limit <= 0:
            return 0.0
        return self.current_spend / self._monthly_limit

    @property
    def state(self) -> CircuitState:
        """現在のサーキット状態."""
        self._update_state()
        return self._state

    def _update_state(self) -> None:
        """利用率に基づいて状態を更新."""
        self._maybe_reset_month()
        ratio = self.usage_ratio

        if ratio >= self._breaker_threshold:
            if self._state != CircuitState.OPEN:
                logger.warning(
                    "circuit_breaker.opened",
                    usage_ratio=ratio,
                    current_spend=self.current_spend,
                    limit=self._monthly_limit,
                )
            self._state = CircuitState.OPEN
        elif ratio >= self._alert_threshold:
            if self._state == CircuitState.CLOSED:
                logger.warning(
                    "circuit_breaker.alert",
                    usage_ratio=ratio,
                    current_spend=self.current_spend,
                    limit=self._monthly_limit,
                )
            self._state = CircuitState.HALF_OPEN
        else:
            self._state = CircuitState.CLOSED

    async def check_budget(self) -> None:
        """予算チェック - 遮断中の場合は例外を送出.

        Raises:
            BudgetExceededError: サーキットブレーカーがOPEN状態の場合
        """
        async with self._lock:
            self._update_state()
            if self._state == CircuitState.OPEN:
                raise BudgetExceededError(
                    current_cost=self.current_spend,
                    budget_limit=self._monthly_limit,
                )

    async def record_usage(self, record: UsageRecord) -> None:
        """利用記録を追加.

        Args:
            record: 利用記録
        """
        async with self._lock:
            self._maybe_reset_month()
            self._records.append(record)
            self._update_state()

            logger.info(
                "circuit_breaker.usage_recorded",
                provider=record.provider,
                model=record.model,
                cost_usd=record.cost_usd,
                total_spend=self.current_spend,
                usage_ratio=self.usage_ratio,
                state=self._state.value,
            )

    def get_status(self) -> BudgetStatus:
        """予算ステータスを取得."""
        self._update_state()
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 翌月1日
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            period_end = now.replace(month=now.month + 1, day=1)
        period_end = period_end.replace(hour=0, minute=0, second=0, microsecond=0)

        current = self.current_spend
        return BudgetStatus(
            monthly_limit_usd=self._monthly_limit,
            current_spend_usd=current,
            remaining_usd=max(0, self._monthly_limit - current),
            usage_ratio=self.usage_ratio,
            state=self._state,
            alert_threshold=self._alert_threshold,
            breaker_threshold=self._breaker_threshold,
            period_start=period_start,
            period_end=period_end,
            request_count=len(self._records),
        )

    def get_usage_by_provider(self) -> dict[str, float]:
        """プロバイダー別利用コスト."""
        result: dict[str, float] = {}
        for record in self._records:
            result[record.provider] = result.get(record.provider, 0) + record.cost_usd
        return result

    def get_usage_by_model(self) -> dict[str, float]:
        """モデル別利用コスト."""
        result: dict[str, float] = {}
        for record in self._records:
            result[record.model] = result.get(record.model, 0) + record.cost_usd
        return result

    def to_dict(self) -> dict[str, Any]:
        """辞書形式で出力（API応答用）."""
        status = self.get_status()
        return {
            "state": status.state.value,
            "monthly_limit_usd": status.monthly_limit_usd,
            "current_spend_usd": round(status.current_spend_usd, 4),
            "remaining_usd": round(status.remaining_usd, 4),
            "usage_ratio": round(status.usage_ratio, 4),
            "request_count": status.request_count,
            "by_provider": self.get_usage_by_provider(),
            "by_model": self.get_usage_by_model(),
        }
