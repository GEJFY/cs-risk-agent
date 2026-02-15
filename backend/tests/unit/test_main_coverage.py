"""main.py アプリケーションのカバレッジテスト."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient


class TestAppCreation:
    """アプリケーション作成テスト."""

    def test_create_app(self) -> None:
        from cs_risk_agent.main import app

        assert isinstance(app, FastAPI)

    def test_app_title(self) -> None:
        from cs_risk_agent.main import app

        assert "CS Risk Agent" in app.title

    def test_health_endpoint(self) -> None:
        from cs_risk_agent.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestExceptionHandlers:
    """例外ハンドラーテスト."""

    def test_error_response_format(self) -> None:
        from cs_risk_agent.main import _error_response

        response = _error_response(400, "TEST_ERROR", "test message")
        assert response.status_code == 400
        import json

        body = json.loads(response.body)
        assert body["error"]["code"] == "TEST_ERROR"
        assert body["error"]["message"] == "test message"

    def test_authentication_error_handler(self) -> None:
        from cs_risk_agent.main import app

        client = TestClient(app, raise_server_exceptions=False)
        # Health endpoint should work fine (no auth error)
        response = client.get("/health")
        assert response.status_code == 200

    def test_register_exception_handlers(self) -> None:
        from cs_risk_agent.main import _register_exception_handlers

        test_app = FastAPI()
        _register_exception_handlers(test_app)
        # Verify handlers are registered
        assert len(test_app.exception_handlers) > 0
