"""クロスリファレンスプローブ - 全プローブ結果の相互参照分析."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from cs_risk_agent.ai.agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)


class CrossReferenceProbe:
    """クロスリファレンスプローブ.

    全プローブの検出結果を相互参照し、複数手法で裏付けられた
    高リスク所見を統合評価する。
    """

    def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        """全プローブ結果を相互参照して統合評価.

        複数のプローブで高リスクが検出された場合、相互裏付けとして
        信頼度を高める。検出数に基づいて重大度を判定する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            相互参照結果を追加した状態。
        """
        logger.info("cross_ref_probe.start", company_id=state.get("company_id"))

        try:
            results = state.get("probe_results", [])
            high_findings = [
                r
                for r in results
                if r.get("severity") in ("critical", "high")
            ]

            if len(high_findings) >= 3:
                state["probe_results"].append(
                    {
                        "probe_name": "cross_reference",
                        "finding_type": "corroborating_evidence",
                        "severity": "critical",
                        "confidence": 0.9,
                        "description": (
                            f"複数プローブで{len(high_findings)}件の"
                            "高リスク所見が相互に裏付けられています"
                        ),
                        "evidence": {
                            "high_finding_count": len(high_findings),
                            "probe_names": list(
                                {f.get("probe_name") for f in high_findings}
                            ),
                        },
                    }
                )
                state["risk_factors"].append(
                    "複数の分析手法で高リスクが確認されています"
                )
            elif len(high_findings) >= 1:
                state["probe_results"].append(
                    {
                        "probe_name": "cross_reference",
                        "finding_type": "partial_evidence",
                        "severity": "medium",
                        "confidence": 0.7,
                        "description": (
                            f"{len(high_findings)}件の高リスク所見を検出。"
                            "追加調査を推奨"
                        ),
                        "evidence": {
                            "high_finding_count": len(high_findings),
                        },
                    }
                )
            else:
                state["probe_results"].append(
                    {
                        "probe_name": "cross_reference",
                        "finding_type": "no_major_issues",
                        "severity": "low",
                        "confidence": 0.8,
                        "description": (
                            "クロスリファレンス分析で重大な懸念は"
                            "検出されませんでした"
                        ),
                        "evidence": {},
                    }
                )

            state["current_stage"] = "cross_reference"

        except Exception as e:
            state.setdefault("errors", []).append(f"CrossReferenceProbe: {e}")
            logger.error("cross_ref_probe.error", error=str(e))

        logger.info(
            "cross_ref_probe.complete",
            findings_count=len(state.get("probe_results", [])),
        )
        return state
