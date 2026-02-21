"""認証APIエンドポイント - ログイン・トークン発行."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cs_risk_agent.core.security import Role, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    """ログインリクエスト."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """トークンレスポンス."""

    access_token: str
    token_type: str = "bearer"
    role: str


# デモ用ユーザー (本番ではDB認証に切り替え)
_DEMO_USERS: dict[str, dict] = {
    "admin": {"password": "admin", "role": Role.ADMIN},
    "auditor": {"password": "auditor", "role": Role.AUDITOR},
    "cfo": {"password": "cfo", "role": Role.CFO},
    "viewer": {"password": "viewer", "role": Role.VIEWER},
}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """ログイン - JWTトークン発行.

    デモモードではハードコードユーザーで認証。
    本番ではDB認証に切り替え。
    """
    user = _DEMO_USERS.get(request.username)
    if not user or user["password"] != request.password:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        subject=request.username,
        role=user["role"],
    )
    return TokenResponse(
        access_token=token,
        role=user["role"].value,
    )


@router.get("/me")
async def get_me(authorization: str | None = None):
    """現在のユーザー情報."""
    if not authorization:
        return {"user": None, "authenticated": False}

    from cs_risk_agent.core.security import decode_access_token
    try:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return {"user": None, "authenticated": False}
        payload = decode_access_token(token)
        return {
            "user": payload.sub,
            "role": payload.role.value,
            "authenticated": True,
        }
    except Exception:
        return {"user": None, "authenticated": False}
