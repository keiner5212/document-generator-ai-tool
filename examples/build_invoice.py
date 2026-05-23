#!/usr/bin/env python3
"""Example: build an invoice PDF without MCP (direct Python API)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pdf_ai_tools import tools

OUTPUT = ROOT / "output" / "invoice.pdf"


def main() -> None:
    r = tools.pdf_create_document(
        str(OUTPUT),
        page_size="A4",
        theme="corporate",
    )
    import json
    doc = json.loads(r)
    doc_id = doc["doc_id"]

    tools.pdf_set_metadata(doc_id, title="Invoice #1042", author="PDF AI Tools")
    tools.pdf_configure_header(
        doc_id,
        left="PDF AI Tools Inc.",
        right="Invoice #1042",
        line_below=True,
    )
    tools.pdf_configure_footer(doc_id, center="Thank you for your business")
    tools.pdf_enable_page_numbers(doc_id, True)

    tools.pdf_add_heading(doc_id, "INVOICE", level=1, alignment="center")
    tools.pdf_add_paragraph(
        doc_id,
        "Bill to: <b>Jane Doe</b><br/>123 Main St<br/>Date: 2026-05-23",
        alignment="left",
    )
    tools.pdf_add_spacer(doc_id, 0.5)
    tools.pdf_add_table(
        doc_id,
        data=[
            ["Item", "Qty", "Unit", "Total"],
            ["Consulting", "10", "$150", "$1,500"],
            ["Support plan", "1", "$200", "$200"],
        ],
        header_row=True,
    )
    tools.pdf_add_colored_box(
        doc_id,
        "Total due: <b>$1,700</b> — Payment within 30 days.",
        title="Amount due",
    )
    tools.pdf_add_signature_placeholder(doc_id, label="Authorized signature", name="Jane Doe")

    result = tools.pdf_save_document(doc_id)
    print(result)


if __name__ == "__main__":
    main()
