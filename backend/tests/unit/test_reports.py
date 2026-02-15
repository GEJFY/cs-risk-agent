"""レポート生成モジュールのユニットテスト."""

from __future__ import annotations

from cs_risk_agent.reports.pdf_generator import generate_risk_report_pdf
from cs_risk_agent.reports.pptx_generator import generate_risk_report_pptx

_COMPANIES = [
    {"id": "C1", "name": "Test Corp", "country": "JPN", "segment": "機械"},
    {"id": "S1", "name": "Sub Corp", "country": "USA", "segment": "エネルギー"},
]

_RISK_SCORES = [
    {
        "entity_id": "S1",
        "entity_name": "Sub Corp",
        "total_score": 75.0,
        "risk_level": "high",
        "da_score": 20.0,
        "fraud_score": 25.0,
        "rule_score": 15.0,
        "benford_score": 15.0,
        "risk_factors": ["売上急増", "CF逆相関"],
    },
]

_ALERTS = [
    {
        "id": "A1",
        "entity_id": "S1",
        "title": "テストアラート",
        "severity": "high",
        "description": "テスト用アラート",
        "created_at": "2025-01-15T10:00:00Z",
    },
]

_SUMMARY = {
    "total_companies": 2,
    "by_level": {"critical": 0, "high": 1, "medium": 0, "low": 1},
    "avg_score": 40.0,
}


class TestPdfGenerator:
    """PDF生成のテスト."""

    def test_generate_pdf(self) -> None:
        data = generate_risk_report_pdf(
            companies=_COMPANIES,
            risk_scores=_RISK_SCORES,
            alerts=_ALERTS,
            summary=_SUMMARY,
            fiscal_year=2025,
            language="ja",
        )
        assert isinstance(data, bytes)
        assert len(data) > 0
        # PDF magic bytes
        assert data[:4] == b"%PDF"

    def test_generate_pdf_empty_data(self) -> None:
        data = generate_risk_report_pdf(
            companies=[],
            risk_scores=[],
            alerts=[],
            summary={"total_companies": 0, "by_level": {}, "avg_score": 0},
            fiscal_year=2025,
            language="ja",
        )
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_pdf_english(self) -> None:
        data = generate_risk_report_pdf(
            companies=_COMPANIES,
            risk_scores=_RISK_SCORES,
            alerts=_ALERTS,
            summary=_SUMMARY,
            fiscal_year=2025,
            language="en",
        )
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestPptxGenerator:
    """PPTX生成のテスト."""

    def test_generate_pptx(self) -> None:
        data = generate_risk_report_pptx(
            companies=_COMPANIES,
            risk_scores=_RISK_SCORES,
            alerts=_ALERTS,
            summary=_SUMMARY,
            fiscal_year=2025,
            language="ja",
        )
        assert isinstance(data, bytes)
        assert len(data) > 0
        # PPTX (ZIP) magic bytes
        assert data[:2] == b"PK"

    def test_generate_pptx_empty_data(self) -> None:
        data = generate_risk_report_pptx(
            companies=[],
            risk_scores=[],
            alerts=[],
            summary={"total_companies": 0, "by_level": {}, "avg_score": 0},
            fiscal_year=2025,
            language="ja",
        )
        assert isinstance(data, bytes)
        assert len(data) > 0
