"""デモデータ生成スクリプト.

本番を想定したリアリスティックなサンプルデータを生成する。
- 企業マスタ（50社）
- 連結子会社（200社）
- 財務諸表データ（8四半期分）
- 監査仕訳データ（数千行）
- 不備データ（意図的に混入）
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# 乱数シード固定（再現性確保）
random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "demo_data"

# --- 企業マスタ ---
INDUSTRIES = [
    ("3050", "化学"),
    ("3100", "医薬品"),
    ("3250", "電気機器"),
    ("3300", "輸送用機器"),
    ("3350", "精密機器"),
    ("3400", "情報・通信業"),
    ("3450", "サービス業"),
    ("3500", "小売業"),
    ("3550", "食料品"),
    ("3600", "建設業"),
]

COMPANY_NAMES = [
    "グローバルテック株式会社",
    "日本先端素材株式会社",
    "東京エレクトロニクス株式会社",
    "大阪製薬株式会社",
    "未来通信株式会社",
    "サクラ精密工業株式会社",
    "富士化学工業株式会社",
    "北海道食品株式会社",
    "みなと建設株式会社",
    "九州サービスグループ株式会社",
    "中部自動車部品株式会社",
    "横浜バイオテック株式会社",
    "関西情報システム株式会社",
    "東北エナジー株式会社",
    "四国マテリアル株式会社",
    "沖縄リゾート株式会社",
    "北陸電子デバイス株式会社",
    "千葉ロジスティクス株式会社",
    "名古屋金属加工株式会社",
    "広島船舶工業株式会社",
    "仙台ヘルスケア株式会社",
    "福岡フィナンシャル株式会社",
    "札幌テクノロジーズ株式会社",
    "京都セラミックス株式会社",
    "神戸鉄鋼株式会社",
    "新潟農産加工株式会社",
    "長野光学機器株式会社",
    "静岡自動車株式会社",
    "岡山石油化学株式会社",
    "熊本半導体株式会社",
    "山口セメント株式会社",
    "奈良住宅設備株式会社",
    "和歌山繊維株式会社",
    "三重重工業株式会社",
    "岐阜プラスチック株式会社",
    "栃木機械製作所株式会社",
    "群馬自動車電装株式会社",
    "茨城農業科学株式会社",
    "埼玉情報サービス株式会社",
    "山梨電子工業株式会社",
    "富山化成品株式会社",
    "石川繊維加工株式会社",
    "福井原子力技術株式会社",
    "滋賀環境ソリューション株式会社",
    "大分温泉リゾート株式会社",
    "宮崎食品加工株式会社",
    "鹿児島酒造株式会社",
    "佐賀陶磁器株式会社",
    "長崎造船株式会社",
    "徳島医療機器株式会社",
]

SEGMENTS = ["製造", "販売", "R&D", "管理", "海外", "サービス"]


def generate_companies(n: int = 50) -> list[dict[str, Any]]:
    """企業マスタ生成."""
    companies = []
    for i in range(n):
        industry = random.choice(INDUSTRIES)
        companies.append({
            "id": f"COM-{i+1:04d}",
            "edinet_code": f"E{10000+i}",
            "securities_code": f"{1000+i*50}",
            "name": COMPANY_NAMES[i] if i < len(COMPANY_NAMES) else f"テスト企業{i+1}株式会社",
            "industry_code": industry[0],
            "industry_name": industry[1],
            "fiscal_year_end": random.choice([3, 6, 9, 12]),
            "is_listed": random.random() > 0.2,
            "country": "JPN",
        })
    return companies


def generate_subsidiaries(companies: list[dict], avg_per_company: int = 4) -> list[dict[str, Any]]:
    """連結子会社生成."""
    subsidiaries = []
    sub_id = 1
    countries = ["JPN", "USA", "CHN", "SGP", "GBR", "DEU", "THA", "VNM", "IDN", "IND"]

    for company in companies:
        n_subs = max(1, int(np.random.poisson(avg_per_company)))
        for j in range(n_subs):
            subsidiaries.append({
                "id": f"SUB-{sub_id:04d}",
                "parent_company_id": company["id"],
                "name": f"{company['name'].replace('株式会社', '')}・{random.choice(SEGMENTS)}子会社{j+1}",
                "country": random.choice(countries),
                "ownership_ratio": round(random.uniform(0.51, 1.0), 2),
                "segment": random.choice(SEGMENTS),
                "is_active": random.random() > 0.05,
            })
            sub_id += 1
    return subsidiaries


def generate_financial_statements(
    companies: list[dict], quarters: int = 8
) -> list[dict[str, Any]]:
    """財務諸表データ生成（8四半期分）."""
    statements = []
    base_year = 2024

    for company in companies:
        # ベース値
        base_revenue = random.uniform(10_000, 500_000)  # 百万円
        base_assets = base_revenue * random.uniform(1.5, 4.0)
        growth_rate = random.uniform(-0.05, 0.15)

        for q in range(quarters):
            year = base_year - (q // 4)
            quarter = 4 - (q % 4)
            seasonal_factor = 1.0 + 0.1 * np.sin(quarter * np.pi / 2)

            revenue = base_revenue * (1 + growth_rate) ** (quarters - q) * seasonal_factor
            cogs = revenue * random.uniform(0.55, 0.80)
            sga = revenue * random.uniform(0.10, 0.25)
            operating_income = revenue - cogs - sga
            net_income = operating_income * random.uniform(0.60, 0.85)
            operating_cf = net_income + revenue * random.uniform(0.02, 0.08)
            total_assets = base_assets * (1 + growth_rate * 0.5) ** (quarters - q)
            current_assets = total_assets * random.uniform(0.30, 0.55)
            ppe = total_assets * random.uniform(0.20, 0.40)
            total_liabilities = total_assets * random.uniform(0.30, 0.70)
            total_equity = total_assets - total_liabilities
            receivables = revenue * random.uniform(0.08, 0.20)
            inventory = cogs * random.uniform(0.05, 0.15)
            depreciation = ppe * random.uniform(0.05, 0.12)

            statements.append({
                "company_id": company["id"],
                "company_name": company["name"],
                "fiscal_year": year,
                "fiscal_quarter": quarter,
                "revenue": round(revenue, 1),
                "cogs": round(cogs, 1),
                "sga": round(sga, 1),
                "operating_income": round(operating_income, 1),
                "net_income": round(net_income, 1),
                "operating_cash_flow": round(operating_cf, 1),
                "total_assets": round(total_assets, 1),
                "current_assets": round(current_assets, 1),
                "ppe": round(ppe, 1),
                "total_liabilities": round(total_liabilities, 1),
                "total_equity": round(total_equity, 1),
                "receivables": round(receivables, 1),
                "inventory": round(inventory, 1),
                "depreciation": round(depreciation, 1),
                "current_liabilities": round(total_liabilities * random.uniform(0.3, 0.6), 1),
                "long_term_debt": round(total_liabilities * random.uniform(0.2, 0.5), 1),
                "retained_earnings": round(total_equity * random.uniform(0.5, 0.9), 1),
                "ebit": round(operating_income * 1.05, 1),
            })

    return statements


def generate_journal_entries(companies: list[dict], n_per_company: int = 100) -> list[dict[str, Any]]:
    """監査仕訳データ生成（不備データ含む）."""
    entries = []
    entry_id = 1

    account_codes = {
        "1100": "現金及び預金", "1200": "売掛金", "1300": "棚卸資産",
        "1400": "前払費用", "1500": "その他流動資産",
        "2100": "有形固定資産", "2200": "無形固定資産", "2300": "投資有価証券",
        "3100": "買掛金", "3200": "短期借入金", "3300": "未払費用",
        "3400": "長期借入金", "3500": "退職給付引当金",
        "4100": "売上高", "4200": "売上原価",
        "5100": "販売費", "5200": "一般管理費",
        "6100": "営業外収益", "6200": "営業外費用",
        "7100": "特別利益", "7200": "特別損失",
    }

    for company in companies:
        for j in range(n_per_company):
            code = random.choice(list(account_codes.keys()))
            amount = round(random.lognormvariate(10, 2), 0)
            is_debit = random.random() > 0.5
            date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 364))

            entry = {
                "id": f"JE-{entry_id:06d}",
                "company_id": company["id"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": code,
                "account_name": account_codes[code],
                "debit": amount if is_debit else 0,
                "credit": 0 if is_debit else amount,
                "description": f"通常仕訳_{code}_{j+1}",
                "posted_by": random.choice(["user_a", "user_b", "user_c", "system"]),
                "is_anomaly": False,
            }
            entries.append(entry)
            entry_id += 1

        # --- 不備データの意図的混入（各社5%） ---
        n_anomalies = max(3, n_per_company // 20)
        for k in range(n_anomalies):
            anomaly_type = random.choice(["duplicate", "round_number", "weekend", "large", "reversed"])
            date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 364))

            if anomaly_type == "duplicate":
                amount = 999999.0
                desc = "重複疑い仕訳"
            elif anomaly_type == "round_number":
                amount = random.choice([1000000, 5000000, 10000000, 50000000])
                desc = "端数なし大口仕訳"
            elif anomaly_type == "weekend":
                while date.weekday() < 5:
                    date += timedelta(days=1)
                amount = round(random.lognormvariate(12, 1), 0)
                desc = "休日計上仕訳"
            elif anomaly_type == "large":
                amount = round(random.uniform(100_000_000, 1_000_000_000), 0)
                desc = "異常大口仕訳"
            else:
                amount = round(random.lognormvariate(10, 2), 0)
                desc = "逆仕訳（取消）"

            code = random.choice(list(account_codes.keys()))
            entry = {
                "id": f"JE-{entry_id:06d}",
                "company_id": company["id"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": code,
                "account_name": account_codes[code],
                "debit": amount,
                "credit": 0,
                "description": desc,
                "posted_by": random.choice(["user_a", "user_x", "unknown"]),
                "is_anomaly": True,
                "anomaly_type": anomaly_type,
            }
            entries.append(entry)
            entry_id += 1

    return entries


def save_data(
    companies: list, subsidiaries: list, statements: list, journals: list
) -> None:
    """データをCSV/JSONで保存."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    with open(OUTPUT_DIR / "companies.json", "w", encoding="utf-8") as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DIR / "subsidiaries.json", "w", encoding="utf-8") as f:
        json.dump(subsidiaries, f, ensure_ascii=False, indent=2)

    # CSV
    def write_csv(path: Path, data: list[dict]) -> None:
        if not data:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    write_csv(OUTPUT_DIR / "financial_statements.csv", statements)
    write_csv(OUTPUT_DIR / "journal_entries.csv", journals)

    # サマリー
    n_anomalies = sum(1 for j in journals if j.get("is_anomaly"))
    summary = {
        "generated_at": datetime.now().isoformat(),
        "companies": len(companies),
        "subsidiaries": len(subsidiaries),
        "financial_statements": len(statements),
        "journal_entries": len(journals),
        "anomaly_entries": n_anomalies,
        "anomaly_rate": f"{n_anomalies / len(journals) * 100:.1f}%",
    }
    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"デモデータ生成完了:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"出力先: {OUTPUT_DIR}")


def main() -> None:
    """メイン実行."""
    print("デモデータ生成を開始します...")
    companies = generate_companies(50)
    subsidiaries = generate_subsidiaries(companies, avg_per_company=4)
    statements = generate_financial_statements(companies, quarters=8)
    journals = generate_journal_entries(companies, n_per_company=100)
    save_data(companies, subsidiaries, statements, journals)


if __name__ == "__main__":
    main()
