"""データプロバイダー抽象化 - DemoData/DB切り替え.

DATA_MODE 環境変数で demo / db モードを切り替え。
全APIエンドポイントはこのプロバイダー経由でデータにアクセスする。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from cs_risk_agent.config import DataMode, get_settings

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """データアクセスの抽象基底クラス."""

    @abstractmethod
    def get_all_entities(self) -> list[dict[str, Any]]:
        """全エンティティ取得."""

    @abstractmethod
    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """IDでエンティティ検索."""

    @abstractmethod
    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        """エンティティのリスクスコア."""

    @abstractmethod
    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        """リスク付き子会社一覧."""

    @abstractmethod
    def get_risk_summary(self) -> dict[str, Any]:
        """リスクサマリー."""

    @abstractmethod
    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        """重要度別アラート."""

    @abstractmethod
    def get_unread_alerts(self) -> list[dict[str, Any]]:
        """未読アラート."""

    @abstractmethod
    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        """エンティティ別財務諸表."""

    @abstractmethod
    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        """最新財務データ."""

    @abstractmethod
    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        """試算表."""

    @abstractmethod
    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        """仕訳データ."""

    @abstractmethod
    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        """財務指標."""

    @property
    @abstractmethod
    def risk_scores(self) -> list[dict[str, Any]]:
        """全リスクスコア."""

    @property
    @abstractmethod
    def alerts(self) -> list[dict[str, Any]]:
        """全アラート."""


class DemoDataProvider(DataProvider):
    """デモデータ (JSON/CSV) プロバイダー."""

    def __init__(self) -> None:
        from cs_risk_agent.demo_loader import DemoData
        self._demo = DemoData.get()

    def get_all_entities(self) -> list[dict[str, Any]]:
        return self._demo.get_all_entities()

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        return self._demo.get_entity_by_id(entity_id)

    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._demo.get_risk_score_by_entity(entity_id)

    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        return self._demo.get_subsidiaries_with_risk()

    def get_risk_summary(self) -> dict[str, Any]:
        return self._demo.get_risk_summary()

    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        return self._demo.get_alerts_by_severity(severity)

    def get_unread_alerts(self) -> list[dict[str, Any]]:
        return self._demo.get_unread_alerts()

    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.get_financial_statements_by_entity(entity_id)

    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        return self._demo.get_all_financial_latest()

    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.get_trial_balance(entity_id)

    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._demo.get_journal_entries_by_entity(entity_id, anomaly_only=anomaly_only)

    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        return self._demo.compute_financial_ratios(entity_id)

    @property
    def risk_scores(self) -> list[dict[str, Any]]:
        return self._demo.risk_scores

    @property
    def alerts(self) -> list[dict[str, Any]]:
        return self._demo.alerts


class DBDataProvider(DataProvider):
    """DB (SQLAlchemy) プロバイダー - 将来拡張用スタブ.

    DATA_MODE=db 時に使用。現在はNotImplementedErrorを返す。
    Repository パターン (data/repository.py) を内部で使用する設計。
    """

    def get_all_entities(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_all_entities は未実装です。DATA_MODE=demo を使用してください。")

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("DB mode: get_entity_by_id は未実装です。")

    def get_risk_score_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("DB mode: get_risk_score_by_entity は未実装です。")

    def get_subsidiaries_with_risk(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_subsidiaries_with_risk は未実装です。")

    def get_risk_summary(self) -> dict[str, Any]:
        raise NotImplementedError("DB mode: get_risk_summary は未実装です。")

    def get_alerts_by_severity(self, severity: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_alerts_by_severity は未実装です。")

    def get_unread_alerts(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_unread_alerts は未実装です。")

    def get_financial_statements_by_entity(self, entity_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_financial_statements_by_entity は未実装です。")

    def get_all_financial_latest(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_all_financial_latest は未実装です。")

    def get_trial_balance(self, entity_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_trial_balance は未実装です。")

    def get_journal_entries_by_entity(
        self, entity_id: str, anomaly_only: bool = False,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: get_journal_entries_by_entity は未実装です。")

    def compute_financial_ratios(self, entity_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: compute_financial_ratios は未実装です。")

    @property
    def risk_scores(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: risk_scores は未実装です。")

    @property
    def alerts(self) -> list[dict[str, Any]]:
        raise NotImplementedError("DB mode: alerts は未実装です。")


# シングルトンインスタンス
_provider: DataProvider | None = None


def get_data_provider() -> DataProvider:
    """設定に基づいてデータプロバイダーを返す."""
    global _provider  # noqa: PLW0603
    if _provider is not None:
        return _provider

    settings = get_settings()
    if settings.data_mode == DataMode.DB:
        logger.info("データモード: DB (SQLAlchemy Repository)")
        _provider = DBDataProvider()
    else:
        logger.info("データモード: Demo (JSON/CSV)")
        _provider = DemoDataProvider()

    return _provider


def reset_provider() -> None:
    """プロバイダーをリセット（テスト用）."""
    global _provider  # noqa: PLW0603
    _provider = None
