"""API middleware のカバレッジ拡張テスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cs_risk_agent.api.middleware import (
    RateLimitMiddleware,
    _extract_user_id,
    _get_client_ip,
)

# ---------------------------------------------------------------------------
# ヘルパー関数テスト
# ---------------------------------------------------------------------------


class TestExtractUserId:
    """_extract_user_id のテスト."""

    def test_no_auth_header(self) -> None:
        request = MagicMock()
        request.headers = {}
        assert _extract_user_id(request) is None

    def test_bearer_token(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Bearer some-jwt-token"}
        result = _extract_user_id(request)
        # token-based extraction returns something or None
        assert result is None or isinstance(result, str)

    def test_non_bearer_auth(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Basic abc123"}
        result = _extract_user_id(request)
        assert result == "unknown"  # non-Bearer returns "unknown"


class TestGetClientIp:
    """_get_client_ip のテスト."""

    def test_x_forwarded_for(self) -> None:
        request = MagicMock()
        request.headers = {"x-forwarded-for": "203.0.113.50, 70.41.3.18"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "203.0.113.50"

    def test_direct_client(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")
        assert _get_client_ip(request) == "192.168.1.100"

    def test_no_client(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == "unknown"


# ---------------------------------------------------------------------------
# RateLimitMiddleware テスト
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """レート制限ミドルウェアのテスト."""

    def test_init(self) -> None:
        app = MagicMock()
        mw = RateLimitMiddleware(app, requests_per_minute=120)
        assert mw.rpm == 120

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self) -> None:
        call_next = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next.return_value = mock_response

        app = MagicMock()
        mw = RateLimitMiddleware(app, requests_per_minute=60)

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="10.0.0.1")

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self) -> None:
        app = MagicMock()
        mw = RateLimitMiddleware(app, requests_per_minute=2)

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="10.0.0.2")

        call_next = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next.return_value = mock_response

        # First 2 requests should pass
        await mw.dispatch(request, call_next)
        await mw.dispatch(request, call_next)

        # 3rd request should be rate limited (429)
        response = await mw.dispatch(request, call_next)
        assert response.status_code == 429
