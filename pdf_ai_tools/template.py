"""
Template system for PDF AI Tools.

Templates are JSON files that describe a complete document structure.
They support {{variable}} placeholders substituted at render time.

Schema
------
{
    "name": "My Template",
    "description": "What this template is for",
    "version": "1",
    "variables": {
        "company_name":  "Full legal name of the company",
        "client_name":   "Recipient / client full name",
        "date":          "Document date (e.g. 2026-05-23)"
    },
    "document": {
        "page_size":        "A4",
        "margin_left_cm":   2.5,
        "margin_right_cm":  2.5,
        "margin_top_cm":    2.5,
        "margin_bottom_cm": 2.5,
        "palette":          "ocean_blue"    // built-in name OR null
    },
    "metadata": {
        "title":   "{{company_name}} — Invoice",
        "author":  "{{company_name}}",
        "subject": "Service invoice"
    },
    "header": {
        "left": "{{company_name}}", "center": "", "right": "{{invoice_number}}",
        "font_size": 9, "color": "#718096",
        "show_on_first_page": true, "line_below": true
    },
    "footer": {
        "left": "", "center": "Thank you for your business", "right": "",
        "font_size": 9, "color": "#718096", "show_on_first_page": true
    },
    "page_numbers": true,
    "watermark": null,
    "blocks": [
        {"kind": "heading",   "kwargs": {"text": "INVOICE",      "level": 1, "alignment": "center"}},
        {"kind": "paragraph", "kwargs": {"text": "Dear {{client_name}},"}},
        {"kind": "spacer",    "kwargs": {"height_cm": 0.5}},
        {"kind": "signature_placeholder", "kwargs": {"label": "Authorized signature", "count": 2}}
    ]
}

Block kinds
-----------
heading, paragraph, bullet_list, numbered_list, table, colored_box,
horizontal_line, spacer, page_break, insert_image, qr_code,
signature_placeholder
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_BUILTIN_DIR = Path(__file__).resolve().parent.parent / "templates"


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _substitute(value: Any, variables: dict[str, str]) -> Any:
    """Recursively replace {{var}} in strings, dicts, and lists."""
    if isinstance(value, str):
        def _replace(m: re.Match) -> str:
            return variables.get(m.group(1), m.group(0))
        return _VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(item, variables) for item in value]
    return value


# ---------------------------------------------------------------------------
# Template file I/O
# ---------------------------------------------------------------------------

def load_template(path: str) -> dict:
    """Load a template JSON from path (checks built-in dir if relative)."""
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        candidate = _BUILTIN_DIR / path
        if candidate.exists():
            p = candidate
    if not p.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if "blocks" not in data:
        raise ValueError(f"Template missing 'blocks' key: {path}")
    return data


def load_builtin_template(name: str) -> dict:
    """Load a built-in template by name (without .json)."""
    p = _BUILTIN_DIR / f"{name}.json"
    if not p.exists():
        available = [f.stem for f in sorted(_BUILTIN_DIR.glob("*.json"))]
        raise FileNotFoundError(
            f"Built-in template '{name}' not found. Available: {available}"
        )
    return load_template(str(p))


def save_template(template: dict, path: str) -> Path:
    """Write a template dict to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def list_builtin_templates() -> list[dict[str, str]]:
    if not _BUILTIN_DIR.exists():
        return []
    result = []
    for f in sorted(_BUILTIN_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "name": data.get("name", f.stem),
                "file": f.name,
                "description": data.get("description", ""),
                "variables": list(data.get("variables", {}).keys()),
            })
        except Exception:
            pass
    return result


def list_templates_in_dir(directory: str) -> list[dict[str, str]]:
    d = Path(directory)
    if not d.exists():
        return []
    result = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "name": data.get("name", f.stem),
                "file": str(f),
                "description": data.get("description", ""),
                "variables": list(data.get("variables", {}).keys()),
            })
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Snapshot a session into a template
# ---------------------------------------------------------------------------

def session_to_template(
    session,
    name: str,
    description: str = "",
) -> dict:
    """Build a template dict from a live (or already-logged) session."""
    return {
        "name": name,
        "description": description,
        "version": "1",
        "variables": {},
        "document": {
            "page_size": session.page_size_name,
            "margin_left_cm": session.margins[0],
            "margin_right_cm": session.margins[1],
            "margin_top_cm": session.margins[2],
            "margin_bottom_cm": session.margins[3],
            "palette": None,
        },
        "metadata": dict(session.metadata),
        "header": session.header.as_dict(),
        "footer": session.footer.as_dict(),
        "page_numbers": session.page_numbers,
        "watermark": session.watermark_text,
        "blocks": session._replay_log,
    }


# ---------------------------------------------------------------------------
# Render engine
# ---------------------------------------------------------------------------

def render_template(
    template: dict,
    output_path: str,
    variables: dict[str, str] | None = None,
) -> str:
    """
    Render a template dict into a PDF file.

    Returns the path of the generated PDF as a string.
    Raises ValueError / RuntimeError on bad block kinds or tool errors.
    """
    # Lazy import to avoid circular deps at module load
    from pdf_ai_tools import tools
    from pdf_ai_tools.palette import load_builtin_palette, load_palette

    variables = variables or {}
    tpl = _substitute(template, variables)

    doc_cfg = tpl.get("document", {})
    result = json.loads(tools.pdf_create_document(
        output_path=output_path,
        page_size=doc_cfg.get("page_size", "A4"),
        margin_left_cm=doc_cfg.get("margin_left_cm", 2.5),
        margin_right_cm=doc_cfg.get("margin_right_cm", 2.5),
        margin_top_cm=doc_cfg.get("margin_top_cm", 2.5),
        margin_bottom_cm=doc_cfg.get("margin_bottom_cm", 2.5),
    ))
    if not result.get("ok"):
        raise RuntimeError(f"pdf_create_document failed: {result.get('error')}")

    doc_id = result["doc_id"]

    # Apply palette if requested
    palette_ref = doc_cfg.get("palette")
    if palette_ref:
        try:
            if palette_ref.endswith(".json") or "/" in palette_ref or "\\" in palette_ref:
                palette_data = load_palette(palette_ref)
            else:
                palette_data = load_builtin_palette(palette_ref)
            from pdf_ai_tools.session import get_session
            get_session(doc_id).apply_palette(palette_data)
        except Exception as exc:
            raise ValueError(f"Cannot load palette '{palette_ref}': {exc}") from exc

    # Metadata
    meta = tpl.get("metadata", {})
    if meta:
        tools.pdf_set_metadata(
            doc_id,
            title=meta.get("title", ""),
            author=meta.get("author", ""),
            subject=meta.get("subject", ""),
            keywords=meta.get("keywords", ""),
        )

    # Header
    hdr = tpl.get("header", {})
    if hdr:
        tools.pdf_configure_header(
            doc_id,
            left=hdr.get("left", ""),
            center=hdr.get("center", ""),
            right=hdr.get("right", ""),
            font_size=hdr.get("font_size", 9),
            color=hdr.get("color", "#718096"),
            show_on_first_page=hdr.get("show_on_first_page", True),
            line_below=hdr.get("line_below", False),
        )

    # Footer
    ftr = tpl.get("footer", {})
    if ftr:
        tools.pdf_configure_footer(
            doc_id,
            left=ftr.get("left", ""),
            center=ftr.get("center", ""),
            right=ftr.get("right", ""),
            font_size=ftr.get("font_size", 9),
            color=ftr.get("color", "#718096"),
            show_on_first_page=ftr.get("show_on_first_page", True),
        )

    if tpl.get("page_numbers"):
        tools.pdf_enable_page_numbers(doc_id, True)

    wm = tpl.get("watermark")
    if wm:
        tools.pdf_set_watermark(doc_id, wm)

    # Replay blocks — keep in sync with tools.py _replay_log kinds
    dispatch: dict[str, Any] = {
        # Core content
        "heading":               tools.pdf_add_heading,
        "paragraph":             tools.pdf_add_paragraph,
        "bullet_list":           tools.pdf_add_bullet_list,
        "numbered_list":         tools.pdf_add_numbered_list,
        "table":                 tools.pdf_add_table,
        "colored_box":           tools.pdf_add_colored_box,
        "horizontal_line":       tools.pdf_add_horizontal_line,
        "spacer":                tools.pdf_add_spacer,
        "page_break":            tools.pdf_add_page_break,
        # Media
        "insert_image":          tools.pdf_insert_image,
        "qr_code":               tools.pdf_add_qr_code,
        # Signatures
        "signature_placeholder": tools.pdf_add_signature_placeholder,
        # Advanced decoration
        "cover_page":            tools.pdf_add_cover_page,
        "section_divider":       tools.pdf_add_section_divider,
        "key_metrics":           tools.pdf_add_key_metrics,
        "two_column":            tools.pdf_add_two_column,
        "code_block":            tools.pdf_add_code_block,
        "banner":                tools.pdf_add_banner,
    }

    for i, block in enumerate(tpl.get("blocks", [])):
        kind = block.get("kind")
        kwargs = block.get("kwargs", {})
        fn = dispatch.get(kind)
        if fn is None:
            raise ValueError(f"Block {i}: unknown kind '{kind}'")
        raw = fn(doc_id, **kwargs)
        res = json.loads(raw)
        if not res.get("ok"):
            raise RuntimeError(f"Block {i} ({kind}) failed: {res.get('error')}")

    # Save
    save_res = json.loads(tools.pdf_save_document(doc_id))
    if not save_res.get("ok"):
        raise RuntimeError(f"pdf_save_document failed: {save_res.get('error')}")

    return save_res["saved_to"]
