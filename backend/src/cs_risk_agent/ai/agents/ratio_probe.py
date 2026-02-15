"""財務比率分析プローブ.

ROE、ROA、利益率、回転率、D/Eレシオ、流動比率などの
主要財務比率を算出し、異常値をフラグする。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from cs_risk_agent.ai.agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RatioThreshold:
    """財務比率の正常範囲定義.

    Attributes:
        name: 比率名称。
        lower: 正常範囲下限。
        upper: 正常範囲上限。
        severity_on_breach: 逸脱時の重大度。
    """

    name: str
    lower: float
    upper: float
    severity_on_breach: str = "medium"


# --- 財務比率の正常範囲定義 ---
DEFAULT_RATIO_THRESHOLDS: list[RatioThreshold] = [
    # 収益性指標
    RatioThreshold("roe", -0.30, 0.40, "high"),
    RatioThreshold("roa", -0.15, 0.25, "high"),
    RatioThreshold("gross_margin", 0.05, 0.85, "medium"),
    RatioThreshold("operating_margin", -0.20, 0.40, "medium"),
    RatioThreshold("net_margin", -0.25, 0.30, "high"),
    # 効率性指標
    RatioThreshold("asset_turnover", 0.10, 5.00, "medium"),
    RatioThreshold("inventory_turnover", 1.00, 50.00, "medium"),
    RatioThreshold("receivables_turnover", 2.00, 30.00, "medium"),
    # 安全性指標
    RatioThreshold("debt_equity_ratio", 0.00, 4.00, "high"),
    RatioThreshold("current_ratio", 0.30, 6.00, "high"),
    RatioThreshold("quick_ratio", 0.20, 5.00, "medium"),
    RatioThreshold("interest_coverage", 0.50, 100.00, "critical"),
]


class RatioProbe:
    """財務比率分析プローブ.

    主要財務比率を算出し、事前定義された正常範囲と比較して
    異常値を検出する。
    """

    def __init__(
        self,
        thresholds: list[RatioThreshold] | None = None,
    ) -> None:
        """初期化.

        Args:
            thresholds: 比率閾値リスト。Noneの場合はデフォルト値を使用。
        """
        self._thresholds = {
            t.name: t for t in (thresholds or DEFAULT_RATIO_THRESHOLDS)
        }

    def analyze(self, state: AgentState) -> AgentState:
        """財務比率分析を実行する.

        財務データから主要比率を算出し、正常範囲外の比率を
        検出結果として報告する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            probe_resultsに検出結果を追加した状態。
        """
        logger.info(
            "ratio_probe.start",
            company_id=state["company_id"],
        )
        state["current_stage"] = "ratio_analysis"

        data = state.get("financial_data", {})
        if not data:
            state["errors"].append("ratio_probe: 財務データが空です")
            return state

        try:
            # 比率算出
            ratios = self._calculate_ratios(data)
            # 算出結果をデータに追記（後続プローブでの利用用）
            data.update(ratios)

            # 正常範囲チェック
            self._check_ratio_anomalies(state, ratios)

            # 比率間整合性チェック
            self._check_ratio_consistency(state, ratios)

            # 算出結果サマリーを追加
            state["probe_results"].append({
                "probe_name": "ratio_probe",
                "finding_type": "ratio_summary",
                "severity": "info",
                "confidence": 1.0,
                "description": f"財務比率算出完了: {len(ratios)}指標を計算",
                "evidence": {
                    "calculated_ratios": {
                        k: round(v, 4) for k, v in ratios.items()
                    },
                },
            })

        except Exception as e:
            error_msg = f"ratio_probe: 分析中にエラー発生 - {e}"
            logger.error("ratio_probe.error", error=str(e))
            state["errors"].append(error_msg)

        logger.info(
            "ratio_probe.complete",
            findings_count=len(state["probe_results"]),
        )
        return state

    def _calculate_ratios(self, data: dict[str, Any]) -> dict[str, float]:
        """主要財務比率を算出する.

        利用可能なデータから算出可能な比率をすべて計算する。
        分母がゼロの場合はその比率をスキップする。

        Args:
            data: 財務データ辞書。

        Returns:
            算出された財務比率の辞書。
        """
        ratios: dict[str, float] = {}

        # --- 収益性指標 ---
        ratios.update(self._calc_profitability_ratios(data))
        # --- 効率性指標 ---
        ratios.update(self._calc_efficiency_ratios(data))
        # --- 安全性指標 ---
        ratios.update(self._calc_safety_ratios(data))

        return ratios

    def _calc_profitability_ratios(
        self,
        data: dict[str, Any],
    ) -> dict[str, float]:
        """収益性指標の算出.

        ROE、ROA、粗利率、営業利益率、純利益率を算出する。

        Args:
            data: 財務データ辞書。

        Returns:
            収益性指標の辞書。
        """
        ratios: dict[str, float] = {}

        # ROE = 純利益 / 自己資本
        net_income = data.get("net_income")
        equity = data.get("total_equity")
        if self._is_calculable(net_income, equity):
            ratios["roe"] = net_income / equity

        # ROA = 純利益 / 総資産
        total_assets = data.get("total_assets")
        if self._is_calculable(net_income, total_assets):
            ratios["roa"] = net_income / total_assets

        # 粗利率 = 売上総利益 / 売上高
        gross_profit = data.get("gross_profit")
        revenue = data.get("revenue")
        if self._is_calculable(gross_profit, revenue):
            ratios["gross_margin"] = gross_profit / revenue

        # 営業利益率 = 営業利益 / 売上高
        operating_income = data.get("operating_income")
        if self._is_calculable(operating_income, revenue):
            ratios["operating_margin"] = operating_income / revenue

        # 純利益率 = 純利益 / 売上高
        if self._is_calculable(net_income, revenue):
            ratios["net_margin"] = net_income / revenue

        return ratios

    def _calc_efficiency_ratios(
        self,
        data: dict[str, Any],
    ) -> dict[str, float]:
        """効率性指標の算出.

        総資産回転率、棚卸資産回転率、売掛金回転率を算出する。

        Args:
            data: 財務データ辞書。

        Returns:
            効率性指標の辞書。
        """
        ratios: dict[str, float] = {}

        revenue = data.get("revenue")
        total_assets = data.get("total_assets")

        # 総資産回転率 = 売上高 / 総資産
        if self._is_calculable(revenue, total_assets):
            ratios["asset_turnover"] = revenue / total_assets

        # 棚卸資産回転率 = 売上原価 / 棚卸資産
        cogs = data.get("cost_of_goods_sold")
        inventory = data.get("inventory")
        if self._is_calculable(cogs, inventory):
            ratios["inventory_turnover"] = cogs / inventory

        # 売掛金回転率 = 売上高 / 売掛金
        receivables = data.get("receivables")
        if self._is_calculable(revenue, receivables):
            ratios["receivables_turnover"] = revenue / receivables

        return ratios

    def _calc_safety_ratios(
        self,
        data: dict[str, Any],
    ) -> dict[str, float]:
        """安全性指標の算出.

        D/Eレシオ、流動比率、当座比率、インタレストカバレッジを算出する。

        Args:
            data: 財務データ辞書。

        Returns:
            安全性指標の辞書。
        """
        ratios: dict[str, float] = {}

        total_liabilities = data.get("total_liabilities")
        equity = data.get("total_equity")
        current_assets = data.get("current_assets")
        current_liabilities = data.get("current_liabilities")

        # D/Eレシオ = 負債合計 / 自己資本
        if self._is_calculable(total_liabilities, equity):
            ratios["debt_equity_ratio"] = total_liabilities / equity

        # 流動比率 = 流動資産 / 流動負債
        if self._is_calculable(current_assets, current_liabilities):
            ratios["current_ratio"] = current_assets / current_liabilities

        # 当座比率 = (流動資産 - 棚卸資産) / 流動負債
        inventory = data.get("inventory", 0)
        if self._is_calculable(current_assets, current_liabilities):
            quick_assets = current_assets - (
                inventory if isinstance(inventory, (int, float)) else 0
            )
            ratios["quick_ratio"] = quick_assets / current_liabilities

        # インタレストカバレッジ = 営業利益 / 支払利息
        operating_income = data.get("operating_income")
        interest_expense = data.get("interest_expense")
        if self._is_calculable(operating_income, interest_expense):
            ratios["interest_coverage"] = operating_income / interest_expense

        return ratios

    def _check_ratio_anomalies(
        self,
        state: AgentState,
        ratios: dict[str, float],
    ) -> None:
        """算出された比率の正常範囲チェック.

        各比率を事前定義された閾値と比較し、逸脱を検出する。

        Args:
            state: エージェント状態（結果追加先）。
            ratios: 算出済み財務比率。
        """
        for ratio_name, value in ratios.items():
            threshold = self._thresholds.get(ratio_name)
            if threshold is None:
                continue

            if value < threshold.lower or value > threshold.upper:
                deviation = "下限以下" if value < threshold.lower else "上限以上"
                state["probe_results"].append({
                    "probe_name": "ratio_probe",
                    "finding_type": "ratio_anomaly",
                    "severity": threshold.severity_on_breach,
                    "confidence": 0.85,
                    "description": (
                        f"財務比率異常: {ratio_name} = {value:.4f} "
                        f"(正常範囲: {threshold.lower:.2f}~{threshold.upper:.2f}, "
                        f"{deviation})"
                    ),
                    "evidence": {
                        "ratio_name": ratio_name,
                        "value": round(value, 4),
                        "lower_bound": threshold.lower,
                        "upper_bound": threshold.upper,
                        "deviation": deviation,
                    },
                })
                state["risk_factors"].append(
                    f"財務比率異常: {ratio_name} = {value:.4f}"
                )

    def _check_ratio_consistency(
        self,
        state: AgentState,
        ratios: dict[str, float],
    ) -> None:
        """比率間の整合性チェック.

        DuPont分析の整合性など、比率間の論理的関係を検証する。

        Args:
            state: エージェント状態（結果追加先）。
            ratios: 算出済み財務比率。
        """
        # DuPont分析: ROE ≒ 純利益率 × 総資産回転率 × 財務レバレッジ
        roe = ratios.get("roe")
        net_margin = ratios.get("net_margin")
        asset_turnover = ratios.get("asset_turnover")
        de_ratio = ratios.get("debt_equity_ratio")

        if all(v is not None for v in [roe, net_margin, asset_turnover, de_ratio]):
            # 財務レバレッジ = 1 + D/E
            financial_leverage = 1.0 + de_ratio
            dupont_roe = net_margin * asset_turnover * financial_leverage
            discrepancy = abs(roe - dupont_roe)

            if discrepancy > 0.05:
                state["probe_results"].append({
                    "probe_name": "ratio_probe",
                    "finding_type": "ratio_inconsistency",
                    "severity": "medium",
                    "confidence": 0.70,
                    "description": (
                        f"DuPont分析不整合: 実ROE={roe:.4f}, "
                        f"DuPont ROE={dupont_roe:.4f} "
                        f"(乖離={discrepancy:.4f})"
                    ),
                    "evidence": {
                        "actual_roe": round(roe, 4),
                        "dupont_roe": round(dupont_roe, 4),
                        "net_margin": round(net_margin, 4),
                        "asset_turnover": round(asset_turnover, 4),
                        "financial_leverage": round(financial_leverage, 4),
                        "discrepancy": round(discrepancy, 4),
                    },
                })

        # 粗利率 > 営業利益率 の検証
        gross_margin = ratios.get("gross_margin")
        operating_margin = ratios.get("operating_margin")
        if (
            gross_margin is not None
            and operating_margin is not None
            and operating_margin > gross_margin
        ):
            state["probe_results"].append({
                "probe_name": "ratio_probe",
                "finding_type": "ratio_inconsistency",
                "severity": "high",
                "confidence": 0.95,
                "description": (
                    f"利益率不整合: 営業利益率({operating_margin:.4f}) > "
                    f"粗利率({gross_margin:.4f})"
                ),
                "evidence": {
                    "gross_margin": round(gross_margin, 4),
                    "operating_margin": round(operating_margin, 4),
                },
            })
            state["risk_factors"].append(
                "利益率の論理的不整合（営業利益率 > 粗利率）"
            )

    @staticmethod
    def _is_calculable(
        numerator: Any,
        denominator: Any,
    ) -> bool:
        """比率算出可否を判定する.

        分子・分母が数値であり、分母がゼロでないことを確認する。

        Args:
            numerator: 分子。
            denominator: 分母。

        Returns:
            算出可能な場合True。
        """
        return (
            isinstance(numerator, (int, float))
            and isinstance(denominator, (int, float))
            and denominator != 0
        )
