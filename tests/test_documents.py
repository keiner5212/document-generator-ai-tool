from __future__ import annotations

import json

from toon_format import loads

from pdf_ai_tools import tools
from pdf_ai_tools.render import render


def test_list_palettes() -> None:
    payload = tools.pdf_list_palettes()
    assert payload["ok"] is True
    files = {item["file"] for item in payload["palettes"]}
    assert "ocean_blue.json" in files
    assert "legal_classic.json" in files
    assert payload["count"] >= 17
    text = render(payload)
    assert loads(text)["count"] == payload["count"]
    assert "ok: true" in text


def test_list_templates() -> None:
    payload = tools.pdf_list_templates()
    assert payload["ok"] is True
    files = {item["file"] for item in payload["templates"]}
    assert {"invoice.json", "contract.json", "report.json"} <= files
    ids = {item["id"] for item in payload["templates"]}
    assert {"invoice", "contract", "report"} <= ids
    invoice = next(i for i in payload["templates"] if i["id"] == "invoice")
    assert "company_name" in invoice["variables"]
    assert invoice["palette"] == "corporate_slate"


def test_template_catalog_names_the_builtin_templates() -> None:
    from pdf_ai_tools.template import describe_builtin_templates

    catalog = describe_builtin_templates()
    for template_id in ("invoice", "contract", "report"):
        assert template_id in catalog
    assert "company_name" in catalog


def test_mcp_instructions_carry_the_catalog() -> None:
    from pdf_ai_tools.mcp_server import mcp

    instructions = mcp.instructions or ""
    assert "invoice" in instructions
    assert "contract" in instructions
    assert "report" in instructions
    assert "template_json" in instructions


def test_create_and_save(tmp_path) -> None:
    out = tmp_path / "note.pdf"
    created = tools.pdf_create_document(str(out))
    assert created["ok"] is True
    doc_id = created["doc_id"]
    assert tools.pdf_apply_palette(doc_id, "corporate_slate")["ok"] is True
    assert tools.pdf_add_heading(doc_id, "Note", level=1)["ok"] is True
    assert tools.pdf_add_paragraph(doc_id, "Body.")["ok"] is True
    saved = tools.pdf_save_document(doc_id)
    assert saved["ok"] is True
    assert out.is_file()
    assert out.stat().st_size > 0


def test_render_invoice(tmp_path) -> None:
    out = tmp_path / "invoice.pdf"
    saved = tools.pdf_render_template(
        "invoice",
        str(out),
        json.dumps(
            {
                "company_name": "CI Corp",
                "company_address": "1 Test St",
                "client_name": "Test Client",
                "client_address": "2 Test Ave",
                "invoice_number": "CI-001",
                "date": "2026-05-23",
                "due_date": "2026-06-23",
                "total": "$100.00",
            }
        ),
    )
    assert saved["ok"] is True
    assert out.is_file()


def test_render_inline_template(tmp_path) -> None:
    out = tmp_path / "inline.pdf"
    template = {
        "name": "Inline",
        "description": "written by hand",
        "variables": {"client": "who pays"},
        "document": {"page_size": "A4", "palette": "ocean_blue"},
        "metadata": {"title": "Invoice for {{client}}"},
        "header": {"left": "Acme", "right": "{{client}}", "line_below": True},
        "footer": {"center": "Thank you"},
        "page_numbers": True,
        "blocks": [
            {"kind": "heading", "kwargs": {"text": "Hello {{client}}", "level": 1}},
            {"kind": "paragraph", "kwargs": {"text": "Amount due."}},
            {"kind": "table", "kwargs": {"data": [["Item", "Cost"], ["Work", "10"]]}},
        ],
    }
    saved = tools.pdf_render_template(
        output_path=str(out),
        variables_json=json.dumps({"client": "Acme"}),
        template_json=json.dumps(template),
    )
    assert saved["ok"] is True
    assert out.is_file()

    inspected = tools.pdf_inspect_template(template_json=json.dumps(template))
    assert inspected["ok"] is True
    assert inspected["name"] == "Inline"
    assert inspected["block_count"] == 3


def test_inline_template_is_validated(tmp_path) -> None:
    out = tmp_path / "bad.pdf"

    unknown_kind = {"blocks": [{"kind": "nope", "kwargs": {}}]}
    result = tools.pdf_render_template(
        output_path=str(out), template_json=json.dumps(unknown_kind)
    )
    assert result["ok"] is False
    assert "unknown kind" in result["error"]

    unknown_argument = {"blocks": [{"kind": "heading", "kwargs": {"txt": "x"}}]}
    result = tools.pdf_render_template(
        output_path=str(out), template_json=json.dumps(unknown_argument)
    )
    assert result["ok"] is False
    assert "unknown argument" in result["error"]

    wrong_type = {
        "blocks": [{"kind": "heading", "kwargs": {"text": "x", "level": "one"}}]
    }
    result = tools.pdf_render_template(
        output_path=str(out), template_json=json.dumps(wrong_type)
    )
    assert result["ok"] is False
    assert "must be" in result["error"]

    missing_variable = {
        "variables": {"who": "the reader"},
        "blocks": [{"kind": "paragraph", "kwargs": {"text": "Hi {{who}}"}}],
    }
    result = tools.pdf_render_template(
        output_path=str(out), template_json=json.dumps(missing_variable)
    )
    assert result["ok"] is False
    assert "not filled" in result["error"]

    both_sources = tools.pdf_render_template(
        "invoice", str(out), "{}", json.dumps({"blocks": []})
    )
    assert both_sources["ok"] is False
    assert "not both" in both_sources["error"]


def test_saved_template_keeps_the_palette(tmp_path) -> None:
    out = tmp_path / "doc.pdf"
    template_path = tmp_path / "layout.json"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_apply_palette(doc_id, "legal_classic")["ok"] is True
    assert tools.pdf_add_heading(doc_id, "Clause", level=1)["ok"] is True
    assert tools.pdf_add_anchor(doc_id, "clause")["ok"] is True
    assert (
        tools.pdf_save_template(doc_id, str(template_path), name="Layout")["ok"] is True
    )

    template = json.loads(template_path.read_text())
    assert template["document"]["palette"] == "legal_classic"
    assert [block["kind"] for block in template["blocks"]] == ["heading", "anchor"]

    rendered = tools.pdf_render_template(str(template_path), str(tmp_path / "out.pdf"))
    assert rendered["ok"] is True


def test_table_of_contents_and_page_numbers(tmp_path) -> None:
    out = tmp_path / "report.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_table_of_contents(doc_id, levels=[1], title="Contents")["ok"]
    assert tools.pdf_add_heading(doc_id, "Chapter One", level=1)["ok"]
    assert tools.pdf_add_paragraph(doc_id, "First chapter.")["ok"]
    assert tools.pdf_add_page_break(doc_id)["ok"]
    assert tools.pdf_add_heading(doc_id, "Chapter Two", level=1)["ok"]
    assert tools.pdf_add_paragraph(doc_id, "Second chapter.")["ok"]
    assert tools.pdf_enable_page_numbers(doc_id, True, format="page_of_total")["ok"]
    saved = tools.pdf_save_document(doc_id)
    assert saved["ok"] is True
    assert saved["summary"]["total_pages"] == 2
    assert saved["summary"]["table_of_contents"] is True

    info = tools.pdf_read_file_info(str(out))
    assert info["ok"] is True
    assert [entry["title"] for entry in info["outline"]] == [
        "Chapter One",
        "Chapter Two",
    ]


def test_internal_link_resolves_to_the_anchor(tmp_path) -> None:
    out = tmp_path / "links.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_paragraph(doc_id, 'See <a href="#target">the target</a>.')[
        "ok"
    ]
    assert tools.pdf_add_anchor(doc_id, "target")["ok"]
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    annotations = reader.pages[0].get("/Annots")
    assert annotations
    destination = annotations[0].get_object().get("/Dest")
    assert destination is not None


def test_cover_page_is_always_first(tmp_path) -> None:
    out = tmp_path / "cover.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_table_of_contents(doc_id, levels=[1])["ok"] is True
    assert tools.pdf_add_cover_page(doc_id, title="Report")["ok"] is True
    twice = tools.pdf_add_cover_page(doc_id, title="Report")
    assert twice["ok"] is False
    assert "already has a cover page" in twice["error"]
    assert tools.pdf_add_heading(doc_id, "Chapter 1", level=1)["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    first_page = reader.pages[0].extract_text()
    assert "Report" in first_page
    assert "Chapter 1" not in first_page


def test_unknown_page_size_is_rejected(tmp_path) -> None:
    created = tools.pdf_create_document(str(tmp_path / "x.pdf"), page_size="LEGAL")
    assert created["ok"] is False
    assert "Unknown page_size" in created["error"]


def test_missing_image_names_the_path(tmp_path) -> None:
    created = tools.pdf_create_document(str(tmp_path / "x.pdf"))
    result = tools.pdf_insert_image(created["doc_id"], str(tmp_path / "nope.png"))
    assert result["ok"] is False
    assert "nope.png" in result["error"]


def test_cover_with_toc_and_page_of_total(tmp_path) -> None:
    out = tmp_path / "full.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_configure_header(doc_id, left="Corp", right="Q2")["ok"] is True
    assert tools.pdf_enable_page_numbers(doc_id, True, format="page_of_total")["ok"]
    assert tools.pdf_add_cover_page(doc_id, title="Report")["ok"] is True
    assert tools.pdf_add_table_of_contents(doc_id, levels=[1], title="Contents")["ok"]
    assert tools.pdf_add_heading(doc_id, "Chapter One", level=1)["ok"] is True
    assert tools.pdf_add_page_break(doc_id)["ok"] is True
    assert tools.pdf_add_heading(doc_id, "Chapter Two", level=1)["ok"] is True
    saved = tools.pdf_save_document(doc_id)
    assert saved["ok"] is True
    assert saved["summary"]["total_pages"] == 3

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    assert len(reader.pages) == 3
    assert "Page 3 of 3" in reader.pages[2].extract_text()


def test_bullet_marker_renders(tmp_path) -> None:
    out = tmp_path / "bullets.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_bullet_list(doc_id, items=["First", "Second"])["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    text = reader.pages[0].extract_text()
    assert "First" in text
    assert "\x7f" not in text


def test_link_to_a_missing_anchor_is_reported(tmp_path) -> None:
    out = tmp_path / "link.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_paragraph(doc_id, 'To <a href="#nowhere">nowhere</a>')["ok"]
    failed = tools.pdf_save_document(doc_id)
    assert failed["ok"] is False
    assert "nowhere" in failed["error"]
    assert "pdf_add_anchor" in failed["error"]

    assert tools.pdf_add_anchor(doc_id, "nowhere")["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True


def test_list_fonts_finds_installed_fonts() -> None:
    payload = tools.pdf_list_fonts(query="dejavu sans", limit=20)
    assert payload["ok"] is True
    assert payload["count"] > 0
    families = {row["family"] for row in payload["fonts"]}
    assert any("DejaVu Sans" in family for family in families)
    assert all("path" in row for row in payload["fonts"])


def test_use_font_and_render_unicode(tmp_path) -> None:
    out = tmp_path / "unicode.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    applied = tools.pdf_use_font(doc_id, body="DejaVu Sans")
    assert applied["ok"] is True
    assert applied["fonts"]["body"] != "Helvetica"

    assert tools.pdf_add_paragraph(doc_id, "Grüße aus München — 5 €")["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    text = PdfReader(str(out)).pages[0].extract_text()
    assert "Grüße" in text
    assert "München" in text


def test_unknown_characters_use_a_fallback_font(tmp_path) -> None:
    out = tmp_path / "fallback.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_add_paragraph(doc_id, "日本語のテキスト")["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    text = PdfReader(str(out)).pages[0].extract_text()
    assert "日本語" in text


def test_language_metadata_is_written(tmp_path) -> None:
    out = tmp_path / "lang.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_set_metadata(doc_id, title="T", language="ja-JP")["ok"] is True
    assert tools.pdf_add_paragraph(doc_id, "Body.")["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    assert reader.trailer["/Root"].get("/Lang") == "ja-JP"


def test_empty_document_is_refused(tmp_path) -> None:
    out = tmp_path / "empty.pdf"
    created = tools.pdf_create_document(str(out))
    saved = tools.pdf_save_document(created["doc_id"])
    assert saved["ok"] is False
    assert "no content" in saved["error"]


def test_save_can_keep_a_page_range(tmp_path) -> None:
    out = tmp_path / "ranged.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    for index in range(3):
        assert tools.pdf_add_heading(doc_id, f"Chapter {index + 1}", level=1)["ok"]
        assert tools.pdf_add_page_break(doc_id)["ok"]
    saved = tools.pdf_save_document(doc_id, pages="1-2")
    assert saved["ok"] is True

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    assert len(reader.pages) == 2


def test_right_to_left_text_is_ordered(tmp_path) -> None:
    from pdf_ai_tools.bidi import reorder_visual

    assert reorder_visual("ا ب") == "ب ا"
    assert reorder_visual("abc") == "abc"

    out = tmp_path / "rtl.pdf"
    created = tools.pdf_create_document(str(out))
    doc_id = created["doc_id"]
    assert tools.pdf_use_font(doc_id, body="Noto Sans Arabic")["ok"] is True
    assert tools.pdf_add_paragraph(doc_id, "هذه فقرة باللغة العربية")["ok"] is True
    assert tools.pdf_save_document(doc_id)["ok"] is True
    assert out.is_file()


def test_bidi_shim_is_installed() -> None:
    from reportlab.pdfgen import textobject

    from pdf_ai_tools.bidi import has_bidi_support

    assert has_bidi_support() is True
    assert textobject.rtlSupport is True


def test_relative_and_home_paths(tmp_path, monkeypatch) -> None:
    elsewhere = tmp_path / "client"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("HOME", str(tmp_path))
    created = tools.pdf_create_document("note.pdf")
    assert created["ok"] is True
    assert created["output_path"] == str((elsewhere / "note.pdf").resolve())
    assert tools.pdf_add_paragraph(created["doc_id"], "Body.")["ok"] is True
    assert tools.pdf_save_document(created["doc_id"])["ok"] is True
    assert (elsewhere / "note.pdf").is_file()

    created_home = tools.pdf_create_document("~/from-home.pdf")
    assert created_home["output_path"] == str((tmp_path / "from-home.pdf").resolve())
    assert tools.pdf_add_paragraph(created_home["doc_id"], "Body.")["ok"] is True
    assert tools.pdf_save_document(created_home["doc_id"])["ok"] is True
    assert (tmp_path / "from-home.pdf").is_file()

    rendered = tools.pdf_render_template(
        "invoice",
        "invoice.pdf",
        json.dumps(
            {
                "company_name": "CI Corp",
                "company_address": "1 Test St",
                "client_name": "Test Client",
                "client_address": "2 Test Ave",
                "invoice_number": "CI-001",
                "date": "2026-05-23",
                "due_date": "2026-06-23",
                "total": "$100.00",
            }
        ),
    )
    assert rendered["ok"] is True
    assert (elsewhere / "invoice.pdf").is_file()
    info = tools.pdf_read_file_info("~/from-home.pdf")
    assert info["ok"] is True
    assert info["page_count"] >= 1
