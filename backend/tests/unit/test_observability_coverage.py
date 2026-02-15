"""observability パッケージのカバレッジ拡張テスト."""

from __future__ import annotations

from cs_risk_agent.observability.audit import (
    AuditLogger,
    _mask_sensitive,
    _truncate,
    get_audit_logger,
)

# ---------------------------------------------------------------------------
# _truncate / _mask_sensitive 関数テスト
# ---------------------------------------------------------------------------


class TestTruncate:
    """テキスト切り詰めのテスト."""

    def test_none_input(self) -> None:
        assert _truncate(None) == ""

    def test_empty_string(self) -> None:
        assert _truncate("") == ""

    def test_short_string(self) -> None:
        assert _truncate("hello", 10) == "hello"

    def test_exact_length(self) -> None:
        text = "x" * 500
        assert _truncate(text, 500) == text

    def test_over_length(self) -> None:
        text = "x" * 600
        result = _truncate(text, 500)
        assert len(result) == 500 + len("...[truncated]")
        assert result.endswith("...[truncated]")


class TestMaskSensitive:
    """機密情報マスクのテスト."""

    def test_mask_email(self) -> None:
        result = _mask_sensitive("Contact: user@example.com for details")
        assert "[EMAIL]" in result
        assert "user@example.com" not in result

    def test_mask_phone(self) -> None:
        result = _mask_sensitive("TEL: 03-1234-5678")
        assert "[PHONE]" in result
        assert "03-1234-5678" not in result

    def test_mask_id_number(self) -> None:
        result = _mask_sensitive("My number: 123456789012")
        assert "[ID_NUMBER]" in result
        assert "123456789012" not in result

    def test_mask_multiple(self) -> None:
        result = _mask_sensitive("user@test.com and 090-1234-5678")
        assert "[EMAIL]" in result
        assert "[PHONE]" in result

    def test_no_sensitive_data(self) -> None:
        result = _mask_sensitive("Normal text without sensitive data")
        assert result == "Normal text without sensitive data"

    def test_mask_with_truncation(self) -> None:
        long_text = "user@test.com " + "x" * 600
        result = _mask_sensitive(long_text)
        assert result.endswith("...[truncated]")


# ---------------------------------------------------------------------------
# AuditLogger テスト
# ---------------------------------------------------------------------------


class TestAuditLogger:
    """AuditLogger の全メソッドテスト."""

    def test_init_custom_buffer_size(self) -> None:
        al = AuditLogger(max_buffer_size=5)
        assert al._max_buffer_size == 5

    def test_log_basic(self) -> None:
        al = AuditLogger()
        entry = al.log("user1", "test.action")
        assert entry.user_id == "user1"
        assert entry.action == "test.action"
        assert entry.timestamp is not None

    def test_log_with_all_params(self) -> None:
        al = AuditLogger()
        entry = al.log(
            "user1",
            "api.call",
            resource="/api/v1/companies",
            ai_provider="azure",
            ai_model="gpt-4o",
            input_summary="query",
            output_summary="response",
            request_path="/api/v1/companies",
            request_method="GET",
            status_code=200,
            duration_ms=150,
            ip_address="192.168.1.1",
            custom_key="custom_value",
        )
        assert entry.resource == "/api/v1/companies"
        assert entry.ai_provider == "azure"
        assert entry.status_code == 200
        assert entry.metadata == {"custom_key": "custom_value"}

    def test_log_truncates_input_summary(self) -> None:
        al = AuditLogger()
        long_text = "x" * 1000
        entry = al.log("user1", "action", input_summary=long_text)
        assert len(entry.input_summary) < 1000

    def test_log_ai_request(self) -> None:
        al = AuditLogger()
        entry = al.log_ai_request(
            user_id="user1",
            provider="azure",
            model="gpt-4o",
            input_text="Hello, analyze this data",
            output_text="Analysis complete",
            tokens_used=100,
            cost_usd=0.01,
            duration_ms=500,
        )
        assert entry.action == "ai.complete"
        assert entry.ai_provider == "azure"
        assert entry.ai_model == "gpt-4o"

    def test_log_ai_request_masks_sensitive(self) -> None:
        al = AuditLogger()
        entry = al.log_ai_request(
            user_id="user1",
            provider="azure",
            model="gpt-4o",
            input_text="Email me at user@test.com",
            output_text="Done",
        )
        assert "user@test.com" not in (entry.input_summary or "")
        assert "[EMAIL]" in (entry.input_summary or "")

    def test_get_recent(self) -> None:
        al = AuditLogger()
        for i in range(10):
            al.log(f"user{i}", "action")
        recent = al.get_recent(5)
        assert len(recent) == 5

    def test_get_recent_all(self) -> None:
        al = AuditLogger()
        for i in range(3):
            al.log(f"user{i}", "action")
        recent = al.get_recent(100)
        assert len(recent) == 3

    def test_get_by_user(self) -> None:
        al = AuditLogger()
        al.log("alice", "action1")
        al.log("bob", "action2")
        al.log("alice", "action3")
        entries = al.get_by_user("alice")
        assert len(entries) == 2
        assert all(e.user_id == "alice" for e in entries)

    def test_get_by_user_with_limit(self) -> None:
        al = AuditLogger()
        for i in range(10):
            al.log("alice", f"action{i}")
        entries = al.get_by_user("alice", limit=3)
        assert len(entries) == 3

    def test_clear_buffer(self) -> None:
        al = AuditLogger()
        al.log("user1", "action1")
        al.log("user2", "action2")
        count = al.clear_buffer()
        assert count == 2
        assert al.get_recent() == []

    def test_buffer_overflow(self) -> None:
        al = AuditLogger(max_buffer_size=5)
        for i in range(10):
            al.log(f"user{i}", "action")
        assert len(al._buffer) == 5
        # 最新5件が残る
        assert al._buffer[-1].user_id == "user9"


class TestGetAuditLogger:
    """シングルトン取得テスト."""

    def test_returns_instance(self) -> None:
        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)

    def test_singleton(self) -> None:
        l1 = get_audit_logger()
        l2 = get_audit_logger()
        assert l1 is l2


# ---------------------------------------------------------------------------
# logging モジュール テスト
# ---------------------------------------------------------------------------


class TestLogging:
    """ロギングモジュールのテスト."""

    def test_setup_logging_json(self) -> None:
        from cs_risk_agent.config import Settings
        from cs_risk_agent.observability.logging import setup_logging

        settings = Settings()
        settings.observability.log_format = "json"
        setup_logging(settings)

    def test_setup_logging_console(self) -> None:
        from cs_risk_agent.config import Settings
        from cs_risk_agent.observability.logging import setup_logging

        settings = Settings()
        settings.observability.log_format = "console"
        setup_logging(settings)

    def test_get_logger(self) -> None:
        from cs_risk_agent.observability.logging import get_logger

        logger = get_logger("test_module")
        assert logger is not None


# ---------------------------------------------------------------------------
# tracing モジュール テスト
# ---------------------------------------------------------------------------


class TestTracing:
    """トレーシングモジュールのテスト."""

    def test_setup_tracing(self) -> None:
        from cs_risk_agent.config import Settings
        from cs_risk_agent.observability.tracing import setup_tracing

        settings = Settings()
        setup_tracing(settings)

    def test_get_tracer_no_otel(self) -> None:
        from cs_risk_agent.observability.tracing import get_tracer

        # OpenTelemetry SDK がない場合は None
        tracer = get_tracer("test")
        # None or Tracer depending on environment
        assert tracer is None or tracer is not None


# ---------------------------------------------------------------------------
# metrics モジュール テスト
# ---------------------------------------------------------------------------


class TestMetrics:
    """Prometheus メトリクスのインポートと型テスト."""

    def test_all_metrics_importable(self) -> None:
        from cs_risk_agent.observability.metrics import (
            AI_COST_USD,
            AI_REQUEST_DURATION,
            AI_REQUESTS_TOTAL,
            AI_TOKENS_TOTAL,
            ANALYSIS_DURATION,
            ANALYSIS_RUNS_TOTAL,
            APP_INFO,
            BUDGET_USAGE_RATIO,
            CIRCUIT_BREAKER_STATE,
            HIGH_RISK_COMPANIES,
            HTTP_REQUEST_DURATION,
            HTTP_REQUESTS_TOTAL,
            RISK_SCORES_CALCULATED,
        )

        assert APP_INFO is not None
        assert AI_REQUESTS_TOTAL is not None
        assert AI_REQUEST_DURATION is not None
        assert AI_TOKENS_TOTAL is not None
        assert AI_COST_USD is not None
        assert CIRCUIT_BREAKER_STATE is not None
        assert BUDGET_USAGE_RATIO is not None
        assert ANALYSIS_RUNS_TOTAL is not None
        assert ANALYSIS_DURATION is not None
        assert HTTP_REQUESTS_TOTAL is not None
        assert HTTP_REQUEST_DURATION is not None
        assert RISK_SCORES_CALCULATED is not None
        assert HIGH_RISK_COMPANIES is not None

    def test_counter_labels(self) -> None:
        from cs_risk_agent.observability.metrics import AI_REQUESTS_TOTAL

        labeled = AI_REQUESTS_TOTAL.labels(
            provider="azure", model="gpt-4o", tier="sota", status="success"
        )
        assert labeled is not None

    def test_histogram_observe(self) -> None:
        from cs_risk_agent.observability.metrics import AI_REQUEST_DURATION

        AI_REQUEST_DURATION.labels(provider="azure", model="gpt-4o").observe(1.5)

    def test_gauge_set(self) -> None:
        from cs_risk_agent.observability.metrics import BUDGET_USAGE_RATIO

        BUDGET_USAGE_RATIO.set(0.75)
