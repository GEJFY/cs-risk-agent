"""FastAPI 依存性注入 - DI コンテナ."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from cs_risk_agent.config import Settings, get_settings
from cs_risk_agent.core.exceptions import AuthenticationError, AuthorizationError
from cs_risk_agent.core.security import Role, check_permission, decode_access_token
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


def require_permission(permission: str) -> Callable:
    """RBAC パーミッションチェック依存性を生成する.

    Args:
        permission: 必要なパーミッション文字列 (例: "read", "analysis:run")。

    Returns:
        FastAPI Depends で使用可能な依存性関数。
    """

    async def _check(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        try:
            role = Role(current_user["role"])
            check_permission(role, permission)
        except AuthorizationError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required. Role '{current_user['role']}' is not authorized.",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# AI モデルルーター
# ---------------------------------------------------------------------------

from cs_risk_agent.ai.router import AIModelRouter, get_ai_router  # noqa: E402, F401
