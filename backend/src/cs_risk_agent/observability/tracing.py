"""分散トレーシング設定 - OpenTelemetry ベース."""

from __future__ import annotations

from typing import Any

import structlog

from cs_risk_agent.config import Settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def setup_tracing(settings: Settings) -> None:
    """OpenTelemetry トレーサープロバイダーを初期化する.

    OTLP エクスポーターを設定し、FastAPI の自動計装を有効化する。
    開発環境ではコンソールエクスポーターも併用する。

    TODO: opentelemetry-sdk, opentelemetry-exporter-otlp,
          opentelemetry-instrumentation-fastapi パッケージが
          インストールされ次第、実装を有効化する。

    Args:
        settings: アプリケーション設定。
    """
    service_name = settings.observability.service_name
    otel_endpoint = settings.observability.otel_endpoint

    try:
        # TODO: 以下のインポートと設定を有効化する
        #
        # from opentelemetry import trace
        # from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        #     OTLPSpanExporter,
        # )
        # from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        # from opentelemetry.sdk.resources import Resource
        # from opentelemetry.sdk.trace import TracerProvider
        # from opentelemetry.sdk.trace.export import (
        #     BatchSpanProcessor,
        #     ConsoleSpanExporter,
        # )
        #
        # # リソース定義（サービス識別情報）
        # resource = Resource.create(
        #     {
        #         "service.name": service_name,
        #         "service.version": "0.1.0",
        #         "deployment.environment": settings.app_env.value,
        #     }
        # )
        #
        # # トレーサープロバイダーの作成
        # provider = TracerProvider(resource=resource)
        #
        # # OTLP エクスポーター（本番・ステージング）
        # otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
        # provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        #
        # # 開発環境ではコンソール出力も追加
        # if settings.app_debug:
        #     provider.add_span_processor(
        #         BatchSpanProcessor(ConsoleSpanExporter())
        #     )
        #
        # # グローバルトレーサープロバイダーとして登録
        # trace.set_tracer_provider(provider)
        #
        # # FastAPI 自動計装
        # FastAPIInstrumentor.instrument()

        logger.info(
            "tracing_configured",
            service_name=service_name,
            otel_endpoint=otel_endpoint,
            note="placeholder - OpenTelemetry SDK not yet installed",
        )

    except ImportError:
        logger.warning(
            "tracing_skipped",
            reason="OpenTelemetry packages not installed",
            service_name=service_name,
        )
    except Exception as exc:
        logger.error(
            "tracing_setup_failed",
            error=str(exc),
            service_name=service_name,
        )


def get_tracer(name: str) -> Any:
    """指定した名前でトレーサーを取得する.

    OpenTelemetry SDK がインストールされていない場合は
    何も行わないダミートレーサーを返す。

    Args:
        name: トレーサー名（通常はモジュール名 ``__name__``）。

    Returns:
        OpenTelemetry Tracer インスタンス、または None。
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        logger.debug("tracer_unavailable", name=name)
        return None
