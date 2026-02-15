"""カスタム例外定義."""

from __future__ import annotations


class CSRiskAgentError(Exception):
    """基底例外クラス."""

    def __init__(self, message: str = "", code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class ProviderError(CSRiskAgentError):
    """AIプロバイダーエラー."""

    def __init__(self, provider: str, message: str = "") -> None:
        self.provider = provider
        super().__init__(
            message=f"Provider '{provider}' error: {message}",
            code="PROVIDER_ERROR",
        )


class ProviderUnavailableError(ProviderError):
    """プロバイダー利用不可エラー."""

    def __init__(self, provider: str, message: str = "Provider unavailable") -> None:
        super().__init__(provider=provider, message=message)


class AllProvidersFailedError(CSRiskAgentError):
    """全プロバイダー失敗エラー."""

    def __init__(self, providers: list[str]) -> None:
        self.providers = providers
        super().__init__(
            message=f"All providers failed: {', '.join(providers)}",
            code="ALL_PROVIDERS_FAILED",
        )


class BudgetExceededError(CSRiskAgentError):
    """予算超過エラー（サーキットブレーカー）."""

    def __init__(self, current_cost: float, budget_limit: float) -> None:
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        super().__init__(
            message=(
                f"Budget exceeded: ${current_cost:.2f} / ${budget_limit:.2f}. "
                "Circuit breaker activated."
            ),
            code="BUDGET_EXCEEDED",
        )


class ModelNotFoundError(CSRiskAgentError):
    """モデル未定義エラー."""

    def __init__(self, provider: str, tier: str) -> None:
        super().__init__(
            message=f"Model not found for provider='{provider}', tier='{tier}'",
            code="MODEL_NOT_FOUND",
        )


class AuthenticationError(CSRiskAgentError):
    """認証エラー."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(CSRiskAgentError):
    """認可エラー."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


class AnalysisError(CSRiskAgentError):
    """分析エンジンエラー."""

    def __init__(self, engine: str, message: str = "") -> None:
        self.engine = engine
        super().__init__(
            message=f"Analysis engine '{engine}' error: {message}",
            code="ANALYSIS_ERROR",
        )


class ETLError(CSRiskAgentError):
    """ETLパイプラインエラー."""

    def __init__(self, stage: str, message: str = "") -> None:
        self.stage = stage
        super().__init__(
            message=f"ETL stage '{stage}' error: {message}",
            code="ETL_ERROR",
        )


class DataValidationError(CSRiskAgentError):
    """データ検証エラー."""

    def __init__(self, field: str, message: str = "") -> None:
        self.field = field
        super().__init__(
            message=f"Validation error on '{field}': {message}",
            code="VALIDATION_ERROR",
        )
