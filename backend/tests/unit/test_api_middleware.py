"""API middleware/deps のユニットテスト."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cs_risk_agent.core.security import Role, create_access_token

# ---------------------------------------------------------------------------
# Middleware テスト
# ---------------------------------------------------------------------------


class TestAuditLogMiddleware:
    """監査ログミドルウェアのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.api.middleware import AuditLogMiddleware

        assert AuditLogMiddleware is not None

    def test_extract_user_id_with_bearer(self) -> None:
        from cs_risk_agent.api.middleware import _extract_user_id

        request = MagicMock()
        request.headers.get.return_value = "Bearer eyJhbGciOiJIUzI1NiJ9.test"
        user_id = _extract_user_id(request)
        assert user_id is not None

    def test_extract_user_id_no_auth(self) -> None:
        from cs_risk_agent.api.middleware import _extract_user_id

        request = MagicMock()
        request.headers.get.return_value = None
        user_id = _extract_user_id(request)
        assert user_id is None

    def test_get_client_ip_direct(self) -> None:
        from cs_risk_agent.api.middleware import _get_client_ip

        request = MagicMock()
        request.headers.get.return_value = None
        request.client.host = "192.168.1.1"
        ip = _get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_forwarded(self) -> None:
        from cs_risk_agent.api.middleware import _get_client_ip

        request = MagicMock()
        request.headers.get.return_value = "10.0.0.1, 192.168.1.1"
        ip = _get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_no_client(self) -> None:
        from cs_risk_agent.api.middleware import _get_client_ip

        request = MagicMock()
        request.headers.get.return_value = None
        request.client = None
        ip = _get_client_ip(request)
        assert ip == "unknown"


# ---------------------------------------------------------------------------
# Deps テスト
# ---------------------------------------------------------------------------


class TestDeps:
    """依存性注入モジュールのテスト."""

    def test_imports(self) -> None:
        from cs_risk_agent.api.deps import AIModelRouter, get_ai_router, get_db

        assert get_db is not None
        assert AIModelRouter is not None
        assert get_ai_router is not None

    def test_ai_model_router_class(self) -> None:
        from cs_risk_agent.api.deps import AIModelRouter

        # AIModelRouter は ai.router.AIModelRouter と同一
        from cs_risk_agent.ai.router import AIModelRouter as RealRouter

        assert AIModelRouter is RealRouter

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth(self) -> None:
        from fastapi import HTTPException

        from cs_risk_agent.api.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_scheme(self) -> None:
        from fastapi import HTTPException

        from cs_risk_agent.api.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Basic dXNlcjpwYXNz")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_jwt(self) -> None:
        from cs_risk_agent.api.deps import get_current_user

        token = create_access_token(subject="user-1", role=Role.ADMIN)
        result = await get_current_user(authorization=f"Bearer {token}")
        assert isinstance(result, dict)
        assert result["sub"] == "user-1"
        assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_jwt(self) -> None:
        from fastapi import HTTPException

        from cs_risk_agent.api.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer bogus.jwt.token")
        assert exc_info.value.status_code == 401

    def test_get_ai_router_singleton(self) -> None:
        from cs_risk_agent.ai import router as router_mod
        from cs_risk_agent.api.deps import AIModelRouter, get_ai_router

        router_mod._router = None
        router1 = get_ai_router()
        router2 = get_ai_router()
        assert router1 is router2
        assert isinstance(router1, AIModelRouter)
        router_mod._router = None
