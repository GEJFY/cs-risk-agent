"""データモデル・リポジトリのユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# ORM モデル テスト
# ---------------------------------------------------------------------------


class TestModels:
    """SQLAlchemy ORM モデルのテスト."""

    def test_risk_level_enum(self) -> None:
        from cs_risk_agent.data.models import RiskLevel

        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"

    def test_analysis_status_enum(self) -> None:
        from cs_risk_agent.data.models import AnalysisStatus

        assert AnalysisStatus.PENDING.value == "pending"
        assert AnalysisStatus.RUNNING.value == "running"
        assert AnalysisStatus.COMPLETED.value == "completed"
        assert AnalysisStatus.FAILED.value == "failed"

    def test_company_model_import(self) -> None:
        from cs_risk_agent.data.models import Company

        assert Company is not None
        assert Company.__tablename__ == "companies"

    def test_subsidiary_model_import(self) -> None:
        from cs_risk_agent.data.models import Subsidiary

        assert Subsidiary is not None
        assert Subsidiary.__tablename__ == "subsidiaries"

    def test_financial_statement_model_import(self) -> None:
        from cs_risk_agent.data.models import FinancialStatement

        assert FinancialStatement is not None
        assert FinancialStatement.__tablename__ == "financial_statements"

    def test_account_model_import(self) -> None:
        from cs_risk_agent.data.models import Account

        assert Account is not None
        assert Account.__tablename__ == "accounts"

    def test_risk_score_model_import(self) -> None:
        from cs_risk_agent.data.models import RiskScore

        assert RiskScore is not None
        assert RiskScore.__tablename__ == "risk_scores"

    def test_analysis_result_model_import(self) -> None:
        from cs_risk_agent.data.models import AnalysisResult

        assert AnalysisResult is not None
        assert AnalysisResult.__tablename__ == "analysis_results"

    def test_ai_insight_model_import(self) -> None:
        from cs_risk_agent.data.models import AIInsight

        assert AIInsight is not None
        assert AIInsight.__tablename__ == "ai_insights"

    def test_audit_log_model_import(self) -> None:
        from cs_risk_agent.data.models import AuditLog

        assert AuditLog is not None
        assert AuditLog.__tablename__ == "audit_logs"

    def test_rule_definition_model_import(self) -> None:
        from cs_risk_agent.data.models import RuleDefinition

        assert RuleDefinition is not None
        assert RuleDefinition.__tablename__ == "rule_definitions"

    def test_user_model_import(self) -> None:
        from cs_risk_agent.data.models import User

        assert User is not None
        assert User.__tablename__ == "users"

    def test_base_import(self) -> None:
        from cs_risk_agent.data.models import Base

        assert Base is not None


# ---------------------------------------------------------------------------
# Database テスト
# ---------------------------------------------------------------------------


class TestDatabase:
    """データベース接続のテスト."""

    def test_imports(self) -> None:
        from cs_risk_agent.data.database import (
            get_async_engine,
            get_async_session_factory,
            get_db_session,
            get_sync_engine,
        )

        assert get_async_engine is not None
        assert get_sync_engine is not None
        assert get_async_session_factory is not None
        assert get_db_session is not None


# ---------------------------------------------------------------------------
# Repository テスト
# ---------------------------------------------------------------------------


class TestRepositoryImports:
    """リポジトリのインポートテスト."""

    def test_company_repository_import(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        assert CompanyRepository is not None

    def test_risk_score_repository_import(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        assert RiskScoreRepository is not None

    def test_audit_log_repository_import(self) -> None:
        from cs_risk_agent.data.repository import AuditLogRepository

        assert AuditLogRepository is not None

    def test_user_repository_import(self) -> None:
        from cs_risk_agent.data.repository import UserRepository

        assert UserRepository is not None


class TestCompanyRepository:
    """CompanyRepository のロジックテスト."""

    def test_init(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        session = MagicMock()
        repo = CompanyRepository(session)
        assert repo._session is session

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = CompanyRepository(session)
        result = await repo.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        session = AsyncMock()
        repo = CompanyRepository(session)
        company = await repo.create(
            name="Test Corp",
            edinet_code="E00001",
            industry_code="IND_A",
        )
        assert company is not None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


class TestRiskScoreRepository:
    """RiskScoreRepository のロジックテスト."""

    def test_init(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        session = MagicMock()
        repo = RiskScoreRepository(session)
        assert repo._session is session

    @pytest.mark.asyncio
    async def test_get_latest(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = RiskScoreRepository(session)
        result = await repo.get_latest("SUB-0001")
        assert result is None

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        session = AsyncMock()
        repo = RiskScoreRepository(session)
        score = await repo.create(
            company_id="SUB-0001",
            fiscal_year=2025,
            fiscal_quarter=4,
            total_score=75.0,
            risk_level="high",
        )
        assert score is not None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
