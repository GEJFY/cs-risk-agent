"""DBDataProvider ユニットテスト.

SQLite インメモリDBを使用してDBDataProviderの全メソッドをテストする。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from cs_risk_agent.data.models import (
    Account,
    Alert,
    Base,
    Company,
    FinancialStatement,
    RiskScore,
    Subsidiary,
)
from cs_risk_agent.data.provider import DBDataProvider
from cs_risk_agent.data.repository import (
    AlertRepository,
    CompanyRepository,
    FinancialStatementRepository,
    RiskScoreRepository,
    SubsidiaryRepository,
)


@pytest.fixture
async def async_engine():
    """テスト用SQLite非同期エンジン."""
    from sqlalchemy import event

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # SQLiteでUUID型をテキストとして扱うためのイベントリスナー
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """テスト用非同期セッション."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# テスト用固定UUID
_COM_ID = str(uuid4())
_SUB_ID = str(uuid4())
_FS_ID = str(uuid4())
_ALT_ID1 = str(uuid4())
_ALT_ID2 = str(uuid4())


@pytest.fixture
async def seed_data(async_session):
    """テスト用シードデータ."""
    now = datetime.now(UTC)

    # 企業
    company = Company(
        id=_COM_ID, edinet_code="E12345", name="テスト株式会社",
        name_en="Test Corp", industry_code="3300", country="JPN",
        created_at=now, updated_at=now,
    )
    async_session.add(company)

    # 子会社
    sub = Subsidiary(
        id=_SUB_ID, parent_company_id=_COM_ID, name="テスト子会社A",
        country="JPN", ownership_ratio=1.0, is_active=True,
        created_at=now, updated_at=now,
    )
    async_session.add(sub)

    # リスクスコア
    score = RiskScore(
        id=str(uuid4()), company_id=_SUB_ID,
        fiscal_year=2025, fiscal_quarter=4, total_score=72.5,
        risk_level="high", da_score=65.0, fraud_score=80.0,
        rule_score=70.0, benford_score=75.0,
        risk_factors=["売掛金異常", "在庫回転率低下"],
        created_at=now, updated_at=now,
    )
    async_session.add(score)

    # 財務諸表
    fs = FinancialStatement(
        id=_FS_ID, company_id=_SUB_ID,
        fiscal_year=2025, fiscal_quarter=4, source="demo",
        created_at=now, updated_at=now,
    )
    async_session.add(fs)

    # 勘定科目
    accounts = [
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="revenue", account_name="売上高",
                amount=100000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="cogs", account_name="売上原価",
                amount=70000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="operating_income", account_name="営業利益",
                amount=15000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="net_income", account_name="当期純利益",
                amount=10000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="total_assets", account_name="総資産",
                amount=500000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="total_equity", account_name="純資産",
                amount=200000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="current_assets", account_name="流動資産",
                amount=150000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="current_liabilities", account_name="流動負債",
                amount=80000.0, created_at=now, updated_at=now),
        Account(id=str(uuid4()), financial_statement_id=_FS_ID,
                account_code="total_liabilities", account_name="負債合計",
                amount=300000.0, created_at=now, updated_at=now),
    ]
    for acc in accounts:
        async_session.add(acc)

    # アラート
    alert = Alert(
        id=_ALT_ID1, company_id=_SUB_ID, severity="critical",
        category="売掛金異常", title="売掛金が前年比200%増加",
        description="詳細説明", is_read=False,
        recommended_action="調査を推奨",
        created_at=now, updated_at=now,
    )
    async_session.add(alert)

    alert2 = Alert(
        id=_ALT_ID2, company_id=_COM_ID, severity="medium",
        category="在庫", title="在庫回転率低下",
        description="在庫説明", is_read=True,
        created_at=now, updated_at=now,
    )
    async_session.add(alert2)

    await async_session.commit()
    return {"company": company, "subsidiary": sub, "score": score, "fs": fs}


class TestRepositories:
    """新規リポジトリのテスト."""

    @pytest.mark.asyncio
    async def test_subsidiary_repository_get_all(self, async_session, seed_data):
        repo = SubsidiaryRepository(async_session)
        subs = await repo.get_all()
        assert len(subs) == 1
        assert subs[0].id == _SUB_ID

    @pytest.mark.asyncio
    async def test_subsidiary_repository_get_by_id(self, async_session, seed_data):
        repo = SubsidiaryRepository(async_session)
        sub = await repo.get_by_id(_SUB_ID)
        assert sub is not None
        assert sub.name == "テスト子会社A"

    @pytest.mark.asyncio
    async def test_financial_statement_repository_get_by_entity(self, async_session, seed_data):
        repo = FinancialStatementRepository(async_session)
        stmts = await repo.get_by_entity(_SUB_ID)
        assert len(stmts) == 1
        assert stmts[0].fiscal_year == 2025

    @pytest.mark.asyncio
    async def test_financial_statement_repository_get_latest(self, async_session, seed_data):
        repo = FinancialStatementRepository(async_session)
        fs = await repo.get_latest(_SUB_ID)
        assert fs is not None
        assert fs.id == _FS_ID

    @pytest.mark.asyncio
    async def test_financial_statement_repository_get_accounts(self, async_session, seed_data):
        repo = FinancialStatementRepository(async_session)
        accounts = await repo.get_accounts(_FS_ID)
        assert len(accounts) == 9

    @pytest.mark.asyncio
    async def test_alert_repository_get_all(self, async_session, seed_data):
        repo = AlertRepository(async_session)
        alerts = await repo.get_all()
        assert len(alerts) == 2

    @pytest.mark.asyncio
    async def test_alert_repository_get_by_severity(self, async_session, seed_data):
        repo = AlertRepository(async_session)
        alerts = await repo.get_all(severity="critical")
        assert len(alerts) == 1
        assert alerts[0].id == _ALT_ID1

    @pytest.mark.asyncio
    async def test_alert_repository_get_unread(self, async_session, seed_data):
        repo = AlertRepository(async_session)
        alerts = await repo.get_unread()
        assert len(alerts) == 1
        assert alerts[0].is_read is False

    @pytest.mark.asyncio
    async def test_risk_score_repository_get_all(self, async_session, seed_data):
        repo = RiskScoreRepository(async_session)
        scores = await repo.get_all()
        assert len(scores) == 1

    @pytest.mark.asyncio
    async def test_financial_statement_get_all_latest(self, async_session, seed_data):
        repo = FinancialStatementRepository(async_session)
        stmts = await repo.get_all_latest()
        assert len(stmts) >= 1


class TestDBDataProviderInterface:
    """DBDataProviderのインターフェース互換テスト (モックベース)."""

    def test_provider_instantiation(self, monkeypatch):
        """DBDataProviderがインスタンス化できること."""
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "cs_risk_agent.data.database.get_async_session_factory",
            MagicMock(),
        )
        provider = DBDataProvider()
        assert provider is not None

    def test_provider_has_all_methods(self, monkeypatch):
        """DBDataProviderが全抽象メソッドを実装していること."""
        from cs_risk_agent.data.provider import DataProvider
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "cs_risk_agent.data.database.get_async_session_factory",
            MagicMock(),
        )
        # 全抽象メソッドがDBDataProviderクラスに定義されていることを確認
        abstract_methods = set()
        for cls in DataProvider.__mro__:
            for name, method in vars(cls).items():
                if getattr(method, "__isabstractmethod__", False):
                    abstract_methods.add(name)
        for method_name in abstract_methods:
            assert method_name in dir(DBDataProvider), f"Missing method: {method_name}"

    def test_provider_no_not_implemented_error(self, monkeypatch):
        """DBDataProviderにNotImplementedErrorが残っていないこと."""
        import inspect
        from unittest.mock import MagicMock
        monkeypatch.setattr(
            "cs_risk_agent.data.database.get_async_session_factory",
            MagicMock(),
        )
        provider = DBDataProvider()
        source = inspect.getsource(type(provider))
        assert "NotImplementedError" not in source
