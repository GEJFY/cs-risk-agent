"""財務データAPIエンドポイント 統合テスト."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cs_risk_agent.core.security import Role, create_access_token
from cs_risk_agent.main import app


def _auth_header() -> dict[str, str]:
    token = create_access_token(subject="testuser", role=Role.ADMIN)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    """テスト用非同期HTTPクライアント (認証付き)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=_auth_header()
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# 財務諸表 テスト
# ---------------------------------------------------------------------------


class TestFinancialStatements:
    """財務諸表エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_list_all_statements(self, client: AsyncClient) -> None:
        """GET /financials/statements が財務データを返すこと."""
        response = await client.get("/api/v1/financials/statements")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_statements_by_entity(self, client: AsyncClient) -> None:
        """entity_id指定で財務データをフィルタできること."""
        response = await client.get(
            "/api/v1/financials/statements",
            params={"entity_id": "SUB-0001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["entity_id"] == "SUB-0001"

    @pytest.mark.asyncio
    async def test_financial_trend(self, client: AsyncClient) -> None:
        """GET /financials/statements/{id}/trend がトレンドを返すこと."""
        response = await client.get("/api/v1/financials/statements/SUB-0001/trend")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "trends" in data
        if data["trends"]:
            trend = data["trends"][0]
            assert "period" in trend
            assert "revenue" in trend
            assert "total_assets" in trend
            assert "operating_cash_flow" in trend


# ---------------------------------------------------------------------------
# 財務指標 テスト
# ---------------------------------------------------------------------------


class TestFinancialRatios:
    """財務指標エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_ratios_by_entity(self, client: AsyncClient) -> None:
        """GET /financials/ratios/{id} が指標を返すこと."""
        response = await client.get("/api/v1/financials/ratios/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "ratios" in data
        if data["ratios"]:
            r = data["ratios"][0]
            assert "gross_margin" in r
            assert "operating_margin" in r
            assert "roe" in r
            assert "current_ratio" in r

    @pytest.mark.asyncio
    async def test_all_ratios(self, client: AsyncClient) -> None:
        """GET /financials/ratios が全エンティティの指標を返すこと."""
        response = await client.get("/api/v1/financials/ratios")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# ---------------------------------------------------------------------------
# 試算表 テスト
# ---------------------------------------------------------------------------


class TestTrialBalance:
    """試算表エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_trial_balance(self, client: AsyncClient) -> None:
        """GET /financials/trial-balance/{id} がTBを返すこと."""
        response = await client.get("/api/v1/financials/trial-balance/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "accounts" in data
        assert "total_accounts" in data
        if data["accounts"]:
            account = data["accounts"][0]
            assert "account_code" in account
            assert "total_debit" in account
            assert "total_credit" in account
            assert "balance" in account


# ---------------------------------------------------------------------------
# 仕訳 テスト
# ---------------------------------------------------------------------------


class TestJournalEntries:
    """仕訳エンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_journal_entries(self, client: AsyncClient) -> None:
        """GET /financials/journal-entries/{id} が仕訳を返すこと."""
        response = await client.get("/api/v1/financials/journal-entries/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_journal_entries_anomaly_filter(self, client: AsyncClient) -> None:
        """anomaly_only=trueで異常仕訳のみフィルタできること."""
        response = await client.get(
            "/api/v1/financials/journal-entries/SUB-0001",
            params={"anomaly_only": "true"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item.get("is_anomaly") is True

    @pytest.mark.asyncio
    async def test_journal_entries_limit(self, client: AsyncClient) -> None:
        """limitパラメータでレスポンス件数を制限できること."""
        response = await client.get(
            "/api/v1/financials/journal-entries/SUB-0001",
            params={"limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["returned"] <= 5


# ---------------------------------------------------------------------------
# BS/PL テスト
# ---------------------------------------------------------------------------


class TestBalanceSheetAndPL:
    """BS/PLエンドポイントの検証."""

    @pytest.mark.asyncio
    async def test_balance_sheet(self, client: AsyncClient) -> None:
        """GET /financials/balance-sheet/{id} がBS構造化データを返すこと."""
        response = await client.get("/api/v1/financials/balance-sheet/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "balance_sheets" in data
        if data["balance_sheets"]:
            bs = data["balance_sheets"][0]
            assert "period" in bs
            assert "assets" in bs
            assert "liabilities" in bs
            assert "equity" in bs

    @pytest.mark.asyncio
    async def test_income_statement(self, client: AsyncClient) -> None:
        """GET /financials/income-statement/{id} がPLデータを返すこと."""
        response = await client.get("/api/v1/financials/income-statement/SUB-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "SUB-0001"
        assert "income_statements" in data
        if data["income_statements"]:
            pl = data["income_statements"][0]
            assert "revenue" in pl
            assert "gross_profit" in pl
            assert "operating_income" in pl
            assert "net_income" in pl
            assert "gross_margin_pct" in pl
