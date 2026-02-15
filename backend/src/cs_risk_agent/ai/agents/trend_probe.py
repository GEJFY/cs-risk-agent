"""トレンド分析プローブ.

複数期間の財務データからトレンドを分析し、構造変化（ブレーク）、
成長率異常、トレンド反転を検出する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from cs_risk_agent.ai.agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)

# --- 閾値定数 ---
GROWTH_ANOMALY_THRESHOLD: float = 0.30
STRUCTURAL_BREAK_THRESHOLD: float = 2.0
MIN_PERIODS_FOR_TREND: int = 3


class TrendProbe:
    """トレンド分析プローブ.

    複数期間の時系列データを分析し、構造的変化点・成長率異常・
    トレンド反転パターンを検出する。
    """

    def __init__(
        self,
        growth_threshold: float = GROWTH_ANOMALY_THRESHOLD,
        break_threshold: float = STRUCTURAL_BREAK_THRESHOLD,
        min_periods: int = MIN_PERIODS_FOR_TREND,
    ) -> None:
        """初期化.

        Args:
            growth_threshold: 成長率異常判定閾値（デフォルト30%）。
            break_threshold: 構造変化判定閾値（標準偏差の倍数）。
            min_periods: トレンド分析に必要な最小期間数。
        """
        self._growth_threshold = growth_threshold
        self._break_threshold = break_threshold
        self._min_periods = min_periods

    def analyze(self, state: AgentState) -> AgentState:
        """トレンド分析を実行する.

        時系列データの成長率パターン、構造変化、反転シグナルを検出する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            probe_resultsに検出結果を追加した状態。
        """
        logger.info(
            "trend_probe.start",
            company_id=state["company_id"],
        )
        state["current_stage"] = "trend_analysis"

        data = state.get("financial_data", {})
        if not data:
            state["errors"].append("trend_probe: 財務データが空です")
            return state

        try:
            # 時系列データ抽出
            time_series = self._extract_time_series(data)

            if time_series:
                self._analyze_growth_rates(state, time_series)
                self._detect_structural_breaks(state, time_series)
                self._detect_trend_reversals(state, time_series)
                self._check_revenue_expense_divergence(state, data)
            else:
                state["probe_results"].append({
                    "probe_name": "trend_probe",
                    "finding_type": "data_limitation",
                    "severity": "info",
                    "confidence": 1.0,
                    "description": "複数期間データが不足: トレンド分析制限あり",
                    "evidence": {"available_series": 0},
                })

        except Exception as e:
            error_msg = f"trend_probe: 分析中にエラー発生 - {e}"
            logger.error("trend_probe.error", error=str(e))
            state["errors"].append(error_msg)

        logger.info(
            "trend_probe.complete",
            findings_count=len(state["probe_results"]),
        )
        return state

    def _extract_time_series(
        self,
        data: dict[str, Any],
    ) -> dict[str, list[float]]:
        """財務データから時系列データを抽出する.

        "history" キー配下の期間別データ、または "{key}_prev" 形式の
        前年値ペアから時系列を構築する。

        Args:
            data: 財務データ辞書。

        Returns:
            指標名 -> 時系列値リストの辞書。
        """
        time_series: dict[str, list[float]] = {}

        # パターン1: "history" キー配下に期間別データ
        history = data.get("history")
        if isinstance(history, list) and len(history) >= 2:
            for period_data in history:
                if not isinstance(period_data, dict):
                    continue
                for key, value in period_data.items():
                    if isinstance(value, (int, float)) and key != "fiscal_year":
                        if key not in time_series:
                            time_series[key] = []
                        time_series[key].append(float(value))

        # パターン2: "{key}_prev" ペアから2期間の時系列を構築
        if not time_series:
            for key, value in data.items():
                if (
                    not key.endswith("_prev")
                    and isinstance(value, (int, float))
                ):
                    prev_key = f"{key}_prev"
                    prev_value = data.get(prev_key)
                    if isinstance(prev_value, (int, float)):
                        time_series[key] = [float(prev_value), float(value)]

        return time_series

    def _analyze_growth_rates(
        self,
        state: AgentState,
        time_series: dict[str, list[float]],
    ) -> None:
        """成長率分析.

        各指標の期間間成長率を算出し、異常な加速・減速パターンを検出する。

        Args:
            state: エージェント状態（結果追加先）。
            time_series: 時系列データ。
        """
        for metric, values in time_series.items():
            if len(values) < 2:
                continue

            growth_rates = self._compute_growth_rates(values)
            if not growth_rates:
                continue

            for i, rate in enumerate(growth_rates):
                if abs(rate) > self._growth_threshold:
                    period_label = f"期間{i + 1}→{i + 2}"
                    direction = "急増" if rate > 0 else "急減"
                    severity = self._classify_growth_severity(abs(rate))

                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "growth_anomaly",
                        "severity": severity,
                        "confidence": min(abs(rate) / 1.0, 0.95),
                        "description": (
                            f"成長率異常: {metric} が {period_label} で "
                            f"{rate:+.1%} {direction}"
                        ),
                        "evidence": {
                            "metric": metric,
                            "period": period_label,
                            "growth_rate": round(rate, 4),
                            "values": values,
                        },
                    })

            # 成長率の急変（加速度チェック）
            if len(growth_rates) >= 2:
                self._check_growth_acceleration(
                    state, metric, growth_rates,
                )

    def _detect_structural_breaks(
        self,
        state: AgentState,
        time_series: dict[str, list[float]],
    ) -> None:
        """構造変化（ブレーク）の検出.

        時系列の平均・分散の急変を検出し、データ生成プロセスの
        構造的変化を識別する。

        Args:
            state: エージェント状態（結果追加先）。
            time_series: 時系列データ。
        """
        for metric, values in time_series.items():
            if len(values) < self._min_periods:
                continue

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5

            if std == 0:
                continue

            # 各時点の偏差をチェック
            for i, value in enumerate(values):
                deviation = abs(value - mean) / std
                if deviation > self._break_threshold:
                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "structural_break",
                        "severity": "high",
                        "confidence": min(deviation / 5.0, 0.95),
                        "description": (
                            f"構造変化検出: {metric} の期間{i + 1}で "
                            f"平均から{deviation:.1f}σ乖離 "
                            f"(値={value:,.0f}, 平均={mean:,.0f})"
                        ),
                        "evidence": {
                            "metric": metric,
                            "period_index": i,
                            "value": value,
                            "mean": round(mean, 2),
                            "std": round(std, 2),
                            "deviation_sigma": round(deviation, 2),
                        },
                    })
                    state["risk_factors"].append(
                        f"構造変化: {metric} 期間{i + 1} ({deviation:.1f}σ)"
                    )

    def _detect_trend_reversals(
        self,
        state: AgentState,
        time_series: dict[str, list[float]],
    ) -> None:
        """トレンド反転の検出.

        連続した増加/減少トレンドが反転するパターンを検出する。

        Args:
            state: エージェント状態（結果追加先）。
            time_series: 時系列データ。
        """
        for metric, values in time_series.items():
            if len(values) < self._min_periods:
                continue

            # 差分系列
            diffs = [
                values[i + 1] - values[i]
                for i in range(len(values) - 1)
            ]

            # 符号変化の検出
            for i in range(len(diffs) - 1):
                if diffs[i] > 0 and diffs[i + 1] < 0:
                    # 増加→減少（ピーク）
                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "trend_reversal",
                        "severity": "medium",
                        "confidence": 0.70,
                        "description": (
                            f"トレンド反転（ピーク）: {metric} が "
                            f"期間{i + 2}で増加から減少に転換 "
                            f"(値={values[i + 1]:,.0f})"
                        ),
                        "evidence": {
                            "metric": metric,
                            "reversal_type": "peak",
                            "reversal_period": i + 2,
                            "peak_value": values[i + 1],
                            "values": values,
                        },
                    })
                elif diffs[i] < 0 and diffs[i + 1] > 0:
                    # 減少→増加（ボトム）
                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "trend_reversal",
                        "severity": "medium",
                        "confidence": 0.70,
                        "description": (
                            f"トレンド反転（ボトム）: {metric} が "
                            f"期間{i + 2}で減少から増加に転換 "
                            f"(値={values[i + 1]:,.0f})"
                        ),
                        "evidence": {
                            "metric": metric,
                            "reversal_type": "bottom",
                            "reversal_period": i + 2,
                            "bottom_value": values[i + 1],
                            "values": values,
                        },
                    })

    def _check_revenue_expense_divergence(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """売上と費用のトレンド乖離チェック.

        売上が減少しているのに費用が増加している（またはその逆）パターンを検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        revenue = data.get("revenue")
        revenue_prev = data.get("revenue_prev")
        cogs = data.get("cost_of_goods_sold")
        cogs_prev = data.get("cost_of_goods_sold_prev")
        sga = data.get("sga_expense")
        sga_prev = data.get("sga_expense_prev")

        if not all(
            isinstance(v, (int, float))
            for v in [revenue, revenue_prev]
            if v is not None
        ):
            return

        if revenue is not None and revenue_prev is not None and revenue_prev != 0:
            rev_growth = (revenue - revenue_prev) / abs(revenue_prev)

            # 売上原価との乖離チェック
            if all(
                isinstance(v, (int, float))
                for v in [cogs, cogs_prev]
            ) and cogs_prev != 0:
                cogs_growth = (cogs - cogs_prev) / abs(cogs_prev)
                divergence = abs(rev_growth - cogs_growth)
                if divergence > 0.20:
                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "revenue_expense_divergence",
                        "severity": "medium",
                        "confidence": min(divergence, 0.90),
                        "description": (
                            f"売上・原価トレンド乖離: "
                            f"売上成長率={rev_growth:+.1%}, "
                            f"原価成長率={cogs_growth:+.1%} "
                            f"(乖離={divergence:.1%})"
                        ),
                        "evidence": {
                            "revenue_growth": round(rev_growth, 4),
                            "cogs_growth": round(cogs_growth, 4),
                            "divergence": round(divergence, 4),
                        },
                    })

            # 販管費との乖離チェック
            if all(
                isinstance(v, (int, float))
                for v in [sga, sga_prev]
            ) and sga_prev != 0:
                sga_growth = (sga - sga_prev) / abs(sga_prev)
                if rev_growth < -0.10 and sga_growth > 0.10:
                    state["probe_results"].append({
                        "probe_name": "trend_probe",
                        "finding_type": "revenue_expense_divergence",
                        "severity": "high",
                        "confidence": 0.80,
                        "description": (
                            f"売上減少下の販管費増加: "
                            f"売上={rev_growth:+.1%}, "
                            f"販管費={sga_growth:+.1%}"
                        ),
                        "evidence": {
                            "revenue_growth": round(rev_growth, 4),
                            "sga_growth": round(sga_growth, 4),
                        },
                    })
                    state["risk_factors"].append(
                        f"売上減少下の販管費増加: "
                        f"売上{rev_growth:+.1%} vs 販管費{sga_growth:+.1%}"
                    )

    def _check_growth_acceleration(
        self,
        state: AgentState,
        metric: str,
        growth_rates: list[float],
    ) -> None:
        """成長率の加速度（二階差分）チェック.

        成長率自体の急変を検出する。

        Args:
            state: エージェント状態（結果追加先）。
            metric: 指標名。
            growth_rates: 成長率のリスト。
        """
        for i in range(len(growth_rates) - 1):
            acceleration = growth_rates[i + 1] - growth_rates[i]
            if abs(acceleration) > self._growth_threshold * 2:
                state["probe_results"].append({
                    "probe_name": "trend_probe",
                    "finding_type": "growth_acceleration_anomaly",
                    "severity": "medium",
                    "confidence": 0.65,
                    "description": (
                        f"成長率急変: {metric} の成長率が "
                        f"{growth_rates[i]:+.1%} → {growth_rates[i + 1]:+.1%} "
                        f"(加速度={acceleration:+.1%})"
                    ),
                    "evidence": {
                        "metric": metric,
                        "growth_rate_before": round(growth_rates[i], 4),
                        "growth_rate_after": round(growth_rates[i + 1], 4),
                        "acceleration": round(acceleration, 4),
                    },
                })

    @staticmethod
    def _compute_growth_rates(values: list[float]) -> list[float]:
        """時系列値から成長率を算出する.

        Args:
            values: 時系列値リスト。

        Returns:
            期間間成長率のリスト。
        """
        rates: list[float] = []
        for i in range(len(values) - 1):
            if values[i] == 0:
                continue
            rates.append((values[i + 1] - values[i]) / abs(values[i]))
        return rates

    @staticmethod
    def _classify_growth_severity(abs_rate: float) -> str:
        """成長率の絶対値に基づく重大度分類.

        Args:
            abs_rate: 成長率の絶対値。

        Returns:
            重大度文字列。
        """
        if abs_rate > 1.0:
            return "critical"
        if abs_rate > 0.50:
            return "high"
        return "medium"
