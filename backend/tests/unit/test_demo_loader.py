"""DemoData ローダーのユニットテスト."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from cs_risk_agent.demo_loader import DemoData, _load_csv, _load_json


# ---------------------------------------------------------------------------
# _load_json テスト
# ---------------------------------------------------------------------------


class TestLoadJson:
    """JSON読み込み関数のテスト."""

    def test_load_json_list(self, tmp_path: Path) -> None:
        """JSONがリストの場合そのまま返すこと."""
        data = [{"id": "C1", "name": "Test"}]
        (tmp_path / "test.json").write_text(json.dumps(data), encoding="utf-8")
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_json("test.json")
        assert result == data

    def test_load_json_dict(self, tmp_path: Path) -> None:
        """JSONがdictの場合リストに包んで返すこと."""
        data = {"id": "C1", "name": "Test"}
        (tmp_path / "test.json").write_text(json.dumps(data), encoding="utf-8")
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_json("test.json")
        assert result == [data]

    def test_load_json_missing(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合空リストを返すこと."""
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_json("nonexistent.json")
        assert result == []


# ---------------------------------------------------------------------------
# _load_csv テスト
# ---------------------------------------------------------------------------


class TestLoadCsv:
    """CSV読み込み関数のテスト."""

    def test_load_csv_numeric_conversion(self, tmp_path: Path) -> None:
        """数値カラムが正しく変換されること."""
        csv_content = "entity_id,revenue,fiscal_year\nSUB-001,12345.0,2024\n"
        (tmp_path / "test.csv").write_text(csv_content, encoding="utf-8")
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_csv("test.csv")
        assert len(result) == 1
        assert result[0]["revenue"] == 12345
        assert result[0]["fiscal_year"] == 2024
        assert result[0]["entity_id"] == "SUB-001"

    def test_load_csv_boolean_conversion(self, tmp_path: Path) -> None:
        """True/False文字列がboolに変換されること."""
        csv_content = "entity_id,is_anomaly\nSUB-001,True\nSUB-002,False\n"
        (tmp_path / "test.csv").write_text(csv_content, encoding="utf-8")
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_csv("test.csv")
        assert result[0]["is_anomaly"] is True
        assert result[1]["is_anomaly"] is False

    def test_load_csv_bom(self, tmp_path: Path) -> None:
        """UTF-8 BOM付きCSVが正しく読めること."""
        csv_content = "\ufeffentity_id,revenue\nSUB-001,100\n"
        (tmp_path / "test.csv").write_text(csv_content, encoding="utf-8-sig")
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_csv("test.csv")
        assert "entity_id" in result[0]
        assert result[0]["entity_id"] == "SUB-001"

    def test_load_csv_missing(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合空リストを返すこと."""
        with patch("cs_risk_agent.demo_loader._DEMO_DIR", tmp_path):
            result = _load_csv("nonexistent.csv")
        assert result == []


# ---------------------------------------------------------------------------
# DemoData シングルトン テスト
# ---------------------------------------------------------------------------


class TestDemoData:
    """DemoDataシングルトンのテスト."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """各テスト前にシングルトンをリセット."""
        DemoData._instance = None
        yield
        DemoData._instance = None

    def test_singleton(self) -> None:
        """getが毎回同じインスタンスを返すこと."""
        d1 = DemoData.get()
        d2 = DemoData.get()
        assert d1 is d2

    def test_reload(self) -> None:
        """reloadがデータを再読み込みすること."""
        d = DemoData.get()
        d.reload()
        assert d._loaded is True

    def test_get_entity_by_id(self) -> None:
        """IDでエンティティを検索できること."""
        d = DemoData.get()
        if d.companies:
            entity = d.get_entity_by_id(d.companies[0]["id"])
            assert entity is not None
            assert entity["id"] == d.companies[0]["id"]

    def test_get_entity_by_id_not_found(self) -> None:
        """存在しないIDはNoneを返すこと."""
        d = DemoData.get()
        assert d.get_entity_by_id("NONEXISTENT") is None

    def test_get_all_entities(self) -> None:
        """全エンティティが親+子を含むこと."""
        d = DemoData.get()
        all_e = d.get_all_entities()
        assert len(all_e) == len(d.companies) + len(d.subsidiaries)

    def test_get_risk_summary(self) -> None:
        """リスクサマリーが正しい構造を持つこと."""
        d = DemoData.get()
        summary = d.get_risk_summary()
        assert "total_companies" in summary
        assert "by_level" in summary
        assert "avg_score" in summary
        for level in ("critical", "high", "medium", "low"):
            assert level in summary["by_level"]

    def test_get_unread_alerts(self) -> None:
        """未読アラートのフィルタが動作すること."""
        d = DemoData.get()
        unread = d.get_unread_alerts()
        for a in unread:
            assert not a.get("is_read", True)

    def test_get_alerts_by_severity(self) -> None:
        """重要度フィルタが動作すること."""
        d = DemoData.get()
        all_alerts = d.get_alerts_by_severity(None)
        assert len(all_alerts) == len(d.alerts)

    def test_get_risk_score_by_entity(self) -> None:
        """リスクスコア検索が動作すること."""
        d = DemoData.get()
        if d.risk_scores:
            eid = d.risk_scores[0]["entity_id"]
            rs = d.get_risk_score_by_entity(eid)
            assert rs is not None
            assert rs["entity_id"] == eid

    def test_get_subsidiaries_with_risk(self) -> None:
        """子会社にリスク情報が付加されること."""
        d = DemoData.get()
        subs = d.get_subsidiaries_with_risk()
        assert len(subs) == len(d.subsidiaries)


# ---------------------------------------------------------------------------
# 財務データメソッド テスト
# ---------------------------------------------------------------------------


class TestDemoDataFinancials:
    """DemoDataの財務データ関連メソッドのテスト."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        DemoData._instance = None
        yield
        DemoData._instance = None

    def test_get_financial_statements_by_entity(self) -> None:
        """財務諸表がエンティティIDで取得できること."""
        d = DemoData.get()
        if d.financial_statements:
            eid = d.financial_statements[0].get("entity_id")
            fs = d.get_financial_statements_by_entity(eid)
            assert len(fs) > 0
            # ソート確認
            for i in range(1, len(fs)):
                prev = (fs[i - 1].get("fiscal_year", 0), fs[i - 1].get("fiscal_quarter", 0))
                curr = (fs[i].get("fiscal_year", 0), fs[i].get("fiscal_quarter", 0))
                assert prev <= curr

    def test_get_all_financial_latest(self) -> None:
        """最新財務データが全エンティティ分返ること."""
        d = DemoData.get()
        latest = d.get_all_financial_latest()
        if d.financial_statements:
            assert len(latest) > 0

    def test_get_trial_balance(self) -> None:
        """試算表が勘定科目別に集計されること."""
        d = DemoData.get()
        if d.journal_entries:
            eid = d.journal_entries[0].get("entity_id")
            tb = d.get_trial_balance(eid)
            assert len(tb) > 0
            for account in tb:
                assert "account_code" in account
                assert "total_debit" in account
                assert "total_credit" in account
                assert "balance" in account

    def test_get_journal_entries_by_entity(self) -> None:
        """仕訳データがエンティティIDで取得できること."""
        d = DemoData.get()
        if d.journal_entries:
            eid = d.journal_entries[0].get("entity_id")
            entries = d.get_journal_entries_by_entity(eid)
            assert len(entries) > 0

    def test_get_journal_entries_anomaly_only(self) -> None:
        """異常仕訳のみフィルタできること."""
        d = DemoData.get()
        if d.journal_entries:
            eid = d.journal_entries[0].get("entity_id")
            anomalies = d.get_journal_entries_by_entity(eid, anomaly_only=True)
            for je in anomalies:
                assert je.get("is_anomaly") is True

    def test_compute_financial_ratios(self) -> None:
        """財務指標が正しく計算されること."""
        d = DemoData.get()
        if d.financial_statements:
            eid = d.financial_statements[0].get("entity_id")
            ratios = d.compute_financial_ratios(eid)
            assert len(ratios) > 0
            for r in ratios:
                assert "gross_margin" in r
                assert "operating_margin" in r
                assert "roe" in r
                assert "current_ratio" in r
                assert "debt_equity_ratio" in r
