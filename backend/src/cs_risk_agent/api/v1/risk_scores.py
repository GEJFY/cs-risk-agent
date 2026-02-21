"""リスクスコアAPIエンドポイント."""

from __future__ import annotations

from fastapi import APIRouter, Query

from cs_risk_agent.data.provider import get_data_provider

router = APIRouter()


@router.get("/")
async def list_risk_scores(
    risk_level: str | None = None,
    min_score: float | None = None,
):
    """リスクスコア一覧."""
    provider = get_data_provider()
    scores = list(provider.risk_scores)

    if risk_level:
        scores = [s for s in scores if s.get("risk_level") == risk_level]
    if min_score is not None:
        scores = [s for s in scores if s.get("total_score", 0) >= min_score]

    return {"items": scores, "total": len(scores)}


@router.get("/summary")
async def get_summary():
    """リスクサマリー."""
    provider = get_data_provider()
    return provider.get_risk_summary()


@router.get("/high-risk")
async def get_high_risk():
    """高リスク企業一覧."""
    provider = get_data_provider()
    high = [
        s for s in provider.risk_scores
        if s.get("risk_level") in ("critical", "high")
    ]
    high.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    return {"items": high, "total": len(high)}


@router.get("/alerts")
async def get_alerts(severity: str | None = None):
    """アラート一覧."""
    provider = get_data_provider()
    return {"items": provider.get_alerts_by_severity(severity), "total": len(provider.alerts)}
