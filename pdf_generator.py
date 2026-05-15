"""PDF report generation."""

from __future__ import annotations

import logging
import os
from datetime import date
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

import config
from config import MAX_SOURCE_TITLE_LEN, MAX_SOURCES_IN_PDF, PDF_SUMMARY_CHUNK_WORDS, SOURCE_DEDUP_KEY_LEN
from models import Article

logger = logging.getLogger(__name__)


def build_source_list(articles: list[Article]) -> list[tuple[str, str, str]]:
    """Return up to MAX_SOURCES_IN_PDF unique (source, title, url) tuples."""
    seen:   set[str]                  = set()
    result: list[tuple[str, str, str]] = []
    for a in articles:
        key = a.title[:SOURCE_DEDUP_KEY_LEN]
        if key not in seen:
            seen.add(key)
            result.append((a.source, a.title, a.url))
    return result[:MAX_SOURCES_IN_PDF]


def generate_pdf(
    summary:       str,
    key_devs:      list[str],
    sources:       list[tuple[str, str, str]],
    article_count: int,
) -> str:
    """Build and save the dated PDF report; return the file path."""
    today_str    = date.today().strftime("%Y-%m-%d")
    display_date = date.today().strftime("%B %d, %Y")
    filename     = os.path.join(config.OUTPUT_DIR, f"india_security_{today_str}.pdf")

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        rightMargin=2.5 * cm, leftMargin=2.5 * cm,
        topMargin=2.5 * cm,   bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=18, textColor=colors.HexColor("#1a237e"),
        spaceAfter=4, alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#455a64"),
        spaceAfter=2, alignment=TA_CENTER,
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#78909c"),
        spaceAfter=16, alignment=TA_CENTER,
    )
    section_header_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#b71c1c"),
        spaceBefore=14, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyText", parent=styles["Normal"],
        fontSize=10.5, leading=16, textColor=colors.HexColor("#212121"),
        alignment=TA_JUSTIFY, spaceAfter=10,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontSize=10.5, leading=15, textColor=colors.HexColor("#212121"),
        leftIndent=15, spaceAfter=5,
    )
    source_label_style = ParagraphStyle(
        "SourceLabel", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#37474f"),
        leading=13, leftIndent=10, spaceAfter=2,
    )
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#9e9e9e"),
        alignment=TA_CENTER, spaceBefore=20,
    )

    story = []

    story.append(Paragraph("India National Security Digest", title_style))
    story.append(Paragraph("Daily Threat &amp; Security Intelligence Summary", subtitle_style))
    story.append(Paragraph(
        f"Report Date: {display_date}  |  Articles Analysed: {article_count}  |  "
        "AI-Reviewed by Google Gemini",
        meta_style,
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#1a237e"), spaceAfter=10,
    ))

    if key_devs:
        story.append(Paragraph("KEY DEVELOPMENTS", section_header_style))
        story.append(HRFlowable(
            width="100%", thickness=0.5,
            color=colors.HexColor("#e0e0e0"), spaceAfter=8,
        ))
        for dev in key_devs:
            story.append(Paragraph(f"• {xml_escape(dev)}", bullet_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#e0e0e0"), spaceAfter=8,
    ))
    story.append(Paragraph("EXECUTIVE SUMMARY", section_header_style))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#e0e0e0"), spaceAfter=8,
    ))

    words = summary.split()
    for i in range(0, max(len(words), 1), PDF_SUMMARY_CHUNK_WORDS):
        story.append(Paragraph(xml_escape(" ".join(words[i:i + PDF_SUMMARY_CHUNK_WORDS])), body_style))

    story.append(Spacer(1, 0.4 * cm))

    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#e0e0e0"), spaceAfter=8,
    ))
    story.append(Paragraph("NEWS SOURCES REFERENCED", section_header_style))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#e0e0e0"), spaceAfter=8,
    ))
    for i, (src, title, _url) in enumerate(sources, 1):
        display_title = title[:MAX_SOURCE_TITLE_LEN] + (
            "..." if len(title) > MAX_SOURCE_TITLE_LEN else ""
        )
        label = f"{i}. [{src}]  {display_title}"
        story.append(Paragraph(label, source_label_style))

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#e0e0e0"),
    ))
    story.append(Paragraph(
        "Auto-generated by India Security News Summarizer  •  For informational purposes only  •  "
        "AI-powered by Google Gemini  •  "
        "Sources: Google News RSS, NewsAPI, BBC, Reuters, ToI, NDTV, Indian Express, The Hindu",
        footer_style,
    ))

    doc.build(story)
    logger.info("generate_pdf: saved %s", filename)
    return filename
