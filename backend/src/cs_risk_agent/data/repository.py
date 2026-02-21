"""Repository Pattern - データアクセス層.

SQLAlchemy を使用したCRUD操作の抽象化。
"""

from __future__ import annotations

from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from cs_risk_agent.data.models import (
    Account,
    AIInsight,
    Alert,
    AnalysisResult,
    AuditLog,
    Company,
    FinancialStatement,
    RiskScore,
    Subsidiary,
    User,
)


class CompanyRepository:
    """企業リポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: str) -> Company | None:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_edinet_code(self, edinet_code: str) -> Company | None:
        result = await self._session.execute(
            select(Company).where(Company.edinet_code == edinet_code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, page: int = 1, per_page: int = 20, industry_code: str | None = None
    ) -> tuple[Sequence[Company], int]:
        query = select(Company)
        count_query = select(func.count()).select_from(Company)

        if industry_code:
            query = query.where(Company.industry_code == industry_code)
            count_query = count_query.where(Company.industry_code == industry_code)

        total = (await self._session.execute(count_query)).scalar() or 0
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self._session.execute(query)
        return result.scalars().all(), total

    async def create(self, **kwargs: Any) -> Company:
        company = Company(id=str(uuid4()), **kwargs)
        self._session.add(company)
        await self._session.flush()
        return company

    async def update(self, company_id: str, **kwargs: Any) -> Company | None:
        company = await self.get_by_id(company_id)
        if company:
            for key, value in kwargs.items():
                setattr(company, key, value)
            await self._session.flush()
        return company


class RiskScoreRepository:
    """リスクスコアリポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self, company_id: str) -> RiskScore | None:
        result = await self._session.execute(
            select(RiskScore)
            .where(RiskScore.company_id == company_id)
            .order_by(RiskScore.fiscal_year.desc(), RiskScore.fiscal_quarter.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_period(
        self, company_id: str, fiscal_year: int, fiscal_quarter: int = 4
    ) -> RiskScore | None:
        result = await self._session.execute(
            select(RiskScore).where(
                and_(
                    RiskScore.company_id == company_id,
                    RiskScore.fiscal_year == fiscal_year,
                    RiskScore.fiscal_quarter == fiscal_quarter,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_trend(
        self, company_id: str, periods: int = 8
    ) -> Sequence[RiskScore]:
        result = await self._session.execute(
            select(RiskScore)
            .where(RiskScore.company_id == company_id)
            .order_by(RiskScore.fiscal_year.desc(), RiskScore.fiscal_quarter.desc())
            .limit(periods)
        )
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> RiskScore:
        score = RiskScore(id=str(uuid4()), **kwargs)
        self._session.add(score)
        await self._session.flush()
        return score

    async def get_high_risk_companies(
        self, threshold: float = 60.0, limit: int = 20
    ) -> Sequence[RiskScore]:
        result = await self._session.execute(
            select(RiskScore)
            .where(RiskScore.total_score >= threshold)
            .order_by(RiskScore.total_score.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all(self) -> Sequence[RiskScore]:
        """全リスクスコアを取得."""
        result = await self._session.execute(
            select(RiskScore).order_by(RiskScore.created_at.desc())
        )
        return result.scalars().all()


class AuditLogRepository:
    """監査ログリポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> AuditLog:
        log = AuditLog(id=str(uuid4()), **kwargs)
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_recent(
        self,
        limit: int = 100,
        user_id: str | None = None,
        action: str | None = None,
    ) -> Sequence[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        result = await self._session.execute(query)
        return result.scalars().all()


class UserRepository:
    """ユーザーリポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> User:
        user = User(id=str(uuid4()), **kwargs)
        self._session.add(user)
        await self._session.flush()
        return user


class SubsidiaryRepository:
    """子会社リポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, subsidiary_id: str) -> Subsidiary | None:
        result = await self._session.execute(
            select(Subsidiary).where(Subsidiary.id == subsidiary_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[Subsidiary]:
        result = await self._session.execute(select(Subsidiary))
        return result.scalars().all()


class FinancialStatementRepository:
    """財務諸表リポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_entity(
        self, company_id: str, fiscal_year: int | None = None,
    ) -> Sequence[FinancialStatement]:
        query = select(FinancialStatement).where(
            FinancialStatement.company_id == company_id
        )
        if fiscal_year:
            query = query.where(FinancialStatement.fiscal_year == fiscal_year)
        query = query.order_by(
            FinancialStatement.fiscal_year.desc(),
            FinancialStatement.fiscal_quarter.desc(),
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_latest(self, company_id: str) -> FinancialStatement | None:
        result = await self._session.execute(
            select(FinancialStatement)
            .where(FinancialStatement.company_id == company_id)
            .order_by(
                FinancialStatement.fiscal_year.desc(),
                FinancialStatement.fiscal_quarter.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_latest(self) -> Sequence[FinancialStatement]:
        """全企業の最新財務諸表を取得 (company_id 毎に最新1件)."""
        # 各企業の最大fiscal_year + fiscal_quarterを持つレコードを取得
        subq = (
            select(
                FinancialStatement.company_id,
                func.max(FinancialStatement.fiscal_year * 10 + FinancialStatement.fiscal_quarter).label("max_period"),
            )
            .group_by(FinancialStatement.company_id)
            .subquery()
        )
        result = await self._session.execute(
            select(FinancialStatement).join(
                subq,
                and_(
                    FinancialStatement.company_id == subq.c.company_id,
                    (FinancialStatement.fiscal_year * 10 + FinancialStatement.fiscal_quarter) == subq.c.max_period,
                ),
            )
        )
        return result.scalars().all()

    async def get_accounts(self, fs_id: str) -> Sequence[Account]:
        """財務諸表の勘定科目を取得."""
        result = await self._session.execute(
            select(Account)
            .where(Account.financial_statement_id == fs_id)
            .order_by(Account.account_code)
        )
        return result.scalars().all()


class AlertRepository:
    """アラートリポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self, severity: str | None = None) -> Sequence[Alert]:
        query = select(Alert).order_by(Alert.created_at.desc())
        if severity:
            query = query.where(Alert.severity == severity)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_unread(self) -> Sequence[Alert]:
        result = await self._session.execute(
            select(Alert)
            .where(Alert.is_read == False)  # noqa: E712
            .order_by(Alert.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> Alert:
        alert = Alert(id=str(uuid4()), **kwargs)
        self._session.add(alert)
        await self._session.flush()
        return alert
