"""Model Tiering - SOTAモデルと高コスパモデルのプリセット管理.

各プロバイダーの「SOTAモデル」と「高コスパモデル」をプリセットし、
動的に切り替え可能にする。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cs_risk_agent.config import ModelTier, get_settings
from cs_risk_agent.core.exceptions import ModelNotFoundError


@dataclass
class ModelConfig:
    """モデル設定."""

    model_id: str
    tier: ModelTier
    provider: str
    # 概算コスト (USD / 1K tokens)
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    max_context_tokens: int = 128000
    supports_streaming: bool = True
    supports_vision: bool = False
    description: str = ""


# モデルプリセット定義
MODEL_PRESETS: dict[str, dict[ModelTier, ModelConfig]] = {
    "azure": {
        ModelTier.SOTA: ModelConfig(
            model_id="gpt-4o",
            tier=ModelTier.SOTA,
            provider="azure",
            input_cost_per_1k=0.0025,
            output_cost_per_1k=0.01,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=True,
            description="GPT-4o - Azure最高性能モデル",
        ),
        ModelTier.COST_EFFECTIVE: ModelConfig(
            model_id="gpt-4o-mini",
            tier=ModelTier.COST_EFFECTIVE,
            provider="azure",
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=True,
            description="GPT-4o Mini - Azure高コスパモデル",
        ),
    },
    "aws": {
        ModelTier.SOTA: ModelConfig(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            tier=ModelTier.SOTA,
            provider="aws",
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            max_context_tokens=200000,
            supports_streaming=True,
            supports_vision=True,
            description="Claude 3.5 Sonnet - AWS Bedrock SOTA",
        ),
        ModelTier.COST_EFFECTIVE: ModelConfig(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            tier=ModelTier.COST_EFFECTIVE,
            provider="aws",
            input_cost_per_1k=0.00025,
            output_cost_per_1k=0.00125,
            max_context_tokens=200000,
            supports_streaming=True,
            supports_vision=True,
            description="Claude 3 Haiku - AWS Bedrock高コスパ",
        ),
    },
    "gcp": {
        ModelTier.SOTA: ModelConfig(
            model_id="gemini-1.5-pro",
            tier=ModelTier.SOTA,
            provider="gcp",
            input_cost_per_1k=0.00125,
            output_cost_per_1k=0.005,
            max_context_tokens=2000000,
            supports_streaming=True,
            supports_vision=True,
            description="Gemini 1.5 Pro - GCP最高性能モデル",
        ),
        ModelTier.COST_EFFECTIVE: ModelConfig(
            model_id="gemini-1.5-flash",
            tier=ModelTier.COST_EFFECTIVE,
            provider="gcp",
            input_cost_per_1k=0.000075,
            output_cost_per_1k=0.0003,
            max_context_tokens=1000000,
            supports_streaming=True,
            supports_vision=True,
            description="Gemini 1.5 Flash - GCP高コスパモデル",
        ),
    },
    "ollama": {
        ModelTier.SOTA: ModelConfig(
            model_id="llama3.1:70b",
            tier=ModelTier.SOTA,
            provider="ollama",
            input_cost_per_1k=0.0,
            output_cost_per_1k=0.0,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=False,
            description="Llama 3.1 70B - ローカルSOTA",
        ),
        ModelTier.COST_EFFECTIVE: ModelConfig(
            model_id="llama3.1:8b",
            tier=ModelTier.COST_EFFECTIVE,
            provider="ollama",
            input_cost_per_1k=0.0,
            output_cost_per_1k=0.0,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=False,
            description="Llama 3.1 8B - ローカル高コスパ",
        ),
    },
    "vllm": {
        ModelTier.SOTA: ModelConfig(
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            tier=ModelTier.SOTA,
            provider="vllm",
            input_cost_per_1k=0.0,
            output_cost_per_1k=0.0,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=False,
            description="vLLM Llama 3.1 - ローカル推論",
        ),
        ModelTier.COST_EFFECTIVE: ModelConfig(
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            tier=ModelTier.COST_EFFECTIVE,
            provider="vllm",
            input_cost_per_1k=0.0,
            output_cost_per_1k=0.0,
            max_context_tokens=128000,
            supports_streaming=True,
            supports_vision=False,
            description="vLLM Llama 3.1 - ローカル推論",
        ),
    },
}


class ModelTierManager:
    """モデルティア管理クラス.

    プロバイダーとティアに基づいてモデル設定を取得・管理する。
    構成ファイルのオーバーライドにも対応。
    """

    def __init__(
        self,
        presets: dict[str, dict[ModelTier, ModelConfig]] | None = None,
    ) -> None:
        self._presets = presets or MODEL_PRESETS.copy()
        self._overrides: dict[str, dict[ModelTier, str]] = {}
        self._load_overrides_from_settings()

    def _load_overrides_from_settings(self) -> None:
        """環境変数からモデルオーバーライドを読み込む."""
        settings = get_settings()

        # Azure
        if settings.azure.sota_deployment:
            self._set_override("azure", ModelTier.SOTA, settings.azure.sota_deployment)
        if settings.azure.cost_effective_deployment:
            self._set_override(
                "azure", ModelTier.COST_EFFECTIVE, settings.azure.cost_effective_deployment
            )

        # AWS
        if settings.aws.bedrock_sota_model:
            self._set_override("aws", ModelTier.SOTA, settings.aws.bedrock_sota_model)
        if settings.aws.bedrock_cost_effective_model:
            self._set_override(
                "aws", ModelTier.COST_EFFECTIVE, settings.aws.bedrock_cost_effective_model
            )

        # GCP
        if settings.gcp.sota_model:
            self._set_override("gcp", ModelTier.SOTA, settings.gcp.sota_model)
        if settings.gcp.cost_effective_model:
            self._set_override("gcp", ModelTier.COST_EFFECTIVE, settings.gcp.cost_effective_model)

    def _set_override(self, provider: str, tier: ModelTier, model_id: str) -> None:
        """モデルIDオーバーライド設定."""
        if provider not in self._overrides:
            self._overrides[provider] = {}
        self._overrides[provider][tier] = model_id

    def get_model(self, provider: str, tier: ModelTier) -> ModelConfig:
        """指定プロバイダー・ティアのモデル設定を取得.

        Args:
            provider: プロバイダー名
            tier: モデルティア

        Returns:
            ModelConfig: モデル設定

        Raises:
            ModelNotFoundError: モデルが見つからない場合
        """
        if provider not in self._presets:
            raise ModelNotFoundError(provider, tier.value)

        provider_models = self._presets[provider]
        if tier not in provider_models:
            raise ModelNotFoundError(provider, tier.value)

        config = provider_models[tier]

        # オーバーライドがあればモデルIDを差し替え
        override_id = self._overrides.get(provider, {}).get(tier)
        if override_id:
            config = ModelConfig(
                model_id=override_id,
                tier=config.tier,
                provider=config.provider,
                input_cost_per_1k=config.input_cost_per_1k,
                output_cost_per_1k=config.output_cost_per_1k,
                max_context_tokens=config.max_context_tokens,
                supports_streaming=config.supports_streaming,
                supports_vision=config.supports_vision,
                description=config.description,
            )

        return config

    def get_model_id(self, provider: str, tier: ModelTier) -> str:
        """モデルIDのみ取得."""
        return self.get_model(provider, tier).model_id

    def estimate_cost(
        self, provider: str, tier: ModelTier, input_tokens: int, output_tokens: int
    ) -> float:
        """コスト概算 (USD)."""
        model = self.get_model(provider, tier)
        input_cost = (input_tokens / 1000) * model.input_cost_per_1k
        output_cost = (output_tokens / 1000) * model.output_cost_per_1k
        return input_cost + output_cost

    def list_providers(self) -> list[str]:
        """利用可能プロバイダー一覧."""
        return list(self._presets.keys())

    def list_models(self, provider: str | None = None) -> list[ModelConfig]:
        """モデル一覧取得."""
        result: list[ModelConfig] = []
        providers = [provider] if provider else self.list_providers()
        for p in providers:
            if p in self._presets:
                result.extend(self._presets[p].values())
        return result

    def to_dict(self) -> dict[str, Any]:
        """辞書形式で出力（API応答用）."""
        result: dict[str, Any] = {}
        for provider_name, tiers in self._presets.items():
            result[provider_name] = {}
            for tier, config in tiers.items():
                override_id = self._overrides.get(provider_name, {}).get(tier)
                result[provider_name][tier.value] = {
                    "model_id": override_id or config.model_id,
                    "input_cost_per_1k": config.input_cost_per_1k,
                    "output_cost_per_1k": config.output_cost_per_1k,
                    "max_context_tokens": config.max_context_tokens,
                    "description": config.description,
                }
        return result
