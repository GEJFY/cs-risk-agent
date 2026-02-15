"""ビジネスシナリオ E2E テスト.

実際のビジネスシナリオに沿った end-to-end テスト。
AI プロバイダーはモックを使用し、分析パイプライン全体の統合動作を検証する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest

from cs_risk_agent.ai.circuit_breaker import CircuitBreaker, UsageRecord
from cs_risk_agent.ai.cost_tracker import CostTracker
from cs_risk_agent.ai.model_tier import MODEL_PRESETS, ModelTierManager
from cs_risk_agent.ai.provider import AIResponse, Message, MessageRole, TokenUsage
from cs_risk_agent.ai.registry import ProviderRegistry
from cs_risk_agent.ai.router import AIModelRouter
from cs_risk_agent.analysis.benford import BenfordAnalyzer
from cs_risk_agent.analysis.fraud_prediction import FraudPredictor
from cs_risk_agent.analysis.risk_scorer import IntegratedRiskScorer
from cs_risk_agent.analysis.rule_engine import RuleEngine
from cs_risk_agent.core.exceptions import (
    AllProvidersFailedError,
    ProviderError,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _create_mock_provider(name: str, should_fail: bool = False) -> AsyncMock:
    """テスト用モックプロバイダー."""
    provider = AsyncMock()
    provider.name = name
    provider.is_available = True
    if should_fail:
        provider.complete.side_effect = ProviderError(name, "Service unavailable")
    else:
        provider.complete.return_value = AIResponse(
            content=f"[{name}] AI分析結果: リスクスコア中程度。追加監査手続きを推奨します。",
            model="test-model",
            provider=name,
            usage=TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
        )
    return provider


def _create_test_router(
    provider_configs: dict[str, bool],
    budget: float = 1000.0,
) -> AIModelRouter:
    """テスト用ルーターを作成する."""
    registry = ProviderRegistry()
    registry._initialized = True
    registry._providers = {
        name: _create_mock_provider(name, fail)
        for name, fail in provider_configs.items()
    }
    return AIModelRouter(
        registry=registry,
        tier_manager=ModelTierManager(presets=MODEL_PRESETS.copy()),
        circuit_breaker=CircuitBreaker(monthly_limit_usd=budget),
        cost_tracker=CostTracker(),
    )


# ---------------------------------------------------------------------------
# テストデータ生成
# ---------------------------------------------------------------------------


def _generate_company_data() -> dict:
    """テスト用企業財務データを生成する."""
    return {
        "company_id": "C001",
        "company_name": "テスト株式会社",
        "revenue": 150000,
        "revenue_prior": 120000,
        "cogs": 90000,
        "cogs_prior": 72000,
        "sga": 25000,
        "sga_prior": 20000,
        "net_income": 15000,
        "operating_cash_flow": -3000,  # 営業CF赤字（リスクフラグ）
        "total_assets": 300000,
        "total_assets_prior": 250000,
        "current_assets": 120000,
        "current_assets_prior": 100000,
        "ppe": 80000,
        "ppe_prior": 70000,
        "receivables": 45000,  # 売掛金大幅増（リスクフラグ）
        "receivables_prior": 20000,
        "inventory": 15000,
        "inventory_prior": 12000,
        "depreciation": 8000,
        "depreciation_prior": 7000,
        "total_liabilities": 200000,
        "total_equity": 100000,
        "current_liabilities": 60000,
        "current_liabilities_prior": 50000,
        "long_term_debt": 80000,
        "long_term_debt_prior": 70000,
        "retained_earnings": 50000,
        "ebit": 25000,
    }


def _generate_journal_entries(n: int = 2000) -> pd.DataFrame:
    """テスト用仕訳データを生成する."""
    np.random.seed(42)
    amounts = np.random.lognormal(10, 2, n)
    return pd.DataFrame({
        "id": [f"JE-{i:05d}" for i in range(n)],
        "company_id": np.random.choice(["C001", "C002", "C003"], n),
        "debit": amounts,
        "credit": np.zeros(n),
        "date": pd.date_range("2024-01-01", periods=n, freq="2h"),
        "account_code": np.random.choice(["4100", "5100", "6100", "7100"], n),
    })


# ---------------------------------------------------------------------------
# E2E テストケース
# ---------------------------------------------------------------------------


class TestFullAnalysisPipeline:
    """完全な分析パイプラインのE2E検証."""

    def test_full_analysis_pipeline(self):
        """ルールエンジン → 不正予測 → ベンフォード → 統合スコアの一連の流れ."""
        company_data = _generate_company_data()
        journal_df = _generate_journal_entries()

        # Step 1: ルールエンジン評価
        rule_engine = RuleEngine()
        rule_result = rule_engine.evaluate_and_score(company_data)
        assert 0 <= rule_result.total_score <= 100
        assert rule_result.triggered_count > 0  # リスクデータなので発火するはず

        # Step 2: 不正予測（ルールベース）
        predictor = FraudPredictor()
        financial_df = pd.DataFrame([company_data])
        fraud_results = predictor.predict(financial_df)
        assert len(fraud_results) == 1
        assert 0 <= fraud_results[0].risk_score <= 100

        # Step 3: ベンフォード分析
        benford_analyzer = BenfordAnalyzer(min_sample_size=50)
        company_entries = journal_df[journal_df["company_id"] == "C001"]
        benford_result = benford_analyzer.analyze_account(
            company_entries["debit"],
            account_code="4100",
        )
        assert 0 <= benford_result.risk_score <= 100

        # Step 4: 統合リスクスコア
        scorer = IntegratedRiskScorer()
        integrated_result = scorer.evaluate({
            "rule_engine": rule_result.total_score,
            "fraud_prediction": fraud_results[0].risk_score,
            "benford": benford_result.risk_score,
            "discretionary_accruals": 0.0,  # 単体企業では計算不可
        })

        assert 0 <= integrated_result.integrated_score <= 100
        assert integrated_result.risk_level in ("critical", "high", "medium", "low")
        assert len(integrated_result.summary_ja) > 0
        assert "統合リスクスコア" in integrated_result.summary_ja

    def test_pipeline_with_safe_company(self):
        """健全企業データでのパイプライン実行."""
        safe_data = {
            "revenue": 100000,
            "revenue_prior": 95000,
            "cogs": 60000,
            "cogs_prior": 57000,
            "sga": 14000,
            "sga_prior": 14500,
            "net_income": 12000,
            "operating_cash_flow": 15000,
            "total_assets": 200000,
            "total_assets_prior": 190000,
            "current_assets": 80000,
            "current_assets_prior": 75000,
            "ppe": 50000,
            "ppe_prior": 48000,
            "receivables": 13000,
            "receivables_prior": 12000,
            "inventory": 8000,
            "inventory_prior": 7800,
            "depreciation": 5000,
            "depreciation_prior": 4800,
            "total_liabilities": 80000,
            "total_equity": 120000,
            "current_liabilities": 30000,
            "current_liabilities_prior": 28000,
            "long_term_debt": 20000,
            "long_term_debt_prior": 19000,
            "retained_earnings": 70000,
            "ebit": 20000,
        }

        rule_engine = RuleEngine()
        rule_result = rule_engine.evaluate_and_score(safe_data)

        predictor = FraudPredictor()
        fraud_results = predictor.predict(pd.DataFrame([safe_data]))

        scorer = IntegratedRiskScorer()
        integrated = scorer.evaluate({
            "rule_engine": rule_result.total_score,
            "fraud_prediction": fraud_results[0].risk_score,
        })

        # 健全企業は低〜中リスク
        assert integrated.risk_level in ("low", "medium")


class TestFailoverScenario:
    """フェイルオーバーシナリオの E2E 検証."""

    @pytest.mark.asyncio
    async def test_failover_scenario(self):
        """Azure障害 → AWS フォールバック → AI分析完了の一連の流れ."""
        router = _create_test_router({
            "azure": True,    # 障害
            "aws": False,     # 正常
            "gcp": False,
            "ollama": False,
        })

        messages = [
            Message(role=MessageRole.SYSTEM, content="あなたは内部監査の専門家です。"),
            Message(role=MessageRole.USER, content="連結子会社のリスク分析を実行してください。"),
        ]

        response = await router.complete(messages, provider="azure")

        # フォールバック先で正常応答を取得
        assert response.content is not None
        assert len(response.content) > 0
        assert response.provider != "azure"  # Azure以外にフォールバック

    @pytest.mark.asyncio
    async def test_failover_with_cost_tracking(self):
        """フェイルオーバー後のコスト追跡が正しいこと."""
        router = _create_test_router({
            "azure": True,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })

        messages = [Message(role=MessageRole.USER, content="テスト")]
        await router.complete(messages, provider="azure")

        # コストが記録されている
        summary = router._cost_tracker.get_summary()
        assert summary.total_requests == 1
        assert summary.total_input_tokens > 0


class TestHybridGovernanceRouting:
    """ハイブリッドガバナンスルーティングの E2E 検証."""

    @pytest.mark.asyncio
    async def test_hybrid_governance_routing(self):
        """データ分類に基づくルーティングのシミュレーション.

        ハイブリッドルールが未設定の場合はデフォルトプロバイダーを使用。
        """
        router = _create_test_router({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })

        # 一般データ → クラウド
        general_messages = [
            Message(role=MessageRole.USER, content="公開済み有報の分析"),
        ]
        response_general = await router.complete(
            general_messages,
            data_classification="general",
        )
        assert response_general.content is not None

        # 機密データ → ルーティング（ハイブリッドルール未設定のためデフォルト）
        confidential_messages = [
            Message(role=MessageRole.USER, content="従業員の個人情報を含む分析"),
        ]
        response_confidential = await router.complete(
            confidential_messages,
            data_classification="confidential",
        )
        assert response_confidential.content is not None

    @pytest.mark.asyncio
    async def test_multiple_classifications_handled(self):
        """複数のデータ分類が連続して処理できること."""
        router = _create_test_router({
            "azure": False,
            "aws": False,
            "gcp": False,
            "ollama": False,
        })

        classifications = ["public", "general", "internal", "confidential"]
        for classification in classifications:
            messages = [Message(role=MessageRole.USER, content=f"{classification}データの分析")]
            response = await router.complete(
                messages,
                data_classification=classification,
            )
            assert response.content is not None


class TestAnomalyDetectionPipeline:
    """異常検知パイプラインの E2E 検証."""

    def test_anomaly_detection_pipeline(self):
        """仕訳データの異常検知パイプライン全体の動作確認."""
        # テストデータ生成
        journal_df = _generate_journal_entries(3000)

        # ベンフォード分析
        analyzer = BenfordAnalyzer(min_sample_size=50)

        # 企業別・勘定科目別に分析
        results = {}
        for company_id in ["C001", "C002", "C003"]:
            company_data = journal_df[journal_df["company_id"] == company_id]
            for account in company_data["account_code"].unique():
                account_data = company_data[company_data["account_code"] == account]
                key = f"{company_id}_{account}"
                result = analyzer.analyze_account(
                    account_data["debit"],
                    account_code=account,
                )
                results[key] = result

        # 全結果が有効
        assert len(results) > 0
        for key, result in results.items():
            assert 0 <= result.risk_score <= 100
            assert result.duplicate_result is not None

    def test_anomaly_detection_with_injected_anomalies(self):
        """注入した異常データが検出されること."""
        np.random.seed(42)
        n_normal = 2000
        n_anomaly = 100

        # 正常データ（対数正規分布）
        normal_amounts = np.random.lognormal(10, 2, n_normal)

        # 異常データ（同一金額の繰り返し）
        anomaly_amounts = np.full(n_anomaly, 999999.99)

        all_amounts = np.concatenate([normal_amounts, anomaly_amounts])
        np.random.shuffle(all_amounts)

        analyzer = BenfordAnalyzer(min_sample_size=50, duplicate_threshold=0.3)

        # 重複テスト
        dup_result = analyzer.duplicate_test(pd.Series(all_amounts))
        # 999999.99 が大量に含まれているので重複が検出される
        assert dup_result.total_entries == n_normal + n_anomaly

        # 上位重複に注入データが含まれる
        top_amounts = [d["amount"] for d in dup_result.top_duplicates]
        assert 999999.99 in top_amounts

    def test_statistical_outlier_detection(self):
        """統計的外れ値の検出（Z-score ベース）."""
        np.random.seed(42)
        amounts = np.random.lognormal(10, 1, 1000)

        # 外れ値を注入
        amounts = np.append(amounts, [1e10, 1e11, 1e12])

        # Z-score による外れ値検出
        z_scores = (amounts - amounts.mean()) / amounts.std()
        outliers = np.where(np.abs(z_scores) > 3)[0]

        assert len(outliers) > 0, "外れ値が検出されませんでした"
        # 注入した大きな値がすべて検出されるはず
        assert len(outliers) >= 3
