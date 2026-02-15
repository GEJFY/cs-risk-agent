"""異常検知デモスクリプト.

混入させた「不備データ」をAIが検知し、アラートを出すデモ。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(__file__).replace("scripts/demo_anomaly_detection.py", "backend/src"))

from cs_risk_agent.analysis.benford import BenfordAnalyzer
from cs_risk_agent.analysis.rule_engine import RuleEngine


def load_demo_data() -> pd.DataFrame:
    """デモデータ読み込み."""
    data_path = Path(__file__).parent.parent / "demo_data" / "journal_entries.csv"
    if not data_path.exists():
        print("デモデータが見つかりません。先に generate_demo_data.py を実行してください。")
        print("  python scripts/generate_demo_data.py")
        sys.exit(1)
    return pd.read_csv(data_path)


def detect_statistical_anomalies(df: pd.DataFrame) -> list[dict]:
    """統計的異常検知."""
    anomalies = []

    # 金額の異常値検知 (Z-score > 3)
    amounts = df["debit"].replace(0, np.nan).dropna()
    if len(amounts) > 10:
        z_scores = (amounts - amounts.mean()) / amounts.std()
        outliers = df.loc[z_scores.abs() > 3]
        for _, row in outliers.iterrows():
            anomalies.append({
                "type": "statistical_outlier",
                "severity": "high",
                "entry_id": row["id"],
                "company_id": row["company_id"],
                "amount": row["debit"],
                "z_score": round(float(z_scores.loc[row.name]), 2),
                "description": f"統計的異常値 (Z-score: {z_scores.loc[row.name]:.2f})",
            })

    return anomalies


def detect_duplicate_amounts(df: pd.DataFrame) -> list[dict]:
    """重複金額検知."""
    anomalies = []

    for company_id in df["company_id"].unique()[:10]:
        company_df = df[df["company_id"] == company_id]
        debits = company_df[company_df["debit"] > 0]["debit"]

        # 同一金額が3回以上
        counts = debits.value_counts()
        suspicious = counts[counts >= 3]

        for amount, count in suspicious.head(5).items():
            anomalies.append({
                "type": "duplicate_amount",
                "severity": "medium",
                "company_id": company_id,
                "amount": float(amount),
                "count": int(count),
                "description": f"同一金額 ¥{amount:,.0f} が {count}回 出現",
            })

    return anomalies


def detect_round_numbers(df: pd.DataFrame) -> list[dict]:
    """端数なし大口取引検知."""
    anomalies = []

    large_round = df[
        (df["debit"] >= 1_000_000) &
        (df["debit"] % 1_000_000 == 0)
    ]

    for _, row in large_round.head(20).iterrows():
        anomalies.append({
            "type": "round_number",
            "severity": "medium",
            "entry_id": row["id"],
            "company_id": row["company_id"],
            "amount": row["debit"],
            "description": f"端数なし大口仕訳 ¥{row['debit']:,.0f}",
        })

    return anomalies


def detect_weekend_entries(df: pd.DataFrame) -> list[dict]:
    """休日計上仕訳検知."""
    anomalies = []
    df_copy = df.copy()
    df_copy["day_of_week"] = pd.to_datetime(df_copy["date"]).dt.dayofweek

    weekend = df_copy[df_copy["day_of_week"] >= 5]

    for _, row in weekend.head(20).iterrows():
        day_name = "土曜日" if row["day_of_week"] == 5 else "日曜日"
        anomalies.append({
            "type": "weekend_entry",
            "severity": "low",
            "entry_id": row["id"],
            "company_id": row["company_id"],
            "date": row["date"],
            "description": f"{day_name}に計上された仕訳",
        })

    return anomalies


def run_benford_analysis(df: pd.DataFrame) -> dict:
    """ベンフォード法則分析."""
    analyzer = BenfordAnalyzer()
    amounts = df[df["debit"] > 0]["debit"]
    result = analyzer.first_digit_test(amounts)
    return {
        "conformity": result.conformity,
        "mad": round(result.mad, 6),
        "chi_square": round(result.chi_square, 2),
        "p_value": round(result.p_value, 4),
        "sample_size": result.sample_size,
    }


def main():
    """メイン実行."""
    print("=" * 70)
    print("  異常検知デモ")
    print("  不備データの自動検知とアラート生成")
    print("=" * 70)

    # データ読み込み
    print("\n📂 デモデータ読み込み中...")
    df = load_demo_data()
    print(f"  読込件数: {len(df):,}件")
    print(f"  企業数: {df['company_id'].nunique()}社")

    # 既知の不備データ数
    known_anomalies = df[df.get("is_anomaly", False) == True] if "is_anomaly" in df.columns else pd.DataFrame()
    print(f"  混入済み不備データ: {len(known_anomalies)}件")

    # 各検知手法実行
    print("\n🔍 異常検知を実行中...")

    all_anomalies = []

    print("\n  [1/5] 統計的異常値検知 (Z-score > 3)...")
    stat_anomalies = detect_statistical_anomalies(df)
    all_anomalies.extend(stat_anomalies)
    print(f"    → {len(stat_anomalies)}件 検出")

    print("\n  [2/5] 重複金額検知...")
    dup_anomalies = detect_duplicate_amounts(df)
    all_anomalies.extend(dup_anomalies)
    print(f"    → {len(dup_anomalies)}件 検出")

    print("\n  [3/5] 端数なし大口取引検知...")
    round_anomalies = detect_round_numbers(df)
    all_anomalies.extend(round_anomalies)
    print(f"    → {len(round_anomalies)}件 検出")

    print("\n  [4/5] 休日計上仕訳検知...")
    weekend_anomalies = detect_weekend_entries(df)
    all_anomalies.extend(weekend_anomalies)
    print(f"    → {len(weekend_anomalies)}件 検出")

    print("\n  [5/5] ベンフォード法則分析...")
    benford_result = run_benford_analysis(df)
    print(f"    → 適合性: {benford_result['conformity']}")
    print(f"    → MAD: {benford_result['mad']}")
    print(f"    → カイ二乗値: {benford_result['chi_square']}")

    # アラートサマリー
    print("\n" + "=" * 70)
    print("  🚨 異常検知アラート サマリー")
    print("=" * 70)

    by_severity = {}
    for a in all_anomalies:
        sev = a["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    print(f"\n  検出総数: {len(all_anomalies)}件")
    for sev in ["high", "medium", "low"]:
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
        print(f"    {icon} {sev}: {by_severity.get(sev, 0)}件")

    by_type = {}
    for a in all_anomalies:
        t = a["type"]
        by_type[t] = by_type.get(t, 0) + 1

    print(f"\n  検知タイプ別:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    - {t}: {count}件")

    # 上位アラート表示
    print(f"\n  📋 高リスクアラート (上位10件):")
    high_alerts = [a for a in all_anomalies if a["severity"] == "high"]
    for i, alert in enumerate(high_alerts[:10], 1):
        print(f"    {i}. [{alert['type']}] {alert['description']}")

    print("\n" + "=" * 70)
    print("  異常検知デモ完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
