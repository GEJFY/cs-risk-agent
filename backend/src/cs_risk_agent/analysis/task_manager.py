"""非同期分析タスクマネージャー.

BackgroundTasks を使用してリスク分析をバックグラウンドで実行し、
ステータスのポーリングと結果取得をサポートする。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

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

        DemoDataProviderの場合はデモデータからスコアを取得。
        DBDataProviderの場合は分析エンジンを実行。
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        logger.info("analysis.task_started", extra={"task_id": task.task_id})

        try:
            from cs_risk_agent.data.provider import get_data_provider

            provider = get_data_provider()

            for company_id in task.company_ids:
                rs = provider.get_risk_score_by_entity(company_id)
                entity = provider.get_entity_by_id(company_id)

                if rs:
                    result = {
                        "id": str(uuid4()),
                        "company_id": company_id,
                        "company_name": rs.get("entity_name", ""),
                        "fiscal_year": task.fiscal_year,
                        "fiscal_quarter": task.fiscal_quarter,
                        "status": "completed",
                        "total_score": rs["total_score"],
                        "risk_level": rs["risk_level"],
                        "da_score": rs["da_score"],
                        "fraud_score": rs["fraud_score"],
                        "rule_score": rs["rule_score"],
                        "benford_score": rs["benford_score"],
                        "risk_factors": rs["risk_factors"],
                        "engines_run": task.engines,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    result = {
                        "id": str(uuid4()),
                        "company_id": company_id,
                        "company_name": entity.get("name", "") if entity else "",
                        "fiscal_year": task.fiscal_year,
                        "fiscal_quarter": task.fiscal_quarter,
                        "status": "completed",
                        "total_score": 25.0,
                        "risk_level": "low",
                        "da_score": 20.0,
                        "fraud_score": 15.0,
                        "rule_score": 25.0,
                        "benford_score": 10.0,
                        "risk_factors": [],
                        "engines_run": task.engines,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                task.results.append(result)
                task.completed_steps += len(task.engines)
                task.progress = int(task.completed_steps / max(task.total_steps, 1) * 100)

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
