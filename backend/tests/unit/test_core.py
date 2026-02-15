"""core モジュールのユニットテスト (security, exceptions)."""

from __future__ import annotations

import pytest

from cs_risk_agent.core.exceptions import (
    AllProvidersFailedError,
    AnalysisError,
    AuthenticationError,
    AuthorizationError,
    BudgetExceededError,
    CSRiskAgentError,
    DataValidationError,
    ETLError,
    ModelNotFoundError,
    ProviderError,
    ProviderUnavailableError,
)
from cs_risk_agent.core.security import (
    Role,
    check_permission,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# ---------------------------------------------------------------------------
# 例外クラス テスト
# ---------------------------------------------------------------------------


class TestExceptions:
    """カスタム例外のテスト."""

    def test_base_exception(self) -> None:
        e = CSRiskAgentError("test error", code="TEST")
        assert e.message == "test error"
        assert e.code == "TEST"
        assert str(e) == "test error"

    def test_provider_error(self) -> None:
        e = ProviderError("azure", "connection failed")
        assert e.provider == "azure"
        assert "azure" in e.message
        assert e.code == "PROVIDER_ERROR"

    def test_provider_unavailable_error(self) -> None:
        e = ProviderUnavailableError("aws")
        assert e.provider == "aws"
        assert "unavailable" in e.message.lower()

    def test_all_providers_failed_error(self) -> None:
        e = AllProvidersFailedError(["azure", "aws", "gcp"])
        assert e.providers == ["azure", "aws", "gcp"]
        assert e.code == "ALL_PROVIDERS_FAILED"

    def test_budget_exceeded_error(self) -> None:
        e = BudgetExceededError(150.0, 100.0)
        assert e.current_cost == 150.0
        assert e.budget_limit == 100.0
        assert e.code == "BUDGET_EXCEEDED"

    def test_model_not_found_error(self) -> None:
        e = ModelNotFoundError("azure", "sota")
        assert "azure" in e.message
        assert "sota" in e.message
        assert e.code == "MODEL_NOT_FOUND"

    def test_authentication_error(self) -> None:
        e = AuthenticationError()
        assert e.code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self) -> None:
        e = AuthorizationError()
        assert e.code == "AUTHORIZATION_ERROR"

    def test_analysis_error(self) -> None:
        e = AnalysisError("benford", "insufficient data")
        assert e.engine == "benford"
        assert e.code == "ANALYSIS_ERROR"

    def test_etl_error(self) -> None:
        e = ETLError("extract", "file not found")
        assert e.stage == "extract"
        assert e.code == "ETL_ERROR"

    def test_data_validation_error(self) -> None:
        e = DataValidationError("revenue", "must be positive")
        assert e.field == "revenue"
        assert e.code == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# セキュリティ テスト
# ---------------------------------------------------------------------------


class TestSecurity:
    """認証・認可モジュールのテスト."""

    def test_password_hash_and_verify(self) -> None:
        hashed = hash_password("test_password123")
        assert verify_password("test_password123", hashed)
        assert not verify_password("wrong_password", hashed)

    def test_create_and_decode_token(self) -> None:
        token = create_access_token("user1", Role.AUDITOR)
        payload = decode_access_token(token)
        assert payload.sub == "user1"
        assert payload.role == Role.AUDITOR

    def test_create_token_with_extra(self) -> None:
        token = create_access_token("admin1", Role.ADMIN, extra={"department": "audit"})
        payload = decode_access_token(token)
        assert payload.sub == "admin1"
        assert payload.role == Role.ADMIN

    def test_decode_invalid_token(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token("invalid.token.value")

    def test_role_enum(self) -> None:
        assert Role.ADMIN.value == "admin"
        assert Role.AUDITOR.value == "auditor"
        assert Role.VIEWER.value == "viewer"

    def test_check_permission_admin(self) -> None:
        # ADMIN can do everything
        check_permission(Role.ADMIN, "read")
        check_permission(Role.ADMIN, "write")
        check_permission(Role.ADMIN, "admin")
        check_permission(Role.ADMIN, "analysis:run")

    def test_check_permission_auditor(self) -> None:
        check_permission(Role.AUDITOR, "read")
        check_permission(Role.AUDITOR, "analysis:run")
        check_permission(Role.AUDITOR, "reports:generate")

    def test_check_permission_denied(self) -> None:
        with pytest.raises(AuthorizationError):
            check_permission(Role.VIEWER, "write")

    def test_check_permission_viewer(self) -> None:
        check_permission(Role.VIEWER, "read")
        with pytest.raises(AuthorizationError):
            check_permission(Role.VIEWER, "admin")
