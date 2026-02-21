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

    def _make_mock_provider(self) -> MagicMock:
        """分析エンジン用のモックプロバイダーを作成."""
        mock_provider = MagicMock()
        mock_provider.get_entity_by_id.return_value = {"name": "テスト企業"}
        mock_provider.get_risk_score_by_entity.return_value = {
            "total_score": 50.0,
        }
        mock_provider.get_financial_statements_by_entity.return_value = [
            {
                "fiscal_year": 2024, "fiscal_quarter": 4,
                "revenue": 1000000, "revenue_prior": 900000,
                "cogs": 600000, "cogs_prior": 550000,
                "receivables": 200000, "receivables_prior": 150000,
                "total_assets": 5000000, "total_assets_prior": 4500000,
                "current_assets": 2000000, "current_assets_prior": 1800000,
                "ppe": 1500000, "ppe_prior": 1400000,
                "net_income": 100000, "operating_cash_flow": 80000,
                "total_equity": 2000000, "total_liabilities": 3000000,
                "current_liabilities": 1000000, "long_term_debt": 1500000,
                "sga": 250000, "sga_prior": 230000,
                "depreciation": 100000, "depreciation_prior": 95000,
                "inventory": 300000, "inventory_prior": 280000,
                "retained_earnings": 1500000, "operating_income": 150000,
            },
            {
                "fiscal_year": 2025, "fiscal_quarter": 4,
                "revenue": 1100000, "revenue_prior": 1000000,
                "cogs": 660000, "cogs_prior": 600000,
                "receivables": 220000, "receivables_prior": 200000,
                "total_assets": 5500000, "total_assets_prior": 5000000,
                "current_assets": 2200000, "current_assets_prior": 2000000,
                "ppe": 1600000, "ppe_prior": 1500000,
                "net_income": 110000, "operating_cash_flow": 90000,
                "total_equity": 2200000, "total_liabilities": 3300000,
                "current_liabilities": 1100000, "long_term_debt": 1600000,
                "sga": 270000, "sga_prior": 250000,
                "depreciation": 110000, "depreciation_prior": 100000,
                "inventory": 320000, "inventory_prior": 300000,
                "retained_earnings": 1700000, "operating_income": 170000,
            },
        ]
        mock_provider.get_journal_entries_by_entity.return_value = [
            {"debit": 1000 + i * 100, "credit": 0, "account_code": "1100"}
            for i in range(50)
        ]
        return mock_provider

    def test_run_analysis_with_engines(self) -> None:
        """分析エンジン統合テスト."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["SUB001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        mock_provider = self._make_mock_provider()

        with patch("cs_risk_agent.data.provider.get_data_provider", return_value=mock_provider):
            manager.run_analysis(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 100
        assert len(task.results) == 1
        result = task.results[0]
        assert "total_score" in result
        assert "risk_level" in result
        assert result["risk_level"] in ("critical", "high", "medium", "low")
        assert "rule_score" in result
        assert "benford_score" in result
        assert "engines_run" in result

    def test_run_analysis_no_financial_data(self) -> None:
        """財務データなしの企業."""
        manager = TaskManager()
        task = manager.create_task(
            company_ids=["NEW001"],
            fiscal_year=2025,
            fiscal_quarter=4,
        )

        mock_provider = MagicMock()
        mock_provider.get_entity_by_id.return_value = {"name": "新規企業"}
        mock_provider.get_risk_score_by_entity.return_value = None
        mock_provider.get_financial_statements_by_entity.return_value = []
        mock_provider.get_journal_entries_by_entity.return_value = []

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

        mock_provider = self._make_mock_provider()

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
