"""PDF レポート生成.

reportlabを使用してリスク分析レポートをPDF形式で生成する。
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# リスクレベル色マッピング
_RISK_COLORS = {
    "critical": colors.HexColor("#dc2626"),
    "high": colors.HexColor("#f97316"),
    "medium": colors.HexColor("#eab308"),
    "low": colors.HexColor("#22c55e"),
}


def generate_risk_report_pdf(
    companies: list[dict[str, Any]],
    risk_scores: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    summary: dict[str, Any],
    fiscal_year: int,
    language: str = "ja",
) -> bytes:
    """リスク分析レポートPDFを生成.

    Args:
        companies: 企業一覧
        risk_scores: リスクスコア一覧
        alerts: アラート一覧
        summary: リスクサマリー
        fiscal_year: 対象会計年度
        language: 言語 (ja/en)

    Returns:
        PDF バイナリデータ
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
    )

    elements: list[Any] = []

    # タイトル
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(Paragraph(
        f"Consolidated Subsidiary Risk Analysis Report - FY{fiscal_year}",
        title_style,
    ))
    elements.append(Paragraph(f"Generated: {now}", body_style))
    elements.append(Spacer(1, 10 * mm))

    # エグゼクティブサマリー
    elements.append(Paragraph("1. Executive Summary", heading_style))
    total = summary.get("total_companies", 0)
    avg = summary.get("avg_score", 0)
    by_level = summary.get("by_level", {})
    elements.append(Paragraph(
        f"Total subsidiaries analyzed: {total}<br/>"
        f"Average risk score: {avg}<br/>"
        f"Critical: {by_level.get('critical', 0)} | "
        f"High: {by_level.get('high', 0)} | "
        f"Medium: {by_level.get('medium', 0)} | "
        f"Low: {by_level.get('low', 0)}",
        body_style,
    ))
    elements.append(Spacer(1, 5 * mm))

    # リスクスコアテーブル
    elements.append(Paragraph("2. Risk Scores by Subsidiary", heading_style))
    if risk_scores:
        table_data = [["Entity", "Total", "DA", "Fraud", "Rule", "Benford", "Level"]]
        for rs in sorted(risk_scores, key=lambda x: x.get("total_score", 0), reverse=True):
            name = rs.get("entity_name", "")
            if len(name) > 25:
                name = name[:22] + "..."
            table_data.append([
                name,
                f"{rs.get('total_score', 0):.1f}",
                f"{rs.get('da_score', 0):.1f}",
                f"{rs.get('fraud_score', 0):.1f}",
                f"{rs.get('rule_score', 0):.1f}",
                f"{rs.get('benford_score', 0):.1f}",
                rs.get("risk_level", ""),
            ])

        table = Table(
            table_data,
            colWidths=[55 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm, 18 * mm, 18 * mm],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
    elements.append(Spacer(1, 5 * mm))

    # アラート一覧
    elements.append(Paragraph("3. Risk Alerts", heading_style))
    if alerts:
        for alert in alerts:
            sev = alert.get("severity", "medium")
            color = _RISK_COLORS.get(sev, colors.gray)
            elements.append(Paragraph(
                f'<font color="{color.hexval()}">[{sev.upper()}]</font> '
                f'{alert.get("title", "")}',
                body_style,
            ))
            elements.append(Paragraph(
                f'&nbsp;&nbsp;&nbsp;{alert.get("description", "")}',
                ParagraphStyle(
                    "AlertDesc", parent=body_style, fontSize=8,
                    textColor=colors.HexColor("#64748b"),
                ),
            ))
            action = alert.get("recommended_action")
            if action:
                elements.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;Recommended: {action}",
                    ParagraphStyle(
                        "AlertAction", parent=body_style, fontSize=8,
                        textColor=colors.HexColor("#2563eb"),
                    ),
                ))
    else:
        elements.append(Paragraph("No alerts found.", body_style))

    elements.append(Spacer(1, 10 * mm))

    # フッター
    elements.append(Paragraph(
        "This report was auto-generated by CS Risk Agent. "
        "Data accuracy depends on source quality.",
        ParagraphStyle(
            "Footer", parent=body_style, fontSize=7, textColor=colors.gray,
        ),
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("PDF report generated: %d bytes", len(pdf_bytes))
    return pdf_bytes
