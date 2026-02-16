"""API deps モジュールのカバレッジテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cs_risk_agent.api.deps import AIModelRouter, get_ai_router, get_current_user, get_db
from cs_risk_agent.config import Settings
from cs_risk_agent.core.security import Role, create_access_token

# ---------------------------------------------------------------------------
# get_db テスト
# ---------------------------------------------------------------------------


class TestGetDb:
    """DB セッション依存性テスト."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        mock_session = AsyncMock()

        async def _fake_get_db_session():
            yield mock_session

        with patch("cs_risk_agent.api.deps.get_db_session", _fake_get_db_session):
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()


# ---------------------------------------------------------------------------
# get_current_user テスト
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """認証依存性テスト."""

    @pytest.mark.asyncio
    async def test_no_authorization_header(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None, settings=Settings())
        assert exc_info.value.status_code == 401
        assert "Authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_scheme(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Basic abc123", settings=Settings())
        assert exc_info.value.status_code == 401
        assert "Bearer" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_token(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer ", settings=Settings())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self) -> None:
        token = create_access_token(subject="user-123", role=Role.AUDITOR)
        user = await get_current_user(
            authorization=f"Bearer {token}", settings=Settings()
        )
        assert user["sub"] == "user-123"
        assert user["role"] == "auditor"

    @pytest.mark.asyncio
    async def test_invalid_jwt_token(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                authorization="Bearer invalid-jwt-token", settings=Settings()
            )
        assert exc_info.value.status_code == 401
        assert "Invalid or expired" in exc_info.value.detail


# ---------------------------------------------------------------------------
# AIModelRouter テスト
# ---------------------------------------------------------------------------


class TestAIModelRouter:
    """AI モデルルーターテスト."""

    def test_import_from_deps(self) -> None:
        assert AIModelRouter is not None
        assert callable(get_ai_router)

    def test_get_ai_router_returns_instance(self) -> None:
        from cs_risk_agent.ai import router as router_module

        router_module._router = None
        router = get_ai_router()
        assert isinstance(router, AIModelRouter)
        router_module._router = None
