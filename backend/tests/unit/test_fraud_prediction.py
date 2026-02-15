"""不正予測モデル ユニットテスト.

FraudPredictor の Beneish M-Score、Altman Z-Score、
ルールベース予測ロジックを検証する。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cs_risk_agent.analysis.fraud_prediction import (
    BENEISH_REQUIRED_COLUMNS,
    FraudPredictionResult,
    FraudPredictor,
)
from cs_risk_agent.core.exceptions import AnalysisError


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def predictor() -> FraudPredictor:
    """テスト用 FraudPredictor（未学習状態）."""
    return FraudPredictor()


@pytest.fixture
def financial_df(sample_financial_data) -> pd.DataFrame:
    """テスト用財務DataFrame（sample_financial_data から生成）.

    Beneish/Altman 計算に必要な全カラムを含む。
    sample_financial_data のキー名をそのまま使う。
    """
    return pd.DataFrame([sample_financial_data])


# ---------------------------------------------------------------------------
# Beneish M-Score テスト
# ---------------------------------------------------------------------------


class TestCalculateBeneishFeatures:
    """Beneish M-Score 特徴量計算の検証."""

    def test_calculate_beneish_features(self, financial_df):
        """8つの Beneish 変数と m_score が正しく算出されること."""
        result = FraudPredictor.calculate_beneish_features(financial_df)

        # 8変数の存在チェック
        expected_vars = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA"]
        for var in expected_vars:
            assert var in result.columns, f"Beneish変数 '{var}' が存在しません"

        assert "m_score" in result.columns

    def test_beneish_dsri_calculation(self, financial_df):
        """DSRI が正しく計算されること."""
        result = FraudPredictor.calculate_beneish_features(financial_df)
        row = result.iloc[0]

        # DSRI = (receivables/revenue) / (receivables_prior/revenue_prior)
        expected_dsri = (15000 / 100000) / (12000 / 90000)
        assert row["DSRI"] == pytest.approx(expected_dsri, rel=1e-4)

    def test_beneish_sgi_calculation(self, financial_df):
        """SGI が正しく計算されること."""
        result = FraudPredictor.calculate_beneish_features(financial_df)
        row = result.iloc[0]

        # SGI = revenue / revenue_prior
        expected_sgi = 100000 / 90000
        assert row["SGI"] == pytest.approx(expected_sgi, rel=1e-4)

    def test_beneish_missing_columns_error(self):
        """必須カラム不足で AnalysisError が発生すること."""
        df = pd.DataFrame({"dummy": [1, 2, 3]})
        with pytest.raises(AnalysisError):
            FraudPredictor.calculate_beneish_features(df)

    def test_m_score_calculation(self, financial_df):
        """M-Score が係数に基づいて正しく算出されること."""
        result = FraudPredictor.calculate_beneish_features(financial_df)
        row = result.iloc[0]

        # M-Score = intercept + sum(coeff * variable)
        m_score = -4.84
        coefficients = {
            "DSRI": 0.920, "GMI": 0.528, "AQI": 0.404, "SGI": 0.892,
            "DEPI": 0.115, "SGAI": -0.172, "TATA": 4.679, "LVGI": -0.327,
        }
        for var, coeff in coefficients.items():
            m_score += coeff * row[var]

        assert row["m_score"] == pytest.approx(m_score, rel=1e-4)


# ---------------------------------------------------------------------------
# Altman Z-Score テスト
# ---------------------------------------------------------------------------


class TestCalculateAltmanZ:
    """Altman Z-Score 計算の検証."""

    def test_calculate_altman_z(self, financial_df):
        """Z-Score 構成変数と altman_z が正しく算出されること."""
        result = FraudPredictor.calculate_altman_z(financial_df)

        z_vars = ["z_wc_ta", "z_re_ta", "z_ebit_ta", "z_equity_debt", "z_rev_ta"]
        for var in z_vars:
            assert var in result.columns, f"Z-Score変数 '{var}' が存在しません"

        assert "altman_z" in result.columns

    def test_altman_z_wc_ta(self, financial_df):
        """Working Capital / Total Assets が正しいこと."""
        result = FraudPredictor.calculate_altman_z(financial_df)
        row = result.iloc[0]

        expected = (80000 - 40000) / 200000
        assert row["z_wc_ta"] == pytest.approx(expected, rel=1e-4)

    def test_altman_z_score_value(self, financial_df):
        """Z-Score の合計値が正しいこと."""
        result = FraudPredictor.calculate_altman_z(financial_df)
        row = result.iloc[0]

        z = (
            1.2 * row["z_wc_ta"]
            + 1.4 * row["z_re_ta"]
            + 3.3 * row["z_ebit_ta"]
            + 0.6 * row["z_equity_debt"]
            + 1.0 * row["z_rev_ta"]
        )
        assert row["altman_z"] == pytest.approx(z, rel=1e-4)

    def test_altman_missing_columns_error(self):
        """必須カラム不足で AnalysisError が発生すること."""
        df = pd.DataFrame({"dummy": [1, 2, 3]})
        with pytest.raises(AnalysisError):
            FraudPredictor.calculate_altman_z(df)


# ---------------------------------------------------------------------------
# ルールベース予測テスト
# ---------------------------------------------------------------------------


class TestPredictRuleBased:
    """ルールベース予測の検証."""

    def test_predict_rule_based(self, predictor, financial_df):
        """未学習モデルでルールベース予測が実行されること."""
        assert not predictor.is_trained
        results = predictor.predict(financial_df)

        assert len(results) == 1
        assert isinstance(results[0], FraudPredictionResult)
        assert 0 <= results[0].fraud_probability <= 1.0
        assert 0 <= results[0].risk_score <= 100
        assert results[0].risk_level in ("critical", "high", "medium", "low")

    def test_predict_empty_raises_error(self, predictor):
        """空DataFrameで AnalysisError が発生すること."""
        with pytest.raises(AnalysisError):
            predictor.predict(pd.DataFrame())

    def test_predict_risk_level_classification(self, predictor, financial_df):
        """リスクレベル分類が閾値に基づいていること."""
        results = predictor.predict(financial_df)
        result = results[0]

        if result.risk_score >= 80:
            assert result.risk_level == "critical"
        elif result.risk_score >= 60:
            assert result.risk_level == "high"
        elif result.risk_score >= 40:
            assert result.risk_level == "medium"
        else:
            assert result.risk_level == "low"


# ---------------------------------------------------------------------------
# inf/NaN ハンドリングテスト
# ---------------------------------------------------------------------------


class TestInfHandling:
    """inf/NaN 値のハンドリング検証."""

    def test_inf_handling_beneish(self):
        """ゼロ除算による inf が 0 に置換されること（Beneish）."""
        # revenue_prior = 0 で inf が発生するケース
        data = {
            "receivables": [15000], "revenue": [100000],
            "receivables_prior": [0], "revenue_prior": [0],
            "cogs": [60000], "cogs_prior": [0],
            "current_assets": [80000], "ppe": [50000],
            "total_assets": [200000],
            "current_assets_prior": [70000], "ppe_prior": [45000],
            "total_assets_prior": [0],
            "depreciation": [5000], "depreciation_prior": [0],
            "sga": [15000], "sga_prior": [0],
            "long_term_debt": [30000], "current_liabilities": [40000],
            "long_term_debt_prior": [0], "current_liabilities_prior": [0],
            "net_income": [12000], "operating_cash_flow": [15000],
        }
        df = pd.DataFrame(data)
        result = FraudPredictor.calculate_beneish_features(df)

        # inf が 0 に置換されていること
        beneish_cols = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "m_score"]
        for col in beneish_cols:
            assert not np.isinf(result[col]).any(), f"{col} に inf が残っています"
            assert not np.isnan(result[col]).any(), f"{col} に NaN が残っています"

    def test_inf_handling_altman(self):
        """ゼロ除算による inf が 0 に置換されること（Altman）."""
        data = {
            "current_assets": [80000], "current_liabilities": [40000],
            "total_assets": [0],  # ゼロ除算トリガー
            "retained_earnings": [60000], "ebit": [18000],
            "total_equity": [100000], "total_liabilities": [0],
            "revenue": [100000],
        }
        df = pd.DataFrame(data)
        result = FraudPredictor.calculate_altman_z(df)

        z_cols = ["z_wc_ta", "z_re_ta", "z_ebit_ta", "z_equity_debt", "z_rev_ta", "altman_z"]
        for col in z_cols:
            assert not np.isinf(result[col]).any(), f"{col} に inf が残っています"
