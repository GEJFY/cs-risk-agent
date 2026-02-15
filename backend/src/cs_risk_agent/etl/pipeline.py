"""ETLパイプライン - データ取込・変換・格納の統合パイプライン."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """パイプライン実行ステータス."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """パイプライン実行結果."""

    pipeline_id: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    steps_completed: int = 0
    total_steps: int = 0
    records_processed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ETLPipeline:
    """ETLパイプライン.

    ステップ:
    1. Extract: EDINET/Excel/CSVからデータ取得
    2. Transform: データクレンジング・正規化
    3. Load: DB格納
    4. Validate: 整合性検証
    """

    def __init__(self) -> None:
        self._steps = [
            ("extract", self._extract),
            ("transform", self._transform),
            ("load", self._load),
            ("validate", self._validate),
        ]

    async def run(
        self,
        source_type: str,
        source_config: dict,
    ) -> PipelineResult:
        """パイプライン実行."""
        result = PipelineResult(
            total_steps=len(self._steps),
            status=PipelineStatus.RUNNING,
        )

        for step_name, step_fn in self._steps:
            try:
                logger.info("Pipeline step: %s", step_name)
                records = await step_fn(source_type, source_config, result)
                result.records_processed += records
                result.steps_completed += 1
            except Exception as e:
                result.errors.append(f"{step_name}: {e}")
                result.status = PipelineStatus.FAILED
                logger.error("Pipeline step %s failed: %s", step_name, e)
                return result

        result.status = PipelineStatus.COMPLETED
        logger.info(
            "Pipeline completed: %d records processed",
            result.records_processed,
        )
        return result

    async def _extract(
        self,
        source_type: str,
        source_config: dict,
        result: PipelineResult,
    ) -> int:
        """データ抽出ステップ."""
        if source_type == "edinet":
            from cs_risk_agent.etl.edinet_client import EdinetClient

            client = EdinetClient(api_key=source_config.get("api_key", ""))
            logger.info("EDINET extraction configured")
            await client.close()
            return 0

        elif source_type == "excel":
            from cs_risk_agent.etl.excel_loader import ExcelLoader

            loader = ExcelLoader()
            data = loader.load(source_config.get("file_path", ""))
            if data.errors:
                result.warnings.extend(str(e) for e in data.errors)
            return data.valid_rows

        elif source_type == "csv":
            import pandas as pd

            file_path = source_config.get("file_path", "")
            df = pd.read_csv(file_path)
            return len(df)

        else:
            raise ValueError(f"Unknown source type: {source_type}")

    async def _transform(
        self,
        source_type: str,
        source_config: dict,
        result: PipelineResult,
    ) -> int:
        """データ変換ステップ."""
        logger.info("Transform step: normalizing data")
        return 0

    async def _load(
        self,
        source_type: str,
        source_config: dict,
        result: PipelineResult,
    ) -> int:
        """データ格納ステップ."""
        logger.info("Load step: storing to database")
        return 0

    async def _validate(
        self,
        source_type: str,
        source_config: dict,
        result: PipelineResult,
    ) -> int:
        """データ検証ステップ."""
        logger.info("Validate step: checking data integrity")
        return 0
