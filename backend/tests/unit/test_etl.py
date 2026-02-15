"""ETLモジュールのユニットテスト."""

from __future__ import annotations

from cs_risk_agent.etl.pipeline import PipelineResult, PipelineStatus


class TestPipelineModels:
    """パイプラインモデルのテスト."""

    def test_pipeline_status_enum(self) -> None:
        assert PipelineStatus.PENDING == "pending"
        assert PipelineStatus.RUNNING == "running"
        assert PipelineStatus.COMPLETED == "completed"
        assert PipelineStatus.FAILED == "failed"

    def test_pipeline_result_defaults(self) -> None:
        result = PipelineResult()
        assert result.pipeline_id == ""
        assert result.status == PipelineStatus.PENDING
        assert result.steps_completed == 0
        assert result.total_steps == 0
        assert result.records_processed == 0
        assert result.errors == []

    def test_pipeline_result_custom(self) -> None:
        result = PipelineResult(
            pipeline_id="P-001",
            status=PipelineStatus.COMPLETED,
            steps_completed=5,
            total_steps=5,
            records_processed=1000,
            errors=[],
        )
        assert result.pipeline_id == "P-001"
        assert result.status == PipelineStatus.COMPLETED
        assert result.records_processed == 1000

    def test_pipeline_result_with_errors(self) -> None:
        result = PipelineResult(
            pipeline_id="P-002",
            status=PipelineStatus.FAILED,
            errors=["File not found", "Parse error"],
        )
        assert len(result.errors) == 2


class TestExcelLoader:
    """ExcelLoaderのインポートテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.excel_loader import ExcelLoader

        assert ExcelLoader is not None


class TestEdinetClient:
    """EdinetClientのインポートテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.edinet_client import EdinetClient

        assert EdinetClient is not None


class TestXbrlParser:
    """XBRLParserのインポートテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLParser

        assert XBRLParser is not None
