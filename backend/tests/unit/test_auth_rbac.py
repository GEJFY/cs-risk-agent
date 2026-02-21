"""認証・認可 (JWT + RBAC) テスト."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cs_risk_agent.core.security import Role, create_access_token
from cs_risk_agent.main import app


def _auth_header(role: Role = Role.ADMIN, username: str = "testuser") -> dict[str, str]:
    """テスト用 Authorization ヘッダーを生成."""
    token = create_access_token(subject=username, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    """テスト用非同期HTTPクライアント."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestLoginEndpoint:
    """ログインエンドポイントテスト."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """正しい認証情報でログインできること."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client):
        """不正なパスワードで401を返すこと."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client):
        """存在しないユーザーで401を返すこと."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "unknown"},
        )
        assert response.status_code == 401


class TestAuthRequired:
    """認証必須エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client):
        """トークンなしで401が返ること."""
        response = await client.get("/api/v1/companies/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        """不正なトークンで401が返ること."""
        response = await client.get(
            "/api/v1/companies/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_200(self, client):
        """有効なトークンで200が返ること."""
        response = await client.get(
            "/api/v1/companies/",
            headers=_auth_header(Role.ADMIN),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client):
        """ヘルスチェックは認証不要であること."""
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200


class TestRBAC:
    """ロールベースアクセス制御テスト."""

    @pytest.mark.asyncio
    async def test_viewer_can_read(self, client):
        """Viewerは閲覧可能であること."""
        response = await client.get(
            "/api/v1/companies/",
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_write(self, client):
        """Viewerは書き込み不可であること."""
        response = await client.post(
            "/api/v1/companies/",
            json={"name": "テスト企業", "country": "JP"},
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_run_analysis(self, client):
        """Viewerは分析実行不可であること."""
        response = await client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ["C001"], "fiscal_year": 2025, "fiscal_quarter": 4},
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_auditor_can_run_analysis(self, client):
        """Auditorは分析実行可能であること."""
        response = await client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ["SUB001"], "fiscal_year": 2025, "fiscal_quarter": 4},
            headers=_auth_header(Role.AUDITOR),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_admin(self, client):
        """Viewerは管理エンドポイントにアクセス不可であること."""
        response = await client.get(
            "/api/v1/admin/status",
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_access_admin(self, client):
        """Adminは管理エンドポイントにアクセス可能であること."""
        response = await client.get(
            "/api/v1/admin/status",
            headers=_auth_header(Role.ADMIN),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auditor_can_generate_report(self, client):
        """Auditorはレポート生成可能であること."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={
                "company_ids": [],
                "fiscal_year": 2025,
                "format": "pdf",
                "sections": ["summary"],
                "language": "ja",
            },
            headers=_auth_header(Role.AUDITOR),
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_generate_report(self, client):
        """Viewerはレポート生成不可であること."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={
                "company_ids": [],
                "fiscal_year": 2025,
                "format": "pdf",
                "sections": ["summary"],
                "language": "ja",
            },
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_all_roles_for_read_endpoints(self, client):
        """全ロールがreadパーミッションのエンドポイントにアクセスできること."""
        read_endpoints = [
            "/api/v1/risk-scores/",
            "/api/v1/risk-scores/summary",
            "/api/v1/risk-scores/high-risk",
            "/api/v1/financials/statements",
        ]
        for role in [Role.ADMIN, Role.AUDITOR, Role.CFO, Role.VIEWER]:
            for endpoint in read_endpoints:
                response = await client.get(
                    endpoint,
                    headers=_auth_header(role),
                )
                assert response.status_code == 200, (
                    f"Role {role.value} should access {endpoint} but got {response.status_code}"
                )


class TestSettingsAPI:
    """設定APIテスト."""

    @pytest.mark.asyncio
    async def test_get_settings_with_read(self, client):
        """read権限で設定取得可能であること."""
        response = await client.get(
            "/api/v1/admin/settings",
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "thresholds" in data

    @pytest.mark.asyncio
    async def test_update_settings_admin_only(self, client):
        """admin権限で設定更新可能であること."""
        payload = {
            "notifications": {
                "critical_risk_alert": True,
                "analysis_complete": False,
                "daily_summary": True,
                "budget_alert": True,
            },
            "thresholds": {"critical": 90, "high": 70, "medium": 50},
        }
        response = await client.put(
            "/api/v1/admin/settings",
            json=payload,
            headers=_auth_header(Role.ADMIN),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["settings"]["thresholds"]["critical"] == 90
        assert data["settings"]["notifications"]["daily_summary"] is True

    @pytest.mark.asyncio
    async def test_update_settings_viewer_forbidden(self, client):
        """viewer権限で設定更新不可であること."""
        payload = {
            "notifications": {
                "critical_risk_alert": True,
                "analysis_complete": True,
                "daily_summary": False,
                "budget_alert": True,
            },
            "thresholds": {"critical": 80, "high": 60, "medium": 40},
        }
        response = await client.put(
            "/api/v1/admin/settings",
            json=payload,
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_settings_validates_thresholds(self, client):
        """閾値が0-100のバリデーションが効くこと."""
        payload = {
            "notifications": {
                "critical_risk_alert": True,
                "analysis_complete": True,
                "daily_summary": False,
                "budget_alert": True,
            },
            "thresholds": {"critical": 150, "high": 60, "medium": 40},
        }
        response = await client.put(
            "/api/v1/admin/settings",
            json=payload,
            headers=_auth_header(Role.ADMIN),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_settings_roundtrip(self, client):
        """設定の保存→取得が正しく動作すること."""
        payload = {
            "notifications": {
                "critical_risk_alert": False,
                "analysis_complete": True,
                "daily_summary": True,
                "budget_alert": False,
            },
            "thresholds": {"critical": 85, "high": 65, "medium": 45},
        }
        # 保存
        await client.put(
            "/api/v1/admin/settings",
            json=payload,
            headers=_auth_header(Role.ADMIN),
        )
        # 取得して検証
        response = await client.get(
            "/api/v1/admin/settings",
            headers=_auth_header(Role.VIEWER),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thresholds"]["critical"] == 85
        assert data["notifications"]["daily_summary"] is True
