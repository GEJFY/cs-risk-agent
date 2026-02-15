"""FastAPI アプリケーション エントリポイント."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from cs_risk_agent.api.middleware import AuditLogMiddleware, RateLimitMiddleware
from cs_risk_agent.api.v1.router import api_router
from cs_risk_agent.config import get_settings
from cs_risk_agent.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BudgetExceededError,
    CSRiskAgentError,
)
from cs_risk_agent.observability.logging import setup_logging
from cs_risk_agent.observability.tracing import setup_tracing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーションライフサイクル管理."""
    settings = get_settings()
    setup_logging(settings)
    setup_tracing(settings)
    logger.info("Application started (env=%s)", settings.app_env.value)
    yield
    logger.info("Application shutting down")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """標準エラーレスポンス."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _register_exception_handlers(app: FastAPI) -> None:
    """グローバル例外ハンドラを登録."""

    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return _error_response(401, exc.code, exc.message)

    @app.exception_handler(AuthorizationError)
    async def handle_authorization_error(request: Request, exc: AuthorizationError) -> JSONResponse:
        return _error_response(403, exc.code, exc.message)

    @app.exception_handler(BudgetExceededError)
    async def handle_budget_exceeded(request: Request, exc: BudgetExceededError) -> JSONResponse:
        return _error_response(429, exc.code, exc.message)

    @app.exception_handler(CSRiskAgentError)
    async def handle_app_error(request: Request, exc: CSRiskAgentError) -> JSONResponse:
        return _error_response(500, exc.code, exc.message)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(422, "VALIDATION_ERROR", str(exc))

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        settings = get_settings()
        message = str(exc) if settings.app_debug else "Internal server error"
        return _error_response(500, "INTERNAL_ERROR", message)


def create_app() -> FastAPI:
    """FastAPIアプリケーション生成."""
    settings = get_settings()

    app = FastAPI(
        title="CS Risk Agent",
        description=(
            "Enterprise Multi-Cloud AI Orchestrator for Consolidated Subsidiary Risk Analysis"
        ),
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # グローバル例外ハンドラ
    _register_exception_handlers(app)

    # CORS (環境変数で設定可能)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # レート制限 (本番のみ)
    if settings.is_production:
        app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

    # 監査ログミドルウェア
    app.add_middleware(AuditLogMiddleware)

    # API ルーター
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
