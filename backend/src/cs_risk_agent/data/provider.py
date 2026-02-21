"""データプロバイダー抽象化 - DemoData/DB切り替え.

DATA_MODE 環境変数で demo / db モードを切り替え。
全APIエンドポイントはこのプロバイダー経由でデータにアクセスする。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from cs_risk_agent.config import DataMode, get_settings

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """データアクセスの抽象基底クラス."""

    @abstractmethod
    def get_all_entities(self) -> list[dict[str, Any]]:
        """全エンティティ取得."""

    @abstractmethod
    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """IDでエンティティ検索."""

    @abstractmethod
    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        """エンティティのリスクスコア."""

    @abstractmethod
    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        """リスク付き子会社一覧."""

    @abstractmethod
    def get_risk_summary(self) -> dict[str, Any]:
        """リスクサマリー."""

    @abstractmethod
    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        """重要度別アラート."""

    @abstractmethod
    def get_unread_alerts(self) -> list[dict[str, Any]]:
        """未読アラート."""

    @abstractmethod
    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        """エンティティ別財務諸表."""

    @abstractmethod
    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        """最新財務データ."""

    @abstractmethod
    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        """試算表."""

    @abstractmethod
    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        """仕訳データ."""

    @abstractmethod
    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        """財務指標."""

    @property
    @abstractmethod
    def risk_scores(self) -> list[dict[str, Any]]:
        """全リスクスコア."""

    @property
    @abstractmethod
    def alerts(self) -> list[dict[str, Any]]:
        """全アラート."""


class DemoDataProvider(DataProvider):
    """デモデータ (JSON/CSV) プロバイダー."""

    def __init__(self) -> None:
        from cs_risk_agent.demo_loader import DemoData
        self._demo = DemoData.get()

    def get_all_entities(self) -> list[dict[str, Any]]:
        return self._demo.get_all_entities()

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        return self._demo.get_entity_by_id(entity_id)

    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._demo.get_risk_score_by_entity(entity_id)

    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        return self._demo.get_subsidiaries_with_risk()

    def get_risk_summary(self) -> dict[str, Any]:
        return self._demo.get_risk_summary()

    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        return self._demo.get_alerts_by_severity(severity)

    def get_unread_alerts(self) -> list[dict[str, Any]]:
        return self._demo.get_unread_alerts()

    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.get_financial_statements_by_entity(entity_id)

    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        return self._demo.get_all_financial_latest()

    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.get_trial_balance(entity_id)

    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._demo.get_journal_entries_by_entity(entity_id, anomaly_only=anomaly_only)

    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.compute_financial_ratios(entity_id)

    @property
    def risk_scores(self) -> list[dict[str, Any]]:
        return self._demo.risk_scores

    @property
    def alerts(self) -> list[dict[str, Any]]:
        return self._demo.alerts


class DBDataProvider(DataProvider):
    """DB (SQLAlchemy) プロバイダー.

    DATA_MODE=db 時に使用。Repository パターン経由で非同期DBアクセスを行う。
    """

    def __init__(self) -> None:
        from cs_risk_agent.data.database import get_async_session_factory
        self._session_factory = get_async_session_factory()

    def _run(self, coro: Any) -> Any:
        """非同期コルーチンを同期コンテキストで実行."""
        import asyncio
        try:
            asyncio.get_running_loop()
            # イベントループ実行中 → 別スレッドで実行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            return asyncio.run(coro)

    # --- エンティティ ---

    def get_all_entities(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import CompanyRepository, SubsidiaryRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                companies, _ = await CompanyRepository(session).list_all(page=1, per_page=10000)
                subs = await SubsidiaryRepository(session).get_all()
                result: list[dict[str, Any]] = [
                    {"id": c.id, "edinet_code": c.edinet_code, "name": c.name,
                     "name_en": c.name_en, "industry_code": c.industry_code,
                     "country": c.country, "is_listed": c.is_listed}
                    for c in companies
                ]
                result.extend(
                    {"id": s.id, "parent_company_id": s.parent_company_id,
                     "name": s.name, "country": s.country,
                     "ownership_ratio": s.ownership_ratio, "is_active": s.is_active}
                    for s in subs
                )
                return result
        return self._run(_q())

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        from cs_risk_agent.data.repository import CompanyRepository, SubsidiaryRepository

        async def _q() -> dict[str, Any] | None:
            async with self._session_factory() as session:
                c = await CompanyRepository(session).get_by_id(entity_id)
                if c:
                    return {"id": c.id, "edinet_code": c.edinet_code, "name": c.name,
                            "industry_code": c.industry_code, "country": c.country}
                s = await SubsidiaryRepository(session).get_by_id(entity_id)
                if s:
                    return {"id": s.id, "parent_company_id": s.parent_company_id,
                            "name": s.name, "country": s.country,
                            "ownership_ratio": s.ownership_ratio}
                return None
        return self._run(_q())

    # --- リスクスコア ---

    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        from cs_risk_agent.data.repository import RiskScoreRepository

        async def _q() -> dict[str, Any] | None:
            async with self._session_factory() as session:
                s = await RiskScoreRepository(session).get_latest(entity_id)
                if not s:
                    return None
                return {
                    "entity_id": s.company_id, "total_score": s.total_score,
                    "risk_level": s.risk_level, "da_score": s.da_score,
                    "fraud_score": s.fraud_score, "rule_score": s.rule_score,
                    "benford_score": s.benford_score,
                    "risk_factors": s.risk_factors or [],
                    "fiscal_year": s.fiscal_year, "fiscal_quarter": s.fiscal_quarter,
                    "component_details": s.component_details,
                }
        return self._run(_q())

    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import RiskScoreRepository, SubsidiaryRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                subs = await SubsidiaryRepository(session).get_all()
                risk_repo = RiskScoreRepository(session)
                result: list[dict[str, Any]] = []
                for s in subs:
                    entry: dict[str, Any] = {
                        "id": s.id, "parent_company_id": s.parent_company_id,
                        "name": s.name, "country": s.country,
                        "ownership_ratio": s.ownership_ratio, "is_active": s.is_active,
                    }
                    score = await risk_repo.get_latest(s.id)
                    if score:
                        entry["total_score"] = score.total_score
                        entry["risk_level"] = score.risk_level
                        entry["risk_factors"] = score.risk_factors or []
                    result.append(entry)
                return result
        return self._run(_q())

    def get_risk_summary(self) -> dict[str, Any]:
        from cs_risk_agent.data.repository import RiskScoreRepository

        async def _q() -> dict[str, Any]:
            async with self._session_factory() as session:
                scores = await RiskScoreRepository(session).get_all()
                by_level: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                total = 0.0
                for s in scores:
                    by_level[s.risk_level] = by_level.get(s.risk_level, 0) + 1
                    total += s.total_score
                n = max(len(scores), 1)
                return {"total_companies": len(scores), "by_level": by_level,
                        "avg_score": round(total / n, 1)}
        return self._run(_q())

    @property
    def risk_scores(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import RiskScoreRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                scores = await RiskScoreRepository(session).get_all()
                return [
                    {"entity_id": s.company_id, "total_score": s.total_score,
                     "risk_level": s.risk_level, "fiscal_year": s.fiscal_year,
                     "fiscal_quarter": s.fiscal_quarter, "da_score": s.da_score,
                     "fraud_score": s.fraud_score, "rule_score": s.rule_score,
                     "benford_score": s.benford_score, "risk_factors": s.risk_factors or []}
                    for s in scores
                ]
        return self._run(_q())

    # --- アラート ---

    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import AlertRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                alerts = await AlertRepository(session).get_all(severity=severity)
                return [
                    {"id": a.id, "entity_id": a.company_id, "severity": a.severity,
                     "category": a.category, "title": a.title,
                     "description": a.description,
                     "created_at": a.created_at.isoformat(), "is_read": a.is_read,
                     "recommended_action": a.recommended_action}
                    for a in alerts
                ]
        return self._run(_q())

    def get_unread_alerts(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import AlertRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                alerts = await AlertRepository(session).get_unread()
                return [
                    {"id": a.id, "entity_id": a.company_id, "severity": a.severity,
                     "title": a.title, "created_at": a.created_at.isoformat(),
                     "is_read": False}
                    for a in alerts
                ]
        return self._run(_q())

    @property
    def alerts(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import AlertRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                alerts = await AlertRepository(session).get_all()
                return [
                    {"id": a.id, "entity_id": a.company_id, "severity": a.severity,
                     "category": a.category, "title": a.title,
                     "created_at": a.created_at.isoformat(), "is_read": a.is_read}
                    for a in alerts
                ]
        return self._run(_q())

    # --- 財務データ ---

    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import FinancialStatementRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                repo = FinancialStatementRepository(session)
                stmts = await repo.get_by_entity(entity_id)
                result: list[dict[str, Any]] = []
                for fs in stmts:
                    accts = await repo.get_accounts(fs.id)
                    row: dict[str, Any] = {
                        "id": fs.id, "entity_id": fs.company_id,
                        "fiscal_year": fs.fiscal_year, "fiscal_quarter": fs.fiscal_quarter,
                        "filing_date": fs.filing_date.isoformat() if fs.filing_date else None,
                        "source": fs.source,
                    }
                    for a in accts:
                        row[a.account_code] = a.amount
                    result.append(row)
                return result
        return self._run(_q())

    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import FinancialStatementRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                repo = FinancialStatementRepository(session)
                stmts = await repo.get_all_latest()
                result: list[dict[str, Any]] = []
                for fs in stmts:
                    accts = await repo.get_accounts(fs.id)
                    row: dict[str, Any] = {
                        "entity_id": fs.company_id,
                        "fiscal_year": fs.fiscal_year, "fiscal_quarter": fs.fiscal_quarter,
                    }
                    for a in accts:
                        row[a.account_code] = a.amount
                    result.append(row)
                return result
        return self._run(_q())

    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import FinancialStatementRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                repo = FinancialStatementRepository(session)
                fs = await repo.get_latest(entity_id)
                if not fs:
                    return []
                accts = await repo.get_accounts(fs.id)
                tb: dict[str, dict[str, Any]] = {}
                for a in accts:
                    code = a.account_code
                    if code not in tb:
                        tb[code] = {"account_code": code, "account_name": a.account_name,
                                    "total_debit": 0.0, "total_credit": 0.0,
                                    "balance": 0.0, "entry_count": 0}
                    amt = a.amount or 0.0
                    if amt >= 0:
                        tb[code]["total_debit"] += amt
                    else:
                        tb[code]["total_credit"] += abs(amt)
                    tb[code]["balance"] += amt
                    tb[code]["entry_count"] += 1
                return sorted(tb.values(), key=lambda x: x["account_code"])
        return self._run(_q())

    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import FinancialStatementRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                repo = FinancialStatementRepository(session)
                stmts = await repo.get_by_entity(entity_id)
                entries: list[dict[str, Any]] = []
                for fs in stmts:
                    accts = await repo.get_accounts(fs.id)
                    for a in accts:
                        entries.append({
                            "id": a.id, "entity_id": entity_id,
                            "date": fs.filing_date.strftime("%Y-%m-%d") if fs.filing_date else None,
                            "account_code": a.account_code,
                            "account_name": a.account_name,
                            "debit": a.amount if a.amount >= 0 else 0.0,
                            "credit": abs(a.amount) if a.amount < 0 else 0.0,
                            "description": a.account_name, "is_anomaly": False,
                        })
                return entries
        return self._run(_q())

    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        from cs_risk_agent.data.repository import FinancialStatementRepository

        async def _q() -> list[dict[str, Any]]:
            async with self._session_factory() as session:
                repo = FinancialStatementRepository(session)
                stmts = await repo.get_by_entity(entity_id)
                result: list[dict[str, Any]] = []
                for fs in stmts:
                    accts = await repo.get_accounts(fs.id)
                    m = {a.account_code: a.amount for a in accts}
                    rev = m.get("revenue", 0) or 1
                    cogs = m.get("cogs", 0) or 0
                    op = m.get("operating_income", 0) or 0
                    ni = m.get("net_income", 0) or 0
                    ta = m.get("total_assets", 0) or 1
                    eq = m.get("total_equity", 0) or 1
                    ca = m.get("current_assets", 0) or 0
                    cl = m.get("current_liabilities", 0) or 1
                    tl = m.get("total_liabilities", 0) or 0
                    result.append({
                        "entity_id": entity_id,
                        "fiscal_year": fs.fiscal_year, "fiscal_quarter": fs.fiscal_quarter,
                        "period": f"{fs.fiscal_year} Q{fs.fiscal_quarter}",
                        "gross_margin": round((rev - cogs) / rev * 100, 1),
                        "operating_margin": round(op / rev * 100, 1),
                        "net_margin": round(ni / rev * 100, 1),
                        "roe": round(ni / eq * 100, 1),
                        "roa": round(ni / ta * 100, 1),
                        "current_ratio": round(ca / cl, 2),
                        "debt_equity_ratio": round(tl / eq, 2),
                    })
                return result
        return self._run(_q())


# シングルトンインスタンス
_provider: DataProvider | None = None


def get_data_provider() -> DataProvider:
    """設定に基づいてデータプロバイダーを返す."""
    global _provider  # noqa: PLW0603
    if _provider is not None:
        return _provider

    settings = get_settings()
    if settings.data_mode == DataMode.DB:
        logger.info("データモード: DB (SQLAlchemy Repository)")
        _provider = DBDataProvider()
    else:
        logger.info("データモード: Demo (JSON/CSV)")
        _provider = DemoDataProvider()

    return _provider


def reset_provider() -> None:
    """プロバイダーをリセット（テスト用）."""
    global _provider  # noqa: PLW0603
    _provider = None
