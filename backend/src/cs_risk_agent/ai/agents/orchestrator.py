"""LangGraph AIエージェント オーケストレーター.

Perception -> Analysis -> Interpretation -> Cross-Reference の
4段階パイプラインで財務データの探索分析を実行する。
"""

from __future__ import annotations

from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

logger = structlog.get_logger(__name__)


class AgentState(TypedDict):
    """エージェント状態.

    Attributes:
        company_id: 対象企業ID。
        fiscal_year: 対象会計年度。
        financial_data: 財務データ辞書。
        probe_results: 各プローブの検出結果リスト。
        insights: 分析から得られた洞察リスト。
        risk_factors: 識別されたリスク要因リスト。
        final_report: 最終レポート文字列。
        current_stage: 現在の処理段階。
        errors: エラーメッセージリスト。
    """

    company_id: str
    fiscal_year: int
    financial_data: dict[str, Any]
    probe_results: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    risk_factors: list[str]
    final_report: str
    current_stage: str
    errors: list[str]


class AnalysisOrchestrator:
    """分析オーケストレーター - LangGraph State Machine.

    5つの専門プローブ（異常値検出・財務比率・トレンド・関連当事者・
    クロスリファレンス）を順次実行し、統合レポートを生成する。
    """

    def __init__(self) -> None:
        """初期化."""
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """LangGraphグラフ構築.

        Returns:
            コンパイル済みのLangGraphワークフロー。
        """
        from cs_risk_agent.ai.agents.anomaly_probe import AnomalyProbe
        from cs_risk_agent.ai.agents.cross_ref_probe import CrossReferenceProbe
        from cs_risk_agent.ai.agents.ratio_probe import RatioProbe
        from cs_risk_agent.ai.agents.relationship_probe import RelationshipProbe
        from cs_risk_agent.ai.agents.trend_probe import TrendProbe

        anomaly = AnomalyProbe()
        ratio = RatioProbe()
        trend = TrendProbe()
        relationship = RelationshipProbe()
        cross_ref = CrossReferenceProbe()

        workflow = StateGraph(AgentState)

        # ノード登録
        workflow.add_node("perception", self._perception_stage)
        workflow.add_node("anomaly_analysis", anomaly.analyze)
        workflow.add_node("ratio_analysis", ratio.analyze)
        workflow.add_node("trend_analysis", trend.analyze)
        workflow.add_node("relationship_analysis", relationship.analyze)
        workflow.add_node("cross_reference", cross_ref.analyze)
        workflow.add_node("report_generation", self._generate_report)

        # エッジ定義: 線形パイプライン
        workflow.set_entry_point("perception")
        workflow.add_edge("perception", "anomaly_analysis")
        workflow.add_edge("anomaly_analysis", "ratio_analysis")
        workflow.add_edge("ratio_analysis", "trend_analysis")
        workflow.add_edge("trend_analysis", "relationship_analysis")
        workflow.add_edge("relationship_analysis", "cross_reference")
        workflow.add_edge("cross_reference", "report_generation")
        workflow.add_edge("report_generation", END)

        return workflow.compile()

    def _perception_stage(self, state: AgentState) -> AgentState:
        """知覚段階 - データの概要把握.

        財務データの構造と規模を確認し、後続プローブに必要な
        初期情報を状態に格納する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            更新されたエージェント状態。
        """
        logger.info("orchestrator.perception", company_id=state["company_id"])
        state["current_stage"] = "perception"
        state["probe_results"] = state.get("probe_results", [])
        state["insights"] = state.get("insights", [])
        state["risk_factors"] = state.get("risk_factors", [])
        state["errors"] = state.get("errors", [])

        data = state.get("financial_data", {})
        state["probe_results"].append({
            "probe_name": "perception",
            "finding_type": "data_summary",
            "severity": "info",
            "confidence": 1.0,
            "description": f"財務データ概要: {len(data)} 項目を検出",
            "evidence": {"data_keys": list(data.keys())[:20]},
        })
        return state

    def _generate_report(self, state: AgentState) -> AgentState:
        """最終レポート生成.

        全プローブの検出結果を集約し、Markdown形式のレポートを生成する。

        Args:
            state: 全プローブ実行後のエージェント状態。

        Returns:
            final_reportを設定した最終状態。
        """
        logger.info(
            "orchestrator.report_generation",
            company_id=state["company_id"],
        )
        state["current_stage"] = "report"

        findings = state.get("probe_results", [])
        high_severity = [
            f for f in findings
            if f.get("severity") in ("critical", "high")
        ]

        report_lines = [
            f"# AI分析レポート - 企業ID: {state['company_id']}",
            f"## 対象期間: {state['fiscal_year']}年度",
            "",
            "## サマリー",
            f"- 検出された所見: {len(findings)}件",
            f"- 高リスク所見: {len(high_severity)}件",
            f"- リスク要因: {len(state.get('risk_factors', []))}件",
            "",
            "## 主要所見",
        ]
        for f in high_severity[:10]:
            report_lines.append(
                f"- [{f['severity'].upper()}] {f['description']}"
            )

        if state.get("risk_factors"):
            report_lines.append("\n## リスク要因")
            for rf in state["risk_factors"][:10]:
                report_lines.append(f"- {rf}")

        if state.get("errors"):
            report_lines.append("\n## エラー")
            for e in state["errors"]:
                report_lines.append(f"- {e}")

        state["final_report"] = "\n".join(report_lines)
        return state

    async def run(
        self,
        company_id: str,
        fiscal_year: int,
        financial_data: dict[str, Any],
    ) -> dict[str, Any]:
        """分析実行.

        LangGraphワークフローを非同期で実行し、全プローブの結果を
        統合した分析結果を返す。

        Args:
            company_id: 対象企業ID。
            fiscal_year: 対象会計年度。
            financial_data: 財務データ辞書。

        Returns:
            分析結果を含む状態辞書。
        """
        initial_state: AgentState = {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "financial_data": financial_data,
            "probe_results": [],
            "insights": [],
            "risk_factors": [],
            "final_report": "",
            "current_stage": "init",
            "errors": [],
        }

        try:
            result = await self._graph.ainvoke(initial_state)
            return dict(result)
        except Exception as e:
            logger.error("orchestrator.error", error=str(e))
            initial_state["errors"].append(str(e))
            initial_state["final_report"] = f"分析中にエラーが発生: {e}"
            return dict(initial_state)
