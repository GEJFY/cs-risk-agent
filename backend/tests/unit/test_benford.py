"""ベンフォード分析 ユニットテスト.

BenfordAnalyzer の第1桁テスト・重複テスト・アカウント分析を検証する。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cs_risk_agent.analysis.benford import (
    BENFORD_EXPECTED,
    MAD_THRESHOLDS,
    AccountAnalysisResult,
    BenfordAnalyzer,
    BenfordResult,
    DuplicateResult,
)
from cs_risk_agent.core.exceptions import AnalysisError


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> BenfordAnalyzer:
    """テスト用 BenfordAnalyzer."""
    return BenfordAnalyzer(min_sample_size=50)


@pytest.fixture
def benford_conforming_data() -> pd.Series:
    """ベンフォードの法則に適合するデータ（対数正規分布）.

    自然発生的なデータはベンフォードの法則に従う傾向がある。
    """
    np.random.seed(42)
    amounts = np.random.lognormal(10, 2, 5000)
    return pd.Series(amounts, name="amount")


@pytest.fixture
def uniform_digit_data() -> pd.Series:
    """第1桁が均等分布のデータ（非適合を期待）.

    各桁 1-9 が均等に出現する決定論的データ。
    first digit が保持されるよう、1xx, 2xx, ..., 9xx の範囲で生成。
    """
    amounts = []
    for digit in range(1, 10):
        # 各桁60個ずつ = 合計540サンプル
        for i in range(60):
            amounts.append(digit * 100 + i)
    return pd.Series(amounts, dtype=float, name="amount")


# ---------------------------------------------------------------------------
# 第1桁テスト
# ---------------------------------------------------------------------------


class TestFirstDigitTestCompliant:
    """ベンフォード適合データの検証."""

    def test_first_digit_test_compliant(self, analyzer, benford_conforming_data):
        """対数正規分布データが適合判定されること."""
        result = analyzer.first_digit_test(benford_conforming_data)
        assert isinstance(result, BenfordResult)
        assert result.conformity in (
            "close_conformity",
            "acceptable_conformity",
        )

    def test_mad_within_acceptable_range(self, analyzer, benford_conforming_data):
        """MAD が許容範囲内であること."""
        result = analyzer.first_digit_test(benford_conforming_data)
        assert result.mad < MAD_THRESHOLDS["marginally_acceptable"]

    def test_digit_distribution_sums_to_one(self, analyzer, benford_conforming_data):
        """実測分布の合計が概ね1であること."""
        result = analyzer.first_digit_test(benford_conforming_data)
        total = sum(result.digit_distribution.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_sample_size_recorded(self, analyzer, benford_conforming_data):
        """サンプルサイズが正しく記録されること."""
        result = analyzer.first_digit_test(benford_conforming_data)
        assert result.sample_size > 0

    def test_z_scores_calculated(self, analyzer, benford_conforming_data):
        """各桁のZ統計量が算出されること."""
        result = analyzer.first_digit_test(benford_conforming_data)
        assert len(result.z_scores) == 9
        for d in range(1, 10):
            assert d in result.z_scores


class TestFirstDigitTestNonCompliant:
    """ベンフォード非適合データの検証."""

    def test_first_digit_test_non_compliant(self, analyzer, uniform_digit_data):
        """一様分布データが非適合判定されること."""
        result = analyzer.first_digit_test(uniform_digit_data)
        assert isinstance(result, BenfordResult)
        # 一様分布は明らかにベンフォードに適合しない
        assert result.conformity in (
            "marginally_acceptable",
            "nonconforming",
        )

    def test_high_mad_for_uniform(self, analyzer, uniform_digit_data):
        """一様分布データの MAD が高いこと."""
        result = analyzer.first_digit_test(uniform_digit_data)
        assert result.mad > MAD_THRESHOLDS["close_conformity"]

    def test_low_p_value_for_uniform(self, analyzer, uniform_digit_data):
        """一様分布データの p値 が低いこと（有意）."""
        result = analyzer.first_digit_test(uniform_digit_data)
        assert result.p_value < 0.05  # 5%有意水準

    def test_sample_too_small_raises_error(self, analyzer):
        """サンプル不足で AnalysisError が発生すること."""
        small_data = pd.Series([100, 200, 300])
        with pytest.raises(AnalysisError):
            analyzer.first_digit_test(small_data)


# ---------------------------------------------------------------------------
# 重複テスト
# ---------------------------------------------------------------------------


class TestDuplicateTest:
    """重複金額テストの検証."""

    def test_duplicate_test(self, analyzer, benford_conforming_data):
        """重複テストが正しい結果を返すこと."""
        result = analyzer.duplicate_test(benford_conforming_data)
        assert isinstance(result, DuplicateResult)
        assert result.total_entries > 0
        assert result.unique_amounts > 0
        assert 0 <= result.duplicate_ratio <= 1.0

    def test_duplicate_high_ratio(self, analyzer):
        """高い重複率が検出されること."""
        # 同じ値を大量に含むデータ
        amounts = pd.Series([1000.0] * 100 + [2000.0] * 50 + [3000.0] * 50)
        result = analyzer.duplicate_test(amounts)
        assert result.duplicate_ratio > 0.9  # 非常に高い重複率
        assert result.anomaly_detected is True

    def test_duplicate_top_amounts(self, analyzer):
        """上位重複金額が取得できること."""
        amounts = pd.Series([1000.0] * 50 + [2000.0] * 30 + list(range(1, 21)))
        result = analyzer.duplicate_test(amounts, top_n=5)
        assert len(result.top_duplicates) > 0
        assert result.top_duplicates[0]["count"] >= result.top_duplicates[-1]["count"]

    def test_duplicate_empty_data(self, analyzer):
        """空データの重複テストがエラーなく処理されること."""
        result = analyzer.duplicate_test(pd.Series(dtype=float))
        assert result.total_entries == 0
        assert result.anomaly_detected is False


# ---------------------------------------------------------------------------
# MAD 閾値テスト
# ---------------------------------------------------------------------------


class TestMADThresholds:
    """MAD 閾値分類の検証."""

    def test_mad_thresholds_close(self):
        """Close conformity の分類が正しいこと."""
        assert BenfordAnalyzer._classify_conformity(0.004) == "close_conformity"

    def test_mad_thresholds_acceptable(self):
        """Acceptable conformity の分類が正しいこと."""
        assert BenfordAnalyzer._classify_conformity(0.010) == "acceptable_conformity"

    def test_mad_thresholds_marginal(self):
        """Marginally acceptable の分類が正しいこと."""
        assert BenfordAnalyzer._classify_conformity(0.014) == "marginally_acceptable"

    def test_mad_thresholds_nonconforming(self):
        """Nonconforming の分類が正しいこと."""
        assert BenfordAnalyzer._classify_conformity(0.020) == "nonconforming"


# ---------------------------------------------------------------------------
# アカウント分析テスト
# ---------------------------------------------------------------------------


class TestAnalyzeAccount:
    """勘定科目別分析の検証."""

    def test_analyze_account(self, analyzer, benford_conforming_data):
        """アカウント分析が正しい結果を返すこと."""
        result = analyzer.analyze_account(
            benford_conforming_data,
            account_code="4100",
        )
        assert isinstance(result, AccountAnalysisResult)
        assert result.account_code == "4100"
        assert result.sample_size > 0
        assert result.benford_result is not None
        assert result.duplicate_result is not None
        assert 0 <= result.risk_score <= 100

    def test_analyze_account_small_sample(self, analyzer):
        """小サンプルでベンフォードテストがスキップされること."""
        small_data = pd.Series([100, 200, 300, 400, 500])
        result = analyzer.analyze_account(small_data, account_code="9999")
        assert result.benford_result is None  # サンプル不足でスキップ
        assert result.sample_size == 5

    def test_risk_score_range(self, analyzer, benford_conforming_data):
        """リスクスコアが0-100の範囲であること."""
        result = analyzer.analyze_account(benford_conforming_data)
        assert 0.0 <= result.risk_score <= 100.0
