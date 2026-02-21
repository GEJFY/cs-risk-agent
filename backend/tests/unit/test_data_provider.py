"""DataProvider テスト - demo/db モード切り替え."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cs_risk_agent.config import DataMode
from cs_risk_agent.data.provider import (
    DBDataProvider,
    DemoDataProvider,
    get_data_provider,
    reset_provider,
)


class TestDemoDataProvider:
    """DemoDataProvider テスト."""

    def setup_method(self) -> None:
        reset_provider()

    def teardown_method(self) -> None:
        reset_provider()

    def test_get_all_entities(self) -> None:
        """全エンティティ取得."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        assert isinstance(entities, list)
        assert len(entities) > 0

    def test_get_entity_by_id(self) -> None:
        """IDでエンティティ検索."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        if entities:
            entity = provider.get_entity_by_id(entities[0]["id"])
            assert entity is not None
            assert entity["id"] == entities[0]["id"]

    def test_get_entity_by_id_not_found(self) -> None:
        """存在しないID."""
        provider = DemoDataProvider()
        entity = provider.get_entity_by_id("non-existent-id")
        assert entity is None

    def test_get_risk_score_by_entity(self) -> None:
        """リスクスコア取得."""
        provider = DemoDataProvider()
        scores = provider.risk_scores
        if scores:
            rs = provider.get_risk_score_by_entity(scores[0]["entity_id"])
            assert rs is not None
            assert "total_score" in rs

    def test_get_subsidiaries_with_risk(self) -> None:
        """リスク付き子会社一覧."""
        provider = DemoDataProvider()
        subs = provider.get_subsidiaries_with_risk()
        assert isinstance(subs, list)

    def test_get_risk_summary(self) -> None:
        """リスクサマリー."""
        provider = DemoDataProvider()
        summary = provider.get_risk_summary()
        assert "total_companies" in summary
        assert "by_level" in summary

    def test_get_alerts_by_severity(self) -> None:
        """重要度別アラート."""
        provider = DemoDataProvider()
        alerts = provider.get_alerts_by_severity()
        assert isinstance(alerts, list)

    def test_get_unread_alerts(self) -> None:
        """未読アラート."""
        provider = DemoDataProvider()
        alerts = provider.get_unread_alerts()
        assert isinstance(alerts, list)

    def test_get_financial_statements_by_entity(self) -> None:
        """財務諸表."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        if entities:
            fs = provider.get_financial_statements_by_entity(entities[0]["id"])
            assert isinstance(fs, list)

    def test_get_all_financial_latest(self) -> None:
        """最新財務データ."""
        provider = DemoDataProvider()
        latest = provider.get_all_financial_latest()
        assert isinstance(latest, list)

    def test_get_trial_balance(self) -> None:
        """試算表."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        if entities:
            tb = provider.get_trial_balance(entities[0]["id"])
            assert isinstance(tb, list)

    def test_get_journal_entries_by_entity(self) -> None:
        """仕訳データ."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        if entities:
            entries = provider.get_journal_entries_by_entity(entities[0]["id"])
            assert isinstance(entries, list)

    def test_compute_financial_ratios(self) -> None:
        """財務指標."""
        provider = DemoDataProvider()
        entities = provider.get_all_entities()
        if entities:
            ratios = provider.compute_financial_ratios(entities[0]["id"])
            assert isinstance(ratios, list)

    def test_risk_scores_property(self) -> None:
        """risk_scores プロパティ."""
        provider = DemoDataProvider()
        scores = provider.risk_scores
        assert isinstance(scores, list)

    def test_alerts_property(self) -> None:
        """alerts プロパティ."""
        provider = DemoDataProvider()
        alerts = provider.alerts
        assert isinstance(alerts, list)


class TestDBDataProvider:
    """DBDataProvider テスト (スタブ - NotImplementedError)."""

    def test_get_all_entities_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            provider.get_all_entities()

    def test_get_entity_by_id_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            provider.get_entity_by_id("test")

    def test_get_risk_score_by_entity_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            provider.get_risk_score_by_entity("test")

    def test_get_subsidiaries_with_risk_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            provider.get_subsidiaries_with_risk()

    def test_get_risk_summary_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            provider.get_risk_summary()

    def test_risk_scores_property_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            _ = provider.risk_scores

    def test_alerts_property_raises(self) -> None:
        provider = DBDataProvider()
        with pytest.raises(NotImplementedError):
            _ = provider.alerts


class TestGetDataProvider:
    """get_data_provider ファクトリーテスト."""

    def setup_method(self) -> None:
        reset_provider()

    def teardown_method(self) -> None:
        reset_provider()

    def test_default_demo_mode(self) -> None:
        """デフォルトはdemoモード."""
        provider = get_data_provider()
        assert isinstance(provider, DemoDataProvider)

    def test_singleton(self) -> None:
        """シングルトンパターン."""
        p1 = get_data_provider()
        p2 = get_data_provider()
        assert p1 is p2

    def test_db_mode(self) -> None:
        """DB モード."""
        mock_settings = MagicMock()
        mock_settings.data_mode = DataMode.DB
        with patch("cs_risk_agent.data.provider.get_settings", return_value=mock_settings):
            provider = get_data_provider()
            assert isinstance(provider, DBDataProvider)

    def test_reset_provider(self) -> None:
        """リセット."""
        p1 = get_data_provider()
        reset_provider()
        p2 = get_data_provider()
        assert p1 is not p2
