"""ルールベーススコアリングエンジン.

定義済みルール群を用いて企業の財務データを評価し、
リスクスコアを算出する。各ルールは重大度（critical/high/medium/low）と
カテゴリ（財務比率異常、キャッシュフロー、収益・費用ミスマッチ等）を持つ。

重大度ウェイト:
    critical = 1.0
    high     = 0.7
    medium   = 0.4
    low      = 0.2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import structlog

from cs_risk_agent.core.exceptions import AnalysisError

logger = structlog.get_logger(__name__)


class Severity(str, Enum):
    """ルール重大度."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# 重大度ウェイト定義
SEVERITY_WEIGHTS: dict[str, float] = {
    Severity.CRITICAL.value: 1.0,
    Severity.HIGH.value: 0.7,
    Severity.MEDIUM.value: 0.4,
    Severity.LOW.value: 0.2,
}


class RuleCategory(str, Enum):
    """ルールカテゴリ."""

    FINANCIAL_RATIO = "financial_ratio"
    CASH_FLOW = "cash_flow"
    REVENUE_EXPENSE = "revenue_expense"
    RELATED_PARTY = "related_party"
    ACCOUNTING_ESTIMATE = "accounting_estimate"
    SEGMENT = "segment"
    GOVERNANCE = "governance"
    DISCLOSURE = "disclosure"


@dataclass
class RuleDefinition:
    """ルール定義.

    Attributes:
        rule_id: ルールID（R001〜R026）
        name: ルール名（英語）
        description: ルール説明（日本語）
        severity: 重大度
        category: カテゴリ
        check_fn: チェック関数（company_data辞書を受取りboolを返す）
    """

    rule_id: str
    name: str
    description: str
    severity: Severity
    category: RuleCategory
    check_fn: Callable[[dict[str, Any]], bool]


@dataclass
class RuleResult:
    """個別ルール評価結果.

    Attributes:
        rule_id: ルールID
        name: ルール名
        description: ルール説明
        severity: 重大度
        category: カテゴリ
        triggered: ルールが発火したか
        score: ルールスコア（発火時は重大度ウェイト、未発火時は0）
        details: 追加詳細情報
    """

    rule_id: str
    name: str
    description: str
    severity: str
    category: str
    triggered: bool
    score: float
    details: str = ""


@dataclass
class RuleEngineResult:
    """ルールエンジン評価結果.

    Attributes:
        total_score: 総合スコア（0〜100）
        max_possible_score: 最大可能スコア
        triggered_count: 発火ルール数
        total_rules: 全ルール数
        results: 個別ルール結果リスト
        category_scores: カテゴリ別スコア
        severity_distribution: 重大度別発火数
    """

    total_score: float
    max_possible_score: float
    triggered_count: int
    total_rules: int
    results: list[RuleResult] = field(default_factory=list)
    category_scores: dict[str, float] = field(default_factory=dict)
    severity_distribution: dict[str, int] = field(default_factory=dict)


def _safe_get(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    """辞書から安全に数値を取得する.

    Args:
        data: データ辞書。
        key: キー名。
        default: デフォルト値。

    Returns:
        数値。取得失敗時はデフォルト値。
    """
    try:
        value = data.get(key, default)
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_ratio(
    numerator: float, denominator: float, default: float = 0.0,
) -> float:
    """安全な比率計算（ゼロ除算防止）.

    Args:
        numerator: 分子。
        denominator: 分母。
        default: ゼロ除算時のデフォルト値。

    Returns:
        比率。
    """
    if denominator == 0:
        return default
    return numerator / denominator


class RuleEngine:
    """ルールベーススコアリングエンジン.

    26個の定義済みルールを用いて企業データを評価し、
    重大度に応じた加重スコアを算出する。

    Attributes:
        _rules: 登録済みルール一覧
    """

    def __init__(self) -> None:
        """初期化（デフォルトルールを登録）."""
        self._rules: list[RuleDefinition] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """デフォルトルール26個を登録する."""
        rules = [
            # === 財務比率異常 (R001-R005) ===
            RuleDefinition(
                rule_id="R001",
                name="high_receivables_growth",
                description="売掛金が売上高を大幅に上回る増加率（1.5倍超）",
                severity=Severity.HIGH,
                category=RuleCategory.FINANCIAL_RATIO,
                check_fn=lambda d: (
                    _safe_ratio(
                        _safe_get(d, "receivables") - _safe_get(d, "receivables_prior"),
                        max(_safe_get(d, "receivables_prior"), 1),
                    )
                    > 1.5 * _safe_ratio(
                        _safe_get(d, "revenue") - _safe_get(d, "revenue_prior"),
                        max(_safe_get(d, "revenue_prior"), 1),
                    )
                ),
            ),
            RuleDefinition(
                rule_id="R002",
                name="declining_gross_margin",
                description="粗利率が前年比5%ポイント以上低下",
                severity=Severity.MEDIUM,
                category=RuleCategory.FINANCIAL_RATIO,
                check_fn=lambda d: (
                    _safe_ratio(
                        _safe_get(d, "revenue_prior") - _safe_get(d, "cogs_prior"),
                        max(_safe_get(d, "revenue_prior"), 1),
                    )
                    - _safe_ratio(
                        _safe_get(d, "revenue") - _safe_get(d, "cogs"),
                        max(_safe_get(d, "revenue"), 1),
                    )
                    > 0.05
                ),
            ),
            RuleDefinition(
                rule_id="R003",
                name="high_debt_to_equity",
                description="負債自己資本比率が3.0倍超（過剰レバレッジ）",
                severity=Severity.HIGH,
                category=RuleCategory.FINANCIAL_RATIO,
                check_fn=lambda d: (
                    _safe_ratio(
                        _safe_get(d, "total_liabilities"),
                        max(_safe_get(d, "total_equity"), 1),
                    )
                    > 3.0
                ),
            ),
            RuleDefinition(
                rule_id="R004",
                name="current_ratio_below_one",
                description="流動比率が1.0未満（短期支払い能力不足）",
                severity=Severity.MEDIUM,
                category=RuleCategory.FINANCIAL_RATIO,
                check_fn=lambda d: (
                    _safe_ratio(
                        _safe_get(d, "current_assets"),
                        max(_safe_get(d, "current_liabilities"), 1),
                    )
                    < 1.0
                ),
            ),
            RuleDefinition(
                rule_id="R005",
                name="inventory_buildup",
                description="棚卸資産回転期間が前年比50%以上増加",
                severity=Severity.MEDIUM,
                category=RuleCategory.FINANCIAL_RATIO,
                check_fn=lambda d: (
                    _safe_ratio(
                        _safe_get(d, "inventory"),
                        max(_safe_get(d, "cogs"), 1),
                    )
                    > 1.5 * _safe_ratio(
                        _safe_get(d, "inventory_prior"),
                        max(_safe_get(d, "cogs_prior"), 1),
                    )
                    and _safe_get(d, "inventory_prior") > 0
                ),
            ),

            # === キャッシュフローパターン (R006-R010) ===
            RuleDefinition(
                rule_id="R006",
                name="negative_operating_cash_flow",
                description="営業CFが赤字で純利益が黒字（利益の質に疑問）",
                severity=Severity.CRITICAL,
                category=RuleCategory.CASH_FLOW,
                check_fn=lambda d: (
                    _safe_get(d, "operating_cash_flow") < 0
                    and _safe_get(d, "net_income") > 0
                ),
            ),
            RuleDefinition(
                rule_id="R007",
                name="cash_flow_divergence",
                description="営業CFと純利益の乖離が総資産の10%超",
                severity=Severity.HIGH,
                category=RuleCategory.CASH_FLOW,
                check_fn=lambda d: (
                    abs(
                        _safe_get(d, "net_income")
                        - _safe_get(d, "operating_cash_flow")
                    )
                    > 0.10 * max(_safe_get(d, "total_assets"), 1)
                ),
            ),
            RuleDefinition(
                rule_id="R008",
                name="consecutive_negative_ocf",
                description="営業CFが2期連続赤字",
                severity=Severity.CRITICAL,
                category=RuleCategory.CASH_FLOW,
                check_fn=lambda d: (
                    _safe_get(d, "operating_cash_flow") < 0
                    and _safe_get(d, "operating_cash_flow_prior") < 0
                ),
            ),
            RuleDefinition(
                rule_id="R009",
                name="free_cash_flow_negative",
                description="フリーCF（営業CF-設備投資）が大幅マイナス",
                severity=Severity.MEDIUM,
                category=RuleCategory.CASH_FLOW,
                check_fn=lambda d: (
                    (
                        _safe_get(d, "operating_cash_flow")
                        - _safe_get(d, "capex")
                    )
                    < -0.05 * max(_safe_get(d, "total_assets"), 1)
                ),
            ),
            RuleDefinition(
                rule_id="R010",
                name="high_accruals_ratio",
                description="発生高比率（(純利益-営業CF)/総資産）が15%超",
                severity=Severity.HIGH,
                category=RuleCategory.CASH_FLOW,
                check_fn=lambda d: (
                    abs(
                        _safe_ratio(
                            _safe_get(d, "net_income")
                            - _safe_get(d, "operating_cash_flow"),
                            max(_safe_get(d, "total_assets"), 1),
                        )
                    )
                    > 0.15
                ),
            ),

            # === 収益・費用ミスマッチ (R011-R015) ===
            RuleDefinition(
                rule_id="R011",
                name="revenue_spike",
                description="売上高が前年比50%超の急増（異常成長）",
                severity=Severity.MEDIUM,
                category=RuleCategory.REVENUE_EXPENSE,
                check_fn=lambda d: (
                    _safe_get(d, "revenue_prior") > 0
                    and _safe_ratio(
                        _safe_get(d, "revenue"),
                        _safe_get(d, "revenue_prior"),
                    )
                    > 1.5
                ),
            ),
            RuleDefinition(
                rule_id="R012",
                name="q4_revenue_concentration",
                description="第4四半期売上比率が年間の40%超（期末集中）",
                severity=Severity.HIGH,
                category=RuleCategory.REVENUE_EXPENSE,
                check_fn=lambda d: (
                    _safe_get(d, "revenue") > 0
                    and _safe_ratio(
                        _safe_get(d, "q4_revenue"),
                        _safe_get(d, "revenue"),
                    )
                    > 0.40
                ),
            ),
            RuleDefinition(
                rule_id="R013",
                name="sga_revenue_mismatch",
                description="売上減少にもかかわらず販管費が増加",
                severity=Severity.MEDIUM,
                category=RuleCategory.REVENUE_EXPENSE,
                check_fn=lambda d: (
                    _safe_get(d, "revenue") < _safe_get(d, "revenue_prior")
                    and _safe_get(d, "sga") > _safe_get(d, "sga_prior")
                    and _safe_get(d, "revenue_prior") > 0
                ),
            ),
            RuleDefinition(
                rule_id="R014",
                name="unusual_other_income",
                description="営業外収益が営業利益の30%超（利益のかさ上げ疑い）",
                severity=Severity.HIGH,
                category=RuleCategory.REVENUE_EXPENSE,
                check_fn=lambda d: (
                    _safe_get(d, "operating_income") > 0
                    and _safe_ratio(
                        _safe_get(d, "other_income"),
                        _safe_get(d, "operating_income"),
                    )
                    > 0.30
                ),
            ),
            RuleDefinition(
                rule_id="R015",
                name="declining_roa",
                description="ROAが前年比で3%ポイント以上低下",
                severity=Severity.MEDIUM,
                category=RuleCategory.REVENUE_EXPENSE,
                check_fn=lambda d: (
                    _safe_get(d, "roa_prior") - _safe_get(d, "roa") > 0.03
                ),
            ),

            # === 関連当事者取引 (R016-R018) ===
            RuleDefinition(
                rule_id="R016",
                name="high_related_party_sales",
                description="関連当事者取引が売上高の20%超",
                severity=Severity.CRITICAL,
                category=RuleCategory.RELATED_PARTY,
                check_fn=lambda d: (
                    _safe_get(d, "revenue") > 0
                    and _safe_ratio(
                        _safe_get(d, "related_party_sales"),
                        _safe_get(d, "revenue"),
                    )
                    > 0.20
                ),
            ),
            RuleDefinition(
                rule_id="R017",
                name="related_party_loans",
                description="関連当事者への貸付金が総資産の10%超",
                severity=Severity.HIGH,
                category=RuleCategory.RELATED_PARTY,
                check_fn=lambda d: (
                    _safe_get(d, "total_assets") > 0
                    and _safe_ratio(
                        _safe_get(d, "related_party_loans"),
                        _safe_get(d, "total_assets"),
                    )
                    > 0.10
                ),
            ),
            RuleDefinition(
                rule_id="R018",
                name="related_party_increase",
                description="関連当事者取引額が前年比100%超の増加",
                severity=Severity.HIGH,
                category=RuleCategory.RELATED_PARTY,
                check_fn=lambda d: (
                    _safe_get(d, "related_party_total_prior") > 0
                    and _safe_ratio(
                        _safe_get(d, "related_party_total"),
                        _safe_get(d, "related_party_total_prior"),
                    )
                    > 2.0
                ),
            ),

            # === 会計見積り (R019-R022) ===
            RuleDefinition(
                rule_id="R019",
                name="allowance_ratio_decline",
                description="貸倒引当金率が前年比で大幅低下（引当不足疑い）",
                severity=Severity.HIGH,
                category=RuleCategory.ACCOUNTING_ESTIMATE,
                check_fn=lambda d: (
                    _safe_get(d, "allowance_ratio_prior") > 0
                    and _safe_get(d, "allowance_ratio")
                    < _safe_get(d, "allowance_ratio_prior") * 0.7
                ),
            ),
            RuleDefinition(
                rule_id="R020",
                name="depreciation_policy_change",
                description="減価償却方法または耐用年数の変更あり",
                severity=Severity.MEDIUM,
                category=RuleCategory.ACCOUNTING_ESTIMATE,
                check_fn=lambda d: bool(
                    d.get("depreciation_policy_changed", False)
                ),
            ),
            RuleDefinition(
                rule_id="R021",
                name="goodwill_impairment_risk",
                description="のれんが純資産の50%超（減損リスク）",
                severity=Severity.HIGH,
                category=RuleCategory.ACCOUNTING_ESTIMATE,
                check_fn=lambda d: (
                    _safe_get(d, "total_equity") > 0
                    and _safe_ratio(
                        _safe_get(d, "goodwill"),
                        _safe_get(d, "total_equity"),
                    )
                    > 0.50
                ),
            ),
            RuleDefinition(
                rule_id="R022",
                name="deferred_tax_asset_risk",
                description="繰延税金資産が純資産の30%超（回収可能性リスク）",
                severity=Severity.MEDIUM,
                category=RuleCategory.ACCOUNTING_ESTIMATE,
                check_fn=lambda d: (
                    _safe_get(d, "total_equity") > 0
                    and _safe_ratio(
                        _safe_get(d, "deferred_tax_assets"),
                        _safe_get(d, "total_equity"),
                    )
                    > 0.30
                ),
            ),

            # === セグメント不整合 (R023-R024) ===
            RuleDefinition(
                rule_id="R023",
                name="segment_profit_inconsistency",
                description="セグメント利益合計と全社利益の乖離が10%超",
                severity=Severity.HIGH,
                category=RuleCategory.SEGMENT,
                check_fn=lambda d: (
                    _safe_get(d, "operating_income") != 0
                    and abs(
                        _safe_ratio(
                            _safe_get(d, "segment_profit_total")
                            - _safe_get(d, "operating_income"),
                            abs(_safe_get(d, "operating_income")),
                        )
                    )
                    > 0.10
                ),
            ),
            RuleDefinition(
                rule_id="R024",
                name="segment_concentration",
                description="単一セグメントの売上依存度が90%超",
                severity=Severity.LOW,
                category=RuleCategory.SEGMENT,
                check_fn=lambda d: (
                    _safe_get(d, "largest_segment_revenue_ratio") > 0.90
                ),
            ),

            # === ガバナンス・開示 (R025-R026) ===
            RuleDefinition(
                rule_id="R025",
                name="auditor_change",
                description="監査法人の変更あり（独立性・継続性リスク）",
                severity=Severity.CRITICAL,
                category=RuleCategory.GOVERNANCE,
                check_fn=lambda d: bool(d.get("auditor_changed", False)),
            ),
            RuleDefinition(
                rule_id="R026",
                name="going_concern_note",
                description="継続企業の前提に関する注記あり",
                severity=Severity.CRITICAL,
                category=RuleCategory.GOVERNANCE,
                check_fn=lambda d: bool(
                    d.get("going_concern_note", False)
                ),
            ),
        ]
        self._rules = rules

    @property
    def rules(self) -> list[RuleDefinition]:
        """登録済みルール一覧."""
        return self._rules.copy()

    @property
    def rule_count(self) -> int:
        """登録ルール数."""
        return len(self._rules)

    def add_rule(self, rule: RuleDefinition) -> None:
        """カスタムルールを追加する.

        Args:
            rule: 追加するルール定義。

        Raises:
            AnalysisError: ルールIDが重複している場合。
        """
        existing_ids = {r.rule_id for r in self._rules}
        if rule.rule_id in existing_ids:
            raise AnalysisError(
                engine="RuleEngine",
                message=f"ルールID '{rule.rule_id}' は既に登録されています",
            )
        self._rules.append(rule)
        logger.info("rule_engine.rule_added", rule_id=rule.rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        """ルールを削除する.

        Args:
            rule_id: 削除するルールID。

        Returns:
            削除成功したかどうか。
        """
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        removed = len(self._rules) < original_count
        if removed:
            logger.info("rule_engine.rule_removed", rule_id=rule_id)
        return removed

    def evaluate(self, company_data: dict[str, Any]) -> list[RuleResult]:
        """企業データに対して全ルールを評価する.

        Args:
            company_data: 企業の財務データ辞書。

        Returns:
            個別ルール評価結果のリスト。

        Raises:
            AnalysisError: 評価実行エラー時。
        """
        if not company_data:
            raise AnalysisError(
                engine="RuleEngine",
                message="評価対象データが空です",
            )

        results: list[RuleResult] = []

        for rule in self._rules:
            try:
                triggered = rule.check_fn(company_data)
                weight = SEVERITY_WEIGHTS.get(rule.severity.value, 0.0)
                score = weight if triggered else 0.0

                results.append(RuleResult(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    description=rule.description,
                    severity=rule.severity.value,
                    category=rule.category.value,
                    triggered=triggered,
                    score=score,
                    details=(
                        f"ルール発火: {rule.description}"
                        if triggered
                        else ""
                    ),
                ))

            except Exception as exc:
                # 個別ルールの評価失敗はスキップし、ログに記録
                logger.warning(
                    "rule_engine.rule_evaluation_failed",
                    rule_id=rule.rule_id,
                    error=str(exc),
                )
                results.append(RuleResult(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    description=rule.description,
                    severity=rule.severity.value,
                    category=rule.category.value,
                    triggered=False,
                    score=0.0,
                    details=f"評価エラー: {exc}",
                ))

        triggered_count = sum(1 for r in results if r.triggered)
        logger.info(
            "rule_engine.evaluated",
            total_rules=len(results),
            triggered_count=triggered_count,
        )

        return results

    def calculate_total_score(self, results: list[RuleResult]) -> float:
        """ルール評価結果から総合スコア（0〜100）を算出する.

        全ルールの重大度ウェイト合計に対する、発火ルールの
        ウェイト合計の比率を100点満点に換算する。

        Args:
            results: evaluate()の結果リスト。

        Returns:
            総合スコア（0〜100）。
        """
        if not results:
            return 0.0

        max_possible = sum(
            SEVERITY_WEIGHTS.get(r.severity, 0.0)
            for r in results
        )
        if max_possible == 0:
            return 0.0

        triggered_total = sum(r.score for r in results if r.triggered)
        return min(100.0, (triggered_total / max_possible) * 100.0)

    def evaluate_and_score(
        self, company_data: dict[str, Any],
    ) -> RuleEngineResult:
        """企業データを評価し、総合結果を返す.

        evaluate()とcalculate_total_score()を組み合わせた
        コンビニエンスメソッド。

        Args:
            company_data: 企業の財務データ辞書。

        Returns:
            ルールエンジン評価結果。
        """
        results = self.evaluate(company_data)
        total_score = self.calculate_total_score(results)

        # 最大可能スコア
        max_possible = sum(
            SEVERITY_WEIGHTS.get(r.severity, 0.0)
            for r in results
        )

        # カテゴリ別スコア集計
        category_scores: dict[str, float] = {}
        category_max: dict[str, float] = {}
        for r in results:
            cat = r.category
            weight = SEVERITY_WEIGHTS.get(r.severity, 0.0)
            category_max[cat] = category_max.get(cat, 0.0) + weight
            if r.triggered:
                category_scores[cat] = (
                    category_scores.get(cat, 0.0) + r.score
                )

        # カテゴリ別を100点満点に正規化
        normalized_category: dict[str, float] = {}
        for cat, max_val in category_max.items():
            if max_val > 0:
                triggered_val = category_scores.get(cat, 0.0)
                normalized_category[cat] = (triggered_val / max_val) * 100.0
            else:
                normalized_category[cat] = 0.0

        # 重大度別発火数
        severity_dist: dict[str, int] = {s.value: 0 for s in Severity}
        for r in results:
            if r.triggered:
                severity_dist[r.severity] = (
                    severity_dist.get(r.severity, 0) + 1
                )

        triggered_count = sum(1 for r in results if r.triggered)

        return RuleEngineResult(
            total_score=total_score,
            max_possible_score=max_possible,
            triggered_count=triggered_count,
            total_rules=len(results),
            results=results,
            category_scores=normalized_category,
            severity_distribution=severity_dist,
        )

    def get_triggered_rules(
        self, results: list[RuleResult],
    ) -> list[RuleResult]:
        """発火したルールのみを返す.

        Args:
            results: evaluate()の結果リスト。

        Returns:
            発火ルールのリスト（重大度降順）。
        """
        severity_order = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 1,
            Severity.MEDIUM.value: 2,
            Severity.LOW.value: 3,
        }
        triggered = [r for r in results if r.triggered]
        triggered.sort(key=lambda r: severity_order.get(r.severity, 99))
        return triggered

    def get_rules_by_category(
        self, category: RuleCategory,
    ) -> list[RuleDefinition]:
        """指定カテゴリのルール一覧を返す.

        Args:
            category: 対象カテゴリ。

        Returns:
            該当カテゴリのルール定義リスト。
        """
        return [r for r in self._rules if r.category == category]

    def get_rules_by_severity(
        self, severity: Severity,
    ) -> list[RuleDefinition]:
        """指定重大度のルール一覧を返す.

        Args:
            severity: 対象重大度。

        Returns:
            該当重大度のルール定義リスト。
        """
        return [r for r in self._rules if r.severity == severity]
