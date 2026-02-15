"""分析実行APIエンドポイント."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from cs_risk_agent.data.schemas import AnalysisRequest
from cs_risk_agent.demo_loader import DemoData

router = APIRouter()


@router.post("/run")
async def run_analysis(request: AnalysisRequest):
    """分析実行（デモモード: デモデータのリスクスコアを返す）."""
    demo = DemoData.get()
    results = []
    for cid in request.company_ids:
        rs = demo.get_risk_score_by_entity(cid)
        entity = demo.get_entity_by_id(cid)

        if rs:
            results.append({
                "id": str(uuid4()),
                "company_id": cid,
                "company_name": rs.get("entity_name", ""),
                "fiscal_year": request.fiscal_year,
                "fiscal_quarter": request.fiscal_quarter,
                "status": "completed",
                "total_score": rs["total_score"],
                "risk_level": rs["risk_level"],
                "da_score": rs["da_score"],
                "fraud_score": rs["fraud_score"],
                "rule_score": rs["rule_score"],
                "benford_score": rs["benford_score"],
                "risk_factors": rs["risk_factors"],
                "component_details": {},
                "created_at": "2025-12-15T10:00:00Z",
            })
        else:
            results.append({
                "id": str(uuid4()),
                "company_id": cid,
                "company_name": entity.get("name", f"Entity {cid}") if entity else f"Entity {cid}",
                "fiscal_year": request.fiscal_year,
                "fiscal_quarter": request.fiscal_quarter,
                "status": "completed",
                "total_score": 25.0,
                "risk_level": "low",
                "da_score": 20.0,
                "fraud_score": 15.0,
                "rule_score": 25.0,
                "benford_score": 10.0,
                "risk_factors": [],
                "component_details": {},
                "created_at": "2025-12-15T10:00:00Z",
            })

    return {"status": "completed", "results": results}


@router.get("/results/{company_id}")
async def get_results(company_id: str):
    """分析結果取得."""
    demo = DemoData.get()
    rs = demo.get_risk_score_by_entity(company_id)
    if rs:
        return {"company_id": company_id, "results": [rs]}
    return {"company_id": company_id, "results": []}


@router.get("/results/{company_id}/trend")
async def get_trend(company_id: str):
    """リスクスコアトレンド取得."""
    demo = DemoData.get()
    rs = demo.get_risk_score_by_entity(company_id)
    base_score = rs["total_score"] if rs else 30.0

    # 8四半期分のトレンドを生成（徐々にスコアが上昇）
    trends = []
    for q_idx in range(8):
        year = 2025 - (q_idx // 4)
        quarter = 4 - (q_idx % 4)
        score = base_score * (0.7 + 0.3 * (8 - q_idx) / 8)
        trends.append({
            "fiscal_year": year,
            "fiscal_quarter": quarter,
            "total_score": round(score, 1),
        })

    trends.reverse()
    return {"company_id": company_id, "trends": trends}
