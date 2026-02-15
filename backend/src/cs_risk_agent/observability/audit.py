"""監査ログモジュール - 誰が・いつ・どのモデルに・何を入力/出力したかを記録.

GRC要件に基づく完全な監査証跡を提供する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AuditEntry:
    """監査ログエントリ."""

    timestamp: datetime
    user_id: str
    action: str
    resource: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    request_path: str | None = None
    request_method: str | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    ip_address: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """監査ログ記録クラス.

    メモリバッファとstructlogへの同時出力を行う。
    DB永続化はAPIレイヤーで実装。
    """

    def __init__(self, max_buffer_size: int = 10000) -> None:
        self._buffer: list[AuditEntry] = []
        self._max_buffer_size = max_buffer_size

    def log(
        self,
        user_id: str,
        action: str,
        *,
        resource: str | None = None,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        request_path: str | None = None,
        request_method: str | None = None,
        status_code: int | None = None,
        duration_ms: int | None = None,
        ip_address: str | None = None,
        **extra: Any,
    ) -> AuditEntry:
        """監査ログを記録.

        Args:
            user_id: 操作ユーザーID
            action: アクション名 (e.g., "ai.complete", "analysis.run", "report.generate")
            resource: 対象リソース
            ai_provider: 使用AIプロバイダー
            ai_model: 使用AIモデル
            input_summary: 入力要約（機密情報はマスク）
            output_summary: 出力要約
            request_path: リクエストパス
            request_method: HTTPメソッド
            status_code: レスポンスステータスコード
            duration_ms: 処理時間(ms)
            ip_address: クライアントIPアドレス
            **extra: 追加メタデータ

        Returns:
            AuditEntry: 記録されたエントリ
        """
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource=resource,
            ai_provider=ai_provider,
            ai_model=ai_model,
            input_summary=_truncate(input_summary, 500) if input_summary else None,
            output_summary=_truncate(output_summary, 500) if output_summary else None,
            request_path=request_path,
            request_method=request_method,
            status_code=status_code,
            duration_ms=duration_ms,
            ip_address=ip_address,
            metadata=extra,
        )

        # structlogに出力
        logger.info(
            "audit",
            user_id=user_id,
            action=action,
            resource=resource,
            ai_provider=ai_provider,
            ai_model=ai_model,
            status_code=status_code,
            duration_ms=duration_ms,
        )

        # バッファに追加
        self._buffer.append(entry)
        if len(self._buffer) > self._max_buffer_size:
            self._buffer = self._buffer[-self._max_buffer_size:]

        return entry

    def log_ai_request(
        self,
        user_id: str,
        provider: str,
        model: str,
        input_text: str,
        output_text: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
    ) -> AuditEntry:
        """AI リクエスト専用の監査ログ."""
        return self.log(
            user_id=user_id,
            action="ai.complete",
            ai_provider=provider,
            ai_model=model,
            input_summary=_mask_sensitive(input_text),
            output_summary=_truncate(output_text, 500),
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

    def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        """直近の監査ログ取得."""
        return self._buffer[-limit:]

    def get_by_user(self, user_id: str, limit: int = 50) -> list[AuditEntry]:
        """ユーザー別監査ログ取得."""
        entries = [e for e in self._buffer if e.user_id == user_id]
        return entries[-limit:]

    def clear_buffer(self) -> int:
        """バッファクリア. クリアした件数を返す."""
        count = len(self._buffer)
        self._buffer.clear()
        return count


def _truncate(text: str | None, max_length: int = 500) -> str:
    """テキスト切り詰め."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[truncated]"


def _mask_sensitive(text: str) -> str:
    """機密情報のマスク処理."""
    import re

    # メールアドレスのマスク
    text = re.sub(r"[\w.-]+@[\w.-]+\.\w+", "[EMAIL]", text)
    # 電話番号のマスク
    text = re.sub(r"\d{2,4}-\d{2,4}-\d{4}", "[PHONE]", text)
    # マイナンバーのマスク
    text = re.sub(r"\d{12}", "[ID_NUMBER]", text)

    return _truncate(text, 500)


# シングルトン
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """AuditLoggerシングルトン取得."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
