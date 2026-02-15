"""Pydantic スキーマ定義 - API リクエスト/レスポンス."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- 共通 ---

class RiskLevelEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PaginatedResponse(BaseModel):
    """ページネーション付きレスポンス."""

    items: list[Any]
    total: int
    page: int = 1
    per_page: int = 20
    pages: int = 1


# --- 企業 ---

class CompanyCreate(BaseModel):
    edinet_code: str | None = None
    securities_code: str | None = None
    name: str
    name_en: str | None = None
    industry_code: str | None = None
    industry_name: str | None = None
    fiscal_year_end: int | None = None
    is_listed: bool = True
    country: str = "JPN"


class CompanyResponse(BaseModel):
    id: str
    edinet_code: str | None
    securities_code: str | None
    name: str
    name_en: str | None
    industry_code: str | None
    industry_name: str | None
    is_listed: bool
    country: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyWithRisk(CompanyResponse):
    latest_risk_score: float | None = None
    latest_risk_level: RiskLevelEnum | None = None
    subsidiary_count: int = 0


# --- 分析 ---

class AnalysisRequest(BaseModel):
    """分析実行リクエスト."""

    company_ids: list[str] = Field(min_length=1)
    fiscal_year: int
    fiscal_quarter: int = 4
    analysis_types: list[str] = Field(
        default=["da", "fraud", "rule", "benford"],
        description="実行する分析タイプ",
    )
    ai_tier: str = "cost_effective"
    force_rerun: bool = False


class AnalysisResponse(BaseModel):
    """分析結果レスポンス."""

    id: str
    company_id: str
    company_name: str
    fiscal_year: int
    fiscal_quarter: int
    status: AnalysisStatusEnum
    total_score: float | None = None
    risk_level: RiskLevelEnum | None = None
    da_score: float | None = None
    fraud_score: float | None = None
    rule_score: float | None = None
    benford_score: float | None = None
    risk_factors: list[str] = []
    component_details: dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


# --- リスクスコア ---

class RiskScoreResponse(BaseModel):
    """リスクスコアレスポンス."""

    id: str
    company_id: str
    fiscal_year: int
    fiscal_quarter: int
    total_score: float
    risk_level: RiskLevelEnum
    da_score: float | None
    fraud_score: float | None
    rule_score: float | None
    benford_score: float | None
    component_details: dict[str, Any] | None
    risk_factors: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskTrendResponse(BaseModel):
    """リスクトレンドレスポンス."""

    company_id: str
    company_name: str
    trends: list[dict[str, Any]]


# --- AI インサイト ---

class AIInsightRequest(BaseModel):
    """AIインサイトリクエスト."""

    company_id: str
    fiscal_year: int
    query: str | None = None
    provider: str | None = None
    tier: str = "cost_effective"
    data_classification: str = "general"


class AIInsightResponse(BaseModel):
    """AIインサイトレスポンス."""

    id: str
    company_id: str
    fiscal_year: int
    probe_type: str
    insight_text: str
    severity: str
    confidence: float | None
    evidence: dict[str, Any] | None
    ai_provider: str | None
    ai_model: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AIChatRequest(BaseModel):
    """AIチャットリクエスト."""

    message: str
    company_id: str | None = None
    context: dict[str, Any] = {}
    provider: str | None = None
    tier: str = "cost_effective"
    stream: bool = False


class AIChatResponse(BaseModel):
    """AIチャットレスポンス."""

    response: str
    provider: str
    model: str
    tokens_used: int = 0
    cost_usd: float = 0.0


# --- レポート ---

class ReportRequest(BaseModel):
    """レポート生成リクエスト."""

    company_ids: list[str]
    fiscal_year: int
    format: str = "pdf"  # pdf, pptx
    sections: list[str] = [
        "executive_summary",
        "financial_overview",
        "risk_assessment",
        "model_analysis",
        "ai_findings",
    ]
    language: str = "ja"


class ReportResponse(BaseModel):
    """レポート生成レスポンス."""

    report_id: str
    status: str
    download_url: str | None = None


# --- 管理 ---

class ProviderStatusResponse(BaseModel):
    """プロバイダーステータスレスポンス."""

    providers: dict[str, dict[str, Any]]
    budget: dict[str, Any]
    cost: dict[str, Any]
    model_tiers: dict[str, Any]


class BudgetStatusResponse(BaseModel):
    """予算ステータスレスポンス."""

    state: str
    monthly_limit_usd: float
    current_spend_usd: float
    remaining_usd: float
    usage_ratio: float
    request_count: int
    by_provider: dict[str, float]
    by_model: dict[str, float]


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    redis: str
    providers: dict[str, bool]
