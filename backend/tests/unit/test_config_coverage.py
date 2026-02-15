"""config モジュールのカバレッジテスト."""

from __future__ import annotations

from cs_risk_agent.config import (
    AIMode,
    AIOrchestrationSettings,
    AWSSettings,
    AzureSettings,
    DatabaseSettings,
    Environment,
    GCPSettings,
    HybridRule,
    JWTSettings,
    ModelTier,
    ObservabilitySettings,
    OllamaSettings,
    RedisSettings,
    Settings,
    VLLMSettings,
    get_settings,
)


class TestEnums:
    """設定列挙型のテスト."""

    def test_environment(self) -> None:
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"

    def test_ai_mode(self) -> None:
        assert AIMode.CLOUD == "cloud"
        assert AIMode.LOCAL == "local"
        assert AIMode.HYBRID == "hybrid"

    def test_model_tier(self) -> None:
        assert ModelTier.SOTA == "sota"
        assert ModelTier.COST_EFFECTIVE == "cost_effective"


class TestSubSettings:
    """サブ設定クラスのテスト."""

    def test_azure_settings_defaults(self) -> None:
        s = AzureSettings()
        assert s.endpoint == ""
        assert s.api_key == ""
        assert s.is_configured is False

    def test_azure_settings_configured(self) -> None:
        s = AzureSettings(endpoint="https://test.azure.com", api_key="key")
        assert s.is_configured is True

    def test_aws_settings_defaults(self) -> None:
        s = AWSSettings()
        assert s.region == "us-east-1"
        assert s.is_configured is False

    def test_aws_settings_configured(self) -> None:
        s = AWSSettings(access_key_id="AKIA...", secret_access_key="secret")
        assert s.is_configured is True

    def test_gcp_settings_defaults(self) -> None:
        s = GCPSettings()
        assert s.location == "us-central1"
        assert s.is_configured is False

    def test_gcp_settings_configured(self) -> None:
        s = GCPSettings(project_id="my-project")
        assert s.is_configured is True

    def test_ollama_settings(self) -> None:
        s = OllamaSettings()
        assert "localhost" in s.base_url
        assert s.sota_model == "llama3.1:70b"

    def test_vllm_settings(self) -> None:
        s = VLLMSettings()
        assert "localhost" in s.base_url

    def test_ai_orchestration_settings(self) -> None:
        s = AIOrchestrationSettings()
        assert s.default_provider == "azure"
        assert s.fallback_providers == ["azure", "aws", "gcp", "ollama"]
        assert s.monthly_budget_usd == 500.0

    def test_database_settings(self) -> None:
        s = DatabaseSettings()
        assert "postgresql" in s.url
        assert s.pool_size == 10

    def test_redis_settings(self) -> None:
        s = RedisSettings()
        assert "redis" in s.url

    def test_observability_settings(self) -> None:
        s = ObservabilitySettings()
        assert s.log_level == "INFO"
        assert s.log_format == "json"

    def test_jwt_settings(self) -> None:
        s = JWTSettings()
        assert s.algorithm == "HS256"
        assert s.expiration_minutes == 60

    def test_hybrid_rule(self) -> None:
        r = HybridRule()
        assert r.data_classification == "general"
        assert r.provider == "azure"


class TestSettings:
    """メイン Settings のテスト."""

    def test_defaults(self) -> None:
        s = Settings()
        assert s.app_env == Environment.DEVELOPMENT
        assert s.app_debug is True
        assert s.app_port == 8000

    def test_is_production(self) -> None:
        s = Settings()
        assert s.is_production is False

    def test_cors_origins_default(self) -> None:
        s = Settings()
        assert "http://localhost:3005" in s.cors_origins
        assert "http://localhost:3000" in s.cors_origins

    def test_get_settings_singleton(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
