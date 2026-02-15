"""API エンドポイント 統合テスト.

FastAPI アプリケーションのエンドポイントを httpx.AsyncClient で検証する。
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cs_risk_agent.main import app


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """テスト用非同期HTTPクライアント."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# ヘルスチェック テスト
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """ヘルスチェックエンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """GET /api/v1/health/ が 200 を返すこと."""
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_check_response_format(self, client):
        """ヘルスチェックのレスポンス形式が正しいこと."""
        response = await client.get("/api/v1/health/")
        data = response.json()
        assert "status" in data
        assert "version" in data


class TestHealthReadiness:
    """レディネスチェックエンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_health_readiness(self, client):
        """GET /api/v1/health/readiness が 200 を返すこと."""
        response = await client.get("/api/v1/health/readiness")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_readiness_components(self, client):
        """レディネスチェックがコンポーネント状態を含むこと."""
        response = await client.get("/api/v1/health/readiness")
        data = response.json()

        components = data["components"]
        assert "database" in components
        assert "redis" in components

        # 各コンポーネントが status フィールドを持つこと
        for name, detail in components.items():
            assert "status" in detail

    @pytest.mark.asyncio
    async def test_readiness_status_value(self, client):
        """レディネスの status が ready/degraded のいずれかであること."""
        response = await client.get("/api/v1/health/readiness")
        data = response.json()
        assert data["status"] in ("ready", "degraded")


# ---------------------------------------------------------------------------
# 実装済みエンドポイント テスト
# ---------------------------------------------------------------------------


class TestImplementedEndpoints:
    """実装済みエンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_list_companies(self, client):
        """/api/v1/companies/ が企業一覧を返すこと."""
        response = await client.get("/api/v1/companies/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_admin_status(self, client):
        """/api/v1/admin/status がシステムステータスを返すこと."""
        response = await client.get("/api/v1/admin/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_budget(self, client):
        """/api/v1/admin/budget が予算情報を返すこと."""
        response = await client.get("/api/v1/admin/budget")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# ミドルウェア テスト
# ---------------------------------------------------------------------------


class TestMiddleware:
    """ミドルウェアの検証."""

    @pytest.mark.asyncio
    async def test_process_time_header(self, client):
        """レスポンスに X-Process-Time-Ms ヘッダーが含まれること."""
        response = await client.get("/api/v1/health/")
        assert "x-process-time-ms" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """CORS プリフライトリクエストが正しく処理されること."""
        response = await client.options(
            "/api/v1/health/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS ミドルウェアが応答する
        assert response.status_code in (200, 204)
