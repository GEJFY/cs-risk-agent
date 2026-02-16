"""seed_db スクリプトのユニットテスト."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSeedDatabase:
    """seed_database 関数のテスト."""

    @patch("cs_risk_agent.scripts.seed_db.create_engine")
    @patch("cs_risk_agent.scripts.seed_db.DemoData")
    @patch("cs_risk_agent.scripts.seed_db.get_settings")
    def test_seed_skips_when_data_exists(
        self,
        mock_settings: MagicMock,
        mock_demo: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """企業データが既に存在する場合はスキップ."""
        from cs_risk_agent.scripts.seed_db import seed_database

        # Settings モック
        mock_settings.return_value.database.sync_url = "postgresql://test"

        # Engine モック
        engine = MagicMock()
        mock_engine.return_value = engine
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        # tables exist
        conn.execute.return_value.scalar.return_value = 1

        # DemoData モック
        demo_instance = MagicMock()
        demo_instance.companies = [{"id": "COMP-001", "name": "Test"}]
        mock_demo.get.return_value = demo_instance

        # Session モック - 既存データあり
        session = MagicMock()
        session.execute.return_value.scalar.return_value = 5  # 5 companies exist

        with patch("cs_risk_agent.scripts.seed_db.Session") as mock_session_cls:
            mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
            mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

            seed_database()

        # commit は呼ばれない (スキップ)
        session.commit.assert_not_called()

    @patch("cs_risk_agent.scripts.seed_db.create_engine")
    @patch("cs_risk_agent.scripts.seed_db.DemoData")
    @patch("cs_risk_agent.scripts.seed_db.get_settings")
    def test_seed_exits_when_no_tables(
        self,
        mock_settings: MagicMock,
        mock_demo: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """テーブルが存在しない場合は exit."""
        from cs_risk_agent.scripts.seed_db import seed_database

        mock_settings.return_value.database.sync_url = "postgresql://test"

        engine = MagicMock()
        mock_engine.return_value = engine
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.scalar.return_value = 0  # no tables

        with pytest.raises(SystemExit):
            seed_database()

    @patch("cs_risk_agent.scripts.seed_db.create_engine")
    @patch("cs_risk_agent.scripts.seed_db.DemoData")
    @patch("cs_risk_agent.scripts.seed_db.get_settings")
    def test_seed_exits_when_no_demo_data(
        self,
        mock_settings: MagicMock,
        mock_demo: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """デモデータが見つからない場合は exit."""
        from cs_risk_agent.scripts.seed_db import seed_database

        mock_settings.return_value.database.sync_url = "postgresql://test"

        engine = MagicMock()
        mock_engine.return_value = engine
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.scalar.return_value = 1  # tables exist

        demo_instance = MagicMock()
        demo_instance.companies = []  # no data
        mock_demo.get.return_value = demo_instance

        with pytest.raises(SystemExit):
            seed_database()

    @patch("cs_risk_agent.scripts.seed_db.create_engine")
    @patch("cs_risk_agent.scripts.seed_db.DemoData")
    @patch("cs_risk_agent.scripts.seed_db.get_settings")
    def test_seed_inserts_demo_data(
        self,
        mock_settings: MagicMock,
        mock_demo: MagicMock,
        mock_engine: MagicMock,
    ) -> None:
        """正常ケース: デモデータを投入."""
        mock_settings.return_value.database.sync_url = "postgresql://test"

        engine = MagicMock()
        mock_engine.return_value = engine
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.scalar.return_value = 1  # tables exist

        demo_instance = MagicMock()
        demo_instance.companies = [
            {"id": "COMP-001", "name": "Test Co", "country": "JPN"},
        ]
        demo_instance.subsidiaries = [
            {
                "id": "SUB-001",
                "parent_company_id": "COMP-001",
                "name": "Sub Co",
                "country": "JPN",
            },
        ]
        demo_instance.risk_scores = [
            {
                "entity_id": "SUB-001",
                "total_score": 75.0,
                "risk_level": "high",
                "da_score": 60.0,
                "fraud_score": 70.0,
                "rule_score": 80.0,
                "benford_score": 50.0,
            },
        ]
        mock_demo.get.return_value = demo_instance

        session = MagicMock()
        session.execute.return_value.scalar.return_value = 0  # no existing data

        with (
            patch("cs_risk_agent.scripts.seed_db.Session") as mock_session_cls,
            patch("passlib.hash.bcrypt.hash", return_value="hashed") as mock_bcrypt,
        ):
            mock_session_cls.return_value.__enter__ = MagicMock(return_value=session)
            mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

            from cs_risk_agent.scripts.seed_db import seed_database

            seed_database()

        # commit が呼ばれた
        session.commit.assert_called_once()
        # add が呼ばれた (1 company + 1 subsidiary + 1 risk_score + 3 users = 6)
        assert session.add.call_count == 6


class TestDemoLoaderPathResolution:
    """demo_loader のパス解決テスト."""

    def test_resolve_demo_dir_finds_project_root(self) -> None:
        """プロジェクトルートの demo_data/ を見つける."""
        from cs_risk_agent.demo_loader import _DEMO_DIR

        assert _DEMO_DIR.exists()
        assert (_DEMO_DIR / "companies.json").exists()

    def test_resolve_demo_dir_function(self) -> None:
        """_resolve_demo_dir 関数が正しいパスを返す."""
        from cs_risk_agent.demo_loader import _resolve_demo_dir

        result = _resolve_demo_dir()
        assert result.exists()
        assert (result / "companies.json").exists()

    def test_resolve_demo_dir_env_override(self) -> None:
        """DEMO_DATA_DIR 環境変数でオーバーライド可能."""
        from cs_risk_agent.demo_loader import _resolve_demo_dir

        with patch.dict("os.environ", {"DEMO_DATA_DIR": "/tmp/fake"}):
            result = _resolve_demo_dir()
            assert result == Path("/tmp/fake")
