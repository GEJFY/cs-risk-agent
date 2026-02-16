"""FastAPI 依存性注入 - DI コンテナ."""

from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from cs_risk_agent.config import Settings, get_settings
from cs_risk_agent.core.exceptions import AuthenticationError
from cs_risk_agent.core.security import decode_access_token
from cs_risk_agent.data.database import get_db_session


# ---------------------------------------------------------------------------
# データベースセッション
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    """非同期DBセッションを提供するジェネレータ.

    Yields:
        SQLAlchemy AsyncSession インスタンス。
    """
    async for session in get_db_session():
        yield session


# ---------------------------------------------------------------------------
# 認証・認可
# ---------------------------------------------------------------------------


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """JWTトークンからユーザー情報を抽出する.

    Authorization ヘッダーの Bearer トークンを検証し、
    ユーザー情報を辞書として返す。

    Args:
        authorization: Authorization ヘッダー値（Bearer <token>）。
        settings: アプリケーション設定。

    Returns:
        ユーザー情報を含む辞書。

    Raises:
        HTTPException: トークンが欠落または無効な場合（401）。
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Bearer プレフィックスの検証
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        return {
            "sub": payload.sub,
            "role": payload.role.value,
            "exp": payload.exp.isoformat(),
            "iat": payload.iat.isoformat(),
        }
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# AI モデルルーター
# ---------------------------------------------------------------------------

from cs_risk_agent.ai.router import AIModelRouter, get_ai_router  # noqa: E402, F401
