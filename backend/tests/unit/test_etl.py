"""ETLモジュールのユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.etl.pipeline import ETLPipeline, PipelineResult, PipelineStatus

# ---------------------------------------------------------------------------
# PipelineStatus / PipelineResult テスト
# ---------------------------------------------------------------------------


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
        assert result.warnings == []

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

    def test_pipeline_result_warnings(self) -> None:
        result = PipelineResult(
            warnings=["Deprecated column", "Missing optional field"],
        )
        assert len(result.warnings) == 2


# ---------------------------------------------------------------------------
# ETLPipeline テスト
# ---------------------------------------------------------------------------


class TestETLPipeline:
    """ETLパイプラインのテスト."""

    def test_init(self) -> None:
        pipeline = ETLPipeline()
        assert len(pipeline._steps) == 4

    @pytest.mark.asyncio
    async def test_run_unknown_source_type(self) -> None:
        pipeline = ETLPipeline()
        result = await pipeline.run("unknown", {})
        assert result.status == PipelineStatus.FAILED
        assert len(result.errors) > 0
        assert "Unknown source type" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_transform_load_validate(self) -> None:
        """transform/load/validate ステップはログ出力のみ."""
        pipeline = ETLPipeline()
        # _steps リストの参照を直接差し替える (bound method のため patch.object では不可)
        mock_extract = AsyncMock(return_value=10)
        pipeline._steps[0] = ("extract", mock_extract)
        result = await pipeline.run("test", {})
        assert result.status == PipelineStatus.COMPLETED
        assert result.steps_completed == 4
        assert result.records_processed == 10

    @pytest.mark.asyncio
    async def test_run_edinet_source(self) -> None:
        pipeline = ETLPipeline()
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        with patch(
            "cs_risk_agent.etl.edinet_client.EdinetClient",
            return_value=mock_client,
        ):
            # _extract を直接テスト
            pr = PipelineResult()
            records = await pipeline._extract("edinet", {"api_key": "test"}, pr)
            assert records == 0
            mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_excel_source(self) -> None:
        pipeline = ETLPipeline()
        mock_result = MagicMock()
        mock_result.errors = []
        mock_result.valid_rows = 50
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_result
        with patch(
            "cs_risk_agent.etl.excel_loader.ExcelLoader",
            return_value=mock_loader,
        ):
            pr = PipelineResult()
            records = await pipeline._extract("excel", {"file_path": "test.xlsx"}, pr)
            assert records == 50

    @pytest.mark.asyncio
    async def test_run_excel_source_with_errors(self) -> None:
        pipeline = ETLPipeline()
        mock_result = MagicMock()
        mock_result.errors = [MagicMock(__str__=lambda self: "row 1: missing value")]
        mock_result.valid_rows = 45
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_result
        with patch(
            "cs_risk_agent.etl.excel_loader.ExcelLoader",
            return_value=mock_loader,
        ):
            pr = PipelineResult()
            records = await pipeline._extract("excel", {"file_path": "test.xlsx"}, pr)
            assert records == 45
            assert len(pr.warnings) > 0

    @pytest.mark.asyncio
    async def test_transform_step(self) -> None:
        pipeline = ETLPipeline()
        pr = PipelineResult()
        records = await pipeline._transform("test", {}, pr)
        assert records == 0

    @pytest.mark.asyncio
    async def test_load_step(self) -> None:
        pipeline = ETLPipeline()
        pr = PipelineResult()
        records = await pipeline._load("test", {}, pr)
        assert records == 0

    @pytest.mark.asyncio
    async def test_validate_step(self) -> None:
        pipeline = ETLPipeline()
        pr = PipelineResult()
        records = await pipeline._validate("test", {}, pr)
        assert records == 0

    @pytest.mark.asyncio
    async def test_step_failure_stops_pipeline(self) -> None:
        pipeline = ETLPipeline()
        mock_extract = AsyncMock(side_effect=RuntimeError("extract failed"))
        pipeline._steps[0] = ("extract", mock_extract)
        result = await pipeline.run("test", {})
        assert result.status == PipelineStatus.FAILED
        assert result.steps_completed == 0
        assert "extract: extract failed" in result.errors[0]


# ---------------------------------------------------------------------------
# ExcelLoader テスト
# ---------------------------------------------------------------------------


class TestExcelLoader:
    """ExcelLoaderのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.excel_loader import ExcelLoader

        assert ExcelLoader is not None

    def test_init_defaults(self) -> None:
        from cs_risk_agent.etl.excel_loader import ExcelLoader

        loader = ExcelLoader()
        assert loader is not None

    def test_init_custom(self) -> None:
        from cs_risk_agent.etl.excel_loader import ExcelLoader

        loader = ExcelLoader(
            column_map={"test": "test_en"},
            required_columns={"test_en"},
            sheet_name=1,
        )
        assert loader is not None

    def test_load_result_dataclass(self) -> None:
        from cs_risk_agent.etl.excel_loader import LoadResult

        result = LoadResult(
            records=[],
            total_rows=0,
            valid_rows=0,
            errors=[],
            warnings=[],
            column_mapping={},
            metadata={},
        )
        assert result.is_valid is True

    def test_load_result_with_errors(self) -> None:
        from cs_risk_agent.etl.excel_loader import LoadResult, ValidationError

        result = LoadResult(
            records=[],
            total_rows=10,
            valid_rows=8,
            errors=[ValidationError(row=1, column="amount", message="invalid")],
            warnings=[],
            column_mapping={},
            metadata={},
        )
        assert result.is_valid is False

    def test_validation_error_dataclass(self) -> None:
        from cs_risk_agent.etl.excel_loader import ValidationError

        err = ValidationError(row=5, column="revenue", message="missing value")
        assert err.row == 5
        assert err.severity == "error"

    def test_column_map_constant(self) -> None:
        from cs_risk_agent.etl.excel_loader import COLUMN_MAP

        assert "売上高" in COLUMN_MAP
        assert COLUMN_MAP["売上高"] == "revenue"

    def test_load_nonexistent_file(self) -> None:
        from cs_risk_agent.etl.excel_loader import ExcelLoader

        loader = ExcelLoader()
        result = loader.load("/nonexistent/file.xlsx")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# EdinetClient テスト
# ---------------------------------------------------------------------------


class TestEdinetClient:
    """EdinetClientのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.edinet_client import EdinetClient

        assert EdinetClient is not None

    def test_init(self) -> None:
        from cs_risk_agent.etl.edinet_client import EdinetClient

        client = EdinetClient(api_key="test_key")
        assert client is not None

    def test_document_dataclass(self) -> None:
        from cs_risk_agent.etl.edinet_client import EdinetDocument

        doc = EdinetDocument(
            doc_id="S100TEST",
            edinet_code="E00001",
            sec_code="1234",
            filer_name="Test Corp",
            doc_type_code="120",
            doc_description="Annual report",
            filing_date="2025-06-30",
            period_start="2024-04-01",
            period_end="2025-03-31",
            xbrl_flag=True,
            pdf_flag=True,
        )
        assert doc.doc_id == "S100TEST"
        assert doc.xbrl_flag is True

    def test_search_result_dataclass(self) -> None:
        from cs_risk_agent.etl.edinet_client import SearchResult

        sr = SearchResult(documents=[], total=0, metadata={})
        assert sr.total == 0

    def test_doc_type_constants(self) -> None:
        from cs_risk_agent.etl.edinet_client import (
            DOC_TYPE_ANNUAL,
            DOC_TYPE_QUARTERLY,
            DOC_TYPE_SECURITIES_REGISTRATION,
        )

        assert DOC_TYPE_ANNUAL == "120"
        assert DOC_TYPE_QUARTERLY == "140"
        assert DOC_TYPE_SECURITIES_REGISTRATION == "030"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from cs_risk_agent.etl.edinet_client import EdinetClient

        client = EdinetClient(api_key="test_key")
        await client.close()  # should not raise


# ---------------------------------------------------------------------------
# XBRLParser テスト
# ---------------------------------------------------------------------------


class TestXbrlParser:
    """XBRLParserのテスト."""

    def test_import(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLParser

        assert XBRLParser is not None

    def test_init_defaults(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLParser

        parser = XBRLParser()
        assert parser is not None

    def test_init_custom_map(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLParser

        parser = XBRLParser(account_map={"custom_element": "custom_key"})
        assert parser is not None

    def test_xbrl_fact_dataclass(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLFact

        fact = XBRLFact(
            element="Revenue",
            value="1000000",
            context_ref="CurrentYear",
            unit_ref="JPY",
            decimals="-3",
            period_start="2024-04-01",
            period_end="2025-03-31",
        )
        assert fact.element == "Revenue"
        assert fact.value == "1000000"

    def test_parse_result_dataclass(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import ParseResult

        result = ParseResult(
            financial_data={},
            raw_facts=[],
            metadata={},
            errors=[],
        )
        assert result.financial_data == {}

    def test_xbrl_ns_constant(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRL_NS

        assert "xbrli" in XBRL_NS

    def test_account_map_constant(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import ACCOUNT_MAP

        assert isinstance(ACCOUNT_MAP, dict)
        assert len(ACCOUNT_MAP) > 0

    def test_parse_nonexistent_file(self) -> None:
        from cs_risk_agent.etl.xbrl_parser import XBRLParser

        parser = XBRLParser()
        result = parser.parse("/nonexistent/file.xbrl")
        assert len(result.errors) > 0
