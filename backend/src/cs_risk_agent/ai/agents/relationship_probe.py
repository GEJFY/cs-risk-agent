"""関連当事者取引分析プローブ.

関連当事者間取引パターン、企業間残高の異常、循環取引の兆候を
検出し、利益操作リスクを評価する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from cs_risk_agent.ai.agents.orchestrator import AgentState

logger = structlog.get_logger(__name__)

# --- 閾値定数 ---
RELATED_PARTY_REVENUE_THRESHOLD: float = 0.30
RELATED_PARTY_RECEIVABLE_THRESHOLD: float = 0.25
INTERCOMPANY_BALANCE_THRESHOLD: float = 0.20
ROUND_NUMBER_TOLERANCE: float = 0.001


class RelationshipProbe:
    """関連当事者取引分析プローブ.

    関連当事者との取引パターン・企業間残高を分析し、
    不正リスクの兆候を検出する。
    """

    def __init__(
        self,
        revenue_threshold: float = RELATED_PARTY_REVENUE_THRESHOLD,
        receivable_threshold: float = RELATED_PARTY_RECEIVABLE_THRESHOLD,
        balance_threshold: float = INTERCOMPANY_BALANCE_THRESHOLD,
    ) -> None:
        """初期化.

        Args:
            revenue_threshold: 関連当事者売上比率の警告閾値。
            receivable_threshold: 関連当事者売掛金比率の警告閾値。
            balance_threshold: 企業間残高の対総資産比率警告閾値。
        """
        self._revenue_threshold = revenue_threshold
        self._receivable_threshold = receivable_threshold
        self._balance_threshold = balance_threshold

    def analyze(self, state: AgentState) -> AgentState:
        """関連当事者取引分析を実行する.

        取引集中度・残高異常・循環取引兆候・期末取引集中を検出する。

        Args:
            state: 現在のエージェント状態。

        Returns:
            probe_resultsに検出結果を追加した状態。
        """
        logger.info(
            "relationship_probe.start",
            company_id=state["company_id"],
        )
        state["current_stage"] = "relationship_analysis"

        data = state.get("financial_data", {})
        if not data:
            state["errors"].append(
                "relationship_probe: 財務データが空です"
            )
            return state

        try:
            self._analyze_related_party_concentration(state, data)
            self._analyze_intercompany_balances(state, data)
            self._detect_circular_transaction_signals(state, data)
            self._detect_period_end_anomalies(state, data)
            self._analyze_related_party_transactions(state, data)
        except Exception as e:
            error_msg = f"relationship_probe: 分析中にエラー発生 - {e}"
            logger.error("relationship_probe.error", error=str(e))
            state["errors"].append(error_msg)

        logger.info(
            "relationship_probe.complete",
            findings_count=len(state["probe_results"]),
        )
        return state

    def _analyze_related_party_concentration(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """関連当事者取引の集中度分析.

        売上・仕入・売掛金・買掛金における関連当事者の占有率を検証する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        # 関連当事者売上の集中度
        rp_revenue = data.get("related_party_revenue")
        revenue = data.get("revenue")
        if self._is_valid_pair(rp_revenue, revenue):
            ratio = rp_revenue / revenue
            if ratio > self._revenue_threshold:
                severity = "critical" if ratio > 0.50 else "high"
                state["probe_results"].append({
                    "probe_name": "relationship_probe",
                    "finding_type": "related_party_concentration",
                    "severity": severity,
                    "confidence": 0.90,
                    "description": (
                        f"関連当事者売上集中: 売上の{ratio:.1%}が関連当事者向け "
                        f"(閾値: {self._revenue_threshold:.1%})"
                    ),
                    "evidence": {
                        "related_party_revenue": rp_revenue,
                        "total_revenue": revenue,
                        "concentration_ratio": round(ratio, 4),
                        "threshold": self._revenue_threshold,
                    },
                })
                state["risk_factors"].append(
                    f"関連当事者売上集中度: {ratio:.1%}"
                )

        # 関連当事者売掛金の集中度
        rp_receivables = data.get("related_party_receivables")
        receivables = data.get("receivables")
        if self._is_valid_pair(rp_receivables, receivables):
            ratio = rp_receivables / receivables
            if ratio > self._receivable_threshold:
                state["probe_results"].append({
                    "probe_name": "relationship_probe",
                    "finding_type": "related_party_concentration",
                    "severity": "high",
                    "confidence": 0.85,
                    "description": (
                        f"関連当事者売掛金集中: 売掛金の{ratio:.1%}が"
                        f"関連当事者からの残高 "
                        f"(閾値: {self._receivable_threshold:.1%})"
                    ),
                    "evidence": {
                        "related_party_receivables": rp_receivables,
                        "total_receivables": receivables,
                        "concentration_ratio": round(ratio, 4),
                        "threshold": self._receivable_threshold,
                    },
                })

        # 関連当事者仕入の集中度
        rp_purchases = data.get("related_party_purchases")
        cogs = data.get("cost_of_goods_sold")
        if self._is_valid_pair(rp_purchases, cogs):
            ratio = rp_purchases / cogs
            if ratio > self._revenue_threshold:
                state["probe_results"].append({
                    "probe_name": "relationship_probe",
                    "finding_type": "related_party_concentration",
                    "severity": "high",
                    "confidence": 0.85,
                    "description": (
                        f"関連当事者仕入集中: 仕入の{ratio:.1%}が"
                        f"関連当事者からの調達 "
                        f"(閾値: {self._revenue_threshold:.1%})"
                    ),
                    "evidence": {
                        "related_party_purchases": rp_purchases,
                        "total_cogs": cogs,
                        "concentration_ratio": round(ratio, 4),
                    },
                })

    def _analyze_intercompany_balances(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """企業間残高の異常分析.

        グループ企業間の債権・債務残高の不均衡や
        対総資産比率の異常を検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        total_assets = data.get("total_assets")
        if not isinstance(total_assets, (int, float)) or total_assets == 0:
            return

        # 企業間残高リスト
        ic_balances = data.get("intercompany_balances")
        if not isinstance(ic_balances, list):
            # 単一値のケース
            ic_receivables = data.get("intercompany_receivables", 0)
            ic_payables = data.get("intercompany_payables", 0)
            if isinstance(ic_receivables, (int, float)):
                ratio = abs(ic_receivables) / total_assets
                if ratio > self._balance_threshold:
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "intercompany_balance_anomaly",
                        "severity": "high",
                        "confidence": 0.80,
                        "description": (
                            f"企業間債権残高過大: "
                            f"対総資産比率={ratio:.1%} "
                            f"(閾値: {self._balance_threshold:.1%})"
                        ),
                        "evidence": {
                            "intercompany_receivables": ic_receivables,
                            "total_assets": total_assets,
                            "ratio": round(ratio, 4),
                        },
                    })
                    state["risk_factors"].append(
                        f"企業間債権残高過大: 対総資産{ratio:.1%}"
                    )

            # 企業間債権と債務の不均衡チェック
            if (
                isinstance(ic_receivables, (int, float))
                and isinstance(ic_payables, (int, float))
                and ic_payables != 0
            ):
                balance_ratio = ic_receivables / ic_payables
                if balance_ratio > 3.0 or balance_ratio < 0.33:
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "intercompany_balance_imbalance",
                        "severity": "medium",
                        "confidence": 0.75,
                        "description": (
                            f"企業間残高不均衡: "
                            f"債権/債務比率={balance_ratio:.2f} "
                            f"(債権={ic_receivables:,.0f}, "
                            f"債務={ic_payables:,.0f})"
                        ),
                        "evidence": {
                            "intercompany_receivables": ic_receivables,
                            "intercompany_payables": ic_payables,
                            "balance_ratio": round(balance_ratio, 4),
                        },
                    })
            return

        # 企業間残高リストの分析
        for balance in ic_balances:
            if not isinstance(balance, dict):
                continue
            amount = balance.get("amount", 0)
            counterparty = balance.get("counterparty", "不明")
            if isinstance(amount, (int, float)) and total_assets != 0:
                ratio = abs(amount) / total_assets
                if ratio > self._balance_threshold:
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "intercompany_balance_anomaly",
                        "severity": "high",
                        "confidence": 0.80,
                        "description": (
                            f"企業間残高過大: {counterparty} "
                            f"との残高{amount:,.0f} "
                            f"(対総資産{ratio:.1%})"
                        ),
                        "evidence": {
                            "counterparty": counterparty,
                            "amount": amount,
                            "total_assets": total_assets,
                            "ratio": round(ratio, 4),
                        },
                    })

    def _detect_circular_transaction_signals(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """循環取引の兆候検出.

        関連当事者間で売上と仕入が同時に大きい、キリの良い数字が多い等の
        循環取引リスク兆候を検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        rp_revenue = data.get("related_party_revenue")
        rp_purchases = data.get("related_party_purchases")

        # 関連当事者との売上・仕入が同時に存在
        if (
            isinstance(rp_revenue, (int, float))
            and isinstance(rp_purchases, (int, float))
            and rp_revenue > 0
            and rp_purchases > 0
        ):
            # 売上と仕入の類似性チェック
            if rp_purchases != 0:
                similarity = rp_revenue / rp_purchases
                if 0.80 <= similarity <= 1.20:
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "circular_transaction_signal",
                        "severity": "critical",
                        "confidence": 0.70,
                        "description": (
                            f"循環取引兆候: 関連当事者売上({rp_revenue:,.0f})と"
                            f"仕入({rp_purchases:,.0f})が近似 "
                            f"(比率={similarity:.2f})"
                        ),
                        "evidence": {
                            "related_party_revenue": rp_revenue,
                            "related_party_purchases": rp_purchases,
                            "similarity_ratio": round(similarity, 4),
                        },
                    })
                    state["risk_factors"].append(
                        "循環取引の可能性: "
                        "関連当事者売上と仕入が近似"
                    )

        # キリの良い数字の検出（取引リスト）
        rp_transactions = data.get("related_party_transactions")
        if isinstance(rp_transactions, list):
            round_number_count = 0
            total_transactions = 0
            for txn in rp_transactions:
                if not isinstance(txn, dict):
                    continue
                amount = txn.get("amount", 0)
                if isinstance(amount, (int, float)) and amount != 0:
                    total_transactions += 1
                    if self._is_round_number(amount):
                        round_number_count += 1

            if total_transactions > 0:
                round_ratio = round_number_count / total_transactions
                if round_ratio > 0.60 and total_transactions >= 3:
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "circular_transaction_signal",
                        "severity": "medium",
                        "confidence": 0.60,
                        "description": (
                            f"キリの良い金額が多い: "
                            f"関連当事者取引の{round_ratio:.0%}"
                            f"({round_number_count}/{total_transactions}件)"
                            f"がキリの良い数字"
                        ),
                        "evidence": {
                            "round_number_count": round_number_count,
                            "total_transactions": total_transactions,
                            "round_number_ratio": round(round_ratio, 4),
                        },
                    })

    def _detect_period_end_anomalies(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """期末取引集中の検出.

        関連当事者取引が期末に集中しているパターンを検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        q4_rp_revenue = data.get("q4_related_party_revenue")
        annual_rp_revenue = data.get("related_party_revenue")

        if self._is_valid_pair(q4_rp_revenue, annual_rp_revenue):
            q4_ratio = q4_rp_revenue / annual_rp_revenue
            # Q4が年間の50%以上を占める場合
            if q4_ratio > 0.50:
                state["probe_results"].append({
                    "probe_name": "relationship_probe",
                    "finding_type": "period_end_concentration",
                    "severity": "high",
                    "confidence": 0.80,
                    "description": (
                        f"期末関連当事者取引集中: "
                        f"Q4が年間売上の{q4_ratio:.1%}を占有 "
                        f"(Q4={q4_rp_revenue:,.0f}, "
                        f"年間={annual_rp_revenue:,.0f})"
                    ),
                    "evidence": {
                        "q4_related_party_revenue": q4_rp_revenue,
                        "annual_related_party_revenue": annual_rp_revenue,
                        "q4_ratio": round(q4_ratio, 4),
                    },
                })
                state["risk_factors"].append(
                    f"期末関連当事者取引集中: Q4が{q4_ratio:.1%}"
                )

    def _analyze_related_party_transactions(
        self,
        state: AgentState,
        data: dict[str, Any],
    ) -> None:
        """関連当事者取引の詳細分析.

        取引条件の市場価格からの乖離、異常な取引パターンを検出する。

        Args:
            state: エージェント状態（結果追加先）。
            data: 財務データ辞書。
        """
        rp_transactions = data.get("related_party_transactions")
        if not isinstance(rp_transactions, list):
            return

        for txn in rp_transactions:
            if not isinstance(txn, dict):
                continue

            market_price = txn.get("market_price")
            txn_price = txn.get("transaction_price")
            counterparty = txn.get("counterparty", "不明")

            if (
                isinstance(market_price, (int, float))
                and isinstance(txn_price, (int, float))
                and market_price != 0
            ):
                price_deviation = (txn_price - market_price) / abs(market_price)
                if abs(price_deviation) > 0.15:
                    direction = "高値" if price_deviation > 0 else "安値"
                    state["probe_results"].append({
                        "probe_name": "relationship_probe",
                        "finding_type": "non_arms_length_pricing",
                        "severity": "high",
                        "confidence": 0.85,
                        "description": (
                            f"非市場価格取引: {counterparty} との取引が"
                            f"市場価格から{abs(price_deviation):.1%}{direction} "
                            f"(取引価格={txn_price:,.0f}, "
                            f"市場価格={market_price:,.0f})"
                        ),
                        "evidence": {
                            "counterparty": counterparty,
                            "transaction_price": txn_price,
                            "market_price": market_price,
                            "price_deviation": round(price_deviation, 4),
                        },
                    })
                    state["risk_factors"].append(
                        f"非市場価格取引: {counterparty} "
                        f"({abs(price_deviation):.1%}乖離)"
                    )

    @staticmethod
    def _is_valid_pair(numerator: Any, denominator: Any) -> bool:
        """比率算出に有効な数値ペアか判定する.

        Args:
            numerator: 分子。
            denominator: 分母。

        Returns:
            両方が数値で分母が非ゼロの場合True。
        """
        return (
            isinstance(numerator, (int, float))
            and isinstance(denominator, (int, float))
            and denominator != 0
        )

    @staticmethod
    def _is_round_number(value: float) -> bool:
        """キリの良い数字か判定する.

        1000単位で割り切れる数字をキリの良い数字とみなす。

        Args:
            value: 判定対象の数値。

        Returns:
            キリの良い数字の場合True。
        """
        if value == 0:
            return False
        abs_value = abs(value)
        # 1000単位で割り切れるかチェック
        if abs_value >= 1000:
            remainder = abs_value % 1000
            return remainder < ROUND_NUMBER_TOLERANCE * abs_value
        # 100単位で割り切れるかチェック
        if abs_value >= 100:
            remainder = abs_value % 100
            return remainder < ROUND_NUMBER_TOLERANCE * abs_value
        return False
