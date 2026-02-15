"""裁量的会計発生高（Discretionary Accruals）分析エンジン.

修正ジョーンズモデル（Modified Jones Model）およびKothari拡張を用いて
裁量的発生高を推定し、利益操作リスクを評価する。

アルゴリズム:
    Step 1: 総発生高(TA) = 純利益 - 営業キャッシュフロー
    Step 2: 産業別クロスセクション回帰:
            TA/A = alpha(1/A) + beta1(dREV-dREC)/A + beta2(PPE/A) + epsilon
    Step 3: Kothari ROA拡張による非裁量的発生高(NDA)算出
    Step 4: DA = TA/A - NDA、リスク分類
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats.mstats import winsorize

from cs_risk_agent.core.exceptions import AnalysisError

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """裁量的発生高リスクレベル."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True)
class AccrualThresholds:
    """DA判定閾値.

    Attributes:
        high: 高リスク判定閾値（絶対値がこれ以上）
        medium: 中リスク判定閾値（絶対値がこれ以上かつhigh未満）
    """

    high: float = 0.075
    medium: float = 0.035


@dataclass
class RegressionResult:
    """産業別回帰結果.

    Attributes:
        industry_code: 産業コード
        n_observations: 標本数
        r_squared: 決定係数
        adj_r_squared: 自由度調整済み決定係数
        alpha: 切片係数
        beta1: 収益変化係数
        beta2: PPE係数
        beta3_roa: ROA係数（Kothari拡張）
        f_statistic: F統計量
        p_value_f: F統計量のp値
    """

    industry_code: str
    n_observations: int
    r_squared: float
    adj_r_squared: float
    alpha: float
    beta1: float
    beta2: float
    beta3_roa: float
    f_statistic: float
    p_value_f: float


@dataclass
class AccrualAnalysisResult:
    """裁量的発生高分析結果.

    Attributes:
        summary_stats: 要約統計量
        regression_results: 産業別回帰結果
        risk_distribution: リスクレベル別企業数
        warnings: 分析上の警告メッセージ
    """

    summary_stats: dict[str, float] = field(default_factory=dict)
    regression_results: list[RegressionResult] = field(default_factory=list)
    risk_distribution: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class DiscretionaryAccrualsAnalyzer:
    """裁量的発生高分析クラス（修正ジョーンズモデル + Kothari拡張）.

    修正ジョーンズモデルによるクロスセクション回帰を産業別に実行し、
    裁量的発生高（DA）を推定する。Kothari(2005)のROA拡張により
    業績連動バイアスを軽減する。

    Attributes:
        thresholds: リスク判定閾値
        winsorize_limits: ウィンソライズの上下限
        min_industry_obs: 産業別回帰の最小観測数
    """

    # 必須カラム定義
    REQUIRED_COLUMNS: list[str] = [
        "net_income",
        "operating_cash_flow",
        "total_assets",
        "total_assets_prev",
        "revenue",
        "revenue_prev",
        "receivables",
        "receivables_prev",
        "ppe",
        "roa",
    ]

    def __init__(
        self,
        thresholds: AccrualThresholds | None = None,
        winsorize_limits: tuple[float, float] = (0.01, 0.01),
        min_industry_obs: int = 10,
    ) -> None:
        """初期化.

        Args:
            thresholds: リスク判定閾値。Noneの場合はデフォルト値を使用。
            winsorize_limits: ウィンソライズの下限・上限パーセンタイル。
            min_industry_obs: 産業別回帰に必要な最小観測数。
        """
        self.thresholds = thresholds or AccrualThresholds()
        self.winsorize_limits = winsorize_limits
        self.min_industry_obs = min_industry_obs

    def analyze(
        self,
        df: pd.DataFrame,
        industry_col: str = "industry_code",
    ) -> pd.DataFrame:
        """裁量的発生高分析を実行する.

        産業別クロスセクション回帰により非裁量的発生高を推定し、
        裁量的発生高およびリスク分類を返す。

        Args:
            df: 財務データ。REQUIRED_COLUMNSおよびindustry_colを含む必要がある。
            industry_col: 産業コードカラム名。

        Returns:
            入力DataFrameに以下のカラムを追加したDataFrame:
                - total_accruals: 総発生高
                - ta_scaled: 総発生高/前期総資産
                - nda: 非裁量的発生高（Kothari拡張）
                - da: 裁量的発生高
                - da_abs: 裁量的発生高の絶対値
                - da_risk_level: リスクレベル（High/Medium/Low）

        Raises:
            AnalysisError: 必須カラム不足、データ不正等のエラー。
        """
        try:
            self._validate_input(df, industry_col)
            result_df = df.copy()

            # Step 1: 総発生高の算出
            result_df = self._calculate_total_accruals(result_df)

            # ウィンソライズで外れ値を処理
            result_df = self._apply_winsorization(result_df)

            # Step 2 & 3: 産業別回帰とNDA/DA算出
            result_df = self._estimate_discretionary_accruals(
                result_df, industry_col
            )

            # Step 4: リスク分類
            result_df = self._classify_risk(result_df)

            logger.info(
                "裁量的発生高分析完了: %d件処理, DA平均=%.4f",
                len(result_df),
                result_df["da"].mean(),
            )
            return result_df

        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError(
                engine="DiscretionaryAccruals",
                message=f"分析実行中に予期しないエラーが発生: {exc}",
            ) from exc

    def get_analysis_summary(
        self,
        df: pd.DataFrame,
        industry_col: str = "industry_code",
    ) -> AccrualAnalysisResult:
        """分析結果の要約情報を取得する.

        Args:
            df: analyze()で処理済みのDataFrame。
            industry_col: 産業コードカラム名。

        Returns:
            AccrualAnalysisResult: 分析結果の要約。
        """
        result = AccrualAnalysisResult()

        if "da" not in df.columns:
            result.warnings.append("DA未算出: analyze()を先に実行してください")
            return result

        # 要約統計量
        result.summary_stats = {
            "mean_da": float(df["da"].mean()),
            "median_da": float(df["da"].median()),
            "std_da": float(df["da"].std()),
            "mean_abs_da": float(df["da_abs"].mean()),
            "median_abs_da": float(df["da_abs"].median()),
            "min_da": float(df["da"].min()),
            "max_da": float(df["da"].max()),
            "n_total": int(len(df)),
        }

        # リスク分布
        if "da_risk_level" in df.columns:
            risk_counts = df["da_risk_level"].value_counts().to_dict()
            result.risk_distribution = {str(k): int(v) for k, v in risk_counts.items()}

        return result

    def _validate_input(self, df: pd.DataFrame, industry_col: str) -> None:
        """入力データの検証.

        Args:
            df: 検証対象DataFrame。
            industry_col: 産業コードカラム名。

        Raises:
            AnalysisError: 検証エラー時。
        """
        if df.empty:
            raise AnalysisError(
                engine="DiscretionaryAccruals",
                message="入力DataFrameが空です",
            )

        required = self.REQUIRED_COLUMNS + [industry_col]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise AnalysisError(
                engine="DiscretionaryAccruals",
                message=f"必須カラムが不足: {missing}",
            )

        # 前期総資産がゼロの行を検出
        zero_assets = (df["total_assets_prev"] == 0).sum()
        if zero_assets > 0:
            logger.warning(
                "前期総資産がゼロの行が%d件あります（回帰から除外されます）",
                zero_assets,
            )

    def _calculate_total_accruals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 1: 総発生高を算出する.

        TA = 純利益 - 営業キャッシュフロー
        スケーリング: TA / 前期総資産

        Args:
            df: 財務データ。

        Returns:
            total_accruals, ta_scaledカラムを追加したDataFrame。
        """
        df["total_accruals"] = df["net_income"] - df["operating_cash_flow"]

        # 前期総資産でスケーリング（ゼロ除算防止）
        df["ta_scaled"] = np.where(
            df["total_assets_prev"] != 0,
            df["total_accruals"] / df["total_assets_prev"],
            np.nan,
        )
        return df

    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        """外れ値のウィンソライズ処理.

        Args:
            df: スケーリング済みデータ。

        Returns:
            ウィンソライズ適用後のDataFrame。
        """
        cols_to_winsorize = ["ta_scaled"]

        for col in cols_to_winsorize:
            valid_mask = df[col].notna()
            if valid_mask.sum() > 0:
                values = df.loc[valid_mask, col].values.copy()
                winsorized = winsorize(values, limits=self.winsorize_limits)
                df.loc[valid_mask, col] = np.asarray(winsorized)

        return df

    def _estimate_discretionary_accruals(
        self,
        df: pd.DataFrame,
        industry_col: str,
    ) -> pd.DataFrame:
        """Step 2 & 3: 産業別クロスセクション回帰とDA算出.

        修正ジョーンズモデル + Kothari ROA拡張:
            TA/A = alpha(1/A) + beta1(dREV-dREC)/A + beta2(PPE/A) + beta3(ROA) + epsilon

        回帰係数を用いてNDAを算出し、DA = TA/A - NDAとする。

        Args:
            df: 総発生高算出済みデータ。
            industry_col: 産業コードカラム名。

        Returns:
            nda, daカラムを追加したDataFrame。
        """
        df["nda"] = np.nan
        df["da"] = np.nan
        df["da_abs"] = np.nan

        # 回帰用変数の事前計算
        valid_mask = (df["total_assets_prev"] != 0) & df["ta_scaled"].notna()
        df.loc[valid_mask, "_inv_assets"] = 1.0 / df.loc[valid_mask, "total_assets_prev"]
        df.loc[valid_mask, "_delta_rev_rec_scaled"] = (
            (df.loc[valid_mask, "revenue"] - df.loc[valid_mask, "revenue_prev"])
            - (df.loc[valid_mask, "receivables"] - df.loc[valid_mask, "receivables_prev"])
        ) / df.loc[valid_mask, "total_assets_prev"]
        df.loc[valid_mask, "_ppe_scaled"] = (
            df.loc[valid_mask, "ppe"] / df.loc[valid_mask, "total_assets_prev"]
        )

        # 産業別にクロスセクション回帰を実行
        industries = df.loc[valid_mask, industry_col].unique()

        for ind in industries:
            ind_mask = (df[industry_col] == ind) & valid_mask
            ind_data = df.loc[ind_mask]

            if len(ind_data) < self.min_industry_obs:
                logger.warning(
                    "産業 '%s' の観測数(%d)が最小要件(%d)未満のためスキップ",
                    ind,
                    len(ind_data),
                    self.min_industry_obs,
                )
                continue

            try:
                nda_values = self._run_industry_regression(ind_data, str(ind))
                df.loc[ind_mask, "nda"] = nda_values
                df.loc[ind_mask, "da"] = df.loc[ind_mask, "ta_scaled"] - nda_values
                df.loc[ind_mask, "da_abs"] = np.abs(df.loc[ind_mask, "da"])
            except Exception as exc:
                logger.warning(
                    "産業 '%s' の回帰でエラー: %s（スキップ）",
                    ind,
                    exc,
                )
                continue

        # 一時カラムの削除
        temp_cols = ["_inv_assets", "_delta_rev_rec_scaled", "_ppe_scaled"]
        df.drop(columns=[c for c in temp_cols if c in df.columns], inplace=True)

        return df

    def _run_industry_regression(
        self,
        ind_data: pd.DataFrame,
        industry_code: str,
    ) -> np.ndarray:
        """単一産業のクロスセクション回帰を実行する.

        Kothari(2005)拡張: ROAを説明変数に追加し、業績連動バイアスを制御。

        Args:
            ind_data: 単一産業のデータ。
            industry_code: 産業コード（ログ出力用）。

        Returns:
            非裁量的発生高（NDA）の推定値配列。

        Raises:
            ValueError: 回帰が収束しない場合。
        """
        # 説明変数: (1/A), (dREV-dREC)/A, PPE/A, ROA
        x_vars = ind_data[
            ["_inv_assets", "_delta_rev_rec_scaled", "_ppe_scaled", "roa"]
        ].copy()
        y_var = ind_data["ta_scaled"].copy()

        # 欠損値除去
        combined = pd.concat([x_vars, y_var], axis=1).dropna()
        if len(combined) < self.min_industry_obs:
            raise ValueError(
                f"有効観測数不足: {len(combined)} < {self.min_industry_obs}"
            )

        x_clean = combined.iloc[:, :-1]
        y_clean = combined.iloc[:, -1]

        # OLS回帰（定数項はinv_assetsで代替するため追加しない）
        model = sm.OLS(y_clean, x_clean).fit()

        logger.debug(
            "産業 '%s': n=%d, R2=%.4f, AdjR2=%.4f",
            industry_code,
            len(y_clean),
            model.rsquared,
            model.rsquared_adj,
        )

        # NDA = 推定値（フィット値）
        # 全データ（欠損含む）に対して予測
        x_full = ind_data[
            ["_inv_assets", "_delta_rev_rec_scaled", "_ppe_scaled", "roa"]
        ]
        nda = model.predict(x_full)

        return nda.values

    def _classify_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: DA値に基づくリスク分類.

        Args:
            df: DA算出済みデータ。

        Returns:
            da_risk_levelカラムを追加したDataFrame。
        """
        conditions = [
            df["da_abs"] >= self.thresholds.high,
            df["da_abs"] >= self.thresholds.medium,
        ]
        choices = [RiskLevel.HIGH.value, RiskLevel.MEDIUM.value]

        df["da_risk_level"] = np.select(
            conditions, choices, default=RiskLevel.LOW.value
        )

        # NaN行は分類不能
        df.loc[df["da_abs"].isna(), "da_risk_level"] = np.nan

        return df
