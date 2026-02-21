"""管理APIエンドポイント - プロバイダー管理・コスト・設定."""

from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from cs_risk_agent.api.deps import require_permission
from cs_risk_agent.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# 設定永続化用モデル (インメモリストア)
# ---------------------------------------------------------------------------

class NotificationSettings(BaseModel):
    """通知設定."""

    critical_risk_alert: bool = True
    analysis_complete: bool = True
    daily_summary: bool = False
    budget_alert: bool = True


class ThresholdSettings(BaseModel):
    """リスク閾値設定."""

    critical: int = Field(default=80, ge=0, le=100)
    high: int = Field(default=60, ge=0, le=100)
    medium: int = Field(default=40, ge=0, le=100)


class AppSettings(BaseModel):
    """アプリケーション設定."""

    notifications: NotificationSettings = NotificationSettings()
    thresholds: ThresholdSettings = ThresholdSettings()


# インメモリ設定ストア (本番ではDB永続化に切り替え)
_app_settings = AppSettings()


def _get_provider_info(name: str, settings: Any) -> dict[str, Any]:
    """プロバイダーの設定状況を返す（ネストされたSettings構造に対応）."""
    providers_map: dict[str, dict[str, Any]] = {
        "azure": {
            "name": "Azure AI Foundry",
            "configured": settings.azure.is_configured,
            "sota_model": settings.azure.sota_deployment,
            "cost_effective_model": settings.azure.cost_effective_deployment,
        },
        "aws": {
            "name": "AWS Bedrock",
            "configured": settings.aws.is_configured,
            "sota_model": settings.aws.bedrock_sota_model,
            "cost_effective_model": settings.aws.bedrock_cost_effective_model,
        },
        "gcp": {
            "name": "GCP Vertex AI",
            "configured": settings.gcp.is_configured,
            "sota_model": settings.gcp.sota_model,
            "cost_effective_model": settings.gcp.cost_effective_model,
        },
        "ollama": {
            "name": "Ollama (Local)",
            "configured": True,
            "sota_model": settings.ollama.sota_model,
            "cost_effective_model": settings.ollama.cost_effective_model,
        },
    }
    return providers_map.get(name, {"name": name, "configured": False})


@router.get("/status")
async def get_status(
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """システムステータス・プロバイダー一覧."""
    settings = get_settings()
    providers = {}
    for pname in ["azure", "aws", "gcp", "ollama"]:
        info = _get_provider_info(pname, settings)
        providers[pname] = {
            **info,
            "status": "active" if info["configured"] else "inactive",
        }

    return {
        "data_mode": settings.data_mode.value,
        "mode": settings.ai.mode.value,
        "default_provider": settings.ai.default_provider,
        "fallback_chain": settings.ai.fallback_providers,
        "providers": providers,
        "budget": {
            "monthly_limit_usd": settings.ai.monthly_budget_usd,
            "alert_threshold": settings.ai.budget_alert_threshold,
            "circuit_breaker_threshold": settings.ai.circuit_breaker_threshold,
        },
    }


@router.get("/providers")
async def get_providers(
    current_user: dict[str, Any] = Depends(require_permission("read")),
):
    """プロバイダー詳細一覧."""
    settings = get_settings()
    result = []
    for pname in ["azure", "aws", "gcp", "ollama"]:
        info = _get_provider_info(pname, settings)
        result.append({"id": pname, **info, "status": "active" if info["configured"] else "inactive"})
    return {"providers": result}


@router.get("/providers/{provider_id}/health")
async def check_provider_health(
    provider_id: str,
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """プロバイダーのヘルスチェック."""
    try:
        from cs_risk_agent.ai.router import get_ai_router
        ai_router = get_ai_router()
        provider = ai_router._registry.get(provider_id)
        if provider is None:
            return {"provider": provider_id, "healthy": False, "error": "Not registered"}
        healthy = await provider.health_check()
        return {"provider": provider_id, "healthy": healthy}
    except ImportError:
        logger.warning("health_check_failed", provider=provider_id, reason="AI router not available")
        return {"provider": provider_id, "healthy": False, "error": "AI router not available"}
    except Exception as e:
        logger.error("health_check_error", provider=provider_id, error=str(e))
        return {"provider": provider_id, "healthy": False, "error": str(e)}


@router.get("/budget")
async def get_budget(
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """予算ステータス."""
    settings = get_settings()
    try:
        from cs_risk_agent.ai.router import get_ai_router
        return get_ai_router()._circuit_breaker.to_dict()
    except ImportError:
        logger.debug("budget_fallback", reason="AI router not available")
        return {
            "state": "closed",
            "monthly_limit_usd": settings.ai.monthly_budget_usd,
            "current_spend_usd": 0.0,
            "remaining_usd": settings.ai.monthly_budget_usd,
            "usage_ratio": 0.0,
        }
    except Exception as e:
        logger.error("budget_query_error", error=str(e))
        return {
            "state": "closed",
            "monthly_limit_usd": settings.ai.monthly_budget_usd,
            "current_spend_usd": 0.0,
            "remaining_usd": settings.ai.monthly_budget_usd,
            "usage_ratio": 0.0,
        }


@router.get("/cost")
async def get_cost(
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """コスト詳細."""
    try:
        from cs_risk_agent.ai.router import get_ai_router
        return get_ai_router()._cost_tracker.get_summary()
    except ImportError:
        logger.debug("cost_fallback", reason="AI router not available")
        return {"total_cost_usd": 0.0, "total_requests": 0, "by_provider": {}, "by_model": {}}
    except Exception as e:
        logger.error("cost_query_error", error=str(e))
        return {"total_cost_usd": 0.0, "total_requests": 0, "by_provider": {}, "by_model": {}}


@router.post("/providers/{provider_id}/set-default")
async def set_default_provider(
    provider_id: str,
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """デフォルトプロバイダーを変更."""
    valid = ["azure", "aws", "gcp", "ollama", "vllm"]
    if provider_id not in valid:
        return {"error": f"Invalid provider: {provider_id}", "valid": valid}
    os.environ["AI_DEFAULT_PROVIDER"] = provider_id
    get_settings.cache_clear()
    logger.info("default_provider_changed", provider=provider_id, user=current_user.get("sub"))
    return {"status": "ok", "default_provider": provider_id}


# ---------------------------------------------------------------------------
# アプリケーション設定 CRUD
# ---------------------------------------------------------------------------


@router.get("/settings")
async def get_app_settings(
    current_user: dict[str, Any] = Depends(require_permission("read")),
):
    """現在のアプリケーション設定を取得."""
    return _app_settings.model_dump()


@router.put("/settings")
async def update_app_settings(
    payload: AppSettings,
    current_user: dict[str, Any] = Depends(require_permission("admin")),
):
    """アプリケーション設定を更新."""
    global _app_settings  # noqa: PLW0603
    _app_settings = payload
    logger.info(
        "settings_updated",
        user=current_user.get("sub"),
        thresholds=payload.thresholds.model_dump(),
    )
    return {"status": "ok", "settings": _app_settings.model_dump()}
