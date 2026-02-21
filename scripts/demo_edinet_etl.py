#!/usr/bin/env python3
"""EDINET ETL デモスクリプト.

EDINET API からのデータ取得 → XBRL パース → 分析データ変換 の
エンドツーエンドフローを実証する。

Usage:
    # API キーなし (メタデータ検索のみ)
    python scripts/demo_edinet_etl.py

    # API キー指定 (XBRL ダウンロード含む)
    EDINET_API_KEY=your-key python scripts/demo_edinet_etl.py --download

Requirements:
    - EDINET API キー: https://disclosure.edinet-fsa.go.jp/ で取得
    - .env に EDINET_API_KEY を設定
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))


async def demo_search() -> None:
    """EDINET 書類検索デモ."""
    from cs_risk_agent.etl.edinet_client import (
        DOC_TYPE_ANNUAL,
        DOC_TYPE_QUARTERLY,
        EdinetClient,
    )

    print("=" * 60)
    print("EDINET ETL Demo - 書類検索")
    print("=" * 60)

    client = EdinetClient()

    try:
        # 直近1週間の有価証券報告書を検索
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        print(f"\n検索期間: {start_date} ~ {end_date}")
        print("書類タイプ: 有価証券報告書 (120)")
        print("-" * 40)

        result = await client.search_documents(
            date_range=(start_date, end_date),
            doc_type=DOC_TYPE_ANNUAL,
        )

        print(f"\n検索結果: {result.total} 件")
        for i, doc in enumerate(result.documents[:10]):
            print(
                f"  {i+1}. [{doc.doc_id}] {doc.filer_name}"
                f" (EDINET: {doc.edinet_code}, 証券: {doc.sec_code})"
            )
            if doc.period_start and doc.period_end:
                print(f"     期間: {doc.period_start} ~ {doc.period_end}")

        if result.total > 10:
            print(f"  ... 他 {result.total - 10} 件")

        # 四半期報告書も検索
        print("\n" + "-" * 40)
        print("書類タイプ: 四半期報告書 (140)")
        result_q = await client.search_documents(
            date_range=(start_date, end_date),
            doc_type=DOC_TYPE_QUARTERLY,
        )
        print(f"検索結果: {result_q.total} 件")

        return result

    finally:
        await client.close()


async def demo_download_and_parse(doc_id: str | None = None) -> None:
    """XBRL ダウンロード & パースデモ."""
    from cs_risk_agent.etl.edinet_client import EdinetClient
    from cs_risk_agent.etl.xbrl_parser import XBRLParser

    print("\n" + "=" * 60)
    print("EDINET ETL Demo - XBRL ダウンロード & パース")
    print("=" * 60)

    client = EdinetClient()
    parser = XBRLParser()
    output_dir = Path("demo_data/edinet_downloads")

    try:
        if not doc_id:
            # 直近の有価証券報告書から最初の1件を使用
            result = await client.search_documents(
                date_range=(date.today() - timedelta(days=30), date.today()),
            )
            if not result.documents:
                print("直近30日間に有価証券報告書が見つかりませんでした。")
                return
            doc = result.documents[0]
            doc_id = doc.doc_id
            print(f"\n対象: {doc.filer_name} ({doc.doc_id})")
        else:
            print(f"\n対象: {doc_id}")

        # XBRL ダウンロード
        print(f"ダウンロード中...")
        file_path = await client.download_document(doc_id, output_dir, file_type=1)
        print(f"保存先: {file_path} ({file_path.stat().st_size:,} bytes)")

        # XBRL パース
        print("\nパース中...")
        parse_result = parser.parse(file_path)
        print(f"検出ファクト数: {len(parse_result.facts)}")

        # 財務データ抽出
        financial = parser.extract_financial_data(parse_result)
        print(f"\n抽出された財務データ:")
        print("-" * 40)
        for key, value in sorted(financial.items()):
            if value is not None and value != 0:
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value:,.0f}")
                else:
                    print(f"  {key}: {value}")

    finally:
        await client.close()


async def demo_pipeline() -> None:
    """ETL パイプライン統合デモ."""
    print("\n" + "=" * 60)
    print("EDINET ETL Demo - パイプライン統合")
    print("=" * 60)

    from cs_risk_agent.etl.pipeline import ETLPipeline, PipelineStatus

    pipeline = ETLPipeline()
    print(f"\nパイプラインステータス: {pipeline.status.value}")
    print("注: 完全なパイプライン実行にはDB接続が必要です。")
    print("    docker compose up でDB起動後に実行してください。")


def main() -> None:
    parser = argparse.ArgumentParser(description="EDINET ETL デモ")
    parser.add_argument(
        "--download",
        action="store_true",
        help="XBRL ダウンロード & パースも実行 (API キー必要)",
    )
    parser.add_argument(
        "--doc-id",
        help="特定の書類IDを指定してダウンロード",
    )
    args = parser.parse_args()

    asyncio.run(demo_search())

    if args.download:
        asyncio.run(demo_download_and_parse(args.doc_id))

    asyncio.run(demo_pipeline())

    print("\n" + "=" * 60)
    print("デモ完了!")
    print("=" * 60)


if __name__ == "__main__":
    main()
