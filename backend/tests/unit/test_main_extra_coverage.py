"""main.py 例外ハンドラ、ライフサイクル、tracing.py、config.py テスト."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


# --- Exception Handlers ---


class TestExceptionHandlerExecution:
    """例外ハンドラの実行パスをカバー."""

    @staticmethod
    def _make_app():
        from cs_risk_agent.main import _register_exception_handlers

        test_app = FastAPI()
        _register_exception_handlers(test_app)
        return test_app

    def test_authentication_error(self) -> None:
        from cs_risk_agent.core.exceptions import AuthenticationError

        app = self._make_app()

        @app.get("/t")
        async def _():
            raise AuthenticationError("bad token")

        r = TestClient(app).get("/t")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_authorization_error(self) -> None:
        from cs_risk_agent.core.exceptions import AuthorizationError

        app = self._make_app()

        @app.get("/t")
        async def _():
            raise AuthorizationError("forbidden")

        r = TestClient(app).get("/t")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    def test_budget_exceeded_error(self) -> None:
        from cs_risk_agent.core.exceptions import BudgetExceededError

        app = self._make_app()

        @app.get("/t")
        async def _():
            raise BudgetExceededError(100.0, 50.0)

        r = TestClient(app).get("/t")
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "BUDGET_EXCEEDED"

    def test_csriskageniterror(self) -> None:
        from cs_risk_agent.core.exceptions import CSRiskAgentError

        app = self._make_app()

        @app.get("/t")
        async def _():
            raise CSRiskAgentError("internal issue")

        r = TestClient(app, raise_server_exceptions=False).get("/t")
        assert r.status_code == 500

    def test_pydantic_validation_error(self) -> None:
        """pydantic ValidationError ハンドラ."""
        from pydantic import BaseModel

        app = self._make_app()

        @app.get("/t")
        async def _():
            class M(BaseModel):
                x: int

            M.model_validate({"x": "not_a_number"})

        r = TestClient(app, raise_server_exceptions=False).get("/t")
        assert r.status_code in (422, 500)

    def test_unhandled_exception(self) -> None:
        app = self._make_app()

        @app.get("/t")
        async def _():
            raise RuntimeError("unexpected crash")

        r = TestClient(app, raise_server_exceptions=False).get("/t")
        assert r.status_code == 500


# --- Lifespan ---


class TestLifespan:
    """ライフサイクルテスト."""

    def test_lifespan_startup_shutdown(self) -> None:
        """TestClient をコンテキストマネージャで使用し lifespan をトリガー."""
        from cs_risk_agent.main import app

        with TestClient(app) as client:
            r = client.get("/api/v1/health")
            assert r.status_code == 200


# --- Tracing ---


class TestTracingCoverage:
    """tracing.py カバレッジテスト."""

    def test_setup_tracing_normal(self) -> None:
        """正常パス（OpenTelemetry未インストール、TODO コメントアウト済み）."""
        settings = MagicMock()
        settings.observability.service_name = "test-svc"
        settings.observability.otel_endpoint = "http://localhost:4317"

        from cs_risk_agent.observability.tracing import setup_tracing

        setup_tracing(settings)

    def test_setup_tracing_general_exception(self) -> None:
        """logger.info が例外を投げた場合の Exception ハンドラ."""
        settings = MagicMock()
        settings.observability.service_name = "test-svc"
        settings.observability.otel_endpoint = "http://localhost:4317"

        with patch("cs_risk_agent.observability.tracing.logger") as mock_log:
            mock_log.info.side_effect = RuntimeError("log failure")
            mock_log.error = MagicMock()
            from cs_risk_agent.observability.tracing import setup_tracing

            setup_tracing(settings)
            mock_log.error.assert_called_once()

    def test_get_tracer_import_error(self) -> None:
        """OpenTelemetry 未インストール時は None を返す."""
        import sys

        from cs_risk_agent.observability.tracing import get_tracer

        # opentelemetry が実際にインストールされているので sys.modules で一時的に無効化
        otel_mods = {k: v for k, v in sys.modules.items() if k.startswith("opentelemetry")}
        for k in otel_mods:
            sys.modules[k] = None  # type: ignore[assignment]
        try:
            result = get_tracer("test-module")
            assert result is None
        finally:
            for k, v in otel_mods.items():
                sys.modules[k] = v


# --- Config load_config_file ---


class TestConfigLoadFile:
    """config.py load_config_file バリデータ テスト."""

    def test_load_config_file_with_hybrid_rules(self, tmp_path, monkeypatch) -> None:
        """config.yml に hybrid_rules がある場合にマージされる."""
        import yaml

        config_data = {
            "ai": {
                "hybrid_rules": [
                    {"data_classification": "sensitive", "provider": "ollama"},
                ]
            }
        }
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))

        # CWD を tmp_path に変更して Path("config.yml") を解決させる
        monkeypatch.chdir(tmp_path)

        from cs_risk_agent.config import Settings

        data: dict = {}
        result = Settings.load_config_file(data)
        assert "hybrid_rules" in result
        assert result["hybrid_rules"][0]["data_classification"] == "sensitive"

    def test_load_config_file_no_file(self, tmp_path, monkeypatch) -> None:
        """ファイルが存在しない場合はデータをそのまま返す."""
        # config.yml が存在しないディレクトリに移動
        monkeypatch.chdir(tmp_path)

        from cs_risk_agent.config import Settings

        data: dict = {"app_env": "development"}
        result = Settings.load_config_file(data)
        assert result is data

    def test_load_config_file_existing_key_not_overwritten(self, tmp_path, monkeypatch) -> None:
        """既存のキーはファイルのデータで上書きされない (setdefault)."""
        import yaml

        config_data = {
            "ai": {
                "hybrid_rules": [
                    {"data_classification": "general", "provider": "azure"},
                ]
            }
        }
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from cs_risk_agent.config import Settings

        existing_rules = [{"data_classification": "pii", "provider": "local"}]
        data: dict = {"hybrid_rules": existing_rules}
        result = Settings.load_config_file(data)
        # setdefault なので既存のキーは上書きされない
        assert result["hybrid_rules"] is existing_rules

    def test_load_config_file_empty_yaml(self, tmp_path, monkeypatch) -> None:
        """空の YAML ファイルの場合."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("")
        monkeypatch.chdir(tmp_path)

        from cs_risk_agent.config import Settings

        data: dict = {}
        result = Settings.load_config_file(data)
        assert result is data

    def test_load_config_file_no_ai_key(self, tmp_path, monkeypatch) -> None:
        """YAML に ai キーがない場合."""
        import yaml

        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"other_key": 123}))
        monkeypatch.chdir(tmp_path)

        from cs_risk_agent.config import Settings

        data: dict = {}
        result = Settings.load_config_file(data)
        assert "hybrid_rules" not in result
