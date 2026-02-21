"""アプリケーション設定 - Pydantic Settings による環境変数管理."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """実行環境."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DataMode(StrEnum):
    """データソースモード."""

    DEMO = "demo"
    DB = "db"


class AIMode(StrEnum):
    """AI実行モード."""

    CLOUD = "cloud"
    LOCAL = "local"
    HYBRID = "hybrid"


class ModelTier(StrEnum):
    """モデルティア."""

    SOTA = "sota"
    COST_EFFECTIVE = "cost_effective"


class AzureSettings(BaseSettings):
    """Azure AI Foundry 設定."""

    model_config = SettingsConfigDict(env_prefix="AZURE_AI_")

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-12-01-preview"
    sota_deployment: str = "gpt-4o"
    cost_effective_deployment: str = "gpt-4o-mini"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)


class AWSSettings(BaseSettings):
    """AWS Bedrock 設定."""

    model_config = SettingsConfigDict(env_prefix="AWS_")

    access_key_id: str = ""
    secret_access_key: str = ""
    region: str = "us-east-1"
    bedrock_sota_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_cost_effective_model: str = "anthropic.claude-3-haiku-20240307-v1:0"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_key_id and self.secret_access_key)


class GCPSettings(BaseSettings):
    """GCP Vertex AI 設定."""

    model_config = SettingsConfigDict(env_prefix="GCP_")

    project_id: str = ""
    location: str = "us-central1"
    application_credentials: str = ""
    sota_model: str = "gemini-1.5-pro"
    cost_effective_model: str = "gemini-1.5-flash"

    @property
    def is_configured(self) -> bool:
        return bool(self.project_id)


class OllamaSettings(BaseSettings):
    """Ollama ローカルLLM設定."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = "http://localhost:11434"
    sota_model: str = "llama3.1:70b"
    cost_effective_model: str = "llama3.1:8b"


class VLLMSettings(BaseSettings):
    """vLLM ローカルLLM設定."""

    model_config = SettingsConfigDict(env_prefix="VLLM_")

    base_url: str = "http://localhost:8080"
    model: str = "meta-llama/Llama-3.1-8B-Instruct"


class AIOrchestrationSettings(BaseSettings):
    """AI Orchestration 設定."""

    model_config = SettingsConfigDict(env_prefix="AI_")

    default_provider: str = "azure"
    fallback_chain: str = "azure,aws,gcp,ollama"
    mode: AIMode = AIMode.CLOUD
    monthly_budget_usd: float = 500.0
    budget_alert_threshold: float = 0.8
    circuit_breaker_threshold: float = 0.95

    @property
    def fallback_providers(self) -> list[str]:
        return [p.strip() for p in self.fallback_chain.split(",")]


class DatabaseSettings(BaseSettings):
    """データベース設定."""

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cs_risk_agent",
        alias="DATABASE_URL",
    )
    sync_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/cs_risk_agent",
        alias="DATABASE_SYNC_URL",
    )
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class RedisSettings(BaseSettings):
    """Redis設定."""

    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class ObservabilitySettings(BaseSettings):
    """可観測性設定."""

    otel_endpoint: str = Field(
        default="http://localhost:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    service_name: str = Field(default="cs-risk-agent", alias="OTEL_SERVICE_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")


class JWTSettings(BaseSettings):
    """JWT認証設定."""

    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: str = "change-me-to-a-random-jwt-secret"
    algorithm: str = "HS256"
    expiration_minutes: int = 60


class HybridRule(BaseSettings):
    """ハイブリッドモードのルーティングルール."""

    data_classification: str = "general"
    provider: str = "azure"


class Settings(BaseSettings):
    """アプリケーション全体設定."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_secret_key: str = "change-me-to-a-random-secret-key"
    app_host: str = "0.0.0.0"  # noqa: S104
    app_port: int = 8000

    # --- Data Mode ---
    data_mode: DataMode = DataMode.DEMO

    # --- CORS ---
    cors_origins: list[str] = Field(
        default=["http://localhost:3005", "http://localhost:3000"],
    )

    # --- Sub Settings ---
    azure: AzureSettings = Field(default_factory=AzureSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    gcp: GCPSettings = Field(default_factory=GCPSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    vllm: VLLMSettings = Field(default_factory=VLLMSettings)
    ai: AIOrchestrationSettings = Field(default_factory=AIOrchestrationSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    # --- Hybrid Rules ---
    hybrid_rules: list[HybridRule] = Field(default_factory=list)

    # --- EDINET ---
    edinet_api_key: str = ""
    edinet_base_url: str = "https://api.edinet-fsa.go.jp/api/v2"

    @model_validator(mode="before")
    @classmethod
    def load_config_file(cls, data: dict[str, Any]) -> dict[str, Any]:
        """config.yml から追加設定を読み込む."""
        config_path = Path("config.yml")
        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f)
            if yaml_config and isinstance(yaml_config, dict):
                # ハイブリッドルールの読み込み
                ai_config = yaml_config.get("ai", {})
                if "hybrid_rules" in ai_config:
                    data.setdefault("hybrid_rules", ai_config["hybrid_rules"])
        return data

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """シングルトンSettings取得."""
    return Settings()
