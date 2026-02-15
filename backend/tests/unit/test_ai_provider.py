"""AIプロバイダーインターフェース ユニットテスト.

ModelTierManager とプロバイダーレジストリの基本機能を検証する。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cs_risk_agent.ai.model_tier import (
    MODEL_PRESETS,
    ModelConfig,
    ModelTierManager,
)
from cs_risk_agent.ai.provider import AIProvider, AIResponse, Message, MessageRole, TokenUsage
from cs_risk_agent.ai.registry import ProviderRegistry
from cs_risk_agent.config import ModelTier
from cs_risk_agent.core.exceptions import ModelNotFoundError, ProviderUnavailableError


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def tier_manager() -> ModelTierManager:
    """テスト用 ModelTierManager."""
    return ModelTierManager(presets=MODEL_PRESETS.copy())


# ---------------------------------------------------------------------------
# ModelTierManager テスト
# ---------------------------------------------------------------------------


class TestModelTierGetModel:
    """ModelTierManager.get_model の検証."""

    def test_get_model_azure_sota(self, tier_manager):
        """Azure SOTA モデルが正しく取得できること."""
        model = tier_manager.get_model("azure", ModelTier.SOTA)
        assert isinstance(model, ModelConfig)
        assert model.provider == "azure"
        assert model.tier == ModelTier.SOTA
        assert model.model_id == "gpt-4o"

    def test_get_model_aws_cost_effective(self, tier_manager):
        """AWS 高コスパモデルが正しく取得できること."""
        model = tier_manager.get_model("aws", ModelTier.COST_EFFECTIVE)
        assert isinstance(model, ModelConfig)
        assert model.provider == "aws"
        assert model.tier == ModelTier.COST_EFFECTIVE

    def test_get_model_ollama(self, tier_manager):
        """Ollama モデルが正しく取得できること."""
        model = tier_manager.get_model("ollama", ModelTier.SOTA)
        assert isinstance(model, ModelConfig)
        assert model.input_cost_per_1k == 0.0
        assert model.output_cost_per_1k == 0.0


class TestModelTierGetModelId:
    """ModelTierManager.get_model_id の検証."""

    def test_get_model_id(self, tier_manager):
        """モデルIDが正しく取得できること."""
        model_id = tier_manager.get_model_id("azure", ModelTier.SOTA)
        assert model_id == "gpt-4o"

    def test_get_model_id_cost_effective(self, tier_manager):
        """高コスパモデルのIDが正しく取得できること."""
        model_id = tier_manager.get_model_id("azure", ModelTier.COST_EFFECTIVE)
        assert model_id == "gpt-4o-mini"


class TestModelTierEstimateCost:
    """ModelTierManager.estimate_cost の検証."""

    def test_estimate_cost_positive(self, tier_manager):
        """クラウドモデルのコスト見積りが正の値であること."""
        cost = tier_manager.estimate_cost("azure", ModelTier.SOTA, 1000, 500)
        assert cost > 0

    def test_estimate_cost_zero_for_local(self, tier_manager):
        """ローカルモデルのコスト見積りが 0 であること."""
        cost = tier_manager.estimate_cost("ollama", ModelTier.SOTA, 1000, 500)
        assert cost == 0.0

    def test_estimate_cost_proportional(self, tier_manager):
        """コストがトークン数に比例すること."""
        cost_small = tier_manager.estimate_cost("azure", ModelTier.SOTA, 100, 50)
        cost_large = tier_manager.estimate_cost("azure", ModelTier.SOTA, 1000, 500)
        assert cost_large == pytest.approx(cost_small * 10)


class TestModelNotFoundError:
    """モデル未定義エラーの検証."""

    def test_model_not_found_error_unknown_provider(self, tier_manager):
        """存在しないプロバイダーで ModelNotFoundError が発生すること."""
        with pytest.raises(ModelNotFoundError):
            tier_manager.get_model("nonexistent", ModelTier.SOTA)

    def test_model_not_found_error_message(self, tier_manager):
        """エラーメッセージにプロバイダーとティア情報が含まれること."""
        with pytest.raises(ModelNotFoundError) as exc_info:
            tier_manager.get_model("unknown_provider", ModelTier.SOTA)
        assert "unknown_provider" in str(exc_info.value)


class TestListProviders:
    """プロバイダー一覧の検証."""

    def test_list_providers(self, tier_manager):
        """全プロバイダーが一覧に含まれること."""
        providers = tier_manager.list_providers()
        assert "azure" in providers
        assert "aws" in providers
        assert "gcp" in providers
        assert "ollama" in providers
        assert "vllm" in providers

    def test_list_providers_count(self, tier_manager):
        """プロバイダー数がプリセット数と一致すること."""
        providers = tier_manager.list_providers()
        assert len(providers) == len(MODEL_PRESETS)


# ---------------------------------------------------------------------------
# ProviderRegistry テスト
# ---------------------------------------------------------------------------


class TestProviderRegistryGet:
    """ProviderRegistry.get の検証."""

    def test_provider_registry_get(self):
        """登録済みプロバイダーが取得できること."""
        registry = ProviderRegistry()
        registry._initialized = True

        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.name = "test_provider"
        mock_provider.is_available = True
        registry._providers["test"] = mock_provider

        result = registry.get("test")
        assert result.name == "test_provider"

    def test_provider_registry_get_not_found(self):
        """未登録プロバイダーで ProviderUnavailableError が発生すること."""
        registry = ProviderRegistry()
        registry._initialized = True
        registry._providers = {}

        with pytest.raises(ProviderUnavailableError):
            registry.get("nonexistent")


class TestProviderRegistryListAll:
    """ProviderRegistry.list_all の検証."""

    def test_provider_registry_list_all(self):
        """list_all が全プロバイダーの状態を返すこと."""
        registry = ProviderRegistry()
        registry._initialized = True

        mock_available = AsyncMock(spec=AIProvider)
        mock_available.is_available = True

        mock_unavailable = AsyncMock(spec=AIProvider)
        mock_unavailable.is_available = False

        registry._providers = {
            "available": mock_available,
            "unavailable": mock_unavailable,
        }

        result = registry.list_all()
        assert result["available"] is True
        assert result["unavailable"] is False

    def test_provider_registry_register_custom(self):
        """カスタムプロバイダーの登録が動作すること."""
        registry = ProviderRegistry()
        registry._initialized = True
        registry._providers = {}

        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.name = "custom"
        registry.register("custom", mock_provider)

        assert "custom" in registry._providers
