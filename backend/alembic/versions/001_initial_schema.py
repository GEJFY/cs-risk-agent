"""Initial schema - 全テーブル作成

Revision ID: 001
Revises:
Create Date: 2026-02-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 企業マスタ ---
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("edinet_code", sa.String(10), unique=True, index=True, nullable=True),
        sa.Column("securities_code", sa.String(10), index=True, nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("industry_code", sa.String(10), index=True, nullable=True),
        sa.Column("industry_name", sa.String(100), nullable=True),
        sa.Column("fiscal_year_end", sa.Integer, nullable=True),
        sa.Column("is_listed", sa.Boolean, default=True),
        sa.Column("country", sa.String(3), default="JPN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- 連結子会社 ---
    op.create_table(
        "subsidiaries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "parent_company_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("companies.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=True),
        sa.Column("country", sa.String(3), default="JPN"),
        sa.Column("ownership_ratio", sa.Float, nullable=True),
        sa.Column("consolidation_method", sa.String(50), nullable=True),
        sa.Column("segment", sa.String(100), index=True, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- 財務諸表ヘッダ ---
    op.create_table(
        "financial_statements",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("companies.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("fiscal_quarter", sa.Integer, default=4),
        sa.Column("filing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "company_id", "fiscal_year", "fiscal_quarter", name="uq_fs_period",
        ),
    )
    op.create_index("ix_fs_period", "financial_statements", ["fiscal_year", "fiscal_quarter"])

    # --- 勘定科目データ ---
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "financial_statement_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("financial_statements.id"),
            nullable=False,
        ),
        sa.Column("account_code", sa.String(50), nullable=False, index=True),
        sa.Column("account_name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float, default=0.0),
        sa.Column("currency", sa.String(3), default="JPY"),
        sa.Column("taxonomy_element", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_account_lookup", "accounts", ["financial_statement_id", "account_code"],
    )

    # --- リスクレベルENUM ---
    risk_level_enum = postgresql.ENUM(
        "critical", "high", "medium", "low", name="risk_level_enum", create_type=True,
    )
    risk_level_enum.create(op.get_bind(), checkfirst=True)

    # --- 分析ステータスENUM ---
    analysis_status_enum = postgresql.ENUM(
        "pending", "running", "completed", "failed",
        name="analysis_status_enum", create_type=True,
    )
    analysis_status_enum.create(op.get_bind(), checkfirst=True)

    # --- 統合リスクスコア ---
    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("companies.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("fiscal_quarter", sa.Integer, default=4),
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column(
            "risk_level",
            risk_level_enum,
            nullable=False,
        ),
        sa.Column("da_score", sa.Float, nullable=True),
        sa.Column("fraud_score", sa.Float, nullable=True),
        sa.Column("rule_score", sa.Float, nullable=True),
        sa.Column("benford_score", sa.Float, nullable=True),
        sa.Column("component_details", sa.JSON, nullable=True),
        sa.Column("risk_factors", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_risk_period", "risk_scores", ["company_id", "fiscal_year", "fiscal_quarter"],
    )

    # --- 個別分析結果 ---
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "risk_score_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("risk_scores.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("status", analysis_status_enum, default="pending"),
        sa.Column("result_data", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- AIインサイト ---
    op.create_table(
        "ai_insights",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("companies.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("probe_type", sa.String(50), nullable=False),
        sa.Column("insight_text", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20)),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("ai_provider", sa.String(50), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- 監査ログ ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(100), index=True, nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(200), nullable=True),
        sa.Column("ai_provider", sa.String(50), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("request_path", sa.String(500), nullable=True),
        sa.Column("request_method", sa.String(10), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
    )
    op.create_index("ix_audit_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_user", "audit_logs", ["user_id"])

    # --- ルール定義マスタ ---
    op.create_table(
        "rule_definitions",
        sa.Column("id", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("parameters", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- ユーザーマスタ ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("rule_definitions")
    op.drop_table("audit_logs")
    op.drop_table("ai_insights")
    op.drop_table("analysis_results")
    op.drop_table("risk_scores")
    op.drop_table("accounts")
    op.drop_table("financial_statements")
    op.drop_table("subsidiaries")
    op.drop_table("companies")

    op.execute("DROP TYPE IF EXISTS analysis_status_enum")
    op.execute("DROP TYPE IF EXISTS risk_level_enum")
