"""API v1 全エンドポイント カバレッジテスト."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from cs_risk_agent.core.security import Role, create_access_token
from cs_risk_agent.demo_loader import DemoData
from cs_risk_agent.main import app


def _auth_headers(role: Role = Role.ADMIN) -> dict[str, str]:
    """テスト用 Authorization ヘッダー."""
    token = create_access_token(subject="testuser", role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client():
    """認証ヘッダー付きテストクライアント."""
    c = TestClient(app)
    # デフォルトで admin トークンをヘッダーに付与
    c.headers.update(_auth_headers(Role.ADMIN))
    return c


@pytest.fixture()
def entity_id():
    """デモデータから有効なエンティティIDを取得."""
    demo = DemoData.get()
    entities = demo.get_all_entities()
    if entities:
        return entities[0].get("id", entities[0].get("company_id", ""))
    return "unknown"


@pytest.fixture()
def risky_entity_id():
    """リスクスコア付きエンティティID."""
    demo = DemoData.get()
    for rs in demo.risk_scores:
        if rs.get("risk_factors"):
            return rs["entity_id"]
    return None


@pytest.fixture()
def subsidiary_id():
    """子会社ID."""
    demo = DemoData.get()
    if demo.subsidiaries:
        return demo.subsidiaries[0].get("id", demo.subsidiaries[0].get("subsidiary_id", ""))
    return None


# --- Companies ---


class TestCompaniesEndpoints:
    """企業APIエンドポイントテスト."""

    def test_list_companies(self, client) -> None:
        r = client.get("/api/v1/companies/")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0

    def test_list_companies_pagination(self, client) -> None:
        r = client.get("/api/v1/companies/?page=1&per_page=3")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 3
        assert data["per_page"] == 3

    def test_list_companies_page2(self, client) -> None:
        r = client.get("/api/v1/companies/?page=2&per_page=5")
        assert r.status_code == 200

    def test_get_company_found(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/companies/{entity_id}")
        assert r.status_code == 200

    def test_get_company_with_risk(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No risky entity")
        r = client.get(f"/api/v1/companies/{risky_entity_id}")
        assert r.status_code == 200

    def test_get_company_not_found(self, client) -> None:
        r = client.get("/api/v1/companies/NONEXISTENT-ID")
        assert r.status_code == 404

    def test_create_company(self, client) -> None:
        r = client.post("/api/v1/companies/", json={"name": "テスト株式会社"})
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == "テスト株式会社"

    def test_create_company_full(self, client) -> None:
        r = client.post(
            "/api/v1/companies/",
            json={
                "name": "Test Corp",
                "edinet_code": "E99999",
                "securities_code": "9999",
                "industry_code": "3000",
                "country": "JPN",
            },
        )
        assert r.status_code == 201


# --- Reports ---


class TestReportsEndpoints:
    """レポートAPIエンドポイントテスト."""

    def test_generate_pdf_report(self, client) -> None:
        r = client.post(
            "/api/v1/reports/generate",
            json={"company_ids": [], "fiscal_year": 2025, "format": "pdf", "language": "ja"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "report_id" in data
        assert data["status"] in ("completed", "failed")

    def test_generate_pptx_report(self, client) -> None:
        r = client.post(
            "/api/v1/reports/generate",
            json={"company_ids": [], "fiscal_year": 2025, "format": "pptx", "language": "ja"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("completed", "failed")

    def test_report_status_not_found(self, client) -> None:
        r = client.get("/api/v1/reports/unknown-id/status")
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    def test_download_not_found(self, client) -> None:
        r = client.get("/api/v1/reports/unknown-id/download")
        assert r.status_code == 404

    def test_generate_check_status_and_download(self, client) -> None:
        gen = client.post(
            "/api/v1/reports/generate",
            json={"company_ids": [], "fiscal_year": 2025, "format": "pdf"},
        )
        data = gen.json()
        rid = data["report_id"]

        status = client.get(f"/api/v1/reports/{rid}/status")
        assert status.status_code == 200

        if data["status"] == "completed":
            dl = client.get(f"/api/v1/reports/{rid}/download")
            assert dl.status_code == 200

    def test_generate_with_company_filter(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No entity for filter")
        r = client.post(
            "/api/v1/reports/generate",
            json={"company_ids": [risky_entity_id], "fiscal_year": 2025},
        )
        assert r.status_code == 200


# --- Risk Scores ---


class TestRiskScoresEndpoints:
    """リスクスコアAPIエンドポイントテスト."""

    def test_list_risk_scores(self, client) -> None:
        r = client.get("/api/v1/risk-scores/")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_risk_scores_filter_level(self, client) -> None:
        r = client.get("/api/v1/risk-scores/?risk_level=critical")
        assert r.status_code == 200

    def test_list_risk_scores_filter_min_score(self, client) -> None:
        r = client.get("/api/v1/risk-scores/?min_score=50")
        assert r.status_code == 200

    def test_summary(self, client) -> None:
        r = client.get("/api/v1/risk-scores/summary")
        assert r.status_code == 200

    def test_high_risk(self, client) -> None:
        r = client.get("/api/v1/risk-scores/high-risk")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_alerts(self, client) -> None:
        r = client.get("/api/v1/risk-scores/alerts")
        assert r.status_code == 200

    def test_alerts_severity(self, client) -> None:
        r = client.get("/api/v1/risk-scores/alerts?severity=critical")
        assert r.status_code == 200


# --- AI Insights ---


class TestAIInsightsEndpoints:
    """AIインサイトAPIエンドポイントテスト."""

    def test_chat_generic(self, client) -> None:
        r = client.post("/api/v1/ai/chat", json={"message": "概要を教えて"})
        assert r.status_code == 200
        data = r.json()
        assert "response" in data

    def test_chat_with_company_id(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No risky entity")
        r = client.post(
            "/api/v1/ai/chat",
            json={"message": "リスク分析", "company_id": risky_entity_id},
        )
        assert r.status_code == 200

    def test_chat_with_nonexistent_company(self, client) -> None:
        r = client.post(
            "/api/v1/ai/chat",
            json={"message": "分析", "company_id": "NONEXISTENT"},
        )
        assert r.status_code == 200

    def test_chat_shanghai_keyword(self, client) -> None:
        r = client.post("/api/v1/ai/chat", json={"message": "上海子会社のリスク"})
        assert r.status_code == 200

    def test_chat_tier_cost_effective(self, client) -> None:
        r = client.post(
            "/api/v1/ai/chat",
            json={"message": "test", "tier": "cost_effective"},
        )
        assert r.status_code == 200

    def test_chat_tier_sota(self, client) -> None:
        r = client.post("/api/v1/ai/chat", json={"message": "test", "tier": "sota"})
        assert r.status_code == 200

    def test_insights_with_risk(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No risky entity")
        r = client.get(f"/api/v1/ai/insights/{risky_entity_id}")
        assert r.status_code == 200
        assert len(r.json()["insights"]) > 0

    def test_insights_not_found(self, client) -> None:
        r = client.get("/api/v1/ai/insights/NONEXISTENT")
        assert r.status_code == 200
        assert r.json()["insights"] == []


# --- Health ---


class TestHealthEndpoints:
    """ヘルスチェックAPIテスト."""

    def test_health_check(self, client) -> None:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_readiness_check(self, client) -> None:
        r = client.get("/api/v1/health/readiness")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ready", "degraded")
        assert "components" in data
        assert "database" in data["components"]
        assert "redis" in data["components"]


# --- Analysis ---


class TestAnalysisEndpoints:
    """分析APIエンドポイントテスト."""

    def test_run_analysis_known(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No entity")
        r = client.post(
            "/api/v1/analysis/run",
            json={"company_ids": [risky_entity_id], "fiscal_year": 2025},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
        assert len(r.json()["results"]) == 1

    def test_run_analysis_unknown(self, client) -> None:
        r = client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ["UNKNOWN-ID"], "fiscal_year": 2025},
        )
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["total_score"] == 25.0

    def test_run_analysis_multiple(self, client) -> None:
        demo = DemoData.get()
        ids = [e.get("id", e.get("company_id", "")) for e in demo.get_all_entities()[:3]]
        r = client.post(
            "/api/v1/analysis/run",
            json={"company_ids": ids, "fiscal_year": 2025},
        )
        assert r.status_code == 200

    def test_get_results_found(self, client, risky_entity_id) -> None:
        if risky_entity_id is None:
            pytest.skip("No entity")
        r = client.get(f"/api/v1/analysis/results/{risky_entity_id}")
        assert r.status_code == 200

    def test_get_results_not_found(self, client) -> None:
        r = client.get("/api/v1/analysis/results/UNKNOWN")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_get_trend(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/analysis/results/{entity_id}/trend")
        assert r.status_code == 200
        assert len(r.json()["trends"]) == 8

    def test_get_trend_unknown(self, client) -> None:
        r = client.get("/api/v1/analysis/results/UNKNOWN/trend")
        assert r.status_code == 200
        assert len(r.json()["trends"]) == 8


# --- Financials ---


class TestFinancialsEndpoints:
    """財務データAPIエンドポイントテスト."""

    def test_statements_all(self, client) -> None:
        r = client.get("/api/v1/financials/statements")
        assert r.status_code == 200

    def test_statements_by_entity(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/statements?entity_id={entity_id}")
        assert r.status_code == 200

    def test_statements_by_entity_year(self, client, entity_id) -> None:
        r = client.get(
            f"/api/v1/financials/statements?entity_id={entity_id}&fiscal_year=2025"
        )
        assert r.status_code == 200

    def test_trend(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/statements/{entity_id}/trend")
        assert r.status_code == 200

    def test_ratios_entity(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/ratios/{entity_id}")
        assert r.status_code == 200

    def test_ratios_all(self, client) -> None:
        r = client.get("/api/v1/financials/ratios")
        assert r.status_code == 200

    def test_trial_balance(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/trial-balance/{entity_id}")
        assert r.status_code == 200

    def test_journal_entries(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/journal-entries/{entity_id}")
        assert r.status_code == 200

    def test_journal_entries_anomaly(self, client, entity_id) -> None:
        r = client.get(
            f"/api/v1/financials/journal-entries/{entity_id}?anomaly_only=true"
        )
        assert r.status_code == 200

    def test_journal_entries_limit(self, client, entity_id) -> None:
        r = client.get(
            f"/api/v1/financials/journal-entries/{entity_id}?limit=5"
        )
        assert r.status_code == 200

    def test_balance_sheet(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/balance-sheet/{entity_id}")
        assert r.status_code == 200

    def test_income_statement(self, client, entity_id) -> None:
        r = client.get(f"/api/v1/financials/income-statement/{entity_id}")
        assert r.status_code == 200

    def test_financials_unknown_entity(self, client) -> None:
        r = client.get("/api/v1/financials/statements?entity_id=UNKNOWN")
        assert r.status_code == 200
        r2 = client.get("/api/v1/financials/statements/UNKNOWN/trend")
        assert r2.status_code == 200
        r3 = client.get("/api/v1/financials/balance-sheet/UNKNOWN")
        assert r3.status_code == 200
        r4 = client.get("/api/v1/financials/income-statement/UNKNOWN")
        assert r4.status_code == 200


# --- Admin ---


class TestAdminEndpoints:
    """管理APIエンドポイントテスト."""

    def test_status(self, client) -> None:
        r = client.get("/api/v1/admin/status")
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        assert "mode" in data

    def test_providers(self, client) -> None:
        r = client.get("/api/v1/admin/providers")
        assert r.status_code == 200
        assert "providers" in r.json()

    def test_provider_health_registered(self, client) -> None:
        r = client.get("/api/v1/admin/providers/ollama/health")
        assert r.status_code == 200

    def test_provider_health_unknown(self, client) -> None:
        r = client.get("/api/v1/admin/providers/nonexistent/health")
        assert r.status_code == 200

    def test_budget(self, client) -> None:
        r = client.get("/api/v1/admin/budget")
        assert r.status_code == 200

    def test_cost(self, client) -> None:
        r = client.get("/api/v1/admin/cost")
        assert r.status_code == 200

    def test_set_default_valid(self, client) -> None:
        import os

        from cs_risk_agent.config import get_settings

        original = os.environ.get("AI_DEFAULT_PROVIDER")
        try:
            r = client.post("/api/v1/admin/providers/ollama/set-default")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"
        finally:
            if original is None:
                os.environ.pop("AI_DEFAULT_PROVIDER", None)
            else:
                os.environ["AI_DEFAULT_PROVIDER"] = original
            get_settings.cache_clear()

    def test_set_default_invalid(self, client) -> None:
        r = client.post("/api/v1/admin/providers/invalid_provider/set-default")
        assert r.status_code == 200
        assert "error" in r.json()
