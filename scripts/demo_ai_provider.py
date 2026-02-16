#!/usr/bin/env python3
"""AI プロバイダー接続デモスクリプト.

ローカル Ollama / クラウドプロバイダーへの接続を検証し、
リスク分析のサンプルクエリを実行する。

Usage:
    # Ollama ローカル (デフォルト)
    python scripts/demo_ai_provider.py

    # プロバイダー指定
    python scripts/demo_ai_provider.py --provider azure

    # ヘルスチェックのみ
    python scripts/demo_ai_provider.py --health-only

Requirements:
    - Ollama: ollama serve 実行中 + モデルダウンロード済み
    - Cloud: .env に API キー設定済み
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))


async def check_all_providers() -> dict[str, bool]:
    """全プロバイダーのヘルスチェック."""
    from cs_risk_agent.ai.registry import get_provider_registry

    print("=" * 60)
    print("AI Provider ヘルスチェック")
    print("=" * 60)

    registry = get_provider_registry()
    results: dict[str, bool] = {}

    for name, provider in registry._providers.items():
        try:
            is_healthy = await provider.health_check()
            results[name] = is_healthy
            status = "OK" if is_healthy else "NG"
            icon = "[+]" if is_healthy else "[-]"
            print(f"  {icon} {name:12s}: {status}")
        except Exception as e:
            results[name] = False
            print(f"  [-] {name:12s}: ERROR - {e}")

    available = sum(1 for v in results.values() if v)
    print(f"\n利用可能: {available}/{len(results)} プロバイダー")
    return results


async def demo_complete(provider_name: str | None = None) -> None:
    """AIチャット完了デモ."""
    from cs_risk_agent.ai.provider import Message, MessageRole
    from cs_risk_agent.ai.router import get_ai_router
    from cs_risk_agent.config import ModelTier

    print("\n" + "=" * 60)
    print("AI チャット完了デモ")
    print("=" * 60)

    router = get_ai_router()

    # テストクエリ
    queries = [
        "売掛金が前年比233%増加した子会社について、主要なリスクファクターを3つ教えてください。",
        "ベンフォード分析でCritical判定が出た場合の推奨監査手続きを教えてください。",
    ]

    for i, query in enumerate(queries):
        print(f"\n--- クエリ {i+1} ---")
        print(f"Q: {query[:60]}...")

        try:
            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content="あなたは連結子会社リスク分析の専門AIアシスタントです。簡潔に回答してください。",
                ),
                Message(role=MessageRole.USER, content=query),
            ]

            response = await router.complete(
                messages,
                provider=provider_name,
                tier=ModelTier.COST_EFFECTIVE,
                max_tokens=512,
                temperature=0.3,
            )

            print(f"A: {response.content[:200]}...")
            print(
                f"   [provider={response.provider}, model={response.model}, "
                f"tokens={response.usage.total_tokens}]"
            )

        except Exception as e:
            print(f"ERROR: {e}")
            print("   (プロバイダーが利用不可の場合、--health-only でステータスを確認)")


async def demo_router_status() -> None:
    """ルーターステータス表示."""
    from cs_risk_agent.ai.router import get_ai_router

    print("\n" + "=" * 60)
    print("AI Router ステータス")
    print("=" * 60)

    router = get_ai_router()
    status = router.get_status()

    print(f"  モード: {status['mode']}")
    print(f"  デフォルト: {status['default_provider']}")
    print(f"  フォールバック: {' -> '.join(status['fallback_chain'])}")
    print(f"  予算状態: {status['budget']['state']}")
    print(f"  月間予算: ${status['budget']['monthly_limit_usd']}")

    print("\n  プロバイダー別モデル:")
    for provider, tiers in status["model_tiers"].items():
        for tier, info in tiers.items():
            print(f"    {provider}/{tier}: {info['model_id']}")


async def main(args: argparse.Namespace) -> None:
    """メイン処理."""
    # ヘルスチェック
    results = await check_all_providers()

    # ステータス表示
    await demo_router_status()

    if args.health_only:
        return

    # 指定プロバイダーが利用可能か確認
    provider = args.provider
    if provider and not results.get(provider, False):
        print(f"\n[!] {provider} は現在利用不可です。")
        print("    Ollama の場合: ollama serve を起動し、モデルをダウンロードしてください")
        print("    Cloud の場合: .env にAPI キーを設定してください")
        return

    # チャット完了デモ
    await demo_complete(provider)

    print("\n" + "=" * 60)
    print("デモ完了!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI プロバイダー接続デモ")
    parser.add_argument(
        "--provider",
        choices=["azure", "aws", "gcp", "ollama", "vllm"],
        help="使用するプロバイダー (省略時はルーティングロジックで決定)",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="ヘルスチェックのみ実行",
    )
    args = parser.parse_args()

    asyncio.run(main(args))
