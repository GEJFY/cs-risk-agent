"""不正予測モデル - Beneish M-Score + XGBoost アンサンブル.

Beneish M-Score による財務指標ベースの不正検知と、
XGBoost + ロジスティック回帰のアンサンブルモデルを組み合わせて
不正リスクを定量化する。

アルゴリズム:
    Step 1: Beneish M-Score 8変数（DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA）計算
    Step 2: Altman Z-Score 5変数計算（倒産リスク指標）
    Step 3: XGBoost + LogisticRegression アンサンブル予測
    Step 4: リスクスコア（0-100）算出とリスクレベル分類
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, recall_score, roc_auc_score
from sklearn.model_selection import cross_val_score
import xgboost as xgb

from cs_risk_agent.core.exceptions import AnalysisError

logger = structlog.get_logger(__name__)


# --- Beneish M-Score 計算に必要なカラム ---
BENEISH_REQUIRED_COLUMNS: list[str] = [
    "receivables", "revenue", "receivables_prior", "revenue_prior",
    "cogs", "cogs_prior", "current_assets", "ppe", "total_assets",
    "current_assets_prior", "ppe_prior", "total_assets_prior",
    "depreciation", "depreciation_prior", "sga", "sga_prior",
    "long_term_debt", "current_liabilities", "long_term_debt_prior",
    "current_liabilities_prior", "net_income", "operating_cash_flow",
]

# --- Altman Z-Score 計算に必要な追加カラム ---
ALTMAN_REQUIRED_COLUMNS: list[str] = [
    "current_assets", "current_liabilities", "total_assets",
    "retained_earnings", "ebit", "total_equity", "total_liabilities",
    "revenue",
]


@dataclass
class FraudPredictionResult:
    """不正予測結果.

    Attributes:
        fraud_probability: 不正確率（0.0〜1.0）
        risk_score: リスクスコア（0〜100）
        risk_level: リスクレベル（critical/high/medium/low）
        beneish_m_score: Beneish M-Score（> -1.78で不正疑い）
        altman_z_score: Altman Z-Score（< 1.81で倒産危険）
        feature_importance: 特徴量重要度
        shap_values: SHAP値による個別寄与
    """

    fraud_probability: float
    risk_score: float
    risk_level: str
    beneish_m_score: float
    altman_z_score: float
    feature_importance: dict[str, float] = field(default_factory=dict)
    shap_values: dict[str, float] = field(default_factory=dict)


class FraudPredictor:
    """不正予測モデル（Beneish M-Score + XGBoost アンサンブル）.

    学習済みモデルがある場合はアンサンブル予測を行い、
    未学習の場合はルールベース（M-Score + Z-Score）で予測する。

    Attributes:
        _model: 学習済みアンサンブルモデル
        _feature_names: 特徴量名リスト
    """

    # Beneish M-Score 係数（Beneish, 1999）
    _M_SCORE_INTERCEPT: float = -4.84
    _M_SCORE_COEFFICIENTS: dict[str, float] = {
        "DSRI": 0.920,
        "GMI": 0.528,
        "AQI": 0.404,
        "SGI": 0.892,
        "DEPI": 0.115,
        "SGAI": -0.172,
        "TATA": 4.679,
        "LVGI": -0.327,
    }

    # M-Score 不正判定閾値
    _M_SCORE_THRESHOLD: float = -1.78

    # Altman Z-Score 係数（Altman, 1968）
    _Z_SCORE_COEFFICIENTS: dict[str, float] = {
        "z_wc_ta": 1.2,
        "z_re_ta": 1.4,
        "z_ebit_ta": 3.3,
        "z_equity_debt": 0.6,
        "z_rev_ta": 1.0,
    }

    # Z-Score 倒産危険閾値
    _Z_SCORE_DISTRESS: float = 1.81

    # リスクレベル閾値
    _RISK_THRESHOLDS: dict[str, float] = {
        "critical": 80.0,
        "high": 60.0,
        "medium": 40.0,
    }

    def __init__(self) -> None:
        """初期化."""
        self._model: VotingClassifier | None = None
        self._feature_names: list[str] = []

    @staticmethod
    def calculate_beneish_features(df: pd.DataFrame) -> pd.DataFrame:
        """Beneish M-Score 8変数を計算する.

        各指標の意味:
            DSRI: Days Sales in Receivables Index（売掛金回転日数指数）
            GMI:  Gross Margin Index（粗利率指数）
            AQI:  Asset Quality Index（資産品質指数）
            SGI:  Sales Growth Index（売上成長指数）
            DEPI: Depreciation Index（減価償却率指数）
            SGAI: SGA Expense Index（販管費率指数）
            LVGI: Leverage Index（レバレッジ指数）
            TATA: Total Accruals to Total Assets（総発生高対総資産比率）

        Args:
            df: 財務データ。BENEISH_REQUIRED_COLUMNSを含む必要がある。

        Returns:
            Beneish 8変数およびm_scoreカラムを追加したDataFrame。

        Raises:
            AnalysisError: 必須カラム不足時。
        """
        missing = [c for c in BENEISH_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise AnalysisError(
                engine="FraudPredictor",
                message=f"Beneish計算に必要なカラムが不足: {missing}",
            )

        result = df.copy()

        # DSRI: 売掛金/売上高の前年比
        result["DSRI"] = (
            (result["receivables"] / result["revenue"])
            / (result["receivables_prior"] / result["revenue_prior"])
        )

        # GMI: 粗利率の前年/当年比
        result["GMI"] = (
            ((result["revenue_prior"] - result["cogs_prior"]) / result["revenue_prior"])
            / ((result["revenue"] - result["cogs"]) / result["revenue"])
        )

        # AQI: 非流動資産（PPE除く）比率の変動
        result["AQI"] = (
            (1 - (result["current_assets"] + result["ppe"]) / result["total_assets"])
            / (1 - (result["current_assets_prior"] + result["ppe_prior"]) / result["total_assets_prior"])
        )

        # SGI: 売上成長率
        result["SGI"] = result["revenue"] / result["revenue_prior"]

        # DEPI: 減価償却率の前年/当年比
        result["DEPI"] = (
            (result["depreciation_prior"] / (result["ppe_prior"] + result["depreciation_prior"]))
            / (result["depreciation"] / (result["ppe"] + result["depreciation"]))
        )

        # SGAI: 販管費率の変動
        result["SGAI"] = (
            (result["sga"] / result["revenue"])
            / (result["sga_prior"] / result["revenue_prior"])
        )

        # LVGI: レバレッジの変動
        result["LVGI"] = (
            ((result["long_term_debt"] + result["current_liabilities"]) / result["total_assets"])
            / ((result["long_term_debt_prior"] + result["current_liabilities_prior"]) / result["total_assets_prior"])
        )

        # TATA: 発生高/総資産
        result["TATA"] = (
            (result["net_income"] - result["operating_cash_flow"]) / result["total_assets"]
        )

        # M-Score 算出
        result["m_score"] = FraudPredictor._M_SCORE_INTERCEPT
        for var, coeff in FraudPredictor._M_SCORE_COEFFICIENTS.items():
            result["m_score"] = result["m_score"] + coeff * result[var]

        # inf/nan を 0 で置換（ゼロ除算等の結果）
        beneish_cols = list(FraudPredictor._M_SCORE_COEFFICIENTS.keys()) + ["m_score"]
        result[beneish_cols] = (
            result[beneish_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
        )

        return result

    @staticmethod
    def calculate_altman_z(df: pd.DataFrame) -> pd.DataFrame:
        """Altman Z-Score を計算する.

        Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA)
            + 0.6*(Equity/TL) + 1.0*(Revenue/TA)

        Args:
            df: 財務データ。ALTMAN_REQUIRED_COLUMNSを含む必要がある。

        Returns:
            Z-Score構成変数およびaltman_zカラムを追加したDataFrame。

        Raises:
            AnalysisError: 必須カラム不足時。
        """
        missing = [c for c in ALTMAN_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise AnalysisError(
                engine="FraudPredictor",
                message=f"Altman Z計算に必要なカラムが不足: {missing}",
            )

        result = df.copy()

        # 運転資本 / 総資産
        result["z_wc_ta"] = (
            (result["current_assets"] - result["current_liabilities"])
            / result["total_assets"]
        )

        # 利益剰余金 / 総資産
        result["z_re_ta"] = result["retained_earnings"] / result["total_assets"]

        # EBIT / 総資産
        result["z_ebit_ta"] = result["ebit"] / result["total_assets"]

        # 株式時価総額（または自己資本）/ 負債総額
        equity_col = (
            "market_cap" if "market_cap" in result.columns else "total_equity"
        )
        result["z_equity_debt"] = result[equity_col] / result["total_liabilities"]

        # 売上高 / 総資産
        result["z_rev_ta"] = result["revenue"] / result["total_assets"]

        # Z-Score 算出
        result["altman_z"] = sum(
            coeff * result[var]
            for var, coeff in FraudPredictor._Z_SCORE_COEFFICIENTS.items()
        )

        # inf/nan を 0 で置換
        z_cols = list(FraudPredictor._Z_SCORE_COEFFICIENTS.keys()) + ["altman_z"]
        result[z_cols] = (
            result[z_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
        )

        return result

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """モデル入力用の特徴量を準備する.

        Beneish 8変数 + Altman Z構成5変数 = 13特徴量。

        Args:
            df: 財務データ。

        Returns:
            特徴量のみを含むDataFrame。
        """
        df = self.calculate_beneish_features(df)
        df = self.calculate_altman_z(df)

        self._feature_names = [
            "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA",
            "z_wc_ta", "z_re_ta", "z_ebit_ta", "z_equity_debt", "z_rev_ta",
        ]
        return df[self._feature_names]

    def train(
        self,
        df: pd.DataFrame,
        y: pd.Series,
        optimize: bool = True,
    ) -> dict[str, float]:
        """アンサンブルモデルを学習する.

        XGBoost（重み0.7）+ LogisticRegression（重み0.3）の
        ソフト投票アンサンブルを構築し、5-fold CVで評価する。

        Args:
            df: 財務特徴量付きDataFrame。
            y: 正解ラベル（0: normal, 1: fraud）。
            optimize: Optunaハイパーパラメータ最適化（将来拡張用）。

        Returns:
            学習メトリクス（auc, recall, cv_auc_mean）。

        Raises:
            AnalysisError: 学習データ不正時。
        """
        if len(df) == 0:
            raise AnalysisError(
                engine="FraudPredictor",
                message="学習データが空です",
            )

        fraud_count = int((y == 1).sum())
        normal_count = int((y == 0).sum())
        if fraud_count == 0:
            raise AnalysisError(
                engine="FraudPredictor",
                message="正例（fraud=1）が存在しません",
            )

        try:
            X = self._prepare_features(df)

            # 不均衡データ対策: scale_pos_weight
            scale_weight = normal_count / max(fraud_count, 1)

            xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                scale_pos_weight=scale_weight,
                eval_metric="auc",
                random_state=42,
            )
            lr_model = LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )

            self._model = VotingClassifier(
                estimators=[("xgb", xgb_model), ("lr", lr_model)],
                voting="soft",
                weights=[0.7, 0.3],
            )
            self._model.fit(X, y)

            # 学習データでの評価
            y_pred = self._model.predict(X)
            y_prob = self._model.predict_proba(X)[:, 1]

            # 5-fold CV
            cv_scores = cross_val_score(
                self._model, X, y, cv=5, scoring="roc_auc",
            )

            metrics = {
                "auc": float(roc_auc_score(y, y_prob)),
                "recall": float(recall_score(y, y_pred)),
                "cv_auc_mean": float(np.mean(cv_scores)),
                "cv_auc_std": float(np.std(cv_scores)),
                "n_samples": len(df),
                "n_fraud": fraud_count,
                "n_normal": normal_count,
            }

            logger.info("fraud_predictor.trained", **metrics)
            return metrics

        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError(
                engine="FraudPredictor",
                message=f"モデル学習中にエラーが発生: {exc}",
            ) from exc

    def predict(self, df: pd.DataFrame) -> list[FraudPredictionResult]:
        """不正予測を実行する.

        学習済みモデルがある場合はアンサンブル予測、
        未学習の場合はルールベース予測にフォールバックする。

        Args:
            df: 財務データ。

        Returns:
            各行に対するFraudPredictionResultのリスト。

        Raises:
            AnalysisError: 予測実行エラー時。
        """
        if df.empty:
            raise AnalysisError(
                engine="FraudPredictor",
                message="予測対象データが空です",
            )

        if self._model is None:
            logger.info("fraud_predictor.fallback_rule_based")
            return self._predict_rule_based(df)

        try:
            X = self._prepare_features(df)
            probabilities = self._model.predict_proba(X)[:, 1]

            # 特徴量付きデータを準備（M-Score/Z-Score参照用）
            df_with_features = self.calculate_beneish_features(df)
            df_with_features = self.calculate_altman_z(df_with_features)

            # XGBoost 特徴量重要度取得
            importance = self._get_feature_importance()

            results: list[FraudPredictionResult] = []
            for i, prob in enumerate(probabilities):
                score = float(prob * 100)
                level = self._score_to_level(score)

                results.append(FraudPredictionResult(
                    fraud_probability=float(prob),
                    risk_score=score,
                    risk_level=level,
                    beneish_m_score=float(
                        df_with_features.iloc[i].get("m_score", 0)
                    ),
                    altman_z_score=float(
                        df_with_features.iloc[i].get("altman_z", 0)
                    ),
                    feature_importance=importance,
                ))

            logger.info(
                "fraud_predictor.predicted",
                n_samples=len(results),
                mean_probability=float(np.mean(probabilities)),
            )
            return results

        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError(
                engine="FraudPredictor",
                message=f"予測実行中にエラーが発生: {exc}",
            ) from exc

    def _predict_rule_based(
        self, df: pd.DataFrame,
    ) -> list[FraudPredictionResult]:
        """ルールベース予測（モデル未学習時のフォールバック）.

        M-Score と Z-Score を組み合わせて不正確率を推定する。
        M-Score > -1.78 → 不正の疑い（重み0.6）
        Z-Score < 1.81  → 倒産危険（重み0.4）

        Args:
            df: 財務データ。

        Returns:
            各行に対するFraudPredictionResultのリスト。
        """
        try:
            df_calc = self.calculate_beneish_features(df)
            df_calc = self.calculate_altman_z(df_calc)
        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError(
                engine="FraudPredictor",
                message=f"ルールベース予測の特徴量計算中にエラー: {exc}",
            ) from exc

        results: list[FraudPredictionResult] = []
        for _, row in df_calc.iterrows():
            m_score = float(row.get("m_score", 0))
            z_score = float(row.get("altman_z", 0))

            # M-Score リスク: -1.78超で不正疑い、正規化して0〜1
            m_risk = max(
                0.0,
                min(1.0, (m_score - self._M_SCORE_THRESHOLD) / 3.0),
            )

            # Z-Score リスク: 1.81未満で倒産危険、正規化して0〜1
            z_risk = max(
                0.0,
                min(1.0, (self._Z_SCORE_DISTRESS - z_score) / 3.0),
            )

            # 加重平均
            prob = 0.6 * m_risk + 0.4 * z_risk
            score = prob * 100
            level = self._score_to_level(score)

            results.append(FraudPredictionResult(
                fraud_probability=float(prob),
                risk_score=float(score),
                risk_level=level,
                beneish_m_score=m_score,
                altman_z_score=z_score,
            ))

        logger.info(
            "fraud_predictor.rule_based_predicted",
            n_samples=len(results),
        )
        return results

    def _get_feature_importance(self) -> dict[str, float]:
        """XGBoostモデルの特徴量重要度を取得する.

        Returns:
            特徴量名をキー、重要度を値とする辞書。
        """
        if self._model is None or not self._feature_names:
            return {}

        try:
            # VotingClassifierからXGBoostモデルを取得
            xgb_estimator = self._model.named_estimators_.get("xgb")
            if xgb_estimator is None:
                return {}

            importances = xgb_estimator.feature_importances_
            return {
                name: float(imp)
                for name, imp in zip(self._feature_names, importances)
            }
        except (AttributeError, ValueError):
            return {}

    @classmethod
    def _score_to_level(cls, score: float) -> str:
        """リスクスコアからリスクレベルに変換する.

        Args:
            score: リスクスコア（0〜100）。

        Returns:
            リスクレベル文字列。
        """
        if score >= cls._RISK_THRESHOLDS["critical"]:
            return "critical"
        elif score >= cls._RISK_THRESHOLDS["high"]:
            return "high"
        elif score >= cls._RISK_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    @property
    def is_trained(self) -> bool:
        """モデルが学習済みかどうか."""
        return self._model is not None

    @property
    def feature_names(self) -> list[str]:
        """現在の特徴量名リスト."""
        return self._feature_names.copy()
