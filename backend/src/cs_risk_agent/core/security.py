"""認証・認可セキュリティモジュール."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from cs_risk_agent.config import get_settings
from cs_risk_agent.core.exceptions import AuthenticationError, AuthorizationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    """ユーザーロール定義."""

    ADMIN = "admin"
    AUDITOR = "auditor"
    CFO = "cfo"
    CEO = "ceo"
    VIEWER = "viewer"


class TokenPayload(BaseModel):
    """JWTトークンペイロード."""

    sub: str
    role: Role
    exp: datetime
    iat: datetime


# ロール別アクセス権限マッピング
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "read", "write", "delete", "admin", "analysis:run",
        "reports:generate", "models:manage", "settings:manage",
    },
    Role.AUDITOR: {
        "read", "analysis:run", "reports:generate",
    },
    Role.CFO: {
        "read", "analysis:run", "reports:generate",
    },
    Role.CEO: {
        "read", "reports:generate",
    },
    Role.VIEWER: {
        "read",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワード検証."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """パスワードハッシュ化."""
    return pwd_context.hash(password)


def create_access_token(subject: str, role: Role, extra: dict[str, Any] | None = None) -> str:
    """JWTアクセストークン生成."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt.expiration_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": now,
        "exp": expire,
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """JWTアクセストークンデコード."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
        return TokenPayload(
            sub=payload["sub"],
            role=Role(payload["role"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e


def check_permission(role: Role, permission: str) -> None:
    """ロールベースアクセス制御チェック."""
    permissions = ROLE_PERMISSIONS.get(role, set())
    if permission not in permissions:
        raise AuthorizationError(
            f"Role '{role.value}' does not have permission '{permission}'"
        )
