"""分析実行APIエンドポイント.

同期実行と非同期 (BackgroundTasks) 実行の両方をサポート。
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks

from cs_risk_agent.analysis.task_manager import get_task_manager
from cs_risk_agent.data.provider import get_data_provider
from cs_risk_agent.data.schemas import AnalysisRequest

router = APIRouter()


@router.post("/run")
async def run_analysis(request: AnalysisRequest):
    """分析実行（同期 - 即座に結果を返す）."""
    provider = get_data_provider()
    results = []
    for cid in request.company_ids:
        rs = provider.get_risk_score_by_entity(cid)
        entity = provider.get_entity_by_id(cid)

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


@router.post("/run-async")
async def run_analysis_async(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """非同期分析実行（バックグラウンドタスク）.

    タスクIDを即座に返し、バックグラウンドで分析を実行。
    /tasks/{task_id} でステータスをポーリング可能。
    """
    manager = get_task_manager()
    task = manager.create_task(
        company_ids=request.company_ids,
        fiscal_year=request.fiscal_year,
        fiscal_quarter=request.fiscal_quarter,
        engines=request.analysis_types,
    )
    background_tasks.add_task(manager.run_analysis, task)
    return {
        "task_id": task.task_id,
        "status": task.status,
        "message": "分析タスクを開始しました。/tasks/{task_id} でステータスを確認してください。",
    }


@router.get("/tasks")
async def list_tasks(limit: int = 20):
    """分析タスク一覧."""
    manager = get_task_manager()
    return {"tasks": manager.list_tasks(limit)}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """タスクステータス取得."""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    if not task:
        return {"task_id": task_id, "status": "not_found"}
    return task.to_dict()


@router.get("/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    """タスク結果取得."""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    if not task:
        return {"task_id": task_id, "status": "not_found", "results": []}
    return {
        "task_id": task_id,
        "status": task.status,
        "results": task.results,
    }


@router.get("/results/{company_id}")
async def get_results(company_id: str):
    """分析結果取得."""
    provider = get_data_provider()
    rs = provider.get_risk_score_by_entity(company_id)
    if rs:
        return {"company_id": company_id, "results": [rs]}
    return {"company_id": company_id, "results": []}


@router.get("/results/{company_id}/trend")
async def get_trend(company_id: str):
    """リスクスコアトレンド取得."""
    provider = get_data_provider()
    rs = provider.get_risk_score_by_entity(company_id)
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
