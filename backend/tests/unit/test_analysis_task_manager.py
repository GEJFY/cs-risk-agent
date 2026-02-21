"""AnalysisTaskManager テスト - 非同期分析パイプライン."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cs_risk_agent.analysis.task_manager import (
    AnalysisTask,
    TaskManager,
    TaskStatus,
    get_task_manager,
)


class TestAnalysisTask:
    """AnalysisTask テスト."""

    def test_create_task(self) -> None:
        """タスク作成."""
        task = AnalysisTask(
            task_id="test-001",
            company_ids=["C001", "C002"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )
        assert task.task_id == "test-001"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        assert len(task.company_ids) == 2
        assert task.total_steps == 8  # 2 companies * 4 engines

    def test_create_task_custom_engines(self) -> None:
        """カスタムエンジン指定."""
        task = AnalysisTask(
            task_id="test-002",
            company_ids=["C001"],
            fiscal_year=2025,
            fiscal_quarter=4,
            engines=["da", "fraud"],
        )
        assert task.engines == ["da", "fraud"]
        assert task.total_steps == 2

    def test_to_dict(self) -> None:
        """辞書化."""
        task = AnalysisTask(
            task_id="test-003",
            company_ids=["C001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )
        d = task.to_dict()
        assert d["task_id"] == "test-003"
        assert d["status"] == "pending"
        assert d["company_count"] == 1
        assert d["fiscal_year"] == 2025


class TestTaskManager:
    """TaskManager テスト."""

    def test_create_task(self) -> None:
        """タスク作成."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["C001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )
        assert task.task_id is not None
        assert task.status == TaskStatus.PENDING

    def test_get_task(self) -> None:
        """タスク取得."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["C001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )
        retrieved = manager.get_task(task.task_id)
        assert retrieved is task

    def test_get_task_not_found(self) -> None:
        """存在しないタスク."""
        manager = TaskManager()
        assert manager.get_task("non-existent") is None

    def test_list_tasks(self) -> None:
        """タスク一覧."""
        manager = TaskManager()
        for i in range(3):
            manager.create_task(
                company_ids=[f"C00{i}"],
                fiscal_year=2025,
                fiscal_quarter=4,
            )
        tasks = manager.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_limit(self) -> None:
        """タスク一覧 (上限)."""
        manager = TaskManager()
        for i in range(5):
            manager.create_task(
                company_ids=[f"C00{i}"],
                fiscal_year=2025,
                fiscal_quarter=4,
            )
        tasks = manager.list_tasks(limit=2)
        assert len(tasks) == 2

    def test_run_analysis_with_demo_data(self) -> None:
        """デモデータで分析実行."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["SUB001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        mock_provider = MagicMock()
        mock_provider.get_risk_score_by_entity.return_value = {
            "entity_name": "テスト企業",
            "total_score": 75.0,
            "risk_level": "high",
            "da_score": 70.0,
            "fraud_score": 65.0,
            "rule_score": 80.0,
            "benford_score": 85.0,
            "risk_factors": ["売掛金急増"],
        }
        mock_provider.get_entity_by_id.return_value = {"name": "テスト企業"}

        with patch("cs_risk_agent.data.provider.get_data_provider", return_value=mock_provider):
            manager.run_analysis(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 100
        assert len(task.results) == 1
        assert task.results[0]["total_score"] == 75.0

    def test_run_analysis_no_risk_score(self) -> None:
        """リスクスコアなしの企業."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["NEW001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        mock_provider = MagicMock()
        mock_provider.get_risk_score_by_entity.return_value = None
        mock_provider.get_entity_by_id.return_value = {"name": "新規企業"}

        with patch("cs_risk_agent.data.provider.get_data_provider", return_value=mock_provider):
            manager.run_analysis(task)

        assert task.status == TaskStatus.COMPLETED
        assert len(task.results) == 1
        assert task.results[0]["risk_level"] == "low"

    def test_run_analysis_failure(self) -> None:
        """分析失敗."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["C001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        with patch("cs_risk_agent.data.provider.get_data_provider", side_effect=RuntimeError("DB接続エラー")):
            manager.run_analysis(task)

        assert task.status == TaskStatus.FAILED
        assert task.error is not None
        assert "DB接続エラー" in task.error

    def test_run_analysis_multiple_companies(self) -> None:
        """複数企業の分析."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["C001", "C002", "C003"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        mock_provider = MagicMock()
        mock_provider.get_risk_score_by_entity.return_value = {
            "entity_name": "企業",
            "total_score": 50.0,
            "risk_level": "medium",
            "da_score": 45.0,
            "fraud_score": 40.0,
            "rule_score": 55.0,
            "benford_score": 60.0,
            "risk_factors": [],
        }
        mock_provider.get_entity_by_id.return_value = {"name": "企業"}

        with patch("cs_risk_agent.data.provider.get_data_provider", return_value=mock_provider):
            manager.run_analysis(task)

        assert task.status == TaskStatus.COMPLETED
        assert len(task.results) == 3


class TestGetTaskManager:
    """get_task_manager テスト."""

    def test_singleton(self) -> None:
        """シングルトン."""
        m1 = get_task_manager()
        m2 = get_task_manager()
        assert m1 is m2
