"""core パッケージのカバレッジ拡張テスト."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

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

# ---------------------------------------------------------------------------
# 全例外クラスの属性・継承テスト
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """例外クラスの継承と属性を検証."""

    def test_base_error_defaults(self) -> None:
        err = CSRiskAgentError()
        assert err.message == ""
        assert err.code == "INTERNAL_ERROR"
        assert str(err) == ""

    def test_base_error_custom(self) -> None:
        err = CSRiskAgentError(message="custom msg", code="CUSTOM")
        assert err.message == "custom msg"
        assert err.code == "CUSTOM"

    def test_provider_error(self) -> None:
        err = ProviderError("azure", "timeout")
        assert err.provider == "azure"
        assert "azure" in err.message
        assert "timeout" in err.message
        assert err.code == "PROVIDER_ERROR"
        assert isinstance(err, CSRiskAgentError)

    def test_provider_unavailable_error(self) -> None:
        err = ProviderUnavailableError("aws")
        assert err.provider == "aws"
        assert "unavailable" in err.message.lower()
        assert isinstance(err, ProviderError)

    def test_provider_unavailable_custom_message(self) -> None:
        err = ProviderUnavailableError("gcp", "maintenance")
        assert "maintenance" in err.message

    def test_all_providers_failed(self) -> None:
        providers = ["azure", "aws", "gcp"]
        err = AllProvidersFailedError(providers)
        assert err.providers == providers
        assert err.code == "ALL_PROVIDERS_FAILED"
        assert "azure" in err.message
        assert "aws" in err.message
        assert "gcp" in err.message

    def test_budget_exceeded_error(self) -> None:
        err = BudgetExceededError(current_cost=150.0, budget_limit=100.0)
        assert err.current_cost == 150.0
        assert err.budget_limit == 100.0
        assert err.code == "BUDGET_EXCEEDED"
        assert "$150.00" in err.message
        assert "$100.00" in err.message

    def test_model_not_found_error(self) -> None:
        err = ModelNotFoundError("ollama", "sota")
        assert err.code == "MODEL_NOT_FOUND"
        assert "ollama" in err.message
        assert "sota" in err.message

    def test_authentication_error_default(self) -> None:
        err = AuthenticationError()
        assert err.code == "AUTHENTICATION_ERROR"
        assert "Authentication failed" in err.message

    def test_authentication_error_custom(self) -> None:
        err = AuthenticationError("Invalid token")
        assert "Invalid token" in err.message

    def test_authorization_error_default(self) -> None:
        err = AuthorizationError()
        assert err.code == "AUTHORIZATION_ERROR"
        assert "Insufficient permissions" in err.message

    def test_authorization_error_custom(self) -> None:
        err = AuthorizationError("Not allowed")
        assert "Not allowed" in err.message

    def test_analysis_error(self) -> None:
        err = AnalysisError("benford", "insufficient data")
        assert err.engine == "benford"
        assert err.code == "ANALYSIS_ERROR"
        assert "benford" in err.message
        assert "insufficient data" in err.message

    def test_etl_error(self) -> None:
        err = ETLError("extract", "file not found")
        assert err.stage == "extract"
        assert err.code == "ETL_ERROR"
        assert "extract" in err.message

    def test_data_validation_error(self) -> None:
        err = DataValidationError("revenue", "must be positive")
        assert err.field == "revenue"
        assert err.code == "VALIDATION_ERROR"
        assert "revenue" in err.message

    def test_all_exceptions_are_catchable_as_base(self) -> None:
        exceptions = [
            CSRiskAgentError("base"),
            ProviderError("p", "m"),
            ProviderUnavailableError("p"),
            AllProvidersFailedError(["a"]),
            BudgetExceededError(1.0, 0.5),
            ModelNotFoundError("p", "t"),
            AuthenticationError(),
            AuthorizationError(),
            AnalysisError("e", "m"),
            ETLError("s", "m"),
            DataValidationError("f", "m"),
        ]
        for exc in exceptions:
            assert isinstance(exc, CSRiskAgentError)
            assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# Security モジュール - JWT / RBAC テスト
# ---------------------------------------------------------------------------


class TestSecurityRoles:
    """全ロールと権限のテスト."""

    def test_all_roles_exist(self) -> None:
        from cs_risk_agent.core.security import Role

        assert Role.ADMIN.value == "admin"
        assert Role.AUDITOR.value == "auditor"
        assert Role.CFO.value == "cfo"
        assert Role.CEO.value == "ceo"
        assert Role.VIEWER.value == "viewer"

    def test_admin_has_all_permissions(self) -> None:
        from cs_risk_agent.core.security import ROLE_PERMISSIONS, Role

        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert "read" in admin_perms
        assert "write" in admin_perms
        assert "delete" in admin_perms
        assert "admin" in admin_perms
        assert "analysis:run" in admin_perms
        assert "reports:generate" in admin_perms

    def test_auditor_permissions(self) -> None:
        from cs_risk_agent.core.security import ROLE_PERMISSIONS, Role

        perms = ROLE_PERMISSIONS[Role.AUDITOR]
        assert "read" in perms
        assert "analysis:run" in perms
        assert "reports:generate" in perms
        assert "write" not in perms
        assert "admin" not in perms

    def test_cfo_permissions(self) -> None:
        from cs_risk_agent.core.security import ROLE_PERMISSIONS, Role

        perms = ROLE_PERMISSIONS[Role.CFO]
        assert "read" in perms
        assert "analysis:run" in perms
        assert "reports:generate" in perms
        assert "admin" not in perms

    def test_ceo_permissions(self) -> None:
        from cs_risk_agent.core.security import ROLE_PERMISSIONS, Role

        perms = ROLE_PERMISSIONS[Role.CEO]
        assert "read" in perms
        assert "reports:generate" in perms
        assert "analysis:run" not in perms

    def test_viewer_permissions(self) -> None:
        from cs_risk_agent.core.security import ROLE_PERMISSIONS, Role

        perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert perms == {"read"}

    def test_check_permission_allows(self) -> None:
        from cs_risk_agent.core.security import Role, check_permission

        check_permission(Role.ADMIN, "admin")
        check_permission(Role.AUDITOR, "read")
        check_permission(Role.CEO, "reports:generate")
        check_permission(Role.VIEWER, "read")

    def test_check_permission_denies(self) -> None:
        from cs_risk_agent.core.security import Role, check_permission

        with pytest.raises(AuthorizationError):
            check_permission(Role.VIEWER, "write")
        with pytest.raises(AuthorizationError):
            check_permission(Role.CEO, "admin")
        with pytest.raises(AuthorizationError):
            check_permission(Role.AUDITOR, "delete")


class TestSecurityJWT:
    """JWT トークンの生成・検証テスト."""

    def test_create_and_decode_token(self) -> None:
        from cs_risk_agent.core.security import (
            Role,
            create_access_token,
            decode_access_token,
        )

        token = create_access_token("user-123", Role.ADMIN)
        payload = decode_access_token(token)
        assert payload.sub == "user-123"
        assert payload.role == Role.ADMIN

    def test_create_token_with_extra(self) -> None:
        from cs_risk_agent.core.security import (
            Role,
            create_access_token,
            decode_access_token,
        )

        token = create_access_token("user-456", Role.CFO, extra={"dept": "finance"})
        payload = decode_access_token(token)
        assert payload.sub == "user-456"
        assert payload.role == Role.CFO

    def test_decode_invalid_token(self) -> None:
        from cs_risk_agent.core.security import decode_access_token

        with pytest.raises(AuthenticationError, match="Invalid token"):
            decode_access_token("invalid.jwt.token")

    def test_token_payload_model(self) -> None:
        from datetime import UTC, datetime

        from cs_risk_agent.core.security import Role, TokenPayload

        now = datetime.now(UTC)
        payload = TokenPayload(sub="test", role=Role.VIEWER, exp=now, iat=now)
        assert payload.sub == "test"
        assert payload.role == Role.VIEWER

    @patch("cs_risk_agent.core.security.pwd_context")
    def test_hash_and_verify_password(self, mock_ctx) -> None:
        from cs_risk_agent.core.security import hash_password, verify_password

        mock_ctx.hash.return_value = "$2b$12$hashed"
        mock_ctx.verify.return_value = True

        hashed = hash_password("secret")
        assert hashed == "$2b$12$hashed"
        assert verify_password("secret", hashed) is True
        mock_ctx.hash.assert_called_once_with("secret")
        mock_ctx.verify.assert_called_once_with("secret", "$2b$12$hashed")

    @patch("cs_risk_agent.core.security.pwd_context")
    def test_verify_wrong_password(self, mock_ctx) -> None:
        from cs_risk_agent.core.security import verify_password

        mock_ctx.verify.return_value = False
        assert verify_password("wrong", "$hash") is False
