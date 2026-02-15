"""Pydantic スキーマのユニットテスト."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cs_risk_agent.data.schemas import (
    AIChatRequest,
    AIChatResponse,
    AnalysisRequest,
    AnalysisStatusEnum,
    CompanyCreate,
    HealthResponse,
    PaginatedResponse,
    ReadinessResponse,
    ReportRequest,
    ReportResponse,
    RiskLevelEnum,
)


class TestEnums:
    """Enum値の検証."""

    def test_risk_level_values(self) -> None:
        assert RiskLevelEnum.CRITICAL == "critical"
        assert RiskLevelEnum.HIGH == "high"
        assert RiskLevelEnum.MEDIUM == "medium"
        assert RiskLevelEnum.LOW == "low"

    def test_analysis_status_values(self) -> None:
        assert AnalysisStatusEnum.PENDING == "pending"
        assert AnalysisStatusEnum.RUNNING == "running"
        assert AnalysisStatusEnum.COMPLETED == "completed"
        assert AnalysisStatusEnum.FAILED == "failed"


class TestAnalysisRequest:
    """分析リクエストの検証."""

    def test_valid_request(self) -> None:
        req = AnalysisRequest(company_ids=["SUB-0001"], fiscal_year=2025)
        assert req.company_ids == ["SUB-0001"]
        assert req.fiscal_quarter == 4
        assert req.ai_tier == "cost_effective"

    def test_empty_company_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisRequest(company_ids=[], fiscal_year=2025)

    def test_custom_analysis_types(self) -> None:
        req = AnalysisRequest(
            company_ids=["C1"],
            fiscal_year=2025,
            analysis_types=["da", "benford"],
        )
        assert req.analysis_types == ["da", "benford"]


class TestReportRequest:
    """レポートリクエストの検証."""

    def test_valid_request(self) -> None:
        req = ReportRequest(company_ids=["SUB-0001"], fiscal_year=2025)
        assert req.format == "pdf"
        assert req.language == "ja"
        assert len(req.sections) == 5

    def test_pptx_format(self) -> None:
        req = ReportRequest(company_ids=["SUB-0001"], fiscal_year=2025, format="pptx")
        assert req.format == "pptx"


class TestReportResponse:
    """レポートレスポンスの検証."""

    def test_valid_response(self) -> None:
        resp = ReportResponse(
            report_id="abc-123", status="completed", download_url="/reports/abc-123/download"
        )
        assert resp.report_id == "abc-123"

    def test_no_download_url(self) -> None:
        resp = ReportResponse(report_id="abc-123", status="failed")
        assert resp.download_url is None


class TestAIChatModels:
    """AIチャットリクエスト/レスポンスの検証."""

    def test_chat_request_minimal(self) -> None:
        req = AIChatRequest(message="テスト")
        assert req.message == "テスト"
        assert req.company_id is None
        assert req.tier == "cost_effective"

    def test_chat_request_full(self) -> None:
        req = AIChatRequest(
            message="分析して",
            company_id="SUB-0001",
            provider="azure",
            tier="sota",
        )
        assert req.provider == "azure"

    def test_chat_response(self) -> None:
        resp = AIChatResponse(response="結果", provider="demo", model="fallback")
        assert resp.tokens_used == 0
        assert resp.cost_usd == 0.0


class TestCompanyModels:
    """企業スキーマの検証."""

    def test_company_create(self) -> None:
        c = CompanyCreate(name="Test Corp")
        assert c.name == "Test Corp"
        assert c.country == "JPN"
        assert c.is_listed is True

    def test_paginated_response(self) -> None:
        pr = PaginatedResponse(items=[{"id": 1}], total=1)
        assert pr.page == 1
        assert pr.per_page == 20


class TestHealthModels:
    """ヘルスチェックスキーマの検証."""

    def test_health_response(self) -> None:
        h = HealthResponse(status="ok", version="0.1.0")
        assert h.status == "ok"

    def test_readiness_response(self) -> None:
        r = ReadinessResponse(
            status="ready",
            database="connected",
            redis="connected",
            providers={"azure": True, "aws": False},
        )
        assert r.providers["azure"] is True
