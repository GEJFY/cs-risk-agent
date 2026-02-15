"""企業管理APIエンドポイント."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from cs_risk_agent.data.schemas import CompanyCreate, CompanyResponse, PaginatedResponse

router = APIRouter()

# デモ用インメモリストア
_demo_companies = [
    {
        "id": str(uuid4()),
        "edinet_code": f"E{10000 + i}",
        "securities_code": f"{1000 + i * 50}",
        "name": name,
        "name_en": None,
        "industry_code": "3250",
        "industry_name": "電気機器",
        "is_listed": True,
        "country": "JPN",
        "created_at": "2024-01-01T00:00:00Z",
    }
    for i, name in enumerate(
        [
            "グローバルテック株式会社",
            "東京エレクトロニクス株式会社",
            "大阪製薬株式会社",
            "未来通信株式会社",
            "サクラ精密工業株式会社",
        ]
    )
]


@router.get("/", response_model=PaginatedResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """企業一覧取得."""
    total = len(_demo_companies)
    start = (page - 1) * per_page
    items = _demo_companies[start : start + per_page]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/{company_id}")
async def get_company(company_id: str):
    """企業詳細取得."""
    for c in _demo_companies:
        if c["id"] == company_id:
            return c
    raise HTTPException(status_code=404, detail="Company not found")


@router.post("/", status_code=201)
async def create_company(data: CompanyCreate):
    """企業登録."""
    company = {
        "id": str(uuid4()),
        **data.model_dump(),
        "created_at": "2024-01-01T00:00:00Z",
    }
    _demo_companies.append(company)
    return company
