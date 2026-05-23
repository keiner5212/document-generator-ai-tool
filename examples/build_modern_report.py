#!/usr/bin/env python3
"""
Example: modern executive report with cover page, KPIs, sections, and tables.
Shows: cover page (stripe), section dividers (bar), key metrics, colored boxes.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pdf_ai_tools import tools

OUTPUT = ROOT / "output" / "modern_report.pdf"


def main() -> None:
    r = json.loads(tools.pdf_create_document(str(OUTPUT), page_size="A4"))
    doc_id = r["doc_id"]

    # --- Palette: vibrant startup for a modern look ---
    tools.pdf_apply_palette(doc_id, "vibrant_startup")
    tools.pdf_set_metadata(doc_id, title="Q2 2026 Business Report", author="Acme Corp")

    # --- Header / Footer (not shown on cover page) ---
    tools.pdf_configure_header(
        doc_id, left="Acme Corp", right="Q2 2026 — Confidential",
        line_below=True, show_on_first_page=False,
    )
    tools.pdf_configure_footer(
        doc_id, center="© 2026 Acme Corp. All rights reserved.",
        show_on_first_page=False,
    )
    tools.pdf_enable_page_numbers(doc_id, True)

    # --- Cover page ---
    tools.pdf_add_cover_page(
        doc_id,
        title="Q2 2026 Business Report",
        subtitle="Strategy · Financials · Outlook",
        author="Acme Corp",
        date="May 2026",
        style="stripe",
    )

    # --- Executive Summary ---
    tools.pdf_add_section_divider(doc_id, "Executive Summary", style="bar")
    tools.pdf_add_paragraph(
        doc_id,
        "Acme Corp delivered strong Q2 results driven by product expansion and "
        "geographic diversification. Revenue grew <b>34%</b> year-over-year, "
        "surpassing analyst consensus by a significant margin.",
    )
    tools.pdf_add_colored_box(
        doc_id,
        "Net revenue reached <b>$4.8M</b> in Q2 — the strongest quarter in company history.",
        title="Highlight",
        background_color="#f0f9ff",
        border_color="#6366f1",
    )

    # --- KPIs ---
    tools.pdf_add_section_divider(doc_id, "Key Metrics", style="bar")
    tools.pdf_add_key_metrics(
        doc_id,
        metrics=[
            {"value": "$4.8M",  "label": "Revenue"},
            {"value": "+34%",   "label": "YoY Growth"},
            {"value": "142",    "label": "New Clients"},
            {"value": "98%",    "label": "Retention"},
        ],
        columns=4,
    )

    # --- Financial table ---
    tools.pdf_add_section_divider(doc_id, "Financial Summary", style="bar")
    tools.pdf_add_table(
        doc_id,
        data=[
            ["Metric",         "Q1 2026",  "Q2 2026",  "Change"],
            ["Revenue",        "$3.58M",   "$4.80M",   "+34%"],
            ["Gross Margin",   "62%",      "67%",      "+5pp"],
            ["Operating Exp.", "$1.20M",   "$1.35M",   "+12%"],
            ["Net Profit",     "$1.02M",   "$1.87M",   "+83%"],
        ],
        header_row=True,
        zebra_stripes=True,
    )

    # --- Two columns: market / product ---
    tools.pdf_add_section_divider(doc_id, "Strategic Overview", style="bar")
    tools.pdf_add_two_column(
        doc_id,
        left_text=(
            "<b>Market Expansion</b><br/>"
            "We entered 3 new markets in LATAM with localized offerings. "
            "Pipeline in these regions now represents 22% of projected Q3 revenue."
        ),
        right_text=(
            "<b>Product Milestones</b><br/>"
            "Launch of AI-assisted feature set was completed in June, reducing "
            "average onboarding time from 14 days to 3 days."
        ),
        left_width_percent=50,
    )

    # --- Page break → Outlook ---
    tools.pdf_add_page_break(doc_id)
    tools.pdf_add_section_divider(doc_id, "Q3 Outlook", style="bar")
    tools.pdf_add_paragraph(
        doc_id,
        "Management guides Q3 revenue in the range of <b>$5.2M–$5.6M</b>, "
        "reflecting continued client acquisition momentum and two major "
        "enterprise contract closings expected in July.",
    )
    tools.pdf_add_bullet_list(
        doc_id,
        items=[
            "Close enterprise agreements with Globex Corp and Initech ($1.4M combined ARR)",
            "Expand engineering team by 8 FTEs to accelerate roadmap",
            "Launch Partner Program targeting 50 resellers by end of Q3",
            "Achieve SOC 2 Type II certification by August 31",
        ],
    )

    result = json.loads(tools.pdf_save_document(doc_id))
    print(f"Saved: {result['saved_to']}")


if __name__ == "__main__":
    main()
