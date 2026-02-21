"""EDINET クライアントのユニットテスト."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cs_risk_agent.etl.edinet_client import (
    DOC_TYPE_ANNUAL,
    DOC_TYPE_QUARTERLY,
    EdinetClient,
    EdinetDocument,
    SearchResult,
)


class TestEdinetDocument:
    """EdinetDocument データクラスのテスト."""

    def test_create_document(self) -> None:
        doc = EdinetDocument(
            doc_id="S100ABC",
            edinet_code="E12345",
            sec_code="1234",
            filer_name="テスト株式会社",
            doc_type_code="120",
            doc_description="有価証券報告書",
            filing_date="2025-06-30",
            xbrl_flag=True,
            pdf_flag=True,
        )
        assert doc.doc_id == "S100ABC"
        assert doc.filer_name == "テスト株式会社"
        assert doc.xbrl_flag is True

    def test_document_defaults(self) -> None:
        doc = EdinetDocument(
            doc_id="X",
            edinet_code="E",
            sec_code=None,
            filer_name="T",
            doc_type_code="120",
            doc_description="",
            filing_date="",
        )
        assert doc.period_start is None
        assert doc.xbrl_flag is False


class TestSearchResult:
    """SearchResult データクラスのテスト."""

    def test_empty_result(self) -> None:
        result = SearchResult()
        assert result.documents == []
        assert result.total == 0

    def test_result_with_docs(self) -> None:
        docs = [
            EdinetDocument(
                doc_id=f"S{i}",
                edinet_code="E",
                sec_code=None,
                filer_name="Test",
                doc_type_code="120",
                doc_description="",
                filing_date="",
            )
            for i in range(3)
        ]
        result = SearchResult(documents=docs, total=3)
        assert len(result.documents) == 3


class TestEdinetClient:
    """EdinetClient のテスト."""

    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    def test_init_defaults(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = "test-key"
        mock_settings.return_value.edinet_base_url = "https://api.edinet-fsa.go.jp/api/v2"
        client = EdinetClient()
        assert client._api_key == "test-key"
        assert client._max_retries == 3

    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    def test_init_custom(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = ""
        mock_settings.return_value.edinet_base_url = ""
        client = EdinetClient(api_key="custom", base_url="http://test", max_retries=5)
        assert client._api_key == "custom"
        assert client._max_retries == 5

    def test_generate_date_range(self) -> None:
        dates = EdinetClient._generate_date_range(date(2025, 1, 1), date(2025, 1, 3))
        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 1)
        assert dates[-1] == date(2025, 1, 3)

    def test_generate_date_range_single(self) -> None:
        dates = EdinetClient._generate_date_range(date(2025, 6, 15), date(2025, 6, 15))
        assert len(dates) == 1

    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    def test_parse_document_list(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = ""
        mock_settings.return_value.edinet_base_url = ""
        client = EdinetClient()

        response_data = {
            "results": [
                {
                    "docID": "S100ABC",
                    "edinetCode": "E12345",
                    "secCode": "1234",
                    "filerName": "テスト株式会社",
                    "docTypeCode": "120",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2025-06-30",
                    "xbrlFlag": 1,
                    "pdfFlag": 1,
                },
                {
                    "docID": "S100DEF",
                    "edinetCode": "E67890",
                    "secCode": "5678",
                    "filerName": "他社",
                    "docTypeCode": "120",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2025-06-30",
                },
                {
                    "docID": "S100GHI",
                    "edinetCode": "E12345",
                    "secCode": "1234",
                    "filerName": "テスト株式会社",
                    "docTypeCode": "140",
                    "docDescription": "四半期報告書",
                    "submitDateTime": "2025-06-30",
                },
            ]
        }

        # フィルタなし
        docs = client._parse_document_list(response_data, None, "120")
        assert len(docs) == 2  # docType=120 のみ

        # EDINETコードフィルタ
        docs = client._parse_document_list(response_data, "E12345", "120")
        assert len(docs) == 1
        assert docs[0].doc_id == "S100ABC"

        # 四半期報告書
        docs = client._parse_document_list(response_data, None, "140")
        assert len(docs) == 1

    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    def test_parse_empty_results(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = ""
        mock_settings.return_value.edinet_base_url = ""
        client = EdinetClient()
        docs = client._parse_document_list({"results": []}, None, "120")
        assert docs == []

    @pytest.mark.asyncio
    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    async def test_search_documents_single_date(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = "key"
        mock_settings.return_value.edinet_base_url = "https://test"
        client = EdinetClient()

        # _request_with_retry をモックして実際のHTTP通信を回避
        response_data = {
            "results": [
                {
                    "docID": "S100",
                    "edinetCode": "E001",
                    "filerName": "Test",
                    "docTypeCode": "120",
                    "docDescription": "Annual",
                    "submitDateTime": "2025-01-01",
                },
            ]
        }
        with patch.object(
            client, "_request_with_retry", AsyncMock(return_value=response_data)
        ):
            result = await client.search_documents(filing_date=date(2025, 1, 1))
            assert result.total == 1
            assert result.documents[0].doc_id == "S100"

    @pytest.mark.asyncio
    @patch("cs_risk_agent.etl.edinet_client.get_settings")
    async def test_close(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.edinet_api_key = ""
        mock_settings.return_value.edinet_base_url = ""
        client = EdinetClient()
        mock_client = AsyncMock()
        mock_client.is_closed = False
        client._client = mock_client
        await client.close()
        # close() 後に _client は None になるため、事前参照で確認
        mock_client.aclose.assert_called_once()


class TestDocTypeConstants:
    """ドキュメントタイプ定数のテスト."""

    def test_constants(self) -> None:
        assert DOC_TYPE_ANNUAL == "120"
        assert DOC_TYPE_QUARTERLY == "140"
