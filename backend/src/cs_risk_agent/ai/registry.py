"""Provider Registry - プロバイダーファクトリ & レジストリ.

AIプロバイダーの登録・取得・管理を行うファクトリパターン実装。
構成ファイルに基づいたプロバイダーの動的登録に対応。
"""

from __future__ import annotations

from typing import Any

import structlog

from cs_risk_agent.ai.provider import AIProvider
from cs_risk_agent.ai.providers.aws_bedrock import AWSBedrockProvider
from cs_risk_agent.ai.providers.azure_foundry import AzureFoundryProvider
from cs_risk_agent.ai.providers.gcp_vertex import GCPVertexProvider
from cs_risk_agent.ai.providers.ollama_local import OllamaLocalProvider
from cs_risk_agent.ai.providers.vllm_local import VLLMLocalProvider
from cs_risk_agent.config import get_settings
from cs_risk_agent.core.exceptions import ProviderUnavailableError

logger = structlog.get_logger(__name__)

# プロバイダーファクトリマッピング
_PROVIDER_FACTORIES: dict[str, type[AIProvider]] = {
    "azure": AzureFoundryProvider,
    "aws": AWSBedrockProvider,
    "gcp": GCPVertexProvider,
    "ollama": OllamaLocalProvider,
    "vllm": VLLMLocalProvider,
}


class ProviderRegistry:
    """AIプロバイダーレジストリ.

    プロバイダーのシングルトンインスタンスを管理し、
    名前ベースでの取得を提供する。
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._initialized = False

    def initialize(self) -> None:
        """設定に基づいて全プロバイダーを初期化."""
        if self._initialized:
            return

        for name, factory in _PROVIDER_FACTORIES.items():
            try:
                provider = factory()
                self._providers[name] = provider
                logger.info(
                    "provider.registered",
                    provider=name,
                    available=provider.is_available,
                )
            except Exception as e:
                logger.warning(
                    "provider.registration_failed",
                    provider=name,
                    error=str(e),
                )

        self._initialized = True

    def get(self, name: str) -> AIProvider:
        """プロバイダーをname指定で取得.

        Args:
            name: プロバイダー名 (azure, aws, gcp, ollama, vllm)

        Returns:
            AIProvider: プロバイダーインスタンス

        Raises:
            ProviderUnavailableError: プロバイダーが未登録の場合
        """
        if not self._initialized:
            self.initialize()

        provider = self._providers.get(name)
        if provider is None:
            raise ProviderUnavailableError(name, f"Provider '{name}' not registered")
        return provider

    def get_available(self) -> list[AIProvider]:
        """利用可能なプロバイダー一覧取得."""
        if not self._initialized:
            self.initialize()
        return [p for p in self._providers.values() if p.is_available]

    def get_available_names(self) -> list[str]:
        """利用可能なプロバイダー名一覧取得."""
        if not self._initialized:
            self.initialize()
        return [name for name, p in self._providers.items() if p.is_available]

    def list_all(self) -> dict[str, bool]:
        """全プロバイダーの状態取得."""
        if not self._initialized:
            self.initialize()
        return {name: p.is_available for name, p in self._providers.items()}

    def register(self, name: str, provider: AIProvider) -> None:
        """カスタムプロバイダーを登録.

        Args:
            name: プロバイダー名
            provider: プロバイダーインスタンス
        """
        self._providers[name] = provider
        logger.info("provider.custom_registered", provider=name)

    async def health_check_all(self) -> dict[str, bool]:
        """全プロバイダーのヘルスチェック."""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            if provider.is_available:
                results[name] = await provider.health_check()
            else:
                results[name] = False
        return results

    def to_dict(self) -> dict[str, Any]:
        """API応答用辞書変換."""
        return {
            name: {
                "available": provider.is_available,
                "name": provider.name,
            }
            for name, provider in self._providers.items()
        }


# シングルトンインスタンス
_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """ProviderRegistryシングルトン取得."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _registry.initialize()
    return _registry
