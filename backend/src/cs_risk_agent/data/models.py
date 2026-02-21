"""SQLAlchemy データモデル定義.

連結子会社リスク分析に必要な全テーブルを定義する。
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """ベースモデル."""

    pass


class TimestampMixin:
    """タイムスタンプ共通カラム."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class RiskLevel(StrEnum):
    """リスクレベル."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisStatus(StrEnum):
    """分析ステータス."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# --- 企業・子会社 ---

class Company(Base, TimestampMixin):
    """企業マスタ."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    edinet_code: Mapped[str | None] = mapped_column(String(10), unique=True, index=True)
    securities_code: Mapped[str | None] = mapped_column(String(10), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    industry_code: Mapped[str | None] = mapped_column(String(10), index=True)
    industry_name: Mapped[str | None] = mapped_column(String(100))
    fiscal_year_end: Mapped[int | None] = mapped_column(Integer)  # 月(1-12)
    is_listed: Mapped[bool] = mapped_column(Boolean, default=True)
    country: Mapped[str] = mapped_column(String(3), default="JPN")

    subsidiaries: Mapped[list[Subsidiary]] = relationship(back_populates="parent_company")
    financial_statements: Mapped[list[FinancialStatement]] = relationship(
        back_populates="company"
    )
    risk_scores: Mapped[list[RiskScore]] = relationship(back_populates="company")
    alerts: Mapped[list[Alert]] = relationship(back_populates="company")


class Subsidiary(Base, TimestampMixin):
    """連結子会社."""

    __tablename__ = "subsidiaries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    parent_company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(3), default="JPN")
    ownership_ratio: Mapped[float | None] = mapped_column(Float)
    consolidation_method: Mapped[str | None] = mapped_column(String(50))
    segment: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    parent_company: Mapped[Company] = relationship(back_populates="subsidiaries")


# --- 財務データ ---

class FinancialStatement(Base, TimestampMixin):
    """財務諸表ヘッダ."""

    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", "fiscal_quarter", name="uq_fs_period"),
        Index("ix_fs_period", "fiscal_year", "fiscal_quarter"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False, index=True
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, default=4)  # 1-4, 4=通期
    filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(50))  # edinet, excel, manual

    company: Mapped[Company] = relationship(back_populates="financial_statements")
    accounts: Mapped[list[Account]] = relationship(back_populates="financial_statement")


class Account(Base, TimestampMixin):
    """勘定科目データ."""

    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_account_lookup", "financial_statement_id", "account_code"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    financial_statement_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("financial_statements.id"), nullable=False
    )
    account_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="JPY")
    taxonomy_element: Mapped[str | None] = mapped_column(String(200))

    financial_statement: Mapped[FinancialStatement] = relationship(back_populates="accounts")


# --- リスク分析結果 ---

class RiskScore(Base, TimestampMixin):
    """統合リスクスコア."""

    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("ix_risk_period", "company_id", "fiscal_year", "fiscal_quarter"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False, index=True
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, default=4)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum"), nullable=False
    )
    da_score: Mapped[float | None] = mapped_column(Float)
    fraud_score: Mapped[float | None] = mapped_column(Float)
    rule_score: Mapped[float | None] = mapped_column(Float)
    benford_score: Mapped[float | None] = mapped_column(Float)
    component_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_factors: Mapped[list[str] | None] = mapped_column(JSON)

    company: Mapped[Company] = relationship(back_populates="risk_scores")
    analysis_results: Mapped[list[AnalysisResult]] = relationship(back_populates="risk_score")


class AnalysisResult(Base, TimestampMixin):
    """個別分析結果."""

    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    risk_score_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("risk_scores.id"), nullable=False, index=True
    )
    analysis_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # da, fraud, rule, benford
    status: Mapped[str] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status_enum"), default=AnalysisStatus.PENDING
    )
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)

    risk_score: Mapped[RiskScore] = relationship(back_populates="analysis_results")


# --- AIインサイト ---

class AIInsight(Base, TimestampMixin):
    """AIエージェント分析インサイト."""

    __tablename__ = "ai_insights"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False, index=True
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    probe_type: Mapped[str] = mapped_column(String(50), nullable=False)
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_provider: Mapped[str | None] = mapped_column(String(50))
    ai_model: Mapped[str | None] = mapped_column(String(100))


# --- アラート ---

class Alert(Base, TimestampMixin):
    """リスクアラート."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alert_company", "company_id"),
        Index("ix_alert_severity", "severity"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_action: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="alerts")


# --- 監査ログ ---

class AuditLog(Base):
    """監査ログ - 誰が・いつ・どのモデルに・何を入出力したか."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_timestamp", "timestamp"),
        Index("ix_audit_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(200))
    ai_provider: Mapped[str | None] = mapped_column(String(50))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    request_path: Mapped[str | None] = mapped_column(String(500))
    request_method: Mapped[str | None] = mapped_column(String(10))
    status_code: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


# --- ルール定義 ---

class RuleDefinition(Base, TimestampMixin):
    """ルール定義マスタ."""

    __tablename__ = "rule_definitions"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)  # R001, R002, ...
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)


# --- ユーザー ---

class User(Base, TimestampMixin):
    """ユーザーマスタ."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
