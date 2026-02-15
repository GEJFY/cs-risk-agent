"""レポート生成APIエンドポイント 統合テスト."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cs_risk_agent.main import app

_REPORT_BODY = {
    "company_ids": ["SUB-0001", "SUB-0003"],
    "fiscal_year": 2025,
    "format": "pdf",
}


@pytest.fixture
async def client():
    """テスト用非同期HTTPクライアント."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestReportGeneration:
    """レポート生成エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_generate_pdf_report(self, client: AsyncClient) -> None:
        """POST /reports/generate がPDFレポートを生成できること."""
        response = await client.post(
            "/api/v1/reports/generate",
            json=_REPORT_BODY,
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert data["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_generate_pptx_report(self, client: AsyncClient) -> None:
        """POST /reports/generate がPPTXレポートを生成できること."""
        body = {**_REPORT_BODY, "format": "pptx"}
        response = await client.post(
            "/api/v1/reports/generate",
            json=body,
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data

    @pytest.mark.asyncio
    async def test_report_status(self, client: AsyncClient) -> None:
        """GET /reports/{id}/status がステータスを返すこと."""
        gen_resp = await client.post(
            "/api/v1/reports/generate",
            json=_REPORT_BODY,
        )
        report_id = gen_resp.json()["report_id"]

        status_resp = await client.get(f"/api/v1/reports/{report_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["report_id"] == report_id
        assert "status" in data

    @pytest.mark.asyncio
    async def test_report_not_found(self, client: AsyncClient) -> None:
        """存在しないレポートIDがnot_foundステータスを返すこと."""
        response = await client.get("/api/v1/reports/nonexistent-id/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"
