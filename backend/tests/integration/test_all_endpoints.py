"""全APIエンドポイント 統合テスト.

admin, ai_insights, analysis, risk_scores, companies エンドポイントのカバレッジ。
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cs_risk_agent.main import app


@pytest.fixture
async def client():
    """テスト用非同期HTTPクライアント."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Admin エンドポイント
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    """管理APIの検証."""

    @pytest.mark.asyncio
    async def test_admin_status(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/status")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "budget" in data
        assert "mode" in data
        for p in ("azure", "aws", "gcp", "ollama"):
            assert p in data["providers"]

    @pytest.mark.asyncio
    async def test_admin_providers(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) == 4

    @pytest.mark.asyncio
    async def test_admin_provider_health(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/providers/azure/health")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "healthy" in data

    @pytest.mark.asyncio
    async def test_admin_budget(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/budget")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_cost(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/cost")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_set_default_provider_invalid(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/admin/providers/invalid_provider/set-default")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_admin_set_default_provider_valid(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/admin/providers/ollama/set-default")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# AI Insights エンドポイント
# ---------------------------------------------------------------------------


class TestAIInsightsEndpoints:
    """AIインサイトAPIの検証."""

    @pytest.mark.asyncio
    async def test_chat_generic(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/ai-insights/chat",
            json={"message": "高リスク企業は?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["provider"] == "demo"

    @pytest.mark.asyncio
    async def test_chat_with_company_id(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/ai-insights/chat",
            json={"message": "リスク分析して", "company_id": "SUB-0006"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert (
            "SUB-0006" in data["response"]
            or "东洋" in data["response"]
            or "リスクスコア" in data["response"]
        )

    @pytest.mark.asyncio
    async def test_chat_shanghai_keyword(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/ai-insights/chat",
            json={"message": "上海子会社について教えて"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "CRITICAL" in data["response"] or "上海" in data["response"]

    @pytest.mark.asyncio
    async def test_get_insights(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/ai-insights/insights/SUB-0003")
        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == "SUB-0003"
        assert "insights" in data

    @pytest.mark.asyncio
    async def test_get_insights_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/ai-insights/insights/NONEXISTENT")
        assert response.status_code == 200
        data = response.json()
        assert data["insights"] == []


# ---------------------------------------------------------------------------
# Analysis エンドポイント
# ---------------------------------------------------------------------------


class TestAnalysisEndpoints:
    """分析実行APIの検証."""

    @pytest.mark.asyncio
    async def test_run_analysis(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ["SUB-0003", "SUB-0006"], "fiscal_year": 2025},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_run_analysis_unknown_company(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ["UNKNOWN"], "fiscal_year": 2025},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_get_results(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analysis/results/SUB-0003")
        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == "SUB-0003"
        assert len(data["results"]) > 0

    @pytest.mark.asyncio
    async def test_get_results_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analysis/results/NONEXISTENT")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_get_trend(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analysis/results/SUB-0003/trend")
        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == "SUB-0003"
        assert len(data["trends"]) == 8


# ---------------------------------------------------------------------------
# Risk Scores エンドポイント
# ---------------------------------------------------------------------------


class TestRiskScoresEndpoints:
    """リスクスコアAPIの検証."""

    @pytest.mark.asyncio
    async def test_list_risk_scores(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] > 0

    @pytest.mark.asyncio
    async def test_list_risk_scores_filter_level(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/", params={"risk_level": "critical"})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["risk_level"] == "critical"

    @pytest.mark.asyncio
    async def test_list_risk_scores_filter_min_score(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/", params={"min_score": 70})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["total_score"] >= 70

    @pytest.mark.asyncio
    async def test_risk_summary(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_companies" in data
        assert "by_level" in data
        assert "avg_score" in data

    @pytest.mark.asyncio
    async def test_high_risk(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/high-risk")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["risk_level"] in ("critical", "high")

    @pytest.mark.asyncio
    async def test_alerts(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_alerts_severity_filter(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/risk-scores/alerts", params={"severity": "critical"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Companies エンドポイント
# ---------------------------------------------------------------------------


class TestCompaniesEndpoints:
    """企業データAPIの検証."""

    @pytest.mark.asyncio
    async def test_list_companies(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/companies/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] > 0

    @pytest.mark.asyncio
    async def test_get_company(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/companies/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "SUB-0001"

    @pytest.mark.asyncio
    async def test_get_company_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/companies/NONEXISTENT")
        assert response.status_code == 404
