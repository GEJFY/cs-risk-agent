"""異常値検出プローブ.

Zスコア外れ値（>3σ）、前年比急変動（>50%）、業界基準逸脱を
検出し、財務データの異常パターンを識別する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from cs_risk_agent.ai.agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)

# --- 検出閾値定数 ---
Z_SCORE_THRESHOLD: float = 3.0
YOY_CHANGE_THRESHOLD: float = 0.50
# 業界基準レンジ（勘定科目 -> (下限, 上限)）
INDUSTRY_NORMS: dict[str, tuple[float, float]] = {
    "revenue_growth": (-0.30, 0.50),
    "gross_margin": (0.10, 0.80),
    "operating_margin": (-0.10, 0.40),
    "net_margin": (-0.20, 0.30),
    "current_ratio": (0.50, 5.00),
    "debt_equity_ratio": (0.00, 3.00),
    "inventory_turnover": (1.0, 50.0),
    "receivables_turnover": (2.0, 30.0),
}


class AnomalyProbe:
    """異常値検出プローブ.

    財務データに対して統計的異常検出を実行し、
    Zスコア外れ値・前年比急変動・業界基準逸脱の3手法で
    異常パターンを識別する。
    """

    def __init__(
        self,
        z_threshold: float = Z_SCORE_THRESHOLD,
        yoy_threshold: float = YOY_CHANGE_THRESHOLD,
        industry_norms: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """初期化.

        Args:
            z_threshold: Zスコア外れ値判定閾値（デフォルト3.0）。
            yoy_threshold: 前年比変動率閾値（デフォルト50%）。
            industry_norms: 業界基準レンジ辞書。Noneの場合はデフォルト値を使用。
        """
        self._z_threshold = z_threshold
        self._yoy_threshold = yoy_threshold
        self._industry_norms = industry_norms or INDUSTRY_NORMS

    def analyze(self, state: AgentState) -> AgentState:
        """異常値分析を実行する.

        Zスコア分析・前年比分析・業界基準比較の3段階で
        財務データの異常を検出する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            probe_resultsに検出結果を追加した状態。
        """
        logger.info(
            "anomaly_probe.start",
            company_id=state["company_id"],
        )
        state["current_stage"] = "anomaly_analysis"

        data = state.get("financial_data", {})
        if not data:
            state["errors"].append("anomaly_probe: 財務データが空です")
            return state

        try:
            self._detect_z_score_outliers(state, data)
            self._detect_yoy_changes(state, data)
            self._detect_industry_norm_deviations(state, data)
        except Exception as e:
            error_msg = f"anomaly_probe: 分析中にエラー発生 - {e}"
            logger.error("anomaly_probe.error", error=str(e))
            state["errors"].append(error_msg)

        logger.info(
            "anomaly_probe.complete",
            findings_count=len(state["probe_results"]),
        )
        return state

    def _detect_z_score_outliers(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """Zスコアによる外れ値検出.

        各数値項目の平均・標準偏差を算出し、|Z| > 閾値の項目を
        外れ値として報告する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        numeric_items = self._extract_numeric_items(data)
        if len(numeric_items) < 3:
            return

        values = list(numeric_items.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5

        if std == 0:
            return

        for key, value in numeric_items.items():
            z_score = abs((value - mean) / std)
            if z_score > self._z_threshold:
                severity = "critical" if z_score > 5.0 else "high"
                state["probe_results"].append({
                    "probe_name": "anomaly_probe",
                    "finding_type": "z_score_outlier",
                    "severity": severity,
                    "confidence": min(z_score / 10.0, 1.0),
                    "description": (
                        f"Zスコア外れ値検出: {key} = {value:,.0f} "
                        f"(Z={z_score:.2f}, 閾値={self._z_threshold})"
                    ),
                    "evidence": {
                        "item": key,
                        "value": value,
                        "z_score": round(z_score, 4),
                        "mean": round(mean, 4),
                        "std": round(std, 4),
                    },
                })
                state["risk_factors"].append(
                    f"統計的外れ値: {key} (Z={z_score:.2f})"
                )

    def _detect_yoy_changes(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """前年比急変動の検出.

        前年データとの比較で変動率が閾値を超える項目を検出する。
        前年値キーは "{key}_prev" の命名規則を想定。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        for key, current_value in data.items():
            if not isinstance(current_value, (int, float)):
                continue

            prev_key = f"{key}_prev"
            prev_value = data.get(prev_key)
            if prev_value is None or not isinstance(prev_value, (int, float)):
                continue
            if prev_value == 0:
                continue

            change_rate = (current_value - prev_value) / abs(prev_value)

            if abs(change_rate) > self._yoy_threshold:
                direction = "増加" if change_rate > 0 else "減少"
                severity = self._classify_yoy_severity(abs(change_rate))
                state["probe_results"].append({
                    "probe_name": "anomaly_probe",
                    "finding_type": "yoy_sudden_change",
                    "severity": severity,
                    "confidence": min(abs(change_rate), 1.0),
                    "description": (
                        f"前年比急変動: {key} が {abs(change_rate):.1%} {direction} "
                        f"({prev_value:,.0f} -> {current_value:,.0f})"
                    ),
                    "evidence": {
                        "item": key,
                        "current_value": current_value,
                        "previous_value": prev_value,
                        "change_rate": round(change_rate, 4),
                        "direction": direction,
                    },
                })
                state["risk_factors"].append(
                    f"前年比急変動: {key} ({abs(change_rate):.1%} {direction})"
                )

    def _detect_industry_norm_deviations(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """業界基準からの逸脱検出.

        事前定義された業界基準レンジと比較し、
        範囲外の指標を検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        for metric, (lower, upper) in self._industry_norms.items():
            value = data.get(metric)
            if value is None or not isinstance(value, (int, float)):
                continue

            if value < lower or value > upper:
                deviation_direction = "下限以下" if value < lower else "上限以上"
                boundary = lower if value < lower else upper
                deviation_pct = abs(value - boundary) / abs(boundary) if boundary != 0 else 0

                severity = "high" if deviation_pct > 0.5 else "medium"
                state["probe_results"].append({
                    "probe_name": "anomaly_probe",
                    "finding_type": "industry_norm_deviation",
                    "severity": severity,
                    "confidence": min(deviation_pct + 0.5, 1.0),
                    "description": (
                        f"業界基準逸脱: {metric} = {value:.4f} "
                        f"(基準範囲: {lower:.2f}~{upper:.2f}, {deviation_direction})"
                    ),
                    "evidence": {
                        "metric": metric,
                        "value": value,
                        "lower_bound": lower,
                        "upper_bound": upper,
                        "deviation_direction": deviation_direction,
                        "deviation_pct": round(deviation_pct, 4),
                    },
                })

    @staticmethod
    def _classify_yoy_severity(abs_change_rate: float) -> str:
        """前年比変動率に基づく重大度分類.

        Args:
            abs_change_rate: 変動率の絶対値。

        Returns:
            重大度文字列（critical/high/medium）。
        """
        if abs_change_rate > 1.0:
            return "critical"
        if abs_change_rate > 0.75:
            return "high"
        return "medium"

    @staticmethod
    def _extract_numeric_items(data: dict[str, Any]) -> dict[str, float]:
        """辞書から数値項目のみを抽出する.

        "_prev" サフィックス付きの前年値は除外する。

        Args:
            data: 財務データ辞書。

        Returns:
            数値項目のみの辞書。
        """
        return {
            k: float(v)
            for k, v in data.items()
            if isinstance(v, (int, float))
            and not k.endswith("_prev")
        }
