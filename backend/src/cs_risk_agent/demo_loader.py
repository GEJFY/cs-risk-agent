"""デモデータローダー.

demo_data/ ディレクトリからデモデータを読み込み、APIエンドポイントに提供する。
データが存在しない場合はフォールバック用の最小データを返す。
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# demo_data/ はプロジェクトルート直下
_DEMO_DIR = Path(__file__).parent.parent.parent.parent / "demo_data"

# 数値変換対象カラム
_NUMERIC_COLS = {
    "revenue", "revenue_prior", "cogs", "cogs_prior", "sga", "sga_prior",
    "operating_income", "net_income", "operating_cash_flow",
    "total_assets", "total_assets_prior", "current_assets", "current_assets_prior",
    "ppe", "ppe_prior", "receivables", "receivables_prior",
    "inventory", "inventory_prior", "depreciation", "depreciation_prior",
    "total_liabilities", "total_equity",
    "current_liabilities", "current_liabilities_prior",
    "long_term_debt", "long_term_debt_prior",
    "retained_earnings", "ebit",
    "debit", "credit",
    "fiscal_year", "fiscal_quarter",
}


def _load_json(filename: str) -> list[dict[str, Any]] | dict[str, Any]:
    """JSONファイルを読み込む."""
    path = _DEMO_DIR / filename
    if not path.exists():
        logger.warning("デモデータが見つかりません: %s  (make demo-data で生成してください)", path)
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_csv(filename: str) -> list[dict[str, Any]]:
    """CSVファイルを読み込み、数値カラムを変換."""
    path = _DEMO_DIR / filename
    if not path.exists():
        logger.warning("CSVデータが見つかりません: %s", path)
        return []
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            converted: dict[str, Any] = {}
            for k, v in row.items():
                if k in _NUMERIC_COLS and v:
                    try:
                        converted[k] = float(v)
                        if converted[k] == int(converted[k]):
                            converted[k] = int(converted[k])
                    except ValueError:
                        converted[k] = v
                elif v == "True":
                    converted[k] = True
                elif v == "False":
                    converted[k] = False
                else:
                    converted[k] = v
            rows.append(converted)
    return rows


class DemoData:
    """デモデータをシングルトンで管理."""

    _instance: DemoData | None = None

    def __init__(self) -> None:
        self.companies: list[dict[str, Any]] = []
        self.subsidiaries: list[dict[str, Any]] = []
        self.risk_scores: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []
        self.financial_statements: list[dict[str, Any]] = []
        self.journal_entries: list[dict[str, Any]] = []
        self._loaded = False

    @classmethod
    def get(cls) -> DemoData:
        if cls._instance is None:
            cls._instance = cls()
        if not cls._instance._loaded:
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        self.companies = _load_json("companies.json") or []
        self.subsidiaries = _load_json("subsidiaries.json") or []
        self.risk_scores = _load_json("risk_scores.json") or []
        self.alerts = _load_json("alerts.json") or []
        self.financial_statements = _load_csv("financial_statements.csv")
        self.journal_entries = _load_csv("journal_entries.csv")
        self._loaded = True
        if self.companies:
            logger.info(
                "デモデータ読み込み完了: 企業=%d, 子会社=%d, リスクスコア=%d, "
                "アラート=%d, 財務諸表=%d, 仕訳=%d",
                len(self.companies),
                len(self.subsidiaries),
                len(self.risk_scores),
                len(self.alerts),
                len(self.financial_statements),
                len(self.journal_entries),
            )
        else:
            logger.warning(
                "デモデータが空です。python scripts/generate_demo_data.py を実行してください。"
            )

    def reload(self) -> None:
        """データを再読み込み."""
        self._loaded = False
        self._load()

    def get_all_entities(self) -> list[dict[str, Any]]:
        """親会社 + 子会社の全エンティティ."""
        return self.companies + self.subsidiaries

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """IDでエンティティを検索."""
        for e in self.get_all_entities():
            if e.get("id") == entity_id:
                return e
        return None

    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        """エンティティIDでリスクスコアを検索."""
        for rs in self.risk_scores:
            if rs.get("entity_id") == entity_id:
                return rs
        return None

    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        """子会社にリスクスコアを付加して返す."""
        result = []
        for sub in self.subsidiaries:
            entry = {**sub}
            rs = self.get_risk_score_by_entity(sub["id"])
            if rs:
                entry["total_score"] = rs["total_score"]
                entry["risk_level"] = rs["risk_level"]
                entry["risk_factors"] = rs["risk_factors"]
            result.append(entry)
        return result

    def get_risk_summary(self) -> dict[str, Any]:
        """リスクサマリーを集計."""
        by_level = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_score = 0.0
        for rs in self.risk_scores:
            level = rs.get("risk_level", "low")
            by_level[level] = by_level.get(level, 0) + 1
            total_score += rs.get("total_score", 0)

        n = max(len(self.risk_scores), 1)
        return {
            "total_companies": len(self.subsidiaries),
            "by_level": by_level,
            "avg_score": round(total_score / n, 1),
        }

    def get_unread_alerts(self) -> list[dict[str, Any]]:
        """未読アラート."""
        return [a for a in self.alerts if not a.get("is_read", True)]

    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        """重要度でフィルタ."""
        if severity is None:
            return self.alerts
        return [a for a in self.alerts if a.get("severity") == severity]

    # --- 財務データ関連 ---

    def get_financial_statements_by_entity(
        self, entity_id: str,
    ) -> list[dict[str, Any]]:
        """エンティティIDで財務諸表を取得（四半期順ソート）."""
        rows = [
            fs for fs in self.financial_statements
            if fs.get("entity_id") == entity_id
        ]
        rows.sort(key=lambda x: (x.get("fiscal_year", 0), x.get("fiscal_quarter", 0)))
        return rows

    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        """全エンティティの最新四半期の財務データ."""
        latest: dict[str, dict[str, Any]] = {}
        for fs in self.financial_statements:
            eid = fs.get("entity_id", "")
            key = (fs.get("fiscal_year", 0), fs.get("fiscal_quarter", 0))
            if eid not in latest or key > (
                latest[eid].get("fiscal_year", 0),
                latest[eid].get("fiscal_quarter", 0),
            ):
                latest[eid] = fs
        return list(latest.values())

    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        """エンティティIDの仕訳をTB（勘定科目別集計）に変換."""
        entries = [
            je for je in self.journal_entries
            if je.get("entity_id") == entity_id
        ]
        # 勘定科目別に集計
        tb: dict[str, dict[str, Any]] = {}
        for je in entries:
            code = je.get("account_code", "")
            name = je.get("account_name", "")
            if code not in tb:
                tb[code] = {
                    "account_code": code,
                    "account_name": name,
                    "total_debit": 0.0,
                    "total_credit": 0.0,
                    "balance": 0.0,
                    "entry_count": 0,
                }
            tb[code]["total_debit"] += je.get("debit", 0) or 0
            tb[code]["total_credit"] += je.get("credit", 0) or 0
            tb[code]["balance"] = tb[code]["total_debit"] - tb[code]["total_credit"]
            tb[code]["entry_count"] += 1

        result = sorted(tb.values(), key=lambda x: x["account_code"])
        return result

    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        """エンティティIDの仕訳データ."""
        entries = [
            je for je in self.journal_entries
            if je.get("entity_id") == entity_id
        ]
        if anomaly_only:
            entries = [je for je in entries if je.get("is_anomaly")]
        entries.sort(key=lambda x: x.get("date", ""), reverse=True)
        return entries

    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        """エンティティの四半期別財務指標を計算."""
        fs_list = self.get_financial_statements_by_entity(entity_id)
        result = []
        for fs in fs_list:
            rev = fs.get("revenue", 0) or 1
            ta = fs.get("total_assets", 0) or 1
            eq = fs.get("total_equity", 0) or 1
            cl = fs.get("current_liabilities", 0) or 1
            tl = fs.get("total_liabilities", 0) or 1

            ratios = {
                "entity_id": entity_id,
                "fiscal_year": fs.get("fiscal_year"),
                "fiscal_quarter": fs.get("fiscal_quarter"),
                "period": f"{fs.get('fiscal_year')} Q{fs.get('fiscal_quarter')}",
                # 収益性
                "gross_margin": round(
                    (rev - (fs.get("cogs", 0) or 0)) / rev * 100, 1,
                ),
                "operating_margin": round(
                    (fs.get("operating_income", 0) or 0) / rev * 100, 1,
                ),
                "net_margin": round(
                    (fs.get("net_income", 0) or 0) / rev * 100, 1,
                ),
                "roe": round(
                    (fs.get("net_income", 0) or 0) / eq * 100, 1,
                ),
                "roa": round(
                    (fs.get("net_income", 0) or 0) / ta * 100, 1,
                ),
                # 安全性
                "current_ratio": round(
                    (fs.get("current_assets", 0) or 0) / cl, 2,
                ),
                "debt_equity_ratio": round(tl / eq, 2),
                # 効率性
                "asset_turnover": round(rev / ta, 2),
                "receivables_turnover": round(
                    rev / max(fs.get("receivables", 0) or 1, 1), 2,
                ),
                "inventory_turnover": round(
                    (fs.get("cogs", 0) or 0) / max(fs.get("inventory", 0) or 1, 1), 2,
                ),
                # CF
                "ocf_to_revenue": round(
                    (fs.get("operating_cash_flow", 0) or 0) / rev * 100, 1,
                ),
                # 絶対値
                "revenue": fs.get("revenue", 0),
                "operating_income": fs.get("operating_income", 0),
                "net_income": fs.get("net_income", 0),
                "total_assets": fs.get("total_assets", 0),
                "total_equity": fs.get("total_equity", 0),
                "operating_cash_flow": fs.get("operating_cash_flow", 0),
            }
            result.append(ratios)
        return result
