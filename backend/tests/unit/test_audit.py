"""監査ログ ユニットテスト.

AuditLogger のログ記録・検索・マスキングロジックを検証する。
"""

from __future__ import annotations

import pytest

from cs_risk_agent.observability.audit import (
    AuditEntry,
    AuditLogger,
    _mask_sensitive,
    _truncate,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def logger() -> AuditLogger:
    """テスト用 AuditLogger（バッファ上限100件）."""
    return AuditLogger(max_buffer_size=100)


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestLogCreatesEntry:
    """log メソッドの検証."""

    def test_log_creates_entry(self, logger):
        """log が AuditEntry を返すこと."""
        entry = logger.log(
            user_id="user-001",
            action="test.action",
            resource="companies/C001",
        )
        assert isinstance(entry, AuditEntry)
        assert entry.user_id == "user-001"
        assert entry.action == "test.action"
        assert entry.resource == "companies/C001"
        assert entry.timestamp is not None

    def test_log_with_all_params(self, logger):
        """全パラメータ指定でログが記録されること."""
        entry = logger.log(
            user_id="user-002",
            action="analysis.run",
            resource="analysis/fraud",
            ai_provider="azure",
            ai_model="gpt-4o",
            input_summary="テスト入力",
            output_summary="テスト出力",
            request_path="/api/v1/analysis",
            request_method="POST",
            status_code=200,
            duration_ms=150,
            ip_address="192.168.1.1",
            custom_field="extra_data",
        )
        assert entry.ai_provider == "azure"
        assert entry.ai_model == "gpt-4o"
        assert entry.status_code == 200
        assert entry.duration_ms == 150
        assert entry.ip_address == "192.168.1.1"
        assert entry.metadata.get("custom_field") == "extra_data"

    def test_log_increments_buffer(self, logger):
        """log でバッファが増加すること."""
        for i in range(5):
            logger.log(user_id=f"user-{i}", action="test.action")
        assert len(logger.get_recent(limit=100)) == 5


class TestLogAIRequest:
    """AI リクエスト専用ログの検証."""

    def test_log_ai_request(self, logger):
        """log_ai_request が AI 関連情報を記録すること."""
        entry = logger.log_ai_request(
            user_id="user-001",
            provider="azure",
            model="gpt-4o",
            input_text="リスク分析を実行",
            output_text="分析結果: 低リスク",
            tokens_used=100,
            cost_usd=0.05,
            duration_ms=500,
        )
        assert entry.action == "ai.complete"
        assert entry.ai_provider == "azure"
        assert entry.ai_model == "gpt-4o"
        assert entry.duration_ms == 500
        assert entry.metadata.get("tokens_used") == 100
        assert entry.metadata.get("cost_usd") == 0.05


class TestGetRecent:
    """直近ログ取得の検証."""

    def test_get_recent(self, logger):
        """直近ログが正しく取得できること."""
        for i in range(10):
            logger.log(user_id=f"user-{i}", action="test.action")

        recent = logger.get_recent(limit=5)
        assert len(recent) == 5

        # 最新5件が返ること
        assert recent[-1].user_id == "user-9"
        assert recent[0].user_id == "user-5"

    def test_get_recent_less_than_limit(self, logger):
        """ログ数がlimitより少ない場合に全件返ること."""
        logger.log(user_id="user-001", action="test.action")
        logger.log(user_id="user-002", action="test.action")

        recent = logger.get_recent(limit=100)
        assert len(recent) == 2

    def test_get_recent_empty(self, logger):
        """ログが空の場合に空リストを返すこと."""
        recent = logger.get_recent()
        assert recent == []


class TestGetByUser:
    """ユーザー別ログ取得の検証."""

    def test_get_by_user(self, logger):
        """特定ユーザーのログが正しくフィルタされること."""
        logger.log(user_id="user-001", action="action.a")
        logger.log(user_id="user-002", action="action.b")
        logger.log(user_id="user-001", action="action.c")
        logger.log(user_id="user-003", action="action.d")

        user1_logs = logger.get_by_user("user-001")
        assert len(user1_logs) == 2
        for entry in user1_logs:
            assert entry.user_id == "user-001"

    def test_get_by_user_not_found(self, logger):
        """存在しないユーザーで空リストが返ること."""
        logger.log(user_id="user-001", action="test.action")
        result = logger.get_by_user("nonexistent")
        assert result == []


class TestSensitiveDataMasking:
    """機密データマスキングの検証."""

    def test_email_masked(self):
        """メールアドレスがマスクされること."""
        text = "連絡先: yamada@example.com までお問い合わせください"
        result = _mask_sensitive(text)
        assert "[EMAIL]" in result
        assert "yamada@example.com" not in result

    def test_phone_masked(self):
        """電話番号がマスクされること."""
        text = "電話番号: 03-1234-5678"
        result = _mask_sensitive(text)
        assert "[PHONE]" in result
        assert "03-1234-5678" not in result

    def test_id_number_masked(self):
        """マイナンバー（12桁数字）がマスクされること."""
        text = "マイナンバー: 123456789012"
        result = _mask_sensitive(text)
        assert "[ID_NUMBER]" in result
        assert "123456789012" not in result

    def test_no_sensitive_data_unchanged(self):
        """機密情報がないテキストは変更されないこと."""
        text = "通常のテキストです"
        result = _mask_sensitive(text)
        assert result == text

    def test_log_ai_request_masks_input(self, logger):
        """log_ai_request がinputをマスクして記録すること."""
        entry = logger.log_ai_request(
            user_id="user-001",
            provider="azure",
            model="gpt-4o",
            input_text="メール: test@example.com の情報を分析",
            output_text="分析完了",
        )
        assert "[EMAIL]" in entry.input_summary
        assert "test@example.com" not in entry.input_summary


class TestBufferLimit:
    """バッファ上限の検証."""

    def test_buffer_limit(self):
        """バッファ上限を超えた場合に古いエントリが削除されること."""
        logger = AuditLogger(max_buffer_size=5)

        for i in range(10):
            logger.log(user_id=f"user-{i}", action="test.action")

        # 最新5件のみ残る
        recent = logger.get_recent(limit=100)
        assert len(recent) == 5
        assert recent[0].user_id == "user-5"
        assert recent[-1].user_id == "user-9"

    def test_clear_buffer(self, logger):
        """clear_buffer がバッファをクリアすること."""
        for i in range(5):
            logger.log(user_id=f"user-{i}", action="test.action")

        count = logger.clear_buffer()
        assert count == 5
        assert logger.get_recent(limit=100) == []


class TestTruncate:
    """テキスト切り詰めの検証."""

    def test_truncate_long_text(self):
        """長いテキストが切り詰められること."""
        long_text = "A" * 1000
        result = _truncate(long_text, max_length=100)
        assert len(result) == 100 + len("...[truncated]")
        assert result.endswith("...[truncated]")

    def test_truncate_short_text(self):
        """短いテキストはそのまま返ること."""
        short_text = "Hello"
        result = _truncate(short_text, max_length=100)
        assert result == short_text

    def test_truncate_none(self):
        """None が空文字列を返すこと."""
        result = _truncate(None)
        assert result == ""

    def test_truncate_empty(self):
        """空文字列が空文字列を返すこと."""
        result = _truncate("")
        assert result == ""
