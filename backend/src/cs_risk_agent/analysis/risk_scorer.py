"""統合リスクスコアラー - 各分析エンジンのスコアを統合.

ルールエンジン、裁量的発生高分析、不正予測モデル、ベンフォード分析の
各スコアを重み付けで統合し、企業全体のリスクスコアを算出する。

重みデフォルト:
    ルールエンジン:         30%
    裁量的発生高:          25%
    不正予測モデル:         25%
    ベンフォード分析:       20%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskComponent:
    """リスクコンポーネント.

    Attributes:
        name: コンポーネント名
        score: スコア（0-100）
        weight: 重み（0.0-1.0）
        details: 詳細情報
    """

    name: str
    score: float
    weight: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegratedRiskResult:
    """統合リスク評価結果.

    Attributes:
        integrated_score: 統合リスクスコア（0-100）
        risk_level: リスクレベル（critical/high/medium/low）
        components: 各コンポーネントのスコア
        summary_ja: 日本語サマリー
        recommendations: 推奨アクション
    """

    integrated_score: float
    risk_level: str
    components: list[RiskComponent]
    summary_ja: str = ""
    recommendations: list[str] = field(default_factory=list)


# リスクレベル閾値
RISK_LEVEL_THRESHOLDS: dict[str, float] = {
    "critical": 80.0,
    "high": 60.0,
    "medium": 40.0,
}

# デフォルト重み
DEFAULT_WEIGHTS: dict[str, float] = {
    "rule_engine": 0.30,
    "discretionary_accruals": 0.25,
    "fraud_prediction": 0.25,
    "benford": 0.20,
}


class IntegratedRiskScorer:
    """統合リスクスコアラー.

    各分析エンジンのスコアを重み付けで統合し、
    企業全体のリスクスコアを算出する。

    Attributes:
        weights: 各コンポーネントの重み
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        """初期化.

        Args:
            weights: 各コンポーネントの重み。Noneの場合はデフォルト値を使用。
                     重みの合計は自動正規化される。
        """
        raw_weights = weights or DEFAULT_WEIGHTS.copy()
        total = sum(raw_weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in raw_weights.items()}
        else:
            self.weights = raw_weights

    def calculate_integrated_score(
        self,
        scores: dict[str, float],
    ) -> float:
        """統合スコアを算出する.

        各コンポーネントのスコアに重みを掛けて合算する。
        未提供のコンポーネントは0点として扱う。

        Args:
            scores: コンポーネント名→スコア（0-100）のマッピング。

        Returns:
            統合リスクスコア（0-100）。
        """
        integrated = 0.0
        for component, weight in self.weights.items():
            score = scores.get(component, 0.0)
            # スコアを0-100の範囲にクランプ
            score = max(0.0, min(100.0, score))
            integrated += score * weight

        return round(min(100.0, integrated), 1)

    @staticmethod
    def get_risk_level(score: float) -> str:
        """リスクスコアからリスクレベルを判定する.

        Args:
            score: リスクスコア（0-100）。

        Returns:
            リスクレベル文字列。
        """
        if score >= RISK_LEVEL_THRESHOLDS["critical"]:
            return "critical"
        elif score >= RISK_LEVEL_THRESHOLDS["high"]:
            return "high"
        elif score >= RISK_LEVEL_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def evaluate(
        self,
        scores: dict[str, float],
        details: dict[str, dict[str, Any]] | None = None,
    ) -> IntegratedRiskResult:
        """統合リスク評価を実行する.

        Args:
            scores: コンポーネント名→スコア（0-100）のマッピング。
            details: コンポーネント別の詳細情報。

        Returns:
            IntegratedRiskResult: 統合リスク評価結果。
        """
        details = details or {}
        integrated_score = self.calculate_integrated_score(scores)
        risk_level = self.get_risk_level(integrated_score)

        components = []
        for name, weight in self.weights.items():
            score_val = scores.get(name, 0.0)
            components.append(RiskComponent(
                name=name,
                score=max(0.0, min(100.0, score_val)),
                weight=weight,
                details=details.get(name, {}),
            ))

        summary_ja = self._generate_summary_ja(integrated_score, risk_level, components)
        recommendations = self._generate_recommendations(risk_level, components)

        logger.info(
            "統合リスク評価完了: score=%.1f, level=%s",
            integrated_score, risk_level,
        )

        return IntegratedRiskResult(
            integrated_score=integrated_score,
            risk_level=risk_level,
            components=components,
            summary_ja=summary_ja,
            recommendations=recommendations,
        )

    @staticmethod
    def _generate_summary_ja(
        score: float,
        level: str,
        components: list[RiskComponent],
    ) -> str:
        """日本語サマリーを生成する.

        Args:
            score: 統合スコア。
            level: リスクレベル。
            components: コンポーネントリスト。

        Returns:
            日本語サマリー文字列。
        """
        level_ja = {
            "critical": "重大",
            "high": "高",
            "medium": "中",
            "low": "低",
        }
        level_text = level_ja.get(level, level)

        # 最も高リスクなコンポーネントを特定
        high_risk_components = [c for c in components if c.score >= 60.0]
        component_names_ja = {
            "rule_engine": "ルールエンジン",
            "discretionary_accruals": "裁量的発生高分析",
            "fraud_prediction": "不正予測モデル",
            "benford": "ベンフォード分析",
        }

        summary = f"統合リスクスコア: {score:.1f}/100 (リスクレベル: {level_text})"

        if high_risk_components:
            names = [component_names_ja.get(c.name, c.name) for c in high_risk_components]
            summary += f"\n高リスク要因: {', '.join(names)}"

        return summary

    @staticmethod
    def _generate_recommendations(
        level: str,
        components: list[RiskComponent],
    ) -> list[str]:
        """推奨アクションを生成する.

        Args:
            level: リスクレベル。
            components: コンポーネントリスト。

        Returns:
            推奨アクションリスト。
        """
        recommendations = []

        if level in ("critical", "high"):
            recommendations.append("詳細な監査手続きの実施を推奨します")
            recommendations.append("経営陣への報告を検討してください")

        for comp in components:
            if comp.score >= 80:
                if comp.name == "rule_engine":
                    recommendations.append("財務比率の異常パターンについて追加調査が必要です")
                elif comp.name == "discretionary_accruals":
                    recommendations.append("利益操作の可能性を示す高い裁量的発生高が検出されました")
                elif comp.name == "fraud_prediction":
                    recommendations.append("不正リスク指標が警告水準を超過しています")
                elif comp.name == "benford":
                    recommendations.append("仕訳データの数値分布に統計的異常が検出されました")

        if level == "low":
            recommendations.append("現時点で重大なリスクは検出されていません")

        return recommendations
