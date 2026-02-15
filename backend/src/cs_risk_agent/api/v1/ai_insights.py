"""AIインサイトAPIエンドポイント."""

from __future__ import annotations

from fastapi import APIRouter

from cs_risk_agent.data.schemas import AIChatRequest, AIChatResponse
from cs_risk_agent.demo_loader import DemoData

router = APIRouter()

# リスク分析専用システムプロンプト
SYSTEM_PROMPT = """あなたは「CS Risk Agent」の連結子会社リスク分析AIアシスタントです。

## あなたの役割
- 東洋重工グループ（親会社＋連結子会社15社）のリスク分析を支援
- 財務データ、仕訳データ、リスクスコアに基づいた専門的な回答を提供
- 4つの分析エンジン（裁量的発生高、不正予測、ルールエンジン、ベンフォード分析）の結果を解説

## 重要なリスクシナリオ
現在、以下の高リスク子会社が検出されています：
1. 东洋精密机械（上海）- CRITICAL: 売掛金が前年比233%増、架空売上の疑い
2. 東洋建機リース - CRITICAL: 債務超過の兆候、営業CF 4Q連続赤字
3. Toyo Power Systems (USA) - HIGH: ベンフォード逸脱、仕訳パターンに規則性
4. PT Toyo Manufacturing (Indonesia) - HIGH: 在庫滞留、回転日数+85日
5. Toyo Automotive GmbH (Germany) - HIGH: 販管費急増、コンサル費用不透明

## 回答方針
- 日本語で回答
- 具体的な数値・根拠を示す
- 推奨アクションを提示
- 不確実な点は明示する
"""


@router.post("/chat", response_model=AIChatResponse)
async def chat(request: AIChatRequest):
    """AIチャット（システムプロンプト＋コンテキスト付き）."""
    # コンテキスト情報の組み立て
    context_text = ""
    if request.company_id:
        demo = DemoData.get()
        entity = demo.get_entity_by_id(request.company_id)
        rs = demo.get_risk_score_by_entity(request.company_id)
        if entity:
            context_text += f"\n\n## 対象企業情報\n- 名前: {entity.get('name')}\n- 国: {entity.get('country')}\n- セグメント: {entity.get('segment')}\n"
        if rs:
            context_text += f"- リスクスコア: {rs.get('total_score')} ({rs.get('risk_level')})\n"
            context_text += f"- DA: {rs.get('da_score')}, 不正: {rs.get('fraud_score')}, ルール: {rs.get('rule_score')}, ベンフォード: {rs.get('benford_score')}\n"
            if rs.get("risk_factors"):
                context_text += "- リスクファクター:\n" + "\n".join(f"  - {f}" for f in rs["risk_factors"]) + "\n"

    try:
        from cs_risk_agent.ai.provider import Message, MessageRole
        from cs_risk_agent.ai.router import get_ai_router
        from cs_risk_agent.config import ModelTier

        ai_router = get_ai_router()
        messages = [
            Message(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT + context_text),
            Message(role=MessageRole.USER, content=request.message),
        ]
        tier = ModelTier.COST_EFFECTIVE if request.tier == "cost_effective" else ModelTier.SOTA
        response = await ai_router.complete(messages, tier=tier, provider=request.provider)
        return AIChatResponse(
            response=response.content,
            provider=response.provider,
            model=response.model,
            tokens_used=response.usage.total_tokens,
            cost_usd=0.0,
        )
    except Exception as e:
        # プロバイダー未設定時のフォールバック応答
        return _fallback_response(request.message, request.company_id)


def _fallback_response(message: str, company_id: str | None) -> AIChatResponse:
    """プロバイダー未設定時のデモ応答."""
    demo = DemoData.get()
    msg_lower = message.lower()

    # キーワードに基づくデモ応答
    if company_id:
        rs = demo.get_risk_score_by_entity(company_id)
        entity = demo.get_entity_by_id(company_id)
        if rs and entity:
            factors_text = "\n".join(f"- {f}" for f in rs.get("risk_factors", []))
            return AIChatResponse(
                response=f"**{entity.get('name')}** のリスク分析結果です。\n\n"
                f"**総合リスクスコア: {rs['total_score']}** ({rs['risk_level'].upper()})\n\n"
                f"| エンジン | スコア |\n|---|---|\n"
                f"| 裁量的発生高 | {rs['da_score']} |\n"
                f"| 不正予測 | {rs['fraud_score']} |\n"
                f"| ルールエンジン | {rs['rule_score']} |\n"
                f"| ベンフォード | {rs['benford_score']} |\n\n"
                f"**検出されたリスクファクター:**\n{factors_text}\n\n"
                f"_※ AIプロバイダー未設定のためデモ応答です。設定画面からAzure/AWS/GCPを設定すると、より詳細な分析が可能です。_",
                provider="demo",
                model="fallback",
            )

    if any(k in msg_lower for k in ["上海", "中国", "架空", "売掛"]):
        return AIChatResponse(
            response="**东洋精密机械（上海）有限公司** について分析します。\n\n"
            "**リスクレベル: CRITICAL**\n\n"
            "主要な検出事項：\n"
            "1. 売掛金が前年同期比233%増加（業界平均の2.5倍の回収日数）\n"
            "2. 営業キャッシュフローが純利益と逆相関（利益は黒字なのにCFは赤字）\n"
            "3. 期末月に売上の72%が集中（通常は25%程度）\n"
            "4. 特定担当者(chen_w)による仕訳が85%を占める\n\n"
            "**推奨アクション:**\n"
            "- 売掛先への残高確認状の送付\n"
            "- 現地往査の実施\n"
            "- 銀行明細との照合\n\n"
            "_※ デモ応答です_",
            provider="demo",
            model="fallback",
        )

    # 汎用応答
    summary = demo.get_risk_summary()
    return AIChatResponse(
        response=f"東洋重工グループの連結子会社リスク分析へようこそ。\n\n"
        f"**現在のリスク状況:**\n"
        f"- 対象子会社: {summary['total_companies']}社\n"
        f"- Critical: {summary['by_level']['critical']}社\n"
        f"- High: {summary['by_level']['high']}社\n"
        f"- Medium: {summary['by_level']['medium']}社\n"
        f"- Low: {summary['by_level']['low']}社\n"
        f"- 平均リスクスコア: {summary['avg_score']}\n\n"
        f"質問例:\n"
        f"- 「上海子会社のリスクを教えて」\n"
        f"- 「高リスク企業の一覧は？」\n"
        f"- 「ベンフォード分析の結果は？」\n\n"
        f"_※ AIプロバイダー未設定のためデモ応答です。設定画面から設定してください。_",
        provider="demo",
        model="fallback",
    )


@router.get("/insights/{company_id}")
async def get_insights(company_id: str):
    """AIインサイト取得."""
    demo = DemoData.get()
    rs = demo.get_risk_score_by_entity(company_id)
    if not rs:
        return {"company_id": company_id, "insights": []}

    insights = []
    for i, factor in enumerate(rs.get("risk_factors", [])):
        insights.append({
            "id": f"INS-{company_id}-{i}",
            "company_id": company_id,
            "probe_type": "risk_factor",
            "insight_text": factor,
            "severity": rs["risk_level"],
            "confidence": 0.85 - i * 0.05,
        })
    return {"company_id": company_id, "insights": insights}
