"""ヘルスチェックエンドポイント - サービス稼働状態の確認."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# レスポンスモデル
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス."""

    status: str = Field(..., description="サービス稼働状態")
    version: str = Field(..., description="アプリケーションバージョン")


class ReadinessDetail(BaseModel):
    """各コンポーネントの準備状態."""

    status: str = Field(..., description="コンポーネント状態 (ok / error)")
    message: str = Field(default="", description="詳細メッセージ")
    latency_ms: float | None = Field(default=None, description="応答遅延（ミリ秒）")


class ReadinessResponse(BaseModel):
    """レディネスチェックレスポンス."""

    status: str = Field(..., description="総合準備状態")
    timestamp: str = Field(..., description="チェック実行時刻 (ISO 8601)")
    components: dict[str, ReadinessDetail] = Field(
        default_factory=dict, description="各コンポーネントの状態"
    )


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=HealthResponse,
    summary="ヘルスチェック",
    description="サービスが稼働中であることを確認する軽量エンドポイント。",
)
async def health_check() -> HealthResponse:
    """サービスの基本稼働状態を返す.

    Returns:
        ヘルスチェック結果（status と version）。
    """
    return HealthResponse(status="healthy", version="0.1.0")


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    summary="レディネスチェック",
    description="DB・Redis 等の外部依存サービスへの接続状態を確認する。",
)
async def readiness_check() -> ReadinessResponse:
    """外部依存サービスの接続状態を確認する.

    DB と Redis への接続を試行し、各コンポーネントの状態を返す。
    全コンポーネントが正常であれば status="ready"、
    一つでも異常があれば status="degraded" を返す。

    TODO: 実際の DB/Redis 接続チェックを実装する。

    Returns:
        各コンポーネントの準備状態を含むレスポンス。
    """
    components: dict[str, ReadinessDetail] = {}

    # --- データベース接続チェック ---
    components["database"] = await _check_database()

    # --- Redis 接続チェック ---
    components["redis"] = await _check_redis()

    # 総合判定
    all_ok = all(c.status == "ok" for c in components.values())
    overall_status = "ready" if all_ok else "degraded"

    if not all_ok:
        logger.warning(
            "readiness_check_degraded",
            components={k: v.status for k, v in components.items()},
        )

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )


# ---------------------------------------------------------------------------
# 内部チェック関数
# ---------------------------------------------------------------------------


async def _check_database() -> ReadinessDetail:
    """データベース接続を確認する.

    TODO: 実際の AsyncSession で SELECT 1 を実行する。

    Returns:
        データベースの準備状態。
    """
    try:
        # TODO: 実装時は以下に差し替え
        # async with async_session_factory() as session:
        #     await session.execute(text("SELECT 1"))
        return ReadinessDetail(
            status="ok",
            message="placeholder - DB check not yet implemented",
            latency_ms=0.0,
        )
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return ReadinessDetail(
            status="error",
            message=f"Database connection failed: {exc}",
        )


async def _check_redis() -> ReadinessDetail:
    """Redis 接続を確認する.

    TODO: 実際の Redis クライアントで PING を実行する。

    Returns:
        Redis の準備状態。
    """
    try:
        # TODO: 実装時は以下に差し替え
        # redis_client = get_redis()
        # await redis_client.ping()
        return ReadinessDetail(
            status="ok",
            message="placeholder - Redis check not yet implemented",
            latency_ms=0.0,
        )
    except Exception as exc:
        logger.error("redis_health_check_failed", error=str(exc))
        return ReadinessDetail(
            status="error",
            message=f"Redis connection failed: {exc}",
        )
