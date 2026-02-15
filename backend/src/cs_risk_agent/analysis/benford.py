"""ベンフォードの法則 分析エンジン.

仕訳データの第1桁分布がベンフォードの法則に従うかを検定し、
不正リスクの統計的指標を提供する。

アルゴリズム:
    Step 1: 第1桁の出現頻度を集計
    Step 2: ベンフォード理論分布との比較（MAD, カイ二乗検定）
    Step 3: 重複金額テスト
    Step 4: アカウント別分析
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from cs_risk_agent.core.exceptions import AnalysisError

logger = logging.getLogger(__name__)

# ベンフォードの法則: 第1桁の理論確率
BENFORD_EXPECTED: dict[int, float] = {
    1: 0.30103,
    2: 0.17609,
    3: 0.12494,
    4: 0.09691,
    5: 0.07918,
    6: 0.06695,
    7: 0.05799,
    8: 0.05115,
    9: 0.04576,
}

# MAD（Mean Absolute Deviation）閾値
# Nigrini (2012) による分類
MAD_THRESHOLDS: dict[str, float] = {
    "close_conformity": 0.006,
    "acceptable_conformity": 0.012,
    "marginally_acceptable": 0.015,
    "nonconformity": 0.015,  # この値以上は非適合
}


@dataclass
class BenfordResult:
    """ベンフォード分析結果.

    Attributes:
        digit_distribution: 第1桁の実測分布
        expected_distribution: 理論分布
        mad: 平均絶対偏差
        chi_square: カイ二乗統計量
        p_value: p値
        conformity: 適合度判定（close/acceptable/marginal/nonconforming）
        sample_size: サンプルサイズ
        z_scores: 各桁のZ統計量
    """

    digit_distribution: dict[int, float]
    expected_distribution: dict[int, float]
    mad: float
    chi_square: float
    p_value: float
    conformity: str
    sample_size: int
    z_scores: dict[int, float] = field(default_factory=dict)


@dataclass
class DuplicateResult:
    """重複金額テスト結果.

    Attributes:
        total_entries: 総件数
        unique_amounts: ユニーク金額数
        duplicate_ratio: 重複比率
        top_duplicates: 上位重複金額リスト
        anomaly_detected: 異常検出フラグ
    """

    total_entries: int
    unique_amounts: int
    duplicate_ratio: float
    top_duplicates: list[dict[str, Any]]
    anomaly_detected: bool


@dataclass
class AccountAnalysisResult:
    """アカウント別分析結果.

    Attributes:
        account_code: 勘定科目コード
        sample_size: サンプルサイズ
        benford_result: ベンフォード分析結果（Noneの場合はサンプル不足）
        duplicate_result: 重複金額テスト結果
        risk_score: リスクスコア（0-100）
    """

    account_code: str
    sample_size: int
    benford_result: BenfordResult | None
    duplicate_result: DuplicateResult | None
    risk_score: float


class BenfordAnalyzer:
    """ベンフォードの法則 分析クラス.

    仕訳データの金額分布をベンフォードの法則と比較し、
    統計的異常を検出する。

    Attributes:
        min_sample_size: 分析に必要な最小サンプルサイズ
        duplicate_threshold: 重複異常と判定する比率閾値
    """

    def __init__(
        self,
        min_sample_size: int = 50,
        duplicate_threshold: float = 0.5,
    ) -> None:
        """初期化.

        Args:
            min_sample_size: 分析に必要な最小サンプルサイズ。
            duplicate_threshold: 重複異常と判定する比率閾値。
        """
        self.min_sample_size = min_sample_size
        self.duplicate_threshold = duplicate_threshold

    def first_digit_test(
        self,
        amounts: pd.Series,
    ) -> BenfordResult:
        """第1桁テストを実行する.

        金額データの第1桁分布をベンフォードの法則理論分布と比較し、
        MADおよびカイ二乗検定で適合度を評価する。

        Args:
            amounts: 金額データ（正の数値のみ有効）。

        Returns:
            BenfordResult: 分析結果。

        Raises:
            AnalysisError: サンプルサイズ不足等のエラー。
        """
        # 前処理: 正の値のみ、第1桁抽出
        positive = amounts[amounts > 0].dropna()
        if len(positive) < self.min_sample_size:
            raise AnalysisError(
                engine="BenfordAnalyzer",
                message=(
                    f"サンプルサイズ不足: {len(positive)} < {self.min_sample_size}"
                ),
            )

        # 第1桁抽出
        first_digits = positive.apply(self._extract_first_digit)
        first_digits = first_digits[first_digits.between(1, 9)]

        n = len(first_digits)
        if n < self.min_sample_size:
            raise AnalysisError(
                engine="BenfordAnalyzer",
                message=f"有効サンプル不足: {n} < {self.min_sample_size}",
            )

        # 実測分布
        counts = first_digits.value_counts().sort_index()
        observed: dict[int, float] = {}
        for d in range(1, 10):
            observed[d] = counts.get(d, 0) / n

        # MAD計算
        mad = np.mean([abs(observed.get(d, 0) - BENFORD_EXPECTED[d]) for d in range(1, 10)])

        # カイ二乗検定
        obs_array = np.array([counts.get(d, 0) for d in range(1, 10)])
        exp_array = np.array([BENFORD_EXPECTED[d] * n for d in range(1, 10)])

        chi2, p_value = stats.chisquare(obs_array, f_exp=exp_array)

        # Z-score（各桁）
        z_scores: dict[int, float] = {}
        for d in range(1, 10):
            p_e = BENFORD_EXPECTED[d]
            p_o = observed.get(d, 0)
            se = np.sqrt(p_e * (1 - p_e) / n)
            z_scores[d] = (p_o - p_e) / se if se > 0 else 0.0

        # 適合度判定
        conformity = self._classify_conformity(mad)

        logger.info(
            "ベンフォード第1桁テスト完了: n=%d, MAD=%.6f, chi2=%.2f, p=%.4f, 判定=%s",
            n, mad, chi2, p_value, conformity,
        )

        return BenfordResult(
            digit_distribution=observed,
            expected_distribution=dict(BENFORD_EXPECTED),
            mad=float(mad),
            chi_square=float(chi2),
            p_value=float(p_value),
            conformity=conformity,
            sample_size=n,
            z_scores={d: float(z) for d, z in z_scores.items()},
        )

    def duplicate_test(
        self,
        amounts: pd.Series,
        top_n: int = 10,
    ) -> DuplicateResult:
        """重複金額テストを実行する.

        同一金額の出現頻度を分析し、異常な重複パターンを検出する。

        Args:
            amounts: 金額データ。
            top_n: 上位表示件数。

        Returns:
            DuplicateResult: 重複分析結果。
        """
        positive = amounts[amounts > 0].dropna()
        total = len(positive)

        if total == 0:
            return DuplicateResult(
                total_entries=0,
                unique_amounts=0,
                duplicate_ratio=0.0,
                top_duplicates=[],
                anomaly_detected=False,
            )

        unique_count = positive.nunique()
        duplicate_ratio = 1.0 - (unique_count / total) if total > 0 else 0.0

        # 上位重複金額
        value_counts = positive.value_counts().head(top_n)
        top_duplicates = [
            {"amount": float(amount), "count": int(count)}
            for amount, count in value_counts.items()
        ]

        anomaly = duplicate_ratio > self.duplicate_threshold

        return DuplicateResult(
            total_entries=total,
            unique_amounts=unique_count,
            duplicate_ratio=float(duplicate_ratio),
            top_duplicates=top_duplicates,
            anomaly_detected=anomaly,
        )

    def analyze_account(
        self,
        amounts: pd.Series,
        account_code: str = "unknown",
    ) -> AccountAnalysisResult:
        """勘定科目別の総合分析を実行する.

        ベンフォードテストと重複テストを組み合わせ、
        勘定科目単位のリスクスコアを算出する。

        Args:
            amounts: 金額データ。
            account_code: 勘定科目コード。

        Returns:
            AccountAnalysisResult: 総合分析結果。
        """
        positive = amounts[amounts > 0].dropna()
        sample_size = len(positive)

        # ベンフォードテスト
        benford_result: BenfordResult | None = None
        if sample_size >= self.min_sample_size:
            try:
                benford_result = self.first_digit_test(positive)
            except AnalysisError:
                pass

        # 重複テスト
        duplicate_result = self.duplicate_test(positive)

        # リスクスコア算出（0-100）
        risk_score = self._calculate_risk_score(benford_result, duplicate_result)

        return AccountAnalysisResult(
            account_code=account_code,
            sample_size=sample_size,
            benford_result=benford_result,
            duplicate_result=duplicate_result,
            risk_score=risk_score,
        )

    @staticmethod
    def _extract_first_digit(value: float) -> int:
        """数値の第1桁を取得する.

        Args:
            value: 正の数値。

        Returns:
            第1桁（1-9）。無効な値は0を返す。
        """
        try:
            abs_val = abs(value)
            if abs_val == 0:
                return 0
            s = f"{abs_val:.10e}"
            return int(s[0])
        except (ValueError, IndexError):
            return 0

    @staticmethod
    def _classify_conformity(mad: float) -> str:
        """MAD値に基づいて適合度を分類する.

        Nigrini (2012) の分類基準:
            MAD < 0.006: Close conformity
            MAD < 0.012: Acceptable conformity
            MAD < 0.015: Marginally acceptable
            MAD >= 0.015: Nonconforming

        Args:
            mad: 平均絶対偏差。

        Returns:
            適合度文字列。
        """
        if mad < MAD_THRESHOLDS["close_conformity"]:
            return "close_conformity"
        elif mad < MAD_THRESHOLDS["acceptable_conformity"]:
            return "acceptable_conformity"
        elif mad < MAD_THRESHOLDS["marginally_acceptable"]:
            return "marginally_acceptable"
        else:
            return "nonconforming"

    @staticmethod
    def _calculate_risk_score(
        benford: BenfordResult | None,
        duplicate: DuplicateResult | None,
    ) -> float:
        """リスクスコアを算出する.

        ベンフォード適合度（60%重み）と重複比率（40%重み）から
        0-100のスコアを算出する。

        Args:
            benford: ベンフォードテスト結果。
            duplicate: 重複テスト結果。

        Returns:
            リスクスコア（0-100）。
        """
        score = 0.0

        if benford:
            conformity_scores = {
                "close_conformity": 0.0,
                "acceptable_conformity": 25.0,
                "marginally_acceptable": 50.0,
                "nonconforming": 100.0,
            }
            score += 0.6 * conformity_scores.get(benford.conformity, 50.0)

        if duplicate:
            # 重複比率をスコアに変換（0.5以上を100点）
            dup_score = min(100.0, duplicate.duplicate_ratio * 200.0)
            score += 0.4 * dup_score

        return round(min(100.0, score), 1)
