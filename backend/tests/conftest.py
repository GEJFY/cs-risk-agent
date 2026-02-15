"""テスト共通フィクスチャ.

全テストモジュールから共有されるフィクスチャ定義。
pytest-asyncio の auto モードにより、async テストは自動検出される。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# イベントループ設定
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop_policy():
    """セッション全体で使用するイベントループポリシー."""
    return asyncio.DefaultEventLoopPolicy()


# ---------------------------------------------------------------------------
# 財務データフィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_financial_data() -> dict:
    """サンプル財務データ（単一企業分）."""
    return {
        "revenue": 100000,
        "revenue_prior": 90000,
        "cogs": 60000,
        "cogs_prior": 55000,
        "sga": 15000,
        "sga_prior": 14000,
        "net_income": 12000,
        "operating_cash_flow": 15000,
        "total_assets": 200000,
        "total_assets_prior": 180000,
        "current_assets": 80000,
        "current_assets_prior": 70000,
        "ppe": 50000,
        "ppe_prior": 45000,
        "receivables": 15000,
        "receivables_prior": 12000,
        "inventory": 8000,
        "depreciation": 5000,
        "depreciation_prior": 4500,
        "total_liabilities": 100000,
        "total_equity": 100000,
        "current_liabilities": 40000,
        "current_liabilities_prior": 35000,
        "long_term_debt": 30000,
        "long_term_debt_prior": 28000,
        "retained_earnings": 60000,
        "ebit": 18000,
    }


@pytest.fixture
def sample_dataframe(sample_financial_data) -> pd.DataFrame:
    """サンプルDataFrame（1行）."""
    return pd.DataFrame([sample_financial_data])


@pytest.fixture
def multi_company_dataframe() -> pd.DataFrame:
    """複数企業のサンプルDataFrame（裁量的発生高分析用）.

    修正ジョーンズモデルの回帰に必要な最低数（10社以上）を含む。
    """
    np.random.seed(42)
    n = 30

    data = {
        "company_id": [f"C{i:03d}" for i in range(n)],
        "industry_code": ["IND_A"] * 15 + ["IND_B"] * 15,
        "net_income": np.random.uniform(5000, 20000, n),
        "operating_cash_flow": np.random.uniform(6000, 22000, n),
        "total_assets": np.random.uniform(150000, 300000, n),
        "total_assets_prev": np.random.uniform(130000, 280000, n),
        "revenue": np.random.uniform(80000, 150000, n),
        "revenue_prev": np.random.uniform(70000, 140000, n),
        "receivables": np.random.uniform(10000, 25000, n),
        "receivables_prev": np.random.uniform(8000, 22000, n),
        "ppe": np.random.uniform(40000, 80000, n),
        "roa": np.random.uniform(0.03, 0.12, n),
    }
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# AIプロバイダーフィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ai_provider():
    """モックAIプロバイダー."""
    from cs_risk_agent.ai.provider import AIResponse, TokenUsage

    provider = AsyncMock()
    provider.name = "mock"
    provider.is_available = True
    provider.complete.return_value = AIResponse(
        content="Mock response",
        model="mock-model",
        provider="mock",
        usage=TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        ),
    )
    return provider


@pytest.fixture
def mock_ai_provider_failing():
    """常にエラーを返すモックAIプロバイダー."""
    from cs_risk_agent.core.exceptions import ProviderError

    provider = AsyncMock()
    provider.name = "mock_fail"
    provider.is_available = True
    provider.complete.side_effect = ProviderError("mock_fail", "Service unavailable")
    return provider


# ---------------------------------------------------------------------------
# 仕訳データフィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def journal_entries_df() -> pd.DataFrame:
    """テスト用仕訳データ（対数正規分布）.

    ベンフォードの法則に近い分布を生成する。
    """
    np.random.seed(42)
    n = 1000
    amounts = np.random.lognormal(10, 2, n)
    return pd.DataFrame({
        "id": [f"JE-{i:04d}" for i in range(n)],
        "amount": amounts,
        "debit": amounts,
        "credit": np.zeros(n),
        "date": pd.date_range("2024-01-01", periods=n, freq="4h"),
    })


@pytest.fixture
def uniform_digits_df() -> pd.DataFrame:
    """一様分布の仕訳データ（ベンフォード非適合を期待）."""
    np.random.seed(123)
    n = 500
    # 第1桁が均等になるようなデータ
    first_digits = np.random.choice(range(1, 10), n)
    amounts = first_digits * 10 ** np.random.uniform(2, 5, n)
    return pd.DataFrame({
        "id": [f"UNI-{i:04d}" for i in range(n)],
        "amount": amounts,
        "debit": amounts,
        "credit": np.zeros(n),
    })


# ---------------------------------------------------------------------------
# Settings モックフィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """全テストでSettingsをモックし、外部依存を排除する.

    get_settings のキャッシュをクリアして毎テスト新規生成。
    """
    from cs_risk_agent.config import Settings, get_settings

    # lru_cache をクリア
    get_settings.cache_clear()

    # 環境変数を最低限設定
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_DEBUG", "true")

    yield

    # テスト後もキャッシュクリア
    get_settings.cache_clear()
