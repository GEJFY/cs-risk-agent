"""AIインサイトAPIエンドポイント."""

from __future__ import annotations

from fastapi import APIRouter

from cs_risk_agent.ai.provider import Message, MessageRole
from cs_risk_agent.ai.router import get_ai_router
from cs_risk_agent.config import ModelTier
from cs_risk_agent.data.schemas import AIChatRequest, AIChatResponse

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def chat(request: AIChatRequest):
    """AIチャット."""
    try:
        ai_router = get_ai_router()
        messages = [Message(role=MessageRole.USER, content=request.message)]
        tier = (
            ModelTier.COST_EFFECTIVE
            if request.tier == "cost_effective"
            else ModelTier.SOTA
        )
        response = await ai_router.complete(
            messages, tier=tier, provider=request.provider
        )
        return AIChatResponse(
            response=response.content,
            provider=response.provider,
            model=response.model,
            tokens_used=response.usage.total_tokens,
        )
    except Exception as e:
        return AIChatResponse(
            response=f"AI応答エラー: {e}",
            provider="none",
            model="none",
        )


@router.get("/insights/{company_id}")
async def get_insights(company_id: str):
    """AIインサイト取得."""
    return {"company_id": company_id, "insights": []}
