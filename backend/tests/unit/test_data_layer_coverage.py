"""database.py / repository.py カバレッジテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Database ---


class TestDatabaseFunctions:
    """database.py テスト."""

    def test_get_async_engine(self) -> None:
        with (
            patch("cs_risk_agent.data.database.get_settings") as mock_s,
            patch("cs_risk_agent.data.database.create_async_engine") as mock_ce,
        ):
            mock_s.return_value.database.url = "sqlite+aiosqlite://"
            mock_s.return_value.database.echo = False
            mock_s.return_value.database.pool_size = 5
            mock_s.return_value.database.max_overflow = 10

            from cs_risk_agent.data.database import get_async_engine

            result = get_async_engine()
            mock_ce.assert_called_once_with(
                "sqlite+aiosqlite://",
                echo=False,
                pool_size=5,
                max_overflow=10,
            )
            assert result is mock_ce.return_value

    def test_get_sync_engine(self) -> None:
        with (
            patch("cs_risk_agent.data.database.get_settings") as mock_s,
            patch("cs_risk_agent.data.database.create_engine") as mock_ce,
        ):
            mock_s.return_value.database.sync_url = "sqlite:///test.db"
            mock_s.return_value.database.echo = False

            from cs_risk_agent.data.database import get_sync_engine

            result = get_sync_engine()
            mock_ce.assert_called_once_with("sqlite:///test.db", echo=False)
            assert result is mock_ce.return_value

    def test_get_async_session_factory(self) -> None:
        with (
            patch("cs_risk_agent.data.database.get_async_engine") as mock_eng,
            patch("cs_risk_agent.data.database.async_sessionmaker") as mock_sm,
        ):
            from cs_risk_agent.data.database import get_async_session_factory

            result = get_async_session_factory()
            mock_eng.assert_called_once()
            mock_sm.assert_called_once()
            assert result is mock_sm.return_value

    @pytest.mark.asyncio
    async def test_get_db_session_commit(self) -> None:
        """正常パス: commit が呼ばれる."""
        mock_session = AsyncMock()

        mock_factory_instance = AsyncMock()
        mock_factory_instance.__aenter__.return_value = mock_session
        mock_factory_instance.__aexit__.return_value = False

        mock_factory = MagicMock(return_value=mock_factory_instance)

        with patch(
            "cs_risk_agent.data.database.get_async_session_factory",
            return_value=mock_factory,
        ):
            from cs_risk_agent.data.database import get_db_session

            gen = get_db_session()
            session = await gen.__anext__()
            assert session is mock_session

            # 正常終了 → commit
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()
            mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_session_rollback(self) -> None:
        """例外パス: rollback が呼ばれる."""
        mock_session = AsyncMock()

        mock_factory_instance = AsyncMock()
        mock_factory_instance.__aenter__.return_value = mock_session
        mock_factory_instance.__aexit__.return_value = False

        mock_factory = MagicMock(return_value=mock_factory_instance)

        with patch(
            "cs_risk_agent.data.database.get_async_session_factory",
            return_value=mock_factory,
        ):
            from cs_risk_agent.data.database import get_db_session

            gen = get_db_session()
            await gen.__anext__()

            # 例外送信 → rollback
            with pytest.raises(ValueError, match="test error"):
                await gen.athrow(ValueError("test error"))
            mock_session.rollback.assert_awaited_once()


# --- Repository ---


class TestCompanyRepository:
    """CompanyRepository テスト."""

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id="C001")
        mock_session.execute.return_value = mock_result

        repo = CompanyRepository(mock_session)
        result = await repo.get_by_id("C001")
        assert result.id == "C001"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_none(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CompanyRepository(mock_session)
        result = await repo.get_by_id("NONEXIST")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_edinet_code(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(edinet_code="E12345")
        mock_session.execute.return_value = mock_result

        repo = CompanyRepository(mock_session)
        result = await repo.get_by_edinet_code("E12345")
        assert result is not None

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        repo = CompanyRepository(mock_session)

        result = await repo.create(name="New Corp", country="JPN")
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.name == "New Corp"

    @pytest.mark.asyncio
    async def test_update_found(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_company = MagicMock(id="C001")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_company
        mock_session.execute.return_value = mock_result

        repo = CompanyRepository(mock_session)
        result = await repo.update("C001", name="Updated")
        assert result is mock_company
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        from cs_risk_agent.data.repository import CompanyRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CompanyRepository(mock_session)
        result = await repo.update("NONEXIST", name="Updated")
        assert result is None


class TestRiskScoreRepository:
    """RiskScoreRepository テスト."""

    @pytest.mark.asyncio
    async def test_get_latest(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(total_score=75.0)
        mock_session.execute.return_value = mock_result

        repo = RiskScoreRepository(mock_session)
        result = await repo.get_latest("C001")
        assert result.total_score == 75.0

    @pytest.mark.asyncio
    async def test_get_by_period(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(fiscal_year=2025)
        mock_session.execute.return_value = mock_result

        repo = RiskScoreRepository(mock_session)
        result = await repo.get_by_period("C001", 2025, 4)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_trend(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        mock_session.execute.return_value = mock_result

        repo = RiskScoreRepository(mock_session)
        result = await repo.get_trend("C001", periods=4)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        mock_session = AsyncMock()
        repo = RiskScoreRepository(mock_session)

        result = await repo.create(company_id="C001", total_score=80.0)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_high_risk_companies(self) -> None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.return_value = mock_result

        repo = RiskScoreRepository(mock_session)
        result = await repo.get_high_risk_companies(threshold=60.0)
        assert len(result) == 1


class TestAuditLogRepository:
    """AuditLogRepository テスト."""

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import AuditLogRepository

        mock_session = AsyncMock()
        repo = AuditLogRepository(mock_session)

        result = await repo.create(user_id="U001", action="LOGIN")
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_recent(self) -> None:
        from cs_risk_agent.data.repository import AuditLogRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AuditLogRepository(mock_session)
        result = await repo.list_recent(limit=50)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_recent_with_filters(self) -> None:
        from cs_risk_agent.data.repository import AuditLogRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AuditLogRepository(mock_session)
        result = await repo.list_recent(user_id="U001", action="LOGIN")
        assert result == []


class TestUserRepository:
    """UserRepository テスト."""

    @pytest.mark.asyncio
    async def test_get_by_username(self) -> None:
        from cs_risk_agent.data.repository import UserRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(username="admin")
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_username("admin")
        assert result.username == "admin"

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        from cs_risk_agent.data.repository import UserRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id="U001")
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_id("U001")
        assert result.id == "U001"

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        from cs_risk_agent.data.repository import UserRepository

        mock_session = AsyncMock()
        repo = UserRepository(mock_session)

        result = await repo.create(username="newuser", role="viewer")
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
