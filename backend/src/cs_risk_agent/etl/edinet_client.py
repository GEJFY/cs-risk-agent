"""EDINET API クライアント - 有価証券報告書の検索・ダウンロード.

金融庁 EDINET API v2 を使用して、企業の有価証券報告書・四半期報告書の
検索およびXBRLデータのダウンロードを行う。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import structlog

from cs_risk_agent.config import get_settings

logger = structlog.get_logger(__name__)

# EDINET 書類タイプコード
DOC_TYPE_ANNUAL = "120"  # 有価証券報告書
DOC_TYPE_QUARTERLY = "140"  # 四半期報告書
DOC_TYPE_SECURITIES_REGISTRATION = "030"  # 有価証券届出書


@dataclass
class EdinetDocument:
    """EDINET 書類メタデータ."""

    doc_id: str
    edinet_code: str
    sec_code: str | None
    filer_name: str
    doc_type_code: str
    doc_description: str
    filing_date: str
    period_start: str | None = None
    period_end: str | None = None
    xbrl_flag: bool = False
    pdf_flag: bool = False


@dataclass
class SearchResult:
    """検索結果."""

    documents: list[EdinetDocument] = field(default_factory=list)
    total: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class EdinetClient:
    """EDINET API クライアント.

    金融庁 EDINET API v2 に対するHTTPリクエストを管理する。
    レート制限とリトライロジックを内蔵。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """初期化.

        Args:
            api_key: EDINET APIキー。省略時は設定から取得。
            base_url: EDINET APIベースURL。省略時は設定から取得。
            timeout: HTTPタイムアウト（秒）。
            max_retries: 最大リトライ回数。
        """
        settings = get_settings()
        self._api_key = api_key or settings.edinet_api_key
        self._base_url = base_url or settings.edinet_base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアント取得（遅延初期化）."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """クライアントを閉じる."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_documents(
        self,
        filing_date: date | None = None,
        date_range: tuple[date, date] | None = None,
        edinet_code: str | None = None,
        doc_type: str = DOC_TYPE_ANNUAL,
    ) -> SearchResult:
        """EDINET 書類検索.

        指定条件に一致する書類を検索する。date_rangeが指定された場合は
        日付範囲内の全日を検索する。

        Args:
            filing_date: 提出日（単日検索）。
            date_range: 提出日範囲 (開始日, 終了日)。
            edinet_code: EDINET コード（企業フィルタ）。
            doc_type: 書類タイプコード。

        Returns:
            検索結果。
        """
        client = await self._get_client()
        all_documents: list[EdinetDocument] = []

        # 検索日リストを構築
        if date_range:
            search_dates = self._generate_date_range(date_range[0], date_range[1])
        elif filing_date:
            search_dates = [filing_date]
        else:
            search_dates = [date.today()]

        for search_date in search_dates:
            params: dict[str, Any] = {
                "date": search_date.isoformat(),
                "type": 2,  # メタデータ付き
            }
            if self._api_key:
                params["Subscription-Key"] = self._api_key

            try:
                response = await self._request_with_retry(
                    client, "/documents.json", params
                )
                documents = self._parse_document_list(
                    response, edinet_code, doc_type
                )
                all_documents.extend(documents)
            except Exception as e:
                logger.warning(
                    "edinet.search_date_failed",
                    date=search_date.isoformat(),
                    error=str(e),
                )

            # レート制限対策: リクエスト間隔
            await asyncio.sleep(0.5)

        return SearchResult(
            documents=all_documents,
            total=len(all_documents),
            metadata={
                "search_dates": len(search_dates),
                "doc_type": doc_type,
                "edinet_code": edinet_code,
            },
        )

    async def download_document(
        self,
        doc_id: str,
        output_dir: Path | str,
        file_type: int = 1,
    ) -> Path:
        """EDINET 書類ダウンロード.

        指定書類IDのXBRLまたはPDFデータをダウンロードする。

        Args:
            doc_id: 書類管理番号。
            output_dir: 保存先ディレクトリ。
            file_type: ファイルタイプ（1=XBRL, 2=PDF, 5=CSV）。

        Returns:
            ダウンロードしたファイルパス。

        Raises:
            httpx.HTTPStatusError: ダウンロード失敗時。
        """
        client = await self._get_client()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        params: dict[str, Any] = {"type": file_type}
        if self._api_key:
            params["Subscription-Key"] = self._api_key

        logger.info(
            "edinet.download_start",
            doc_id=doc_id,
            file_type=file_type,
        )

        response = await self._request_with_retry(
            client,
            f"/documents/{doc_id}",
            params,
            expect_json=False,
        )

        # ファイル拡張子を決定
        ext_map = {1: ".zip", 2: ".pdf", 5: ".csv"}
        ext = ext_map.get(file_type, ".zip")
        file_path = output_path / f"{doc_id}{ext}"

        file_path.write_bytes(response)

        logger.info(
            "edinet.download_complete",
            doc_id=doc_id,
            file_path=str(file_path),
            size_bytes=file_path.stat().st_size,
        )
        return file_path

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
        expect_json: bool = True,
    ) -> Any:
        """リトライ付きHTTPリクエスト.

        Args:
            client: HTTPクライアント。
            path: APIパス。
            params: クエリパラメータ。
            expect_json: JSONレスポンスを期待するか。

        Returns:
            JSONレスポンスまたはバイトデータ。

        Raises:
            httpx.HTTPStatusError: 全リトライ失敗時。
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await client.get(path, params=params)
                response.raise_for_status()

                if expect_json:
                    return response.json()
                return response.content

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # レート制限: 指数バックオフ
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "edinet.rate_limited",
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                elif e.response.status_code >= 500:
                    # サーバーエラー: リトライ
                    await asyncio.sleep(1)
                else:
                    raise
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    "edinet.request_error",
                    attempt=attempt + 1,
                    error=str(e),
                )
                await asyncio.sleep(1)

        raise last_error or RuntimeError("All retries exhausted")

    def _parse_document_list(
        self,
        response_data: dict[str, Any],
        edinet_code: str | None,
        doc_type: str,
    ) -> list[EdinetDocument]:
        """APIレスポンスからドキュメントリストを解析.

        Args:
            response_data: EDINET APIレスポンスJSON。
            edinet_code: フィルタ用EDINETコード。
            doc_type: フィルタ用書類タイプ。

        Returns:
            フィルタ済みドキュメントリスト。
        """
        documents: list[EdinetDocument] = []
        results = response_data.get("results", [])

        for item in results:
            # フィルタ条件チェック
            if edinet_code and item.get("edinetCode") != edinet_code:
                continue
            if item.get("docTypeCode") != doc_type:
                continue

            doc = EdinetDocument(
                doc_id=item.get("docID", ""),
                edinet_code=item.get("edinetCode", ""),
                sec_code=item.get("secCode"),
                filer_name=item.get("filerName", ""),
                doc_type_code=item.get("docTypeCode", ""),
                doc_description=item.get("docDescription", ""),
                filing_date=item.get("submitDateTime", ""),
                period_start=item.get("periodStart"),
                period_end=item.get("periodEnd"),
                xbrl_flag=bool(item.get("xbrlFlag")),
                pdf_flag=bool(item.get("pdfFlag")),
            )
            documents.append(doc)

        return documents

    @staticmethod
    def _generate_date_range(start: date, end: date) -> list[date]:
        """日付範囲のリストを生成.

        Args:
            start: 開始日。
            end: 終了日。

        Returns:
            日付リスト。
        """
        dates: list[date] = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        return dates
