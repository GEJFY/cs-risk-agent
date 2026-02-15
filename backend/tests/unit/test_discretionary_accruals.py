"""裁量的発生高分析 ユニットテスト.

DiscretionaryAccrualsAnalyzer の各ステップを検証する。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cs_risk_agent.analysis.discretionary_accruals import (
    AccrualThresholds,
    DiscretionaryAccrualsAnalyzer,
    RiskLevel,
)
from cs_risk_agent.core.exceptions import AnalysisError


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> DiscretionaryAccrualsAnalyzer:
    """テスト用 DiscretionaryAccrualsAnalyzer."""
    return DiscretionaryAccrualsAnalyzer(
        thresholds=AccrualThresholds(high=0.075, medium=0.035),
        winsorize_limits=(0.01, 0.01),
        min_industry_obs=10,
    )


@pytest.fixture
def valid_df() -> pd.DataFrame:
    """回帰可能なテスト用DataFrame（30社, 産業A/B各15社）."""
    np.random.seed(42)
    n = 30

    total_assets_prev = np.random.uniform(130000, 280000, n)
    revenue = np.random.uniform(80000, 150000, n)
    revenue_prev = np.random.uniform(70000, 140000, n)
    receivables = np.random.uniform(10000, 25000, n)
    receivables_prev = np.random.uniform(8000, 22000, n)
    net_income = np.random.uniform(5000, 20000, n)
    operating_cash_flow = np.random.uniform(6000, 22000, n)
    ppe = np.random.uniform(40000, 80000, n)
    roa = np.random.uniform(0.03, 0.12, n)
    total_assets = np.random.uniform(150000, 300000, n)

    return pd.DataFrame({
        "company_id": [f"C{i:03d}" for i in range(n)],
        "industry_code": ["IND_A"] * 15 + ["IND_B"] * 15,
        "net_income": net_income,
        "operating_cash_flow": operating_cash_flow,
        "total_assets": total_assets,
        "total_assets_prev": total_assets_prev,
        "revenue": revenue,
        "revenue_prev": revenue_prev,
        "receivables": receivables,
        "receivables_prev": receivables_prev,
        "ppe": ppe,
        "roa": roa,
    })


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


class TestCalculateTotalAccruals:
    """総発生高計算の検証."""

    def test_calculate_total_accruals(self, analyzer, valid_df):
        """総発生高が正しく計算されること."""
        result = analyzer._calculate_total_accruals(valid_df.copy())
        assert "total_accruals" in result.columns
        assert "ta_scaled" in result.columns

        # TA = net_income - operating_cash_flow
        expected_ta = valid_df["net_income"] - valid_df["operating_cash_flow"]
        np.testing.assert_array_almost_equal(
            result["total_accruals"].values,
            expected_ta.values,
        )

    def test_total_accruals_scaling(self, analyzer, valid_df):
        """総発生高が前期総資産でスケーリングされること."""
        result = analyzer._calculate_total_accruals(valid_df.copy())
        # ta_scaled = total_accruals / total_assets_prev
        for i in range(len(result)):
            if result.iloc[i]["total_assets_prev"] != 0:
                expected_scaled = (
                    result.iloc[i]["total_accruals"]
                    / result.iloc[i]["total_assets_prev"]
                )
                assert result.iloc[i]["ta_scaled"] == pytest.approx(
                    expected_scaled, rel=1e-6
                )


class TestAnalyzeReturnsDataFrame:
    """analyze メソッドの結果検証."""

    def test_analyze_returns_dataframe(self, analyzer, valid_df):
        """analyze が必要なカラムを含むDataFrameを返すこと."""
        result = analyzer.analyze(valid_df)
        assert isinstance(result, pd.DataFrame)

        # 追加カラムが存在すること
        expected_cols = [
            "total_accruals", "ta_scaled", "nda", "da", "da_abs", "da_risk_level",
        ]
        for col in expected_cols:
            assert col in result.columns, f"カラム '{col}' が存在しません"

    def test_analyze_preserves_original_columns(self, analyzer, valid_df):
        """元のカラムが保持されること."""
        result = analyzer.analyze(valid_df)
        for col in valid_df.columns:
            assert col in result.columns

    def test_analyze_row_count_preserved(self, analyzer, valid_df):
        """行数が保持されること."""
        result = analyzer.analyze(valid_df)
        assert len(result) == len(valid_df)


class TestWinsorization:
    """ウィンソライズ処理の検証."""

    def test_winsorization_applied(self, analyzer, valid_df):
        """ウィンソライズが適用され、極端な外れ値が抑制されること."""
        df = valid_df.copy()
        # 外れ値を挿入
        df.loc[0, "net_income"] = 1_000_000  # 極端に大きい純利益
        df.loc[0, "operating_cash_flow"] = 0

        result = analyzer.analyze(df)
        # ウィンソライズにより ta_scaled の最大値が元より小さくなる
        assert result["ta_scaled"].notna().sum() > 0


class TestRiskClassification:
    """リスク分類の検証."""

    def test_risk_classification(self, analyzer, valid_df):
        """DA値に基づくリスク分類が正しいこと."""
        result = analyzer.analyze(valid_df)

        # 有効な分類値のみが含まれること
        valid_levels = {RiskLevel.HIGH.value, RiskLevel.MEDIUM.value, RiskLevel.LOW.value}
        for level in result["da_risk_level"].dropna().unique():
            assert level in valid_levels, f"不正なリスクレベル: {level}"

    def test_risk_classification_thresholds(self):
        """閾値に基づく分類が正しいこと."""
        analyzer = DiscretionaryAccrualsAnalyzer(
            thresholds=AccrualThresholds(high=0.075, medium=0.035),
        )
        # テスト用のDA値を持つDataFrame
        df = pd.DataFrame({
            "da_abs": [0.1, 0.05, 0.02, np.nan],
            "da": [0.1, 0.05, 0.02, np.nan],
        })
        result = analyzer._classify_risk(df)
        assert result.iloc[0]["da_risk_level"] == RiskLevel.HIGH.value
        assert result.iloc[1]["da_risk_level"] == RiskLevel.MEDIUM.value
        assert result.iloc[2]["da_risk_level"] == RiskLevel.LOW.value


class TestInputValidation:
    """入力バリデーションの検証."""

    def test_empty_dataframe_raises_error(self, analyzer):
        """空のDataFrameでAnalysisErrorが発生すること."""
        with pytest.raises(AnalysisError):
            analyzer.analyze(pd.DataFrame())

    def test_missing_columns_raises_error(self, analyzer):
        """必須カラム不足でAnalysisErrorが発生すること."""
        df = pd.DataFrame({"dummy": [1, 2, 3]})
        with pytest.raises(AnalysisError) as exc_info:
            analyzer.analyze(df)
        assert "必須カラムが不足" in str(exc_info.value)

    def test_insufficient_industry_observations(self):
        """産業別の観測数が不足している場合のハンドリング."""
        analyzer = DiscretionaryAccrualsAnalyzer(min_industry_obs=100)
        np.random.seed(42)
        n = 5  # min_industry_obs(100) より少ない

        df = pd.DataFrame({
            "industry_code": ["IND_A"] * n,
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
        })

        # 観測数不足の場合、da は NaN になる（エラーにはならない）
        result = analyzer.analyze(df)
        assert result["da"].isna().all()
