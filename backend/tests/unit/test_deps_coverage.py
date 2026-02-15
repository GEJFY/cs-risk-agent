"""API deps モジュールのカバレッジテスト."""

from __future__ import annotations

import pytest

from cs_risk_agent.api.deps import AIModelRouter, get_ai_router, get_current_user, get_db
from cs_risk_agent.config import Settings

# ---------------------------------------------------------------------------
# get_db テスト
# ---------------------------------------------------------------------------


class TestGetDb:
    """DB セッション依存性テスト."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        gen = get_db()
        session = await gen.__anext__()
        assert isinstance(session, dict)
        assert session["_placeholder"] is True
        # cleanup
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
        user = await get_current_user(authorization="Bearer some-token", settings=Settings())
        assert user["sub"] == "placeholder-user-id"
        assert user["token"] == "some-token"
        assert "roles" in user


# ---------------------------------------------------------------------------
# AIModelRouter テスト
# ---------------------------------------------------------------------------


class TestAIModelRouter:
    """AI モデルルーターテスト."""

    def test_init(self) -> None:
        settings = Settings()
        router = AIModelRouter(settings)
        assert router._settings is settings

    @pytest.mark.asyncio
    async def test_route_default_tier(self) -> None:
        settings = Settings()
        router = AIModelRouter(settings)
        result = await router.route("Hello world")
        assert "PLACEHOLDER" in result
        assert "cost_effective" in result
        assert "prompt_len=11" in result

    @pytest.mark.asyncio
    async def test_route_sota_tier(self) -> None:
        settings = Settings()
        router = AIModelRouter(settings)
        result = await router.route("Analyze this", tier="sota")
        assert "sota" in result

    def test_get_ai_router_returns_instance(self) -> None:
        from cs_risk_agent.api import deps

        # Reset singleton
        deps._ai_router_instance = None
        settings = Settings()
        router = get_ai_router(settings)
        assert isinstance(router, AIModelRouter)

    def test_get_ai_router_singleton(self) -> None:
        from cs_risk_agent.api import deps

        deps._ai_router_instance = None
        settings = Settings()
        r1 = get_ai_router(settings)
        r2 = get_ai_router(settings)
        assert r1 is r2
        # Cleanup
        deps._ai_router_instance = None
