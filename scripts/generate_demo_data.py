"""デモデータ生成スクリプト - 東洋重工グループ.

架空のグローバルコングロマリット「東洋重工グループ」を想定した
リアリスティックなデモデータを生成する。

シナリオ:
  - 親会社: 東洋重工業株式会社（東証プライム・総合重工メーカー）
  - 連結子会社: 15社（日本5, 米国1, 欧州2, 中国2, 東南アジア3, インド1, 英国1）
  - 意図的に埋め込まれたリスクシナリオ:
    1. 中国子会社の架空売上疑い（売掛金急増 + 営業CF異常）
    2. 国内リース子会社の債務超過懸念（高レバレッジ + CF赤字）
    3. インドネシア子会社の在庫滞留（在庫回転率悪化）
    4. 米国子会社のベンフォード逸脱（仕訳不正パターン）
    5. ドイツ子会社の利益率低下（販管費急増）
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

# 再現性確保
random.seed(2026)
np.random.seed(2026)

OUTPUT_DIR = Path(__file__).parent.parent / "demo_data"

# =============================================================================
# 親会社定義
# =============================================================================

PARENT_COMPANY = {
    "id": "COM-0001",
    "edinet_code": "E02345",
    "securities_code": "7011",
    "name": "東洋重工業株式会社",
    "name_en": "Toyo Heavy Industries, Ltd.",
    "industry_code": "3300",
    "industry_name": "輸送用機器",
    "fiscal_year_end": 3,
    "is_listed": True,
    "country": "JPN",
    "segment": "持株",
    "description": "総合重工メーカー。エネルギー、航空宇宙、産業機械、自動車部品の4事業を展開。",
}

# =============================================================================
# 連結子会社定義（15社） - リスクレベルとシナリオ付き
# =============================================================================

SUBSIDIARIES: list[dict[str, Any]] = [
    # --- 日本 (5社) ---
    {
        "id": "SUB-0001",
        "name": "東洋エネルギーシステム株式会社",
        "name_en": "Toyo Energy Systems Co., Ltd.",
        "country": "JPN",
        "segment": "エネルギー",
        "ownership_ratio": 1.00,
        "risk_profile": "low",
        "revenue_base": 85_000,  # 百万円
        "asset_base": 180_000,
        "description": "火力・原子力プラント向け機器製造。安定した事業基盤。",
    },
    {
        "id": "SUB-0002",
        "name": "東洋航空宇宙株式会社",
        "name_en": "Toyo Aerospace Corporation",
        "country": "JPN",
        "segment": "航空宇宙",
        "ownership_ratio": 1.00,
        "risk_profile": "low",
        "revenue_base": 62_000,
        "asset_base": 95_000,
        "description": "航空機エンジン部品・防衛関連機器。長期契約が中心。",
    },
    {
        "id": "SUB-0003",
        "name": "東洋建機リース株式会社",
        "name_en": "Toyo Construction Machinery Leasing Co., Ltd.",
        "country": "JPN",
        "segment": "産業機械",
        "ownership_ratio": 0.80,
        "risk_profile": "critical",  # ★ 債務超過懸念
        "revenue_base": 12_000,
        "asset_base": 45_000,
        "description": "建設機械リース。コロナ後の需要回復遅れで収益悪化が顕著。",
    },
    {
        "id": "SUB-0004",
        "name": "東洋精密電子株式会社",
        "name_en": "Toyo Precision Electronics Co., Ltd.",
        "country": "JPN",
        "segment": "自動車部品",
        "ownership_ratio": 0.75,
        "risk_profile": "low",
        "revenue_base": 38_000,
        "asset_base": 52_000,
        "description": "車載半導体・センサー製造。EV需要で成長中。",
    },
    {
        "id": "SUB-0005",
        "name": "東洋情報システム株式会社",
        "name_en": "Toyo Information Systems Co., Ltd.",
        "country": "JPN",
        "segment": "管理",
        "ownership_ratio": 1.00,
        "risk_profile": "low",
        "revenue_base": 8_500,
        "asset_base": 12_000,
        "description": "グループIT統括。基幹システム・セキュリティ運用。",
    },
    # --- 中国 (2社) ---
    {
        "id": "SUB-0006",
        "name": "东洋精密机械（上海）有限公司",
        "name_en": "Toyo Precision Machinery (Shanghai) Co., Ltd.",
        "country": "CHN",
        "segment": "産業機械",
        "ownership_ratio": 0.70,
        "risk_profile": "critical",  # ★ 架空売上疑い
        "revenue_base": 28_000,
        "asset_base": 42_000,
        "description": "中国市場向け産業機械製造・販売。急成長を主張するも売掛金が異常増加。",
    },
    {
        "id": "SUB-0007",
        "name": "东洋新能源科技（深圳）有限公司",
        "name_en": "Toyo New Energy Technology (Shenzhen) Co., Ltd.",
        "country": "CHN",
        "segment": "エネルギー",
        "ownership_ratio": 0.65,
        "risk_profile": "medium",
        "revenue_base": 15_000,
        "asset_base": 25_000,
        "description": "太陽光パネル関連部品。中国市場の競争激化で利益率低下。",
    },
    # --- 米国 (1社) ---
    {
        "id": "SUB-0008",
        "name": "Toyo Power Systems Inc.",
        "name_en": "Toyo Power Systems Inc.",
        "country": "USA",
        "segment": "エネルギー",
        "ownership_ratio": 1.00,
        "risk_profile": "high",  # ★ ベンフォード逸脱
        "revenue_base": 52_000,
        "asset_base": 78_000,
        "description": "北米向けガスタービン製造・保守。仕訳金額に不自然なパターン。",
    },
    # --- 欧州 (2社) ---
    {
        "id": "SUB-0009",
        "name": "Toyo Automotive GmbH",
        "name_en": "Toyo Automotive GmbH",
        "country": "DEU",
        "segment": "自動車部品",
        "ownership_ratio": 0.90,
        "risk_profile": "high",  # ★ 販管費急増
        "revenue_base": 35_000,
        "asset_base": 48_000,
        "description": "欧州自動車OEM向け部品。EV転換コストで販管費が急増。",
    },
    {
        "id": "SUB-0010",
        "name": "Toyo Defence & Aerospace Ltd.",
        "name_en": "Toyo Defence & Aerospace Ltd.",
        "country": "GBR",
        "segment": "航空宇宙",
        "ownership_ratio": 0.51,
        "risk_profile": "medium",
        "revenue_base": 22_000,
        "asset_base": 35_000,
        "description": "英国防衛・航空部品。ブレグジット後のサプライチェーン再編中。",
    },
    # --- 東南アジア (3社) ---
    {
        "id": "SUB-0011",
        "name": "PT Toyo Manufacturing Indonesia",
        "name_en": "PT Toyo Manufacturing Indonesia",
        "country": "IDN",
        "segment": "産業機械",
        "ownership_ratio": 0.85,
        "risk_profile": "high",  # ★ 在庫滞留
        "revenue_base": 18_000,
        "asset_base": 30_000,
        "description": "インドネシア向け産業機械組立。為替影響と需要減で在庫が急増。",
    },
    {
        "id": "SUB-0012",
        "name": "Toyo Chemical Thailand Co., Ltd.",
        "name_en": "Toyo Chemical Thailand Co., Ltd.",
        "country": "THA",
        "segment": "エネルギー",
        "ownership_ratio": 0.75,
        "risk_profile": "low",
        "revenue_base": 9_500,
        "asset_base": 16_000,
        "description": "タイ拠点の化学品製造。安定した東南アジア供給拠点。",
    },
    {
        "id": "SUB-0013",
        "name": "Toyo Vietnam Engineering Co., Ltd.",
        "name_en": "Toyo Vietnam Engineering Co., Ltd.",
        "country": "VNM",
        "segment": "産業機械",
        "ownership_ratio": 0.80,
        "risk_profile": "low",
        "revenue_base": 6_000,
        "asset_base": 10_000,
        "description": "ベトナム製造拠点。低コスト生産ハブとして拡大中。",
    },
    # --- インド (1社) ---
    {
        "id": "SUB-0014",
        "name": "Toyo Semiconductor India Pvt. Ltd.",
        "name_en": "Toyo Semiconductor India Pvt. Ltd.",
        "country": "IND",
        "segment": "自動車部品",
        "ownership_ratio": 0.60,
        "risk_profile": "medium",
        "revenue_base": 11_000,
        "asset_base": 18_000,
        "description": "インド市場向け車載半導体。成長市場だが品質管理課題あり。",
    },
    # --- シンガポール (1社) ---
    {
        "id": "SUB-0015",
        "name": "Toyo Asia Pacific Holdings Pte. Ltd.",
        "name_en": "Toyo Asia Pacific Holdings Pte. Ltd.",
        "country": "SGP",
        "segment": "持株",
        "ownership_ratio": 1.00,
        "risk_profile": "low",
        "revenue_base": 2_000,
        "asset_base": 85_000,
        "description": "アジア太平洋地域統括会社。投資持株機能。",
    },
]

# =============================================================================
# セグメント別 KPI 基準値
# =============================================================================

SEGMENT_PROFILES = {
    "エネルギー": {"margin": 0.12, "receivable_days": 75, "inventory_days": 40, "leverage": 0.50},
    "航空宇宙": {"margin": 0.15, "receivable_days": 90, "inventory_days": 60, "leverage": 0.40},
    "産業機械": {"margin": 0.08, "receivable_days": 65, "inventory_days": 50, "leverage": 0.55},
    "自動車部品": {"margin": 0.10, "receivable_days": 55, "inventory_days": 35, "leverage": 0.45},
    "管理": {"margin": 0.18, "receivable_days": 45, "inventory_days": 10, "leverage": 0.30},
    "持株": {"margin": 0.05, "receivable_days": 30, "inventory_days": 5, "leverage": 0.35},
}

# =============================================================================
# 勘定科目マスタ
# =============================================================================

ACCOUNT_CODES = {
    "1100": "現金及び預金",
    "1200": "売掛金",
    "1300": "棚卸資産",
    "1400": "前払費用",
    "1500": "その他流動資産",
    "2100": "有形固定資産",
    "2200": "無形固定資産",
    "2300": "投資有価証券",
    "3100": "買掛金",
    "3200": "短期借入金",
    "3300": "未払費用",
    "3400": "長期借入金",
    "3500": "退職給付引当金",
    "4100": "売上高",
    "4200": "売上原価",
    "5100": "販売費",
    "5200": "一般管理費",
    "6100": "営業外収益",
    "6200": "営業外費用",
    "7100": "特別利益",
    "7200": "特別損失",
}


# =============================================================================
# 財務データ生成
# =============================================================================


def _seasonal_factor(quarter: int) -> float:
    """四半期の季節性係数（Q3が高め、Q1が低め）."""
    factors = {1: 0.92, 2: 0.98, 3: 1.08, 4: 1.02}
    return factors.get(quarter, 1.0)


def _generate_entity_financials(
    entity: dict[str, Any],
    quarters: int = 8,
) -> list[dict[str, Any]]:
    """1エンティティ分の四半期財務データを生成."""
    statements = []
    profile = SEGMENT_PROFILES.get(entity["segment"], SEGMENT_PROFILES["産業機械"])
    risk = entity.get("risk_profile", "low")

    base_revenue = entity["revenue_base"]
    base_assets = entity["asset_base"]

    # リスクプロファイルに応じたパラメータ
    if risk == "critical" and entity["id"] == "SUB-0006":
        # 中国子会社: 売上急成長（見かけ上）、売掛金異常膨張
        growth_rate = 0.25  # 年25%成長（不自然に高い）
        receivable_growth_premium = 0.40  # 売掛金は売上以上に増加
        ocf_penalty = -0.15  # 営業CF はマイナス傾向
    elif risk == "critical" and entity["id"] == "SUB-0003":
        # 建機リース: 売上減少、債務増加
        growth_rate = -0.12
        receivable_growth_premium = 0.0
        ocf_penalty = -0.20
    elif risk == "high" and entity["id"] == "SUB-0011":
        # インドネシア: 在庫滞留
        growth_rate = -0.05
        receivable_growth_premium = 0.0
        ocf_penalty = -0.05
    elif risk == "high" and entity["id"] == "SUB-0009":
        # ドイツ: 販管費急増
        growth_rate = 0.02
        receivable_growth_premium = 0.0
        ocf_penalty = -0.03
    else:
        growth_rate = random.uniform(0.02, 0.08)
        receivable_growth_premium = 0.0
        ocf_penalty = 0.0

    for q_idx in range(quarters):
        year = 2025 - (q_idx // 4)
        quarter = 4 - (q_idx % 4)
        seasonal = _seasonal_factor(quarter)
        time_factor = (1 + growth_rate / 4) ** (quarters - q_idx)

        # 売上
        revenue = base_revenue / 4 * time_factor * seasonal
        noise = random.uniform(0.95, 1.05)
        revenue *= noise

        # 売上原価
        cogs_ratio = random.uniform(0.60, 0.75) if risk != "high" else random.uniform(0.65, 0.80)
        cogs = revenue * cogs_ratio

        # 販管費（ドイツ子会社は急増パターン）
        if entity["id"] == "SUB-0009":
            sga_ratio = 0.15 + 0.03 * (quarters - q_idx) / quarters  # 時間とともに増加
        else:
            sga_ratio = profile["margin"] + random.uniform(0.05, 0.12)
        sga = revenue * sga_ratio

        operating_income = revenue - cogs - sga
        net_income = operating_income * random.uniform(0.65, 0.85)

        # 営業キャッシュフロー
        base_ocf = net_income + revenue * random.uniform(0.03, 0.08)
        operating_cf = base_ocf * (1 + ocf_penalty)
        if entity["id"] == "SUB-0003" and q_idx < 4:
            operating_cf = -abs(operating_cf) * random.uniform(0.5, 1.5)  # 直近は赤字
        if entity["id"] == "SUB-0006" and q_idx < 4:
            operating_cf = net_income * -0.3  # 利益が出ているのにCF赤字

        # 資産
        total_assets = base_assets * (1 + growth_rate * 0.3 / 4) ** (quarters - q_idx) * noise
        current_assets = total_assets * random.uniform(0.30, 0.50)
        ppe = total_assets * random.uniform(0.25, 0.40)

        # 売掛金（中国子会社は急増）
        receivable_days = profile["receivable_days"]
        if entity["id"] == "SUB-0006":
            receivable_days = 75 + 30 * (quarters - q_idx) / quarters  # 回収日数が悪化
        receivables = revenue * receivable_days / 90 * (1 + receivable_growth_premium * (quarters - q_idx) / quarters)

        # 在庫（インドネシア子会社は滞留）
        inventory_days = profile["inventory_days"]
        if entity["id"] == "SUB-0011":
            inventory_days = 50 + 40 * (quarters - q_idx) / quarters  # 在庫回転悪化
        inventory = cogs * inventory_days / 90

        depreciation = ppe * random.uniform(0.05, 0.10)

        # 負債
        leverage = profile["leverage"]
        if entity["id"] == "SUB-0003":
            leverage = 0.75 + 0.05 * (quarters - q_idx) / quarters  # レバレッジ上昇
        total_liabilities = total_assets * leverage * random.uniform(0.95, 1.05)
        if entity["id"] == "SUB-0003":
            total_liabilities = total_assets * 1.05  # 債務超過

        total_equity = total_assets - total_liabilities
        current_liabilities = total_liabilities * random.uniform(0.35, 0.55)
        long_term_debt = total_liabilities * random.uniform(0.25, 0.45)
        retained_earnings = max(total_equity * random.uniform(0.4, 0.8), -abs(total_equity) * 0.5)
        ebit = operating_income * 1.05

        statements.append({
            "entity_id": entity["id"],
            "entity_name": entity["name"],
            "entity_type": "subsidiary" if entity["id"].startswith("SUB") else "parent",
            "fiscal_year": year,
            "fiscal_quarter": quarter,
            "revenue": round(revenue, 1),
            "revenue_prior": round(revenue / time_factor * (1 + growth_rate / 4) ** max(0, quarters - q_idx - 4), 1),
            "cogs": round(cogs, 1),
            "cogs_prior": round(cogs * 0.95, 1),
            "sga": round(sga, 1),
            "sga_prior": round(sga * 0.90, 1),
            "operating_income": round(operating_income, 1),
            "net_income": round(net_income, 1),
            "operating_cash_flow": round(operating_cf, 1),
            "total_assets": round(total_assets, 1),
            "total_assets_prior": round(total_assets * 0.93, 1),
            "current_assets": round(current_assets, 1),
            "current_assets_prior": round(current_assets * 0.95, 1),
            "ppe": round(ppe, 1),
            "ppe_prior": round(ppe * 0.95, 1),
            "receivables": round(receivables, 1),
            "receivables_prior": round(receivables * 0.70, 1),
            "inventory": round(inventory, 1),
            "inventory_prior": round(inventory * 0.80, 1),
            "depreciation": round(depreciation, 1),
            "depreciation_prior": round(depreciation * 0.95, 1),
            "total_liabilities": round(total_liabilities, 1),
            "total_equity": round(total_equity, 1),
            "current_liabilities": round(current_liabilities, 1),
            "current_liabilities_prior": round(current_liabilities * 0.92, 1),
            "long_term_debt": round(long_term_debt, 1),
            "long_term_debt_prior": round(long_term_debt * 0.90, 1),
            "retained_earnings": round(retained_earnings, 1),
            "ebit": round(ebit, 1),
        })

    return statements


# =============================================================================
# 仕訳データ生成
# =============================================================================


def _generate_entity_journals(
    entity: dict[str, Any],
    n_normal: int = 120,
) -> list[dict[str, Any]]:
    """1エンティティ分の仕訳データを生成（異常データ含む）."""
    entries: list[dict[str, Any]] = []
    risk = entity.get("risk_profile", "low")
    entry_id_base = int(entity["id"].split("-")[1]) * 10000

    users = ["tanaka_m", "suzuki_k", "yamada_t", "watanabe_a", "system_batch"]

    # --- 通常仕訳 ---
    for j in range(n_normal):
        code = random.choice(list(ACCOUNT_CODES.keys()))
        # ベンフォードに従う金額（対数正規分布）
        amount = round(np.random.lognormal(10, 2), 0)
        is_debit = random.random() > 0.5
        date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))

        entries.append({
            "id": f"JE-{entry_id_base + j:06d}",
            "entity_id": entity["id"],
            "entity_name": entity["name"],
            "date": date.strftime("%Y-%m-%d"),
            "account_code": code,
            "account_name": ACCOUNT_CODES[code],
            "debit": float(amount) if is_debit else 0.0,
            "credit": 0.0 if is_debit else float(amount),
            "description": f"通常仕訳_{ACCOUNT_CODES[code]}_{j+1}",
            "posted_by": random.choice(users),
            "is_anomaly": False,
            "anomaly_type": None,
        })

    # --- 異常仕訳の混入 ---
    anomaly_entries = []

    if risk == "critical" and entity["id"] == "SUB-0006":
        # 中国子会社: 架空売上パターン（期末集中・丸い数字・同額連発）
        for k in range(15):
            # Q4に集中する売上計上
            date = datetime(2025, 3, 1) + timedelta(days=random.randint(0, 30))
            amount = random.choice([5_000_000, 10_000_000, 15_000_000, 20_000_000, 50_000_000])
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": "4100",
                "account_name": "売上高",
                "debit": 0.0,
                "credit": float(amount),
                "description": f"新規大口顧客向け機器販売_{k+1}",
                "posted_by": "chen_w",  # 特定人物に集中
                "is_anomaly": True,
                "anomaly_type": "round_number_period_end",
            })

    elif risk == "critical" and entity["id"] == "SUB-0003":
        # 建機リース: 引当金操作・逆仕訳パターン
        for k in range(10):
            date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))
            amount = random.uniform(50_000_000, 200_000_000)
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": random.choice(["3500", "7200"]),
                "account_name": random.choice(["退職給付引当金", "特別損失"]),
                "debit": round(amount, 0),
                "credit": 0.0,
                "description": "引当金戻入処理" if random.random() > 0.5 else "前期計上取消",
                "posted_by": "yamamoto_h",
                "is_anomaly": True,
                "anomaly_type": "reversal_provision",
            })

    elif risk == "high" and entity["id"] == "SUB-0008":
        # 米国: ベンフォード逸脱パターン（均一な第1桁分布）
        for k in range(40):
            # 意図的に第1桁を均等に（ベンフォード逸脱）
            first_digit = (k % 9) + 1
            remaining = random.randint(1000, 9999)
            amount = float(first_digit * 10000 + remaining)
            date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": random.choice(["5100", "5200", "6200"]),
                "account_name": random.choice(["販売費", "一般管理費", "営業外費用"]),
                "debit": amount,
                "credit": 0.0,
                "description": f"Consulting fee payment #{k+1}",
                "posted_by": "johnson_r",
                "is_anomaly": True,
                "anomaly_type": "benford_violation",
            })

    elif risk == "high" and entity["id"] == "SUB-0011":
        # インドネシア: 在庫水増し（大口仕入れ + 休日計上）
        for k in range(12):
            date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))
            while date.weekday() < 5:
                date += timedelta(days=1)
            amount = random.choice([100_000_000, 200_000_000, 300_000_000])
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": "1300",
                "account_name": "棚卸資産",
                "debit": float(amount),
                "credit": 0.0,
                "description": f"原材料大量仕入_{k+1}",
                "posted_by": "widodo_s",
                "is_anomaly": True,
                "anomaly_type": "weekend_large_inventory",
            })

    elif risk == "high" and entity["id"] == "SUB-0009":
        # ドイツ: 不透明なコンサルティング費用
        for k in range(8):
            date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))
            amount = random.choice([5_000_000, 8_000_000, 10_000_000])
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": "5200",
                "account_name": "一般管理費",
                "debit": float(amount),
                "credit": 0.0,
                "description": f"EV転換コンサルティング費用 Phase {k+1}",
                "posted_by": "mueller_k",
                "is_anomaly": True,
                "anomaly_type": "suspicious_consulting",
            })

    else:
        # LOW/MEDIUM: 少数の一般的な異常
        n_anomalies = random.randint(2, 5)
        for k in range(n_anomalies):
            date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 364))
            anomaly_type = random.choice(["duplicate", "round_number", "large"])
            if anomaly_type == "duplicate":
                amount = 999_999.0
                desc = "重複疑い仕訳"
            elif anomaly_type == "round_number":
                amount = float(random.choice([1_000_000, 5_000_000, 10_000_000]))
                desc = "端数なし大口仕訳"
            else:
                amount = round(random.uniform(50_000_000, 300_000_000), 0)
                desc = "異常大口仕訳"

            code = random.choice(list(ACCOUNT_CODES.keys()))
            anomaly_entries.append({
                "id": f"JE-{entry_id_base + n_normal + k:06d}",
                "entity_id": entity["id"],
                "entity_name": entity["name"],
                "date": date.strftime("%Y-%m-%d"),
                "account_code": code,
                "account_name": ACCOUNT_CODES[code],
                "debit": amount,
                "credit": 0.0,
                "description": desc,
                "posted_by": random.choice(users),
                "is_anomaly": True,
                "anomaly_type": anomaly_type,
            })

    entries.extend(anomaly_entries)
    return entries


# =============================================================================
# リスクスコア生成
# =============================================================================


def _calculate_risk_scores(entity: dict[str, Any]) -> dict[str, Any]:
    """エンティティのリスクスコアを計算."""
    risk = entity.get("risk_profile", "low")

    # リスクプロファイルに基づくベーススコア
    score_ranges = {
        "critical": (75, 95),
        "high": (55, 75),
        "medium": (35, 55),
        "low": (10, 35),
    }
    low, high = score_ranges.get(risk, (10, 35))
    total_score = round(random.uniform(low, high), 1)

    # 各コンポーネントスコア
    if risk == "critical" and entity["id"] == "SUB-0006":
        da_score = round(random.uniform(70, 90), 1)
        fraud_score = round(random.uniform(80, 95), 1)
        rule_score = round(random.uniform(75, 90), 1)
        benford_score = round(random.uniform(60, 80), 1)
        risk_factors = [
            "売掛金対売上高比率が前年比180%超",
            "営業キャッシュフローが純利益と逆相関",
            "期末月への売上集中率が異常（72%）",
            "特定担当者による仕訳集中",
            "売掛金回転日数が業界平均の2.5倍",
        ]
    elif risk == "critical" and entity["id"] == "SUB-0003":
        da_score = round(random.uniform(60, 80), 1)
        fraud_score = round(random.uniform(55, 75), 1)
        rule_score = round(random.uniform(80, 95), 1)
        benford_score = round(random.uniform(30, 50), 1)
        risk_factors = [
            "債務超過（自己資本比率 -5.2%）",
            "営業キャッシュフロー4四半期連続赤字",
            "長期借入金の急増（前年比+45%）",
            "引当金の不自然な戻入パターン",
            "継続企業の前提に関する注記の可能性",
        ]
    elif risk == "high" and entity["id"] == "SUB-0008":
        da_score = round(random.uniform(40, 55), 1)
        fraud_score = round(random.uniform(50, 70), 1)
        rule_score = round(random.uniform(45, 65), 1)
        benford_score = round(random.uniform(80, 95), 1)  # ベンフォード大幅逸脱
        risk_factors = [
            "仕訳金額のベンフォード適合度が「非適合」",
            "第1桁分布のMADが0.025（閾値: 0.015）",
            "費用仕訳の金額パターンに規則性",
            "特定担当者の仕訳にのみ逸脱が集中",
        ]
    elif risk == "high" and entity["id"] == "SUB-0009":
        da_score = round(random.uniform(50, 65), 1)
        fraud_score = round(random.uniform(40, 60), 1)
        rule_score = round(random.uniform(55, 70), 1)
        benford_score = round(random.uniform(35, 50), 1)
        risk_factors = [
            "販管費率が前年比+8.5pt（業界平均+2.1pt）",
            "コンサルティング費用が売上高の12%に達する",
            "EV転換名目の費用計上に具体的成果物が不明",
            "営業利益率が2年前の半分以下に低下",
        ]
    elif risk == "high" and entity["id"] == "SUB-0011":
        da_score = round(random.uniform(45, 60), 1)
        fraud_score = round(random.uniform(50, 65), 1)
        rule_score = round(random.uniform(55, 70), 1)
        benford_score = round(random.uniform(40, 55), 1)
        risk_factors = [
            "棚卸資産回転日数が前年比+85日",
            "休日計上の大口仕入仕訳が12件",
            "在庫評価損計上の可能性（推定: 15億円）",
            "為替差損の影響額が開示と不整合",
        ]
    elif risk == "medium":
        da_score = round(random.uniform(30, 50), 1)
        fraud_score = round(random.uniform(25, 45), 1)
        rule_score = round(random.uniform(35, 55), 1)
        benford_score = round(random.uniform(20, 40), 1)
        risk_factors = [
            "軽微な会計方針変更の影響",
            "関連当事者取引の開示不足",
        ]
    else:
        da_score = round(random.uniform(5, 25), 1)
        fraud_score = round(random.uniform(5, 20), 1)
        rule_score = round(random.uniform(10, 30), 1)
        benford_score = round(random.uniform(5, 20), 1)
        risk_factors = []

    risk_level = (
        "critical" if total_score >= 75
        else "high" if total_score >= 55
        else "medium" if total_score >= 35
        else "low"
    )

    return {
        "entity_id": entity["id"],
        "entity_name": entity["name"],
        "total_score": total_score,
        "risk_level": risk_level,
        "da_score": da_score,
        "fraud_score": fraud_score,
        "rule_score": rule_score,
        "benford_score": benford_score,
        "risk_factors": risk_factors,
        "analysis_date": "2025-12-15",
        "fiscal_year": 2025,
        "fiscal_quarter": 4,
    }


# =============================================================================
# アラート生成
# =============================================================================


def _generate_alerts() -> list[dict[str, Any]]:
    """リスクアラートを生成."""
    alerts = [
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0006",
            "entity_name": "东洋精密机械（上海）有限公司",
            "severity": "critical",
            "category": "売掛金異常",
            "title": "【緊急】売掛金が前年比233%増加 - 架空売上の疑い",
            "description": "上海子会社の売掛金残高が前年同期比233%増加。営業CFはマイナスであり、"
                           "売上の実在性に重大な疑義。期末月に売上の72%が集中し、"
                           "特定担当者(chen_w)による仕訳が85%を占める。",
            "created_at": "2025-12-15T14:30:00+09:00",
            "is_read": False,
            "recommended_action": "現地往査の実施、売掛先への残高確認、銀行明細との照合",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0003",
            "entity_name": "東洋建機リース株式会社",
            "severity": "critical",
            "category": "継続企業",
            "title": "【緊急】債務超過の兆候 - 継続企業の前提に疑義",
            "description": "建機リース子会社の自己資本比率が-5.2%に低下。"
                           "営業CFが4四半期連続赤字、長期借入金が前年比+45%。"
                           "引当金の不自然な戻入（12件）が確認された。",
            "created_at": "2025-12-15T15:00:00+09:00",
            "is_read": False,
            "recommended_action": "経営陣へのヒアリング、事業計画の妥当性検証、減損テスト実施",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0008",
            "entity_name": "Toyo Power Systems Inc.",
            "severity": "high",
            "category": "ベンフォード逸脱",
            "title": "仕訳金額のベンフォード分析で重大な逸脱を検出",
            "description": "米国子会社の費用仕訳（販売費・管理費・営業外費用）について"
                           "ベンフォード第1桁テストを実施した結果、MAD=0.025で「非適合」判定。"
                           "特にjohnson_r担当分の仕訳に規則的なパターンが認められる。",
            "created_at": "2025-12-14T10:15:00+09:00",
            "is_read": True,
            "recommended_action": "担当者ヒアリング、証憑の突合確認、類似パターンの他社横展開",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0011",
            "entity_name": "PT Toyo Manufacturing Indonesia",
            "severity": "high",
            "category": "在庫滞留",
            "title": "棚卸資産回転日数が業界平均の2.8倍に悪化",
            "description": "インドネシア子会社の棚卸資産回転日数が前年比+85日。"
                           "休日計上の大口仕入仕訳12件を検出。在庫評価損（推定15億円）の"
                           "計上漏れの可能性。",
            "created_at": "2025-12-13T16:45:00+09:00",
            "is_read": False,
            "recommended_action": "実地棚卸の前倒し実施、滞留在庫の個別評価、減損見積りの検証",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0009",
            "entity_name": "Toyo Automotive GmbH",
            "severity": "high",
            "category": "費用異常",
            "title": "コンサルティング費用が売上高比12%に急増",
            "description": "ドイツ子会社のEV転換コンサルティング費用が前年比300%増。"
                           "成果物の具体性が不明で、営業利益率は2年前の半分以下に低下。",
            "created_at": "2025-12-12T11:30:00+09:00",
            "is_read": True,
            "recommended_action": "コンサルティング契約書・成果物の閲覧、発注プロセスの監査",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0007",
            "entity_name": "东洋新能源科技（深圳）有限公司",
            "severity": "medium",
            "category": "利益率低下",
            "title": "営業利益率が3四半期連続で低下傾向",
            "description": "深圳子会社の営業利益率が8.2%→5.1%→3.8%と3四半期連続低下。"
                           "中国太陽光パネル市場の競争激化による価格下落が主因。",
            "created_at": "2025-12-10T09:00:00+09:00",
            "is_read": True,
            "recommended_action": "事業計画の見直し、コスト削減施策の検討",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0014",
            "entity_name": "Toyo Semiconductor India Pvt. Ltd.",
            "severity": "medium",
            "category": "品質管理",
            "title": "製品不良率が社内基準を超過",
            "description": "インド子会社の製品不良率が2.8%（社内基準: 1.5%）に上昇。"
                           "品質コスト増加による利益への影響を注視。",
            "created_at": "2025-12-08T14:20:00+09:00",
            "is_read": True,
            "recommended_action": "品質管理プロセスの監査、是正措置計画の確認",
        },
        {
            "id": f"ALT-{str(uuid4())[:8]}",
            "entity_id": "SUB-0010",
            "entity_name": "Toyo Defence & Aerospace Ltd.",
            "severity": "medium",
            "category": "サプライチェーン",
            "title": "主要部品の調達リードタイムが50%延長",
            "description": "英国子会社の主要部品調達リードタイムがブレグジット後の"
                           "関税・通関手続き影響で50%延長。納期遅延リスクあり。",
            "created_at": "2025-12-05T10:00:00+09:00",
            "is_read": True,
            "recommended_action": "代替調達先の確保、バッファ在庫の検討",
        },
    ]
    return alerts


# =============================================================================
# データ保存
# =============================================================================


def save_data(
    companies: list[dict],
    subsidiaries: list[dict],
    statements: list[dict],
    journals: list[dict],
    risk_scores: list[dict],
    alerts: list[dict],
) -> None:
    """全データをJSON/CSVで保存."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- JSON ---
    def write_json(filename: str, data: Any) -> None:
        with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    write_json("companies.json", companies)
    write_json("subsidiaries.json", subsidiaries)
    write_json("risk_scores.json", risk_scores)
    write_json("alerts.json", alerts)

    # --- CSV ---
    def write_csv(filename: str, data: list[dict]) -> None:
        if not data:
            return
        with open(OUTPUT_DIR / filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    write_csv("financial_statements.csv", statements)
    write_csv("journal_entries.csv", journals)

    # --- サマリー ---
    n_anomalies = sum(1 for j in journals if j.get("is_anomaly"))
    summary = {
        "generated_at": datetime.now().isoformat(),
        "scenario": "東洋重工グループ - グローバルコングロマリット連結子会社リスク分析",
        "parent_company": PARENT_COMPANY["name"],
        "total_entities": 1 + len(subsidiaries),
        "subsidiaries": len(subsidiaries),
        "countries": len(set(s["country"] for s in subsidiaries)),
        "segments": len(set(s["segment"] for s in subsidiaries)),
        "financial_statements": len(statements),
        "journal_entries": len(journals),
        "anomaly_entries": n_anomalies,
        "anomaly_rate": f"{n_anomalies / max(len(journals), 1) * 100:.1f}%",
        "risk_distribution": {
            "critical": sum(1 for s in subsidiaries if s.get("risk_profile") == "critical"),
            "high": sum(1 for s in subsidiaries if s.get("risk_profile") == "high"),
            "medium": sum(1 for s in subsidiaries if s.get("risk_profile") == "medium"),
            "low": sum(1 for s in subsidiaries if s.get("risk_profile") == "low"),
        },
        "alerts": len(alerts),
    }
    write_json("summary.json", summary)

    print("=" * 60)
    print("  東洋重工グループ デモデータ生成完了")
    print("=" * 60)
    for k, v in summary.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")
    print(f"\n  出力先: {OUTPUT_DIR}")
    print("=" * 60)


# =============================================================================
# メイン
# =============================================================================


def main() -> None:
    """メイン実行."""
    print("\n東洋重工グループ デモデータ生成を開始します...\n")

    # 1. 企業マスタ
    companies = [PARENT_COMPANY]

    # 2. 子会社
    subsidiaries = []
    for sub in SUBSIDIARIES:
        subsidiaries.append({
            "id": sub["id"],
            "parent_company_id": PARENT_COMPANY["id"],
            "name": sub["name"],
            "name_en": sub.get("name_en", ""),
            "country": sub["country"],
            "segment": sub["segment"],
            "ownership_ratio": sub["ownership_ratio"],
            "risk_profile": sub["risk_profile"],
            "is_active": True,
            "description": sub.get("description", ""),
        })

    # 3. 財務データ
    all_statements = []
    print("  財務データ生成中...")
    # 親会社
    all_statements.extend(_generate_entity_financials(PARENT_COMPANY | {"revenue_base": 420_000, "asset_base": 850_000, "risk_profile": "low"}, quarters=8))
    # 子会社
    for sub in SUBSIDIARIES:
        all_statements.extend(_generate_entity_financials(sub, quarters=8))

    # 4. 仕訳データ
    all_journals = []
    print("  仕訳データ生成中...")
    for sub in SUBSIDIARIES:
        n_normal = 120 if sub["risk_profile"] in ("critical", "high") else 80
        all_journals.extend(_generate_entity_journals(sub, n_normal=n_normal))

    # 5. リスクスコア
    print("  リスクスコア計算中...")
    risk_scores = []
    for sub in SUBSIDIARIES:
        risk_scores.append(_calculate_risk_scores(sub))

    # 6. アラート
    alerts = _generate_alerts()

    # 保存
    save_data(companies, subsidiaries, all_statements, all_journals, risk_scores, alerts)


if __name__ == "__main__":
    main()
