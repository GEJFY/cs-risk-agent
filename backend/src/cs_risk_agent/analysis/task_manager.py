"""非同期分析タスクマネージャー.

BackgroundTasks を使用してリスク分析をバックグラウンドで実行し、
ステータスのポーリングと結果取得をサポートする。

分析エンジン統合:
    - RuleEngine: ルールベースリスク評価
    - BenfordAnalyzer: 仕訳データのベンフォード法則検定
    - IntegratedRiskScorer: 各エンジンスコアの重み付け統合
    - FraudPredictor / DA分析: データ要件が満たされる場合に実行
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

import pandas as pd

logger = logging.getLogger(__name__)


class TaskStatus(StrEnum):
    """タスクステータス."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTask:
    """分析タスク."""

    def __init__(
        self,
        task_id: str,
        company_ids: list[str],
        fiscal_year: int,
        fiscal_quarter: int,
        engines: list[str] | None = None,
    ) -> None:
        self.task_id = task_id
        self.company_ids = company_ids
        self.fiscal_year = fiscal_year
        self.fiscal_quarter = fiscal_quarter
        self.engines = engines or ["da", "fraud", "rule", "benford"]
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total_steps = len(company_ids) * len(self.engines)
        self.completed_steps = 0
        self.results: list[dict[str, Any]] = []
        self.error: str | None = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: str | None = None
        self.completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """タスク情報を辞書化."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "company_count": len(self.company_ids),
            "engines": self.engines,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_count": len(self.results),
        }


def _run_rule_engine(company_data: dict[str, Any]) -> dict[str, Any]:
    """ルールエンジン実行."""
    from cs_risk_agent.analysis.rule_engine import RuleEngine

    engine = RuleEngine()
    result = engine.evaluate_and_score(company_data)
    return {
        "score": result.total_score,
        "triggered_count": result.triggered_count,
        "total_rules": result.total_rules,
        "severity_distribution": result.severity_distribution,
        "triggered_rules": [
            {"rule_id": r.rule_id, "name": r.name, "severity": r.severity}
            for r in result.results if r.triggered
        ],
    }


def _run_benford(journal_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """ベンフォード分析実行."""
    from cs_risk_agent.analysis.benford import BenfordAnalyzer

    analyzer = BenfordAnalyzer(min_sample_size=10)
    amounts = [
        abs(je.get("debit", 0) or 0) + abs(je.get("credit", 0) or 0)
        for je in journal_entries
    ]
    amounts = [a for a in amounts if a > 0]

    if len(amounts) < 10:
        return {"score": 0.0, "detail": "サンプル不足", "sample_size": len(amounts)}

    series = pd.Series(amounts)
    account_result = analyzer.analyze_account(series, account_code="ALL")
    return {
        "score": account_result.risk_score,
        "sample_size": account_result.sample_size,
        "conformity": account_result.benford_result.conformity if account_result.benford_result else None,
        "mad": account_result.benford_result.mad if account_result.benford_result else None,
        "duplicate_ratio": account_result.duplicate_result.duplicate_ratio if account_result.duplicate_result else None,
    }


def _build_company_data(
    entity: dict[str, Any],
    financial: dict[str, Any] | None,
    risk_score: dict[str, Any] | None,
) -> dict[str, Any]:
    """ルールエンジン用のcompany_data辞書を構築."""
    data: dict[str, Any] = {**entity}
    if financial:
        data.update(financial)
    if risk_score:
        data["total_score"] = risk_score.get("total_score", 0)
    return data


class TaskManager:
    """分析タスクのライフサイクル管理.

    インメモリストア。将来的にRedisまたはDBに移行可能。
    """

    def __init__(self) -> None:
        self._tasks: dict[str, AnalysisTask] = {}

    def create_task(
        self,
        company_ids: list[str],
        fiscal_year: int,
        fiscal_quarter: int,
        engines: list[str] | None = None,
    ) -> AnalysisTask:
        """新規タスク作成."""
        task_id = str(uuid4())
        task = AnalysisTask(
            task_id=task_id,
            company_ids=company_ids,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            engines=engines,
        )
        self._tasks[task_id] = task
        logger.info(
            "analysis.task_created",
            extra={"task_id": task_id, "companies": len(company_ids)},
        )
        return task

    def get_task(self, task_id: str) -> AnalysisTask | None:
        """タスク取得."""
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        """最近のタスク一覧."""
        tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return [t.to_dict() for t in tasks[:limit]]

    def run_analysis(self, task: AnalysisTask) -> None:
        """分析実行 (同期 - BackgroundTask内で呼ばれる).

        実際の分析エンジン (RuleEngine, BenfordAnalyzer, IntegratedRiskScorer) を
        呼び出し、デモデータに対してリアルなスコアリングを行う。
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        logger.info("analysis.task_started", extra={"task_id": task.task_id})

        try:
            from cs_risk_agent.analysis.risk_scorer import IntegratedRiskScorer
            from cs_risk_agent.data.provider import get_data_provider

            provider = get_data_provider()
            scorer = IntegratedRiskScorer()

            for company_id in task.company_ids:
                entity = provider.get_entity_by_id(company_id)
                entity_name = entity.get("name", "") if entity else ""

                # 各エンジンのスコアと詳細を収集
                engine_scores: dict[str, float] = {}
                engine_details: dict[str, dict[str, Any]] = {}
                risk_factors: list[str] = []

                # --- ルールエンジン ---
                if "rule" in task.engines:
                    try:
                        fs_list = provider.get_financial_statements_by_entity(company_id)
                        latest_fs = fs_list[-1] if fs_list else {}
                        rs_data = provider.get_risk_score_by_entity(company_id)
                        company_data = _build_company_data(
                            entity or {}, latest_fs, rs_data,
                        )
                        rule_result = _run_rule_engine(company_data)
                        engine_scores["rule_engine"] = rule_result["score"]
                        engine_details["rule_engine"] = rule_result
                        for tr in rule_result.get("triggered_rules", []):
                            risk_factors.append(f"[Rule] {tr['name']} ({tr['severity']})")
                    except Exception as e:
                        logger.warning("rule_engine failed for %s: %s", company_id, e)
                        engine_scores["rule_engine"] = 0.0

                    task.completed_steps += 1
                    task.progress = int(task.completed_steps / max(task.total_steps, 1) * 100)

                # --- ベンフォード分析 ---
                if "benford" in task.engines:
                    try:
                        journal_entries = provider.get_journal_entries_by_entity(company_id)
                        benford_result = _run_benford(journal_entries)
                        engine_scores["benford"] = benford_result["score"]
                        engine_details["benford"] = benford_result
                        if benford_result["score"] >= 60:
                            risk_factors.append(
                                f"[Benford] 数値分布異常 (スコア: {benford_result['score']:.0f})"
                            )
                    except Exception as e:
                        logger.warning("benford failed for %s: %s", company_id, e)
                        engine_scores["benford"] = 0.0

                    task.completed_steps += 1
                    task.progress = int(task.completed_steps / max(task.total_steps, 1) * 100)

                # --- 裁量的発生高 (DA) ---
                if "da" in task.engines:
                    try:
                        fs_list = provider.get_financial_statements_by_entity(company_id)
                        if len(fs_list) >= 2:
                            latest = fs_list[-1]
                            ta = (latest.get("total_assets", 0) or 1)
                            ni = latest.get("net_income", 0) or 0
                            ocf = latest.get("operating_cash_flow", 0) or 0
                            total_accruals = (ni - ocf) / ta
                            # DA score: 高い裁量的発生高 → 高リスク
                            da_score = min(100.0, abs(total_accruals) * 1000)
                            engine_scores["discretionary_accruals"] = da_score
                            engine_details["discretionary_accruals"] = {
                                "total_accruals_ratio": round(total_accruals, 4),
                                "score": da_score,
                            }
                            if da_score >= 60:
                                risk_factors.append(
                                    f"[DA] 高い裁量的発生高 (比率: {total_accruals:.4f})"
                                )
                        else:
                            engine_scores["discretionary_accruals"] = 0.0
                    except Exception as e:
                        logger.warning("DA analysis failed for %s: %s", company_id, e)
                        engine_scores["discretionary_accruals"] = 0.0

                    task.completed_steps += 1
                    task.progress = int(task.completed_steps / max(task.total_steps, 1) * 100)

                # --- 不正予測 ---
                if "fraud" in task.engines:
                    try:
                        fs_list = provider.get_financial_statements_by_entity(company_id)
                        if len(fs_list) >= 2:
                            curr = fs_list[-1]
                            prev = fs_list[-2]
                            # Beneish M-Score 簡易計算 (DSRI + GMI)
                            recv = curr.get("receivables", 0) or 1
                            recv_p = prev.get("receivables", 0) or 1
                            rev = curr.get("revenue", 0) or 1
                            rev_p = prev.get("revenue", 0) or 1
                            dsri = (recv / rev) / max(recv_p / rev_p, 0.001)
                            gmi_num = (rev_p - (prev.get("cogs", 0) or 0)) / max(rev_p, 1)
                            gmi_den = (rev - (curr.get("cogs", 0) or 0)) / max(rev, 1)
                            gmi = gmi_num / max(gmi_den, 0.001)
                            # 正規化してスコア化
                            m_indicator = (dsri - 1.0) * 30 + (gmi - 1.0) * 20
                            fraud_score = max(0.0, min(100.0, 30.0 + m_indicator))
                            engine_scores["fraud_prediction"] = fraud_score
                            engine_details["fraud_prediction"] = {
                                "dsri": round(dsri, 3),
                                "gmi": round(gmi, 3),
                                "score": round(fraud_score, 1),
                            }
                            if fraud_score >= 60:
                                risk_factors.append(
                                    f"[Fraud] Beneish指標異常 (DSRI: {dsri:.2f})"
                                )
                        else:
                            engine_scores["fraud_prediction"] = 0.0
                    except Exception as e:
                        logger.warning("fraud analysis failed for %s: %s", company_id, e)
                        engine_scores["fraud_prediction"] = 0.0

                    task.completed_steps += 1
                    task.progress = int(task.completed_steps / max(task.total_steps, 1) * 100)

                # --- 統合スコア ---
                integrated = scorer.evaluate(engine_scores, engine_details)

                result = {
                    "id": str(uuid4()),
                    "company_id": company_id,
                    "company_name": entity_name,
                    "fiscal_year": task.fiscal_year,
                    "fiscal_quarter": task.fiscal_quarter,
                    "status": "completed",
                    "total_score": integrated.integrated_score,
                    "risk_level": integrated.risk_level,
                    "da_score": round(engine_scores.get("discretionary_accruals", 0), 1),
                    "fraud_score": round(engine_scores.get("fraud_prediction", 0), 1),
                    "rule_score": round(engine_scores.get("rule_engine", 0), 1),
                    "benford_score": round(engine_scores.get("benford", 0), 1),
                    "risk_factors": risk_factors or integrated.recommendations,
                    "engines_run": task.engines,
                    "engine_details": engine_details,
                    "summary": integrated.summary_ja,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                task.results.append(result)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            task.progress = 100
            logger.info(
                "analysis.task_completed",
                extra={"task_id": task.task_id, "results": len(task.results)},
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            logger.exception("analysis.task_failed", extra={"task_id": task.task_id})


# シングルトン
_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """TaskManager シングルトン取得."""
    global _task_manager  # noqa: PLW0603
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
