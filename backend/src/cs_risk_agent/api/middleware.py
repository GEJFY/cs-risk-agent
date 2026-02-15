"""HTTPミドルウェア定義 - 監査ログ・リクエストトレーシング."""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """全HTTPリクエストの監査ログを記録するミドルウェア.

    各リクエストについて以下の情報を structlog で出力する:
    - HTTPメソッド
    - リクエストパス
    - ユーザー識別子（認証済みの場合）
    - レスポンスステータスコード
    - 処理時間（ミリ秒）
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """リクエストを処理し監査ログを記録する.

        Args:
            request: 受信HTTPリクエスト。
            call_next: 次のミドルウェアまたはルートハンドラ。

        Returns:
            HTTPレスポンス。
        """
        start_time = time.perf_counter()

        # ユーザー識別子の抽出（認証ヘッダーがある場合）
        user_id = _extract_user_id(request)

        # リクエスト開始ログ
        log = logger.bind(
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            client_ip=_get_client_ip(request),
        )
        log.info("request_started")

        try:
            response = await call_next(request)
        except Exception:
            # 未処理例外の場合もログを記録
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.error(
                "request_failed",
                status_code=500,
                duration_ms=round(duration_ms, 2),
            )
            raise

        # 処理時間の計算
        duration_ms = (time.perf_counter() - start_time) * 1000

        # レスポンスログ
        log_method = log.warning if response.status_code >= 400 else log.info
        log_method(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # レスポンスヘッダーに処理時間を付加
        response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))

        return response


def _extract_user_id(request: Request) -> str | None:
    """リクエストからユーザー識別子を抽出する.

    Authorization ヘッダーが存在する場合、トークンの先頭8文字を
    マスク済み識別子として返す。

    Args:
        request: 受信HTTPリクエスト。

    Returns:
        マスク済みユーザー識別子、またはヘッダーが無い場合は None。
    """
    auth_header: str | None = request.headers.get("authorization")
    if auth_header is None:
        return None

    # Bearer トークンの先頭部分をマスクして返す（ログ安全性確保）
    parts = auth_header.split(" ", maxsplit=1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        # トークンの先頭8文字のみ記録（セキュリティ考慮）
        return f"token:{token[:8]}..." if len(token) > 8 else "token:***"
    return "unknown"


def _get_client_ip(request: Request) -> str:
    """リクエスト元のクライアントIPアドレスを取得する.

    X-Forwarded-For ヘッダーがあればそちらを優先する（プロキシ対応）。

    Args:
        request: 受信HTTPリクエスト。

    Returns:
        クライアントIPアドレス文字列。
    """
    # リバースプロキシ経由の場合
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # 最初のIPがオリジナルクライアント
        return forwarded_for.split(",")[0].strip()

    # 直接接続の場合
    if request.client:
        return request.client.host
    return "unknown"
