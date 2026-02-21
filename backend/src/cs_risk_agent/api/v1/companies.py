"""企業管理APIエンドポイント."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from cs_risk_agent.api.deps import require_permission
from cs_risk_agent.data.provider import get_data_provider
from cs_risk_agent.data.schemas import CompanyCreate, PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(require_permission("read")),
):
    """企業一覧取得（親会社 + 子会社）."""
    provider = get_data_provider()
    entities = provider.get_subsidiaries_with_risk()
    # 親会社を先頭に
    all_entities = provider.get_all_entities()[:1] + entities

    total = len(all_entities)
    start = (page - 1) * per_page
    items = all_entities[start : start + per_page]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user: dict[str, Any] = Depends(require_permission("read")),
):
    """企業・子会社詳細取得."""
    provider = get_data_provider()
    entity = provider.get_entity_by_id(company_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # リスクスコアを付加
    rs = provider.get_risk_score_by_entity(company_id)
    result = {**entity}
    if rs:
        result["risk_score"] = rs
    return result


@router.post("/", status_code=201)
async def create_company(
    data: CompanyCreate,
    current_user: dict[str, Any] = Depends(require_permission("write")),
):
    """企業登録."""
    company = {
        "id": str(uuid4()),
        **data.model_dump(),
        "created_at": "2024-01-01T00:00:00Z",
    }
    return company
