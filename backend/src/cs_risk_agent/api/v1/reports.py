"""レポート生成APIエンドポイント."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from cs_risk_agent.data.schemas import ReportRequest, ReportResponse

router = APIRouter()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """レポート生成."""
    report_id = str(uuid4())
    return ReportResponse(
        report_id=report_id,
        status="queued",
        download_url=None,
    )


@router.get("/{report_id}/status")
async def get_report_status(report_id: str):
    """レポート生成ステータス."""
    return {
        "report_id": report_id,
        "status": "completed",
        "download_url": f"/api/v1/reports/{report_id}/download",
    }
