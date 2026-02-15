"""サーキットブレーカー ユニットテスト.

CircuitBreaker の状態遷移・予算管理ロジックを検証する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cs_risk_agent.ai.circuit_breaker import (
    BudgetStatus,
    CircuitBreaker,
    CircuitState,
    UsageRecord,
)
from cs_risk_agent.core.exceptions import BudgetExceededError


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_record(
    provider: str = "azure",
    cost: float = 1.0,
    model: str = "gpt-4o",
) -> UsageRecord:
    """テスト用 UsageRecord を生成する."""
    return UsageRecord(
        timestamp=datetime.now(timezone.utc),
        provider=provider,
        model=model,
        input_tokens=100,
        output_tokens=50,
        cost_usd=cost,
        request_id="test-req-001",
    )


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestCircuitBreakerInitialState:
    """初期状態の検証."""

    def test_initial_state_closed(self):
        """初期状態は CLOSED であること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        assert cb.state == CircuitState.CLOSED

    def test_initial_spend_zero(self):
        """初期の累計コストは 0 であること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        assert cb.current_spend == 0.0

    def test_initial_usage_ratio_zero(self):
        """初期の利用率は 0 であること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        assert cb.usage_ratio == 0.0


class TestRecordUsage:
    """利用記録の検証."""

    @pytest.mark.asyncio
    async def test_record_usage_updates_spend(self):
        """record_usage 後に累計コストが更新されること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        record = _make_record(cost=10.0)
        await cb.record_usage(record)
        assert cb.current_spend == pytest.approx(10.0)

    @pytest.mark.asyncio
    async def test_multiple_records_accumulate(self):
        """複数レコードのコストが累積すること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        for _ in range(5):
            await cb.record_usage(_make_record(cost=5.0))
        assert cb.current_spend == pytest.approx(25.0)


class TestStateTransitions:
    """状態遷移の検証."""

    @pytest.mark.asyncio
    async def test_alert_threshold_half_open(self):
        """アラート閾値超過時に HALF_OPEN になること."""
        # 月額100, アラート80%, ブレーカー95%
        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )
        # 85%まで消費 → HALF_OPEN
        await cb.record_usage(_make_record(cost=85.0))
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_breaker_threshold_open(self):
        """ブレーカー閾値超過時に OPEN になること."""
        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )
        # 96%まで消費 → OPEN
        await cb.record_usage(_make_record(cost=96.0))
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_raises_error(self):
        """OPEN 状態で check_budget が BudgetExceededError を送出すること."""
        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )
        await cb.record_usage(_make_record(cost=96.0))
        assert cb.state == CircuitState.OPEN

        with pytest.raises(BudgetExceededError):
            await cb.check_budget()

    @pytest.mark.asyncio
    async def test_closed_circuit_passes_check(self):
        """CLOSED 状態で check_budget は正常通過すること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        await cb.record_usage(_make_record(cost=10.0))
        # 例外が発生しないことを確認
        await cb.check_budget()

    @pytest.mark.asyncio
    async def test_half_open_circuit_passes_check(self):
        """HALF_OPEN 状態で check_budget は正常通過すること（アラートのみ）."""
        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )
        await cb.record_usage(_make_record(cost=85.0))
        assert cb.state == CircuitState.HALF_OPEN
        # 例外は発生しない
        await cb.check_budget()


class TestMonthlyReset:
    """月次リセットの検証."""

    @pytest.mark.asyncio
    async def test_monthly_reset(self):
        """月が変わった場合にレコードがリセットされること."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        await cb.record_usage(_make_record(cost=50.0))
        assert cb.current_spend == pytest.approx(50.0)

        # 月を変更してリセットをトリガー
        with patch.object(
            CircuitBreaker,
            "_get_current_month",
            return_value="2099-12",
        ):
            assert cb.current_spend == 0.0
            assert cb.state == CircuitState.CLOSED


class TestUsageByProvider:
    """プロバイダー別利用コストの検証."""

    @pytest.mark.asyncio
    async def test_usage_by_provider(self):
        """プロバイダー別コスト集計が正しいこと."""
        cb = CircuitBreaker(monthly_limit_usd=1000.0)
        await cb.record_usage(_make_record(provider="azure", cost=10.0))
        await cb.record_usage(_make_record(provider="azure", cost=15.0))
        await cb.record_usage(_make_record(provider="aws", cost=5.0))

        by_provider = cb.get_usage_by_provider()
        assert by_provider["azure"] == pytest.approx(25.0)
        assert by_provider["aws"] == pytest.approx(5.0)

    @pytest.mark.asyncio
    async def test_usage_by_model(self):
        """モデル別コスト集計が正しいこと."""
        cb = CircuitBreaker(monthly_limit_usd=1000.0)
        await cb.record_usage(_make_record(model="gpt-4o", cost=20.0))
        await cb.record_usage(_make_record(model="gpt-4o-mini", cost=5.0))

        by_model = cb.get_usage_by_model()
        assert by_model["gpt-4o"] == pytest.approx(20.0)
        assert by_model["gpt-4o-mini"] == pytest.approx(5.0)


class TestStatusReport:
    """ステータスレポートの検証."""

    @pytest.mark.asyncio
    async def test_status_report(self):
        """get_status が正しい BudgetStatus を返すこと."""
        cb = CircuitBreaker(
            monthly_limit_usd=100.0,
            alert_threshold=0.8,
            breaker_threshold=0.95,
        )
        await cb.record_usage(_make_record(cost=30.0))

        status = cb.get_status()
        assert isinstance(status, BudgetStatus)
        assert status.monthly_limit_usd == 100.0
        assert status.current_spend_usd == pytest.approx(30.0)
        assert status.remaining_usd == pytest.approx(70.0)
        assert status.usage_ratio == pytest.approx(0.3)
        assert status.state == CircuitState.CLOSED
        assert status.request_count == 1

    @pytest.mark.asyncio
    async def test_to_dict_format(self):
        """to_dict が正しい辞書形式を返すこと."""
        cb = CircuitBreaker(monthly_limit_usd=100.0)
        await cb.record_usage(_make_record(cost=10.0))

        result = cb.to_dict()
        assert "state" in result
        assert "monthly_limit_usd" in result
        assert "current_spend_usd" in result
        assert "remaining_usd" in result
        assert "usage_ratio" in result
        assert "request_count" in result
        assert "by_provider" in result
        assert "by_model" in result
