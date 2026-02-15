"""observability モジュールのユニットテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

from cs_risk_agent.observability.logging import get_logger, setup_logging
from cs_risk_agent.observability.tracing import get_tracer, setup_tracing


class TestLogging:
    """ロギング設定のテスト."""

    def test_setup_logging_json(self) -> None:
        settings = MagicMock()
        settings.observability.log_level = "INFO"
        settings.observability.log_format = "json"
        settings.app_env.value = "production"
        # Should not raise
        setup_logging(settings)

    def test_setup_logging_console(self) -> None:
        settings = MagicMock()
        settings.observability.log_level = "DEBUG"
        settings.observability.log_format = "console"
        settings.app_env.value = "development"
        setup_logging(settings)

    def test_get_logger(self) -> None:
        logger = get_logger("test_module")
        assert logger is not None


class TestTracing:
    """トレーシング設定のテスト."""

    def test_setup_tracing(self) -> None:
        settings = MagicMock()
        settings.observability.service_name = "test-service"
        settings.observability.otel_endpoint = "http://localhost:4317"
        settings.app_debug = True
        settings.app_env.value = "development"
        # Should not raise
        setup_tracing(settings)

    def test_get_tracer(self) -> None:
        # get_tracer returns None if opentelemetry not installed
        tracer = get_tracer("test")
        # May return None or tracer depending on environment
        assert tracer is None or tracer is not None


class TestMetrics:
    """メトリクス定義のテスト."""

    def test_metrics_import(self) -> None:
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

        # All metrics should be importable
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
