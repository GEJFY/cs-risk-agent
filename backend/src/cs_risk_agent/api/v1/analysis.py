"""分析実行APIエンドポイント."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from cs_risk_agent.data.schemas import AnalysisRequest, AnalysisResponse

router = APIRouter()


@router.post("/run")
async def run_analysis(request: AnalysisRequest):
    """分析実行."""
    results = []
    for cid in request.company_ids:
        results.append(
            {
                "id": str(uuid4()),
                "company_id": cid,
                "company_name": f"Company {cid[:8]}",
                "fiscal_year": request.fiscal_year,
                "fiscal_quarter": request.fiscal_quarter,
                "status": "completed",
                "total_score": 45.5,
                "risk_level": "medium",
                "da_score": 35.0,
                "fraud_score": 50.0,
                "rule_score": 48.0,
                "benford_score": 40.0,
                "risk_factors": ["売上高成長率の異常", "運転資本比率の悪化"],
                "component_details": {},
                "created_at": "2024-01-01T00:00:00Z",
            }
        )
    return {"status": "completed", "results": results}


@router.get("/results/{company_id}")
async def get_results(company_id: str):
    """分析結果取得."""
    return {"company_id": company_id, "results": []}


@router.get("/results/{company_id}/trend")
async def get_trend(company_id: str):
    """リスクスコアトレンド取得."""
    return {
        "company_id": company_id,
        "trends": [
            {"fiscal_year": 2024, "fiscal_quarter": q, "total_score": 40 + q * 5}
            for q in range(1, 5)
        ],
    }
