"""構造化ロギング設定 - structlog ベース."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from cs_risk_agent.config import Settings


def setup_logging(settings: Settings) -> None:
    """structlog を設定してアプリケーション全体のロギングを初期化する.

    JSON フォーマット（本番用）またはコンソールフォーマット（開発用）を
    settings.observability.log_format に基づいて選択する。

    Args:
        settings: アプリケーション設定。
    """
    log_level = settings.observability.log_level.upper()
    use_json = settings.observability.log_format == "json"

    # 共通プロセッサチェーン
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        # 本番環境: JSON 出力
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer(
            ensure_ascii=False,
        )
    else:
        # 開発環境: カラー付きコンソール出力
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # structlog の設定
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 標準 logging との統合
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # サードパーティライブラリのログレベルを抑制
    for noisy_logger_name in ("uvicorn", "uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)

    structlog.get_logger(__name__).info(
        "logging_configured",
        log_level=log_level,
        format=settings.observability.log_format,
        environment=settings.app_env.value,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """指定した名前でバインド済み structlog ロガーを返す.

    Args:
        name: ロガー名（通常は ``__name__`` を渡す）。

    Returns:
        名前がバインドされた structlog ロガーインスタンス。

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("processing_started", company_id="C001")
    """
    return structlog.get_logger(name)
