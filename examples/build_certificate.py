#!/usr/bin/env python3
"""
Example: award certificate with golden_luxury palette.
Shows: cover page (minimal style), banner, signature, horizontal lines.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pdf_ai_tools import tools

OUTPUT = ROOT / "output" / "certificate.pdf"


def main() -> None:
    r = json.loads(tools.pdf_create_document(str(OUTPUT), page_size="A4"))
    doc_id = r["doc_id"]

    tools.pdf_apply_palette(doc_id, "golden_luxury")
    tools.pdf_set_metadata(
        doc_id,
        title="Certificate of Excellence",
        author="Acme Corp",
        subject="Annual recognition award",
    )

    # No header/footer — certificates are single-page, clean
    # Cover page uses the palette's primary (dark) as background
    tools.pdf_add_cover_page(
        doc_id,
        title="Certificate of Excellence",
        subtitle="In Recognition of Outstanding Achievement",
        author="Acme Corp · 2026",
        date="",
        style="minimal",
        title_font_size=32,
    )

    # --- Certificate body ---
    tools.pdf_add_spacer(doc_id, 1.5)
    tools.pdf_add_heading(
        doc_id, "CERTIFICATE OF EXCELLENCE",
        level=1, alignment="center",
    )
    tools.pdf_add_horizontal_line(doc_id, width_percent=60, color="#d4a017", thickness=1.5)
    tools.pdf_add_spacer(doc_id, 1.0)

    tools.pdf_add_paragraph(
        doc_id,
        "This certificate is proudly presented to",
        alignment="center", font_size=12, color="#6b3a1f",
    )
    tools.pdf_add_paragraph(
        doc_id,
        "<b>Jane Doe</b>",
        alignment="center", font_size=22, color="#1a1200",
    )
    tools.pdf_add_spacer(doc_id, 0.5)
    tools.pdf_add_paragraph(
        doc_id,
        "in recognition of exceptional leadership, dedication, and outstanding "
        "contributions to the success of Acme Corporation during the fiscal year 2026.",
        alignment="center", font_size=12, color="#6b3a1f",
    )
    tools.pdf_add_spacer(doc_id, 1.5)
    tools.pdf_add_horizontal_line(doc_id, width_percent=60, color="#d4a017", thickness=1.5)
    tools.pdf_add_spacer(doc_id, 1.5)

    # Two signatures side by side
    tools.pdf_add_signature_placeholder(
        doc_id,
        label="Chief Executive Officer",
        name="A. Smith",
        count=2,
        layout="row",
        width_cm=7.0,
        height_cm=2.5,
    )

    tools.pdf_add_spacer(doc_id, 0.5)
    tools.pdf_add_paragraph(
        doc_id,
        "Acme Corporation · New York, NY · May 2026",
        alignment="center", font_size=10, color="#8a7340",
    )

    result = json.loads(tools.pdf_save_document(doc_id))
    print(f"Saved: {result['saved_to']}")


if __name__ == "__main__":
    main()
