"""API v1 メインルーター - サブルーターの集約."""

from __future__ import annotations

from fastapi import APIRouter

from cs_risk_agent.api.v1.admin import router as admin_router
from cs_risk_agent.api.v1.ai_insights import router as ai_insights_router
from cs_risk_agent.api.v1.analysis import router as analysis_router
from cs_risk_agent.api.v1.companies import router as companies_router
from cs_risk_agent.api.v1.financials import router as financials_router
from cs_risk_agent.api.v1.health import router as health_router
from cs_risk_agent.api.v1.reports import router as reports_router
from cs_risk_agent.api.v1.risk_scores import router as risk_scores_router

api_router = APIRouter()

# ヘルスチェック（認証不要）
api_router.include_router(
    health_router,
    prefix="/health",
    tags=["health"],
)

# 企業情報管理
api_router.include_router(
    companies_router,
    prefix="/companies",
    tags=["companies"],
)

# 分析実行
api_router.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["analysis"],
)

# リスクスコア
api_router.include_router(
    risk_scores_router,
    prefix="/risk-scores",
    tags=["risk-scores"],
)

# AI インサイト
api_router.include_router(
    ai_insights_router,
    prefix="/ai",
    tags=["ai"],
)

# レポート生成
api_router.include_router(
    reports_router,
    prefix="/reports",
    tags=["reports"],
)

# 財務データ
api_router.include_router(
    financials_router,
    prefix="/financials",
    tags=["financials"],
)

# 管理機能
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["admin"],
)
