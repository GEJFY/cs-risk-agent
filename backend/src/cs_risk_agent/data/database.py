"""データベース接続管理."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine

from cs_risk_agent.config import get_settings


def get_async_engine():
    """非同期エンジン取得."""
    settings = get_settings()
    return create_async_engine(
        settings.database.url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
    )


def get_sync_engine():
    """同期エンジン取得（マイグレーション用）."""
    settings = get_settings()
    return create_engine(settings.database.sync_url, echo=settings.database.echo)


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """非同期セッションファクトリ取得."""
    engine = get_async_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """非同期DBセッション - FastAPI依存性注入用."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
