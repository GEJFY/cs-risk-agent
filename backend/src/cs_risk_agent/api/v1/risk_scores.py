"""リスクスコアAPIエンドポイント."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/")
async def list_risk_scores(
    risk_level: str | None = None,
    min_score: float | None = None,
):
    """リスクスコア一覧."""
    return {"items": [], "total": 0}


@router.get("/summary")
async def get_summary():
    """リスクサマリー."""
    return {
        "total_companies": 50,
        "by_level": {"critical": 3, "high": 8, "medium": 22, "low": 17},
        "avg_score": 42.5,
    }


@router.get("/high-risk")
async def get_high_risk():
    """高リスク企業一覧."""
    return {"items": [], "total": 0}
