"""ProviderRegistry / ModelTierManager 残りカバレッジテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.ai.provider import AIProvider


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    """ProviderRegistry テスト."""

    def _make_registry(self):
        from cs_risk_agent.ai.registry import ProviderRegistry

        return ProviderRegistry()

    def test_initialize_twice_is_noop(self) -> None:
        reg = self._make_registry()
        # mock _PROVIDER_FACTORIES to avoid real provider creation
        with patch(
            "cs_risk_agent.ai.registry._PROVIDER_FACTORIES",
            {"fake": lambda: MagicMock(spec=AIProvider, is_available=True, name="fake")},
        ):
            reg.initialize()
            assert reg._initialized is True
            # 2回目は何もしない
            reg.initialize()
            assert len(reg._providers) == 1

    def test_initialize_factory_failure(self) -> None:
        """ファクトリが例外を投げた場合はスキップ."""
        reg = self._make_registry()
        with patch(
            "cs_risk_agent.ai.registry._PROVIDER_FACTORIES",
            {"broken": MagicMock(side_effect=RuntimeError("boom"))},
        ):
            reg.initialize()
            assert "broken" not in reg._providers

    def test_get_auto_initializes(self) -> None:
        reg = self._make_registry()
        mock_provider = MagicMock(spec=AIProvider, is_available=True, name="fake")
        with patch(
            "cs_risk_agent.ai.registry._PROVIDER_FACTORIES",
            {"fake": lambda: mock_provider},
        ):
            result = reg.get("fake")
            assert result is mock_provider

    def test_get_not_found(self) -> None:
        from cs_risk_agent.core.exceptions import ProviderUnavailableError

        reg = self._make_registry()
        with patch("cs_risk_agent.ai.registry._PROVIDER_FACTORIES", {}):
            with pytest.raises(ProviderUnavailableError):
                reg.get("nonexistent")

    def test_get_available(self) -> None:
        reg = self._make_registry()
        available = MagicMock(spec=AIProvider, is_available=True)
        unavailable = MagicMock(spec=AIProvider, is_available=False)
        reg._providers = {"a": available, "b": unavailable}
        reg._initialized = True

        result = reg.get_available()
        assert len(result) == 1
        assert result[0] is available

    def test_get_available_names(self) -> None:
        reg = self._make_registry()
        reg._providers = {
            "a": MagicMock(is_available=True),
            "b": MagicMock(is_available=False),
        }
        reg._initialized = True
        names = reg.get_available_names()
        assert names == ["a"]

    def test_list_all(self) -> None:
        reg = self._make_registry()
        reg._providers = {
            "a": MagicMock(is_available=True),
            "b": MagicMock(is_available=False),
        }
        reg._initialized = True
        result = reg.list_all()
        assert result == {"a": True, "b": False}

    def test_register_custom(self) -> None:
        reg = self._make_registry()
        reg._initialized = True
        custom = MagicMock(spec=AIProvider)
        reg.register("custom", custom)
        assert reg._providers["custom"] is custom

    @pytest.mark.asyncio
    async def test_health_check_all(self) -> None:
        reg = self._make_registry()
        available = AsyncMock(is_available=True, health_check=AsyncMock(return_value=True))
        unavailable = MagicMock(is_available=False)
        reg._providers = {"a": available, "b": unavailable}
        reg._initialized = True

        result = await reg.health_check_all()
        assert result == {"a": True, "b": False}

    def test_to_dict(self) -> None:
        reg = self._make_registry()
        mock_a = MagicMock(is_available=True)
        mock_a.name = "a"
        mock_b = MagicMock(is_available=False)
        mock_b.name = "b"
        reg._providers = {"a": mock_a, "b": mock_b}
        reg._initialized = True
        d = reg.to_dict()
        assert d["a"]["available"] is True
        assert d["b"]["name"] == "b"


# ---------------------------------------------------------------------------
# ModelTierManager
# ---------------------------------------------------------------------------


class TestModelTierManager:
    """ModelTierManager テスト."""

    def _make_manager(self):
        from cs_risk_agent.ai.model_tier import ModelConfig, ModelTier, ModelTierManager

        presets = {
            "test_provider": {
                ModelTier.SOTA: ModelConfig(
                    model_id="sota-v1",
                    tier=ModelTier.SOTA,
                    provider="test_provider",
                    input_cost_per_1k=0.01,
                    output_cost_per_1k=0.02,
                    description="Test SOTA",
                ),
                ModelTier.COST_EFFECTIVE: ModelConfig(
                    model_id="ce-v1",
                    tier=ModelTier.COST_EFFECTIVE,
                    provider="test_provider",
                    input_cost_per_1k=0.001,
                    output_cost_per_1k=0.002,
                    description="Test CE",
                ),
            }
        }
        with patch("cs_risk_agent.ai.model_tier.get_settings") as mock_s:
            mock_s.return_value = MagicMock(
                azure=MagicMock(sota_deployment="", cost_effective_deployment=""),
                aws=MagicMock(bedrock_sota_model="", bedrock_cost_effective_model=""),
                gcp=MagicMock(sota_model="", cost_effective_model=""),
            )
            return ModelTierManager(presets=presets)

    def test_get_model(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier

        mgr = self._make_manager()
        model = mgr.get_model("test_provider", ModelTier.SOTA)
        assert model.model_id == "sota-v1"

    def test_get_model_unknown_provider(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier
        from cs_risk_agent.core.exceptions import ModelNotFoundError

        mgr = self._make_manager()
        with pytest.raises(ModelNotFoundError):
            mgr.get_model("nonexistent", ModelTier.SOTA)

    def test_get_model_unknown_tier(self) -> None:
        """有効なプロバイダーだがティアが存在しない場合."""
        from cs_risk_agent.ai.model_tier import ModelConfig, ModelTier, ModelTierManager
        from cs_risk_agent.core.exceptions import ModelNotFoundError

        # COST_EFFECTIVE のみ持つプロバイダー
        presets = {
            "partial": {
                ModelTier.COST_EFFECTIVE: ModelConfig(
                    model_id="ce",
                    tier=ModelTier.COST_EFFECTIVE,
                    provider="partial",
                ),
            }
        }
        with patch("cs_risk_agent.ai.model_tier.get_settings") as mock_s:
            mock_s.return_value = MagicMock(
                azure=MagicMock(sota_deployment="", cost_effective_deployment=""),
                aws=MagicMock(bedrock_sota_model="", bedrock_cost_effective_model=""),
                gcp=MagicMock(sota_model="", cost_effective_model=""),
            )
            mgr = ModelTierManager(presets=presets)
        with pytest.raises(ModelNotFoundError):
            mgr.get_model("partial", ModelTier.SOTA)

    def test_get_model_with_override(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier

        mgr = self._make_manager()
        mgr._set_override("test_provider", ModelTier.SOTA, "overridden-model")
        model = mgr.get_model("test_provider", ModelTier.SOTA)
        assert model.model_id == "overridden-model"

    def test_get_model_id(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier

        mgr = self._make_manager()
        assert mgr.get_model_id("test_provider", ModelTier.SOTA) == "sota-v1"

    def test_estimate_cost(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier

        mgr = self._make_manager()
        cost = mgr.estimate_cost("test_provider", ModelTier.SOTA, 1000, 500)
        # input: 1.0 * 0.01 = 0.01, output: 0.5 * 0.02 = 0.01
        assert abs(cost - 0.02) < 1e-6

    def test_list_providers(self) -> None:
        mgr = self._make_manager()
        assert "test_provider" in mgr.list_providers()

    def test_list_models_all(self) -> None:
        mgr = self._make_manager()
        models = mgr.list_models()
        assert len(models) == 2

    def test_list_models_filtered(self) -> None:
        mgr = self._make_manager()
        models = mgr.list_models(provider="test_provider")
        assert len(models) == 2

    def test_list_models_unknown_provider(self) -> None:
        mgr = self._make_manager()
        models = mgr.list_models(provider="nonexistent")
        assert len(models) == 0

    def test_to_dict(self) -> None:
        mgr = self._make_manager()
        d = mgr.to_dict()
        assert "test_provider" in d
        assert "sota" in d["test_provider"]
        assert d["test_provider"]["sota"]["model_id"] == "sota-v1"

    def test_to_dict_with_override(self) -> None:
        from cs_risk_agent.ai.model_tier import ModelTier

        mgr = self._make_manager()
        mgr._set_override("test_provider", ModelTier.SOTA, "custom-id")
        d = mgr.to_dict()
        assert d["test_provider"]["sota"]["model_id"] == "custom-id"
