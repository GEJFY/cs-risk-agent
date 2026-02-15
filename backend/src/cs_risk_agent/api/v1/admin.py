"""管理APIエンドポイント."""

from __future__ import annotations

from fastapi import APIRouter

from cs_risk_agent.ai.router import get_ai_router

router = APIRouter()


@router.get("/status")
async def get_status():
    """システムステータス取得."""
    try:
        return get_ai_router().get_status()
    except Exception:
        return {
            "mode": "cloud",
            "default_provider": "azure",
            "providers": {},
            "budget": {},
            "cost": {},
        }


@router.get("/budget")
async def get_budget():
    """予算ステータス."""
    try:
        return get_ai_router()._circuit_breaker.to_dict()
    except Exception:
        return {
            "state": "closed",
            "monthly_limit_usd": 500,
            "current_spend_usd": 0,
        }


@router.get("/providers")
async def get_providers():
    """プロバイダー一覧."""
    try:
        return get_ai_router()._registry.to_dict()
    except Exception:
        return {}
