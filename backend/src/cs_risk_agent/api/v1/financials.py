"""財務データAPIエンドポイント.

財務諸表、TB(試算表)、仕訳データ、財務指標を提供する。
ルールベースエンジンやAIエージェントが洞察を得るための分析用データも含む。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from cs_risk_agent.demo_loader import DemoData

router = APIRouter()


@router.get("/statements")
async def list_financial_statements(
    entity_id: str | None = None,
    fiscal_year: int | None = None,
) -> dict[str, Any]:
    """財務諸表一覧.

    entity_id指定でエンティティ別、未指定で全エンティティの最新四半期を返す。
    """
    demo = DemoData.get()

    if entity_id:
        items = demo.get_financial_statements_by_entity(entity_id)
        if fiscal_year:
            items = [fs for fs in items if fs.get("fiscal_year") == fiscal_year]
        return {"entity_id": entity_id, "items": items, "total": len(items)}
    else:
        items = demo.get_all_financial_latest()
        return {"items": items, "total": len(items)}


@router.get("/statements/{entity_id}/trend")
async def get_financial_trend(entity_id: str) -> dict[str, Any]:
    """財務推移データ(PL/BS/CF主要項目の四半期トレンド)."""
    demo = DemoData.get()
    fs_list = demo.get_financial_statements_by_entity(entity_id)

    trends = []
    for fs in fs_list:
        trends.append(
            {
                "period": f"{fs.get('fiscal_year')} Q{fs.get('fiscal_quarter')}",
                "fiscal_year": fs.get("fiscal_year"),
                "fiscal_quarter": fs.get("fiscal_quarter"),
                # PL
                "revenue": fs.get("revenue", 0),
                "cogs": fs.get("cogs", 0),
                "sga": fs.get("sga", 0),
                "operating_income": fs.get("operating_income", 0),
                "net_income": fs.get("net_income", 0),
                # BS
                "total_assets": fs.get("total_assets", 0),
                "current_assets": fs.get("current_assets", 0),
                "receivables": fs.get("receivables", 0),
                "inventory": fs.get("inventory", 0),
                "total_liabilities": fs.get("total_liabilities", 0),
                "total_equity": fs.get("total_equity", 0),
                "long_term_debt": fs.get("long_term_debt", 0),
                # CF
                "operating_cash_flow": fs.get("operating_cash_flow", 0),
            }
        )

    entity = demo.get_entity_by_id(entity_id)
    return {
        "entity_id": entity_id,
        "entity_name": entity.get("name", "") if entity else "",
        "trends": trends,
    }


@router.get("/ratios/{entity_id}")
async def get_financial_ratios(entity_id: str) -> dict[str, Any]:
    """財務指標の四半期推移.

    収益性・安全性・効率性・CFの指標をルールエンジンやエージェントの入力に使用可能。
    """
    demo = DemoData.get()
    ratios = demo.compute_financial_ratios(entity_id)
    entity = demo.get_entity_by_id(entity_id)
    return {
        "entity_id": entity_id,
        "entity_name": entity.get("name", "") if entity else "",
        "ratios": ratios,
    }


@router.get("/ratios")
async def get_all_financial_ratios() -> dict[str, Any]:
    """全エンティティの最新財務指標一覧(比較分析用)."""
    demo = DemoData.get()
    all_entities = demo.get_all_entities()
    result = []
    for entity in all_entities:
        eid = entity.get("id", "")
        ratios = demo.compute_financial_ratios(eid)
        if ratios:
            latest = ratios[-1]
            latest["entity_name"] = entity.get("name", "")
            # リスクスコアも付加
            rs = demo.get_risk_score_by_entity(eid)
            if rs:
                latest["risk_score"] = rs.get("total_score")
                latest["risk_level"] = rs.get("risk_level")
            result.append(latest)
    return {"items": result, "total": len(result)}


@router.get("/trial-balance/{entity_id}")
async def get_trial_balance(entity_id: str) -> dict[str, Any]:
    """試算表(TB).

    仕訳データを勘定科目別に集計し、借方・貸方・残高を返す。
    """
    demo = DemoData.get()
    tb = demo.get_trial_balance(entity_id)
    entity = demo.get_entity_by_id(entity_id)
    return {
        "entity_id": entity_id,
        "entity_name": entity.get("name", "") if entity else "",
        "accounts": tb,
        "total_accounts": len(tb),
    }


@router.get("/journal-entries/{entity_id}")
async def get_journal_entries(
    entity_id: str,
    anomaly_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """仕訳データ一覧.

    anomaly_only=true で異常仕訳のみフィルタ。
    """
    demo = DemoData.get()
    entries = demo.get_journal_entries_by_entity(entity_id, anomaly_only=anomaly_only)
    total = len(entries)
    entries = entries[:limit]
    return {
        "entity_id": entity_id,
        "items": entries,
        "total": total,
        "returned": len(entries),
    }


@router.get("/balance-sheet/{entity_id}")
async def get_balance_sheet(entity_id: str) -> dict[str, Any]:
    """貸借対照表データ(BS構造化).

    資産・負債・純資産の内訳と推移をチャート描画用に整形。
    """
    demo = DemoData.get()
    fs_list = demo.get_financial_statements_by_entity(entity_id)
    entity = demo.get_entity_by_id(entity_id)

    bs_trend = []
    for fs in fs_list:
        bs_trend.append(
            {
                "period": f"{fs.get('fiscal_year')} Q{fs.get('fiscal_quarter')}",
                "assets": {
                    "current_assets": fs.get("current_assets", 0),
                    "receivables": fs.get("receivables", 0),
                    "inventory": fs.get("inventory", 0),
                    "ppe": fs.get("ppe", 0),
                    "other_assets": max(
                        (fs.get("total_assets", 0) or 0)
                        - (fs.get("current_assets", 0) or 0)
                        - (fs.get("ppe", 0) or 0),
                        0,
                    ),
                    "total": fs.get("total_assets", 0),
                },
                "liabilities": {
                    "current_liabilities": fs.get("current_liabilities", 0),
                    "long_term_debt": fs.get("long_term_debt", 0),
                    "other_liabilities": max(
                        (fs.get("total_liabilities", 0) or 0)
                        - (fs.get("current_liabilities", 0) or 0)
                        - (fs.get("long_term_debt", 0) or 0),
                        0,
                    ),
                    "total": fs.get("total_liabilities", 0),
                },
                "equity": {
                    "retained_earnings": fs.get("retained_earnings", 0),
                    "other_equity": max(
                        (fs.get("total_equity", 0) or 0) - (fs.get("retained_earnings", 0) or 0),
                        0,
                    ),
                    "total": fs.get("total_equity", 0),
                },
            }
        )

    return {
        "entity_id": entity_id,
        "entity_name": entity.get("name", "") if entity else "",
        "balance_sheets": bs_trend,
    }


@router.get("/income-statement/{entity_id}")
async def get_income_statement(entity_id: str) -> dict[str, Any]:
    """損益計算書データ(PL構造化).

    売上→売上原価→売上総利益→販管費→営業利益→純利益の構造。
    """
    demo = DemoData.get()
    fs_list = demo.get_financial_statements_by_entity(entity_id)
    entity = demo.get_entity_by_id(entity_id)

    pl_trend = []
    for fs in fs_list:
        rev = fs.get("revenue", 0) or 0
        cogs = fs.get("cogs", 0) or 0
        sga = fs.get("sga", 0) or 0
        oi = fs.get("operating_income", 0) or 0
        ni = fs.get("net_income", 0) or 0

        pl_trend.append(
            {
                "period": f"{fs.get('fiscal_year')} Q{fs.get('fiscal_quarter')}",
                "revenue": rev,
                "cogs": cogs,
                "gross_profit": rev - cogs,
                "sga": sga,
                "operating_income": oi,
                "net_income": ni,
                "gross_margin_pct": round((rev - cogs) / max(rev, 1) * 100, 1),
                "operating_margin_pct": round(oi / max(rev, 1) * 100, 1),
                "net_margin_pct": round(ni / max(rev, 1) * 100, 1),
                # 前年比
                "revenue_prior": fs.get("revenue_prior", 0),
                "revenue_growth_pct": round(
                    (rev - (fs.get("revenue_prior", 0) or 0))
                    / max(fs.get("revenue_prior", 0) or 1, 1)
                    * 100,
                    1,
                )
                if fs.get("revenue_prior")
                else None,
            }
        )

    return {
        "entity_id": entity_id,
        "entity_name": entity.get("name", "") if entity else "",
        "income_statements": pl_trend,
    }
