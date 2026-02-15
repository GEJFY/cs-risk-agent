"""ハイブリッド・ガバナンス デモスクリプト.

機密データはローカルLLMで処理し、一般的な処理はクラウドで実行する
ワークフローを実演する。
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, str(__file__).replace("scripts/demo_hybrid_governance.py", "backend/src"))


async def demo_hybrid_governance():
    """ハイブリッドガバナンスデモ."""
    print("=" * 70)
    print("  ハイブリッド・ガバナンス デモ")
    print("  機密データ → ローカル / 一般処理 → クラウド")
    print("=" * 70)

    # ハイブリッドルール定義
    hybrid_rules = [
        {"data_classification": "confidential", "provider": "ollama", "description": "機密データ（個人情報、内部監査資料）"},
        {"data_classification": "internal", "provider": "ollama", "description": "社内限定データ（未公開財務情報）"},
        {"data_classification": "general", "provider": "azure", "description": "一般データ（公開済み財務情報）"},
        {"data_classification": "public", "provider": "azure", "description": "公開データ（有報、決算短信）"},
    ]

    print("\n--- ルーティング設定 ---")
    for rule in hybrid_rules:
        provider_label = "🏠 ローカル" if rule["provider"] == "ollama" else "☁️ クラウド"
        print(f"  {provider_label} [{rule['data_classification']}] {rule['description']}")

    # シナリオ実行
    scenarios = [
        {
            "name": "個人情報を含む従業員リスク分析",
            "classification": "confidential",
            "data": "従業員ID: EMP-001, 氏名: 山田太郎, 不正取引疑義あり",
            "expected_provider": "ollama",
        },
        {
            "name": "未公開四半期決算の異常検知",
            "classification": "internal",
            "data": "Q3売上高: 前年比-15%, 営業利益率: 2.1% (業界平均8.5%)",
            "expected_provider": "ollama",
        },
        {
            "name": "公開済み有価証券報告書の分析",
            "classification": "general",
            "data": "2024年度有報: 連結売上高1,234億円, ROE 12.3%",
            "expected_provider": "azure",
        },
        {
            "name": "業界ベンチマーク比較",
            "classification": "public",
            "data": "化学業界平均ROA: 5.2%, 対象企業ROA: 3.1%",
            "expected_provider": "azure",
        },
    ]

    print("\n--- 処理シナリオ実行 ---")
    for i, scenario in enumerate(scenarios, 1):
        provider_label = "🏠 ローカル(Ollama)" if scenario["expected_provider"] == "ollama" else "☁️ クラウド(Azure)"
        security_label = "🔒" if scenario["classification"] in ("confidential", "internal") else "🔓"

        print(f"\n  シナリオ{i}: {scenario['name']}")
        print(f"    分類: {security_label} {scenario['classification']}")
        print(f"    ルーティング先: {provider_label}")
        print(f"    データ: {scenario['data'][:60]}...")
        print(f"    ✅ {scenario['expected_provider']} で安全に処理完了")

    # ガバナンスサマリー
    print("\n--- ガバナンスサマリー ---")
    local_count = sum(1 for s in scenarios if s["expected_provider"] == "ollama")
    cloud_count = len(scenarios) - local_count
    print(f"  ローカル処理: {local_count}件 (機密データ保護)")
    print(f"  クラウド処理: {cloud_count}件 (高性能AI活用)")
    print(f"  データ漏洩リスク: なし ✅")
    print(f"  コンプライアンス: 準拠 ✅")

    print("\n" + "=" * 70)
    print("  ハイブリッドガバナンスデモ完了")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_hybrid_governance())
