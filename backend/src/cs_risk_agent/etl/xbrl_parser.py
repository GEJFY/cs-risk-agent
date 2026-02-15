"""XBRL パーサー - 有価証券報告書のXBRLデータ解析.

EDINET からダウンロードしたXBRLファイルを解析し、
財務データを構造化された辞書形式に変換する。
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# XBRL 名前空間定義
XBRL_NS = {
    "xbrli": "http://www.xbrl.org/2003/instance",
    "xlink": "http://www.w3.org/1999/xlink",
    "jppfs_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023-11-01/jppfs_cor",
    "jpcrp_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2023-11-01/jpcrp_cor",
    "ix": "http://www.xbrl.org/2013/inlineXBRL",
}

# 主要財務勘定科目マッピング（XBRL要素名 -> 標準キー名）
ACCOUNT_MAP: dict[str, str] = {
    # 売上・収益
    "Revenue": "revenue",
    "NetSales": "net_sales",
    "OperatingRevenue1": "operating_revenue",
    # 利益
    "GrossProfit": "gross_profit",
    "OperatingIncome": "operating_income",
    "OrdinaryIncome": "ordinary_income",
    "ProfitLoss": "net_income",
    "ProfitLossAttributableToOwnersOfParent": "net_income_parent",
    # 資産
    "TotalAssets": "total_assets",
    "CurrentAssets": "current_assets",
    "NoncurrentAssets": "noncurrent_assets",
    "CashAndDeposits": "cash_and_deposits",
    "NotesAndAccountsReceivableTrade": "accounts_receivable",
    "Inventories": "inventories",
    # 負債
    "TotalLiabilities": "total_liabilities",
    "CurrentLiabilities": "current_liabilities",
    "NoncurrentLiabilities": "noncurrent_liabilities",
    "ShortTermLoansPayable": "short_term_loans",
    "LongTermLoansPayable": "long_term_loans",
    # 純資産
    "NetAssets": "net_assets",
    "TotalShareholdersEquity": "shareholders_equity",
    # キャッシュフロー
    "NetCashProvidedByUsedInOperatingActivities": "cf_operating",
    "NetCashProvidedByUsedInInvestingActivities": "cf_investing",
    "NetCashProvidedByUsedInFinancingActivities": "cf_financing",
    # その他
    "NumberOfEmployees": "employees",
}


@dataclass
class XBRLFact:
    """XBRL ファクト（勘定科目の値）."""

    element: str
    value: str
    context_ref: str
    unit_ref: str | None = None
    decimals: str | None = None
    period_start: str | None = None
    period_end: str | None = None


@dataclass
class ParseResult:
    """XBRLパース結果."""

    financial_data: dict[str, Any] = field(default_factory=dict)
    raw_facts: list[XBRLFact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class XBRLParser:
    """XBRL パーサー.

    XBRLファイルを解析して財務データを抽出する。
    lxml によるXMLパースとiXBRLの解析に対応。
    """

    def __init__(
        self,
        account_map: dict[str, str] | None = None,
    ) -> None:
        """初期化.

        Args:
            account_map: カスタム勘定科目マッピング。
        """
        self._account_map = account_map or ACCOUNT_MAP

    def parse(self, file_path: Path | str) -> ParseResult:
        """XBRLファイルを解析.

        ZIPファイルまたはXBRLファイルを受け取り、財務データを抽出する。

        Args:
            file_path: XBRLファイルまたはZIPアーカイブのパス。

        Returns:
            パース結果。
        """
        file_path = Path(file_path)
        result = ParseResult()

        logger.info("xbrl_parser.start", file_path=str(file_path))

        try:
            if file_path.suffix == ".zip":
                result = self._parse_zip(file_path)
            elif file_path.suffix in (".xbrl", ".xml", ".htm", ".html"):
                result = self._parse_xbrl_file(file_path)
            else:
                result.errors.append(
                    f"サポートされていないファイル形式: {file_path.suffix}"
                )
        except Exception as e:
            error_msg = f"XBRLパースエラー: {e}"
            logger.error("xbrl_parser.error", error=str(e))
            result.errors.append(error_msg)

        logger.info(
            "xbrl_parser.complete",
            facts_count=len(result.raw_facts),
            data_keys=len(result.financial_data),
            errors=len(result.errors),
        )
        return result

    def extract_financial_data(
        self,
        facts: list[XBRLFact],
        target_context: str | None = None,
    ) -> dict[str, Any]:
        """ファクトリストから財務データを抽出.

        勘定科目マッピングに基づいて、標準キー名の辞書に変換する。

        Args:
            facts: XBRLファクトリスト。
            target_context: 対象コンテキスト（当期/前期フィルタ用）。

        Returns:
            標準化された財務データ辞書。
        """
        data: dict[str, Any] = {}

        for fact in facts:
            # コンテキストフィルタ
            if target_context and target_context not in fact.context_ref:
                continue

            # 勘定科目マッピング
            element_name = fact.element.split(":")[-1] if ":" in fact.element else fact.element
            standard_key = self._account_map.get(element_name)

            if standard_key is None:
                continue

            # 数値変換
            try:
                value = self._parse_numeric_value(fact.value, fact.decimals)
                if value is not None:
                    # 前期データの判定
                    is_prior = self._is_prior_period(fact.context_ref)
                    key = f"{standard_key}_prev" if is_prior else standard_key
                    data[key] = value
            except ValueError:
                logger.debug(
                    "xbrl_parser.value_parse_failed",
                    element=element_name,
                    value=fact.value,
                )

        return data

    def _parse_zip(self, zip_path: Path) -> ParseResult:
        """ZIPファイルからXBRLを抽出して解析.

        Args:
            zip_path: ZIPファイルパス。

        Returns:
            パース結果。
        """
        result = ParseResult()

        with zipfile.ZipFile(zip_path, "r") as zf:
            # XBRLファイルを検索
            xbrl_files = [
                name
                for name in zf.namelist()
                if name.endswith((".xbrl", ".htm", ".html"))
                and "XBRL/PublicDoc/" in name
            ]

            if not xbrl_files:
                # PublicDoc以外も検索
                xbrl_files = [
                    name
                    for name in zf.namelist()
                    if name.endswith((".xbrl", ".htm", ".html"))
                ]

            if not xbrl_files:
                result.errors.append("ZIPアーカイブ内にXBRLファイルが見つかりません")
                return result

            logger.info(
                "xbrl_parser.zip_contents",
                xbrl_files=xbrl_files[:5],
                total_files=len(zf.namelist()),
            )

            # メインのXBRLファイルを解析
            for xbrl_file in xbrl_files[:3]:  # 最大3ファイル
                try:
                    content = zf.read(xbrl_file)
                    facts = self._extract_facts_from_bytes(content)
                    result.raw_facts.extend(facts)
                except Exception as e:
                    result.errors.append(f"ファイル解析エラー ({xbrl_file}): {e}")

        # ファクトから財務データを抽出
        result.financial_data = self.extract_financial_data(result.raw_facts)
        result.metadata["source"] = str(zip_path)
        result.metadata["xbrl_files_parsed"] = len(xbrl_files[:3])

        return result

    def _parse_xbrl_file(self, file_path: Path) -> ParseResult:
        """単一XBRLファイルを解析.

        Args:
            file_path: XBRLファイルパス。

        Returns:
            パース結果。
        """
        result = ParseResult()

        content = file_path.read_bytes()
        facts = self._extract_facts_from_bytes(content)
        result.raw_facts = facts
        result.financial_data = self.extract_financial_data(facts)
        result.metadata["source"] = str(file_path)

        return result

    def _extract_facts_from_bytes(self, content: bytes) -> list[XBRLFact]:
        """バイトデータからXBRLファクトを抽出.

        lxml を使用してXMLを解析し、ファクト要素を抽出する。

        Args:
            content: XMLバイトデータ。

        Returns:
            XBRLファクトリスト。
        """
        facts: list[XBRLFact] = []

        try:
            from lxml import etree

            # パーサー設定: HTMLも許容
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            root = etree.fromstring(content, parser=parser)

            if root is None:
                return facts

            # 標準XBRLインスタンスのファクト抽出
            for ns_prefix, ns_uri in XBRL_NS.items():
                if ns_prefix in ("xbrli", "xlink"):
                    continue
                for elem in root.iter(f"{{{ns_uri}}}*"):
                    context_ref = elem.get("contextRef", "")
                    if not context_ref:
                        continue

                    fact = XBRLFact(
                        element=elem.tag,
                        value=elem.text or "",
                        context_ref=context_ref,
                        unit_ref=elem.get("unitRef"),
                        decimals=elem.get("decimals"),
                    )
                    facts.append(fact)

            # iXBRL (Inline XBRL) の解析
            ix_ns = XBRL_NS.get("ix", "")
            for elem in root.iter(f"{{{ix_ns}}}nonFraction"):
                fact = XBRLFact(
                    element=elem.get("name", ""),
                    value=elem.text or "",
                    context_ref=elem.get("contextRef", ""),
                    unit_ref=elem.get("unitRef"),
                    decimals=elem.get("decimals"),
                )
                facts.append(fact)

        except ImportError:
            logger.warning("xbrl_parser.lxml_not_available")
            # lxml未インストール時のフォールバック
            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(content)
                for elem in root.iter():
                    context_ref = elem.get("contextRef", "")
                    if context_ref and elem.text:
                        facts.append(
                            XBRLFact(
                                element=elem.tag,
                                value=elem.text,
                                context_ref=context_ref,
                                unit_ref=elem.get("unitRef"),
                                decimals=elem.get("decimals"),
                            )
                        )
            except ET.ParseError as e:
                logger.error("xbrl_parser.xml_parse_error", error=str(e))

        return facts

    @staticmethod
    def _parse_numeric_value(
        value: str,
        decimals: str | None = None,
    ) -> float | None:
        """文字列値を数値に変換.

        Args:
            value: 文字列値。
            decimals: 小数桁数指定。

        Returns:
            数値。変換不可の場合はNone。
        """
        if not value or not value.strip():
            return None

        cleaned = value.strip().replace(",", "").replace(" ", "")

        # マイナス記号の正規化
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        elif cleaned.startswith("△") or cleaned.startswith("▲"):
            cleaned = "-" + cleaned[1:]

        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _is_prior_period(context_ref: str) -> bool:
        """コンテキストIDが前期データかどうかを判定.

        EDINET のコンテキストID命名規則に基づく判定。
        "Prior" を含む場合は前期とみなす。

        Args:
            context_ref: コンテキスト参照ID。

        Returns:
            前期データの場合True。
        """
        prior_indicators = [
            "Prior",
            "prior",
            "PreviousYear",
            "LastYear",
            "Comparative",
        ]
        return any(indicator in context_ref for indicator in prior_indicators)
