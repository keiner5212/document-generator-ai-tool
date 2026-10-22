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
