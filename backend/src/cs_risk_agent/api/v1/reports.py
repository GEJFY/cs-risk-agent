"""レポート生成APIエンドポイント.

PDF/PPTX形式のリスク分析レポートを生成し、ダウンロードを提供する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from cs_risk_agent.data.schemas import ReportRequest, ReportResponse
from cs_risk_agent.demo_loader import DemoData

logger = logging.getLogger(__name__)

router = APIRouter()

# 生成済みレポートのインメモリストア (デモ用)
_report_store: dict[str, dict] = {}

# 一時ファイル保存先
_REPORT_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "demo_data" / "reports"


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """レポート生成.

    デモデータを使用してPDFまたはPPTX形式のレポートを生成する。
    """
    report_id = str(uuid4())
    demo = DemoData.get()

    # データ準備
    entities = demo.get_all_entities()
    risk_scores = demo.risk_scores
    alerts = demo.alerts
    summary = demo.get_risk_summary()

    # 指定企業のフィルタ
    if request.company_ids:
        target_ids = set(request.company_ids)
        risk_scores = [rs for rs in risk_scores if rs.get("entity_id") in target_ids]
        alerts = [a for a in alerts if a.get("entity_id") in target_ids]

    try:
        fmt = request.format.lower()
        _REPORT_DIR.mkdir(parents=True, exist_ok=True)

        if fmt == "pptx":
            from cs_risk_agent.reports.pptx_generator import generate_risk_report_pptx

            data = generate_risk_report_pptx(
                companies=entities,
                risk_scores=risk_scores,
                alerts=alerts,
                summary=summary,
                fiscal_year=request.fiscal_year,
                language=request.language,
            )
            ext = ".pptx"
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            from cs_risk_agent.reports.pdf_generator import generate_risk_report_pdf

            data = generate_risk_report_pdf(
                companies=entities,
                risk_scores=risk_scores,
                alerts=alerts,
                summary=summary,
                fiscal_year=request.fiscal_year,
                language=request.language,
            )
            ext = ".pdf"
            media_type = "application/pdf"

        # ファイル保存
        filepath = _REPORT_DIR / f"report_{report_id}{ext}"
        filepath.write_bytes(data)

        _report_store[report_id] = {
            "report_id": report_id,
            "status": "completed",
            "format": fmt,
            "filepath": str(filepath),
            "media_type": media_type,
            "download_url": f"/api/v1/reports/{report_id}/download",
            "size_bytes": len(data),
        }

        return ReportResponse(
            report_id=report_id,
            status="completed",
            download_url=f"/api/v1/reports/{report_id}/download",
        )

    except Exception:
        logger.exception("Report generation failed: %s", report_id)
        _report_store[report_id] = {
            "report_id": report_id,
            "status": "failed",
            "download_url": None,
        }
        return ReportResponse(
            report_id=report_id,
            status="failed",
            download_url=None,
        )


@router.get("/{report_id}/status")
async def get_report_status(report_id: str):
    """レポート生成ステータス."""
    if report_id in _report_store:
        info = _report_store[report_id]
        return {
            "report_id": report_id,
            "status": info["status"],
            "download_url": info.get("download_url"),
        }
    return {
        "report_id": report_id,
        "status": "not_found",
        "download_url": None,
    }


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """レポートダウンロード."""
    if report_id not in _report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    info = _report_store[report_id]
    if info["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Report status: {info['status']}")

    filepath = Path(info["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=str(filepath),
        media_type=info["media_type"],
        filename=filepath.name,
    )
