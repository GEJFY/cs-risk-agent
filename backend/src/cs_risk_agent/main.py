"""FastAPI アプリケーション エントリポイント."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cs_risk_agent.api.middleware import AuditLogMiddleware
from cs_risk_agent.api.v1.router import api_router
from cs_risk_agent.config import get_settings
from cs_risk_agent.observability.logging import setup_logging
from cs_risk_agent.observability.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーションライフサイクル管理."""
    settings = get_settings()
    setup_logging(settings)
    setup_tracing(settings)
    yield


def create_app() -> FastAPI:
    """FastAPIアプリケーション生成."""
    settings = get_settings()

    app = FastAPI(
        title="CS Risk Agent",
        description="Enterprise Multi-Cloud AI Orchestrator for Consolidated Subsidiary Risk Analysis",
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3005", "http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 監査ログミドルウェア
    app.add_middleware(AuditLogMiddleware)

    # API ルーター
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
