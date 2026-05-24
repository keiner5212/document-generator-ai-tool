"""High-level PDF operations exposed as AI-callable tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import KeepTogether

from pdf_ai_tools.reader import read_pdf_info, read_pdf_page_dimensions, read_pdf_text
from pdf_ai_tools.session import PDFSession, SignatureBox, close_session, get_session, list_sessions
from pdf_ai_tools.styles import ALIGN_MAP, parse_color


def _ok(data: dict) -> str:
    return json.dumps({"ok": True, **data}, ensure_ascii=False, indent=2)


def _err(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2)


def _color_to_hex(color_obj) -> str:
    """Convert a ReportLab Color object to a #RRGGBB hex string."""
    try:
        r = max(0, min(255, int(color_obj.red * 255)))
        g = max(0, min(255, int(color_obj.green * 255)))
        b = max(0, min(255, int(color_obj.blue * 255)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#000000"


# ===========================================================================
# Document lifecycle
# ===========================================================================

def pdf_create_document(
    output_path: str,
    page_size: str = "A4",
    theme: str = "default",
    margin_left_cm: float = 2.5,
    margin_right_cm: float = 2.5,
    margin_top_cm: float = 2.5,
    margin_bottom_cm: float = 2.5,
) -> str:
    """
    Start a new PDF document session.

    Returns a doc_id required by all other tools.
    Themes (built-in): default, corporate, minimal, elegant.
    Use pdf_apply_palette to override with a custom color palette.
    """
    try:
        path = Path(output_path)
        s = PDFSession(
            output_path=path,
            page_size=page_size,
            margins_cm=(margin_left_cm, margin_right_cm, margin_top_cm, margin_bottom_cm),
            theme=theme,
        )
        s.log_element("create", output_path=str(path))
        return _ok({
            "doc_id": s.doc_id,
            "output_path": str(path),
            "message": "Document created. Use doc_id in all subsequent calls.",
        })
    except Exception as e:
        return _err(str(e))


def pdf_set_metadata(
    doc_id: str,
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
) -> str:
    """Set PDF document metadata (title, author, subject, keywords)."""
    try:
        s = get_session(doc_id)
        for key, val in [("title", title), ("author", author), ("subject", subject), ("keywords", keywords)]:
            if val:
                s.metadata[key] = val
        s.log_element("metadata", **s.metadata)
        return _ok({"doc_id": doc_id, "metadata": s.metadata})
    except Exception as e:
        return _err(str(e))


def pdf_save_document(doc_id: str) -> str:
    """Build and write the PDF to disk. The session is closed after saving."""
    try:
        s = get_session(doc_id)
        path = s.build()
        summary = s.summary()
        close_session(doc_id)
        return _ok({"doc_id": doc_id, "saved_to": str(path), "summary": summary})
    except Exception as e:
        return _err(str(e))


def pdf_get_document_state(doc_id: str) -> str:
    """Inspect the current document structure without saving."""
    try:
        return _ok(get_session(doc_id).summary())
    except Exception as e:
        return _err(str(e))


def pdf_list_documents() -> str:
    """List all active (unsaved) document sessions."""
    return _ok({"sessions": list_sessions()})


# ===========================================================================
# Palette tools
# ===========================================================================

def pdf_list_palettes(extra_dir: str = "") -> str:
    """
    List available color palettes.

    Always lists the 12 built-in palettes. Pass extra_dir to also list
    palettes in another directory.
    """
    try:
        from pdf_ai_tools.palette import list_builtin_palettes, list_palettes_in_dir
        result = list_builtin_palettes()
        if extra_dir:
            result += list_palettes_in_dir(extra_dir)
        return _ok({"palettes": result, "count": len(result)})
    except Exception as e:
        return _err(str(e))


def pdf_apply_palette(doc_id: str, palette_name_or_path: str) -> str:
    """
    Apply a color palette to an active document session.

    palette_name_or_path: built-in palette name (e.g. 'ocean_blue') OR
    absolute/relative path to a custom .json palette file.
    This overrides the theme set at document creation.
    """
    try:
        from pdf_ai_tools.palette import load_builtin_palette, load_palette
        s = get_session(doc_id)
        ref = palette_name_or_path.strip()
        if ref.endswith(".json") or "/" in ref or "\\" in ref:
            palette = load_palette(ref)
        else:
            palette = load_builtin_palette(ref)
        s.apply_palette(palette)
        s.log_element("apply_palette", palette=palette.get("name"))
        return _ok({
            "doc_id": doc_id,
            "palette_applied": palette.get("name"),
            "colors": palette.get("colors"),
            "fonts": palette.get("fonts"),
            "sizes": palette.get("sizes"),
        })
    except Exception as e:
        return _err(str(e))


def pdf_export_palette(doc_id: str, output_path: str, name: str = "") -> str:
    """
    Export the current document's theme/palette to a reusable JSON file.

    The exported file can later be used with pdf_apply_palette.
    """
    try:
        from pdf_ai_tools.palette import palette_from_session, save_palette
        s = get_session(doc_id)
        palette = palette_from_session(s)
        if name:
            palette["name"] = name
        saved = save_palette(palette, output_path)
        return _ok({"saved_to": str(saved), "palette": palette})
    except Exception as e:
        return _err(str(e))


def pdf_create_palette_from_colors(
    output_path: str,
    name: str,
    description: str = "",
    primary: str = "#1a365d",
    secondary: str = "#2c5282",
    accent: str = "#3182ce",
    muted: str = "#718096",
    border: str = "#e2e8f0",
    background: str = "#f7fafc",
    body_font: str = "Helvetica",
    heading_font: str = "Helvetica-Bold",
    body_size: float = 11,
    h1_size: float = 22,
    h2_size: float = 16,
    h3_size: float = 13,
    caption_size: float = 9,
    page_size: str = "A4",
) -> str:
    """
    Create and save a custom color palette JSON from individual color values.

    All colors accept hex (#RRGGBB), named colors, or 'r,g,b' floats.
    Fonts must be standard PDF fonts: Helvetica, Times-Roman, Courier (and their -Bold/-Oblique variants).
    """
    try:
        from pdf_ai_tools.palette import save_palette
        palette = {
            "name": name,
            "description": description,
            "colors": {
                "primary": primary,
                "secondary": secondary,
                "accent": accent,
                "muted": muted,
                "border": border,
                "background": background,
            },
            "fonts": {
                "body": body_font,
                "heading": heading_font,
            },
            "sizes": {
                "body": body_size,
                "h1": h1_size,
                "h2": h2_size,
                "h3": h3_size,
                "caption": caption_size,
            },
            "document": {
                "page_size": page_size,
                "margins_cm": [2.5, 2.5, 2.5, 2.5],
                "page_numbers": False,
                "watermark": None,
            },
        }
        saved = save_palette(palette, output_path)
        return _ok({"saved_to": str(saved), "palette": palette})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Template tools
# ===========================================================================

def pdf_list_templates(extra_dir: str = "") -> str:
    """
    List available document templates.

    Built-in templates: invoice, contract, report.
    Pass extra_dir to list templates in another directory.
    """
    try:
        from pdf_ai_tools.template import list_builtin_templates, list_templates_in_dir
        result = list_builtin_templates()
        if extra_dir:
            result += list_templates_in_dir(extra_dir)
        return _ok({"templates": result, "count": len(result)})
    except Exception as e:
        return _err(str(e))


def pdf_render_template(
    template_name_or_path: str,
    output_path: str,
    variables_json: str = "{}",
) -> str:
    """
    Render a template into a PDF, filling all {{variable}} placeholders.

    template_name_or_path: built-in name (e.g. 'invoice') OR path to .json file.
    variables_json: JSON object string mapping variable names to values.
                    Example: '{"company_name": "Acme", "client_name": "John"}'
    """
    try:
        from pdf_ai_tools.template import load_builtin_template, load_template, render_template
        ref = template_name_or_path.strip()
        if ref.endswith(".json") or "/" in ref or "\\" in ref:
            tpl = load_template(ref)
        else:
            tpl = load_builtin_template(ref)

        variables = json.loads(variables_json) if variables_json.strip() else {}
        saved_to = render_template(tpl, output_path, variables)
        return _ok({
            "saved_to": saved_to,
            "template": tpl.get("name"),
            "variables_used": list(variables.keys()),
        })
    except Exception as e:
        return _err(str(e))


def pdf_save_template(
    doc_id: str,
    output_path: str,
    name: str = "",
    description: str = "",
) -> str:
    """
    Save the current document's layout as a reusable template JSON.

    The template captures all header/footer config, metadata, and the
    sequence of content blocks. Variables can be added manually by editing
    the JSON and replacing fixed strings with {{var_name}} placeholders.
    """
    try:
        from pdf_ai_tools.template import save_template, session_to_template
        s = get_session(doc_id)
        tpl = session_to_template(s, name=name or s.doc_id, description=description)
        saved = save_template(tpl, output_path)
        return _ok({"saved_to": str(saved), "blocks": len(tpl["blocks"])})
    except Exception as e:
        return _err(str(e))


def pdf_inspect_template(path: str) -> str:
    """
    Load and display a template's structure without rendering it.

    Returns: name, description, required variables, and block summary.
    """
    try:
        from pdf_ai_tools.template import load_builtin_template, load_template
        ref = path.strip()
        if ref.endswith(".json") or "/" in ref or "\\" in ref:
            tpl = load_template(ref)
        else:
            tpl = load_builtin_template(ref)
        return _ok({
            "name": tpl.get("name"),
            "description": tpl.get("description"),
            "variables": tpl.get("variables", {}),
            "block_count": len(tpl.get("blocks", [])),
            "blocks_summary": [
                {"kind": b.get("kind"), "preview": str(b.get("kwargs", {}))}
                for b in tpl.get("blocks", [])
            ],
            "palette": tpl.get("document", {}).get("palette"),
            "page_size": tpl.get("document", {}).get("page_size"),
        })
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Header, footer, decoration
# ===========================================================================

def pdf_configure_header(
    doc_id: str,
    left: str = "",
    center: str = "",
    right: str = "",
    font_size: float = 9,
    color: str = "#718096",
    show_on_first_page: bool = True,
    line_below: bool = False,
) -> str:
    """Configure the page header (left / center / right text on every page)."""
    try:
        s = get_session(doc_id)
        s.header.left = left
        s.header.center = center
        s.header.right = right
        s.header.font_size = font_size
        s.header.color = color
        s.header.show_on_first_page = show_on_first_page
        s.header.line_below = line_below
        s.log_element("header", left=left, center=center, right=right)
        return _ok({"doc_id": doc_id, "header": {"left": left, "center": center, "right": right}})
    except Exception as e:
        return _err(str(e))


def pdf_configure_footer(
    doc_id: str,
    left: str = "",
    center: str = "",
    right: str = "",
    font_size: float = 9,
    color: str = "#718096",
    show_on_first_page: bool = True,
) -> str:
    """Configure the page footer (left / center / right text on every page)."""
    try:
        s = get_session(doc_id)
        s.footer.left = left
        s.footer.center = center
        s.footer.right = right
        s.footer.font_size = font_size
        s.footer.color = color
        s.footer.show_on_first_page = show_on_first_page
        s.log_element("footer", left=left, center=center, right=right)
        return _ok({"doc_id": doc_id, "footer": {"left": left, "center": center, "right": right}})
    except Exception as e:
        return _err(str(e))


def pdf_enable_page_numbers(doc_id: str, enabled: bool = True) -> str:
    """Show page numbers centered at the bottom of every page."""
    try:
        s = get_session(doc_id)
        s.page_numbers = enabled
        s.log_element("page_numbers", enabled=enabled)
        return _ok({"doc_id": doc_id, "page_numbers": enabled})
    except Exception as e:
        return _err(str(e))


def pdf_set_watermark(doc_id: str, text: str) -> str:
    """Add diagonal watermark text (e.g. 'DRAFT', 'CONFIDENTIAL') on every page."""
    try:
        s = get_session(doc_id)
        s.watermark_text = text
        s.log_element("watermark", text=text)
        return _ok({"doc_id": doc_id, "watermark": text})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Content blocks
# ===========================================================================

def pdf_add_heading(
    doc_id: str,
    text: str,
    level: int = 1,
    alignment: Literal["left", "center", "right"] = "left",
    color: str = "",
) -> str:
    """
    Add a heading (level 1–3).

    HTML tags inside text are NOT supported for headings; use plain text.
    """
    try:
        s = get_session(doc_id)
        level = max(1, min(3, level))
        style = s.styles[f"h{level}"].clone(f"H{level}_{id(s)}")
        style.alignment = ALIGN_MAP.get(alignment, ALIGN_MAP["left"])
        if color:
            style.textColor = parse_color(color)
        s.story.append(Paragraph(text, style))
        s.log_element(
            "heading",
            replay_kwargs={"text": text, "level": level, "alignment": alignment, "color": color},
            text=text, level=level,
        )
        return _ok({"doc_id": doc_id, "added": "heading", "level": level})
    except Exception as e:
        return _err(str(e))


def pdf_add_paragraph(
    doc_id: str,
    text: str,
    font_size: float = 11,
    alignment: Literal["left", "center", "right", "justify"] = "justify",
    bold: bool = False,
    italic: bool = False,
    color: str = "",
    space_after: float = 8,
) -> str:
    """
    Add a body paragraph.

    Supports minimal HTML: <b>, <i>, <u>, <br/>.
    alignment: left | center | right | justify
    """
    try:
        s = get_session(doc_id)
        style = s.styles["body"].clone(f"Body_{id(s)}_{len(s.story)}")
        style.fontSize = font_size
        style.leading = font_size * 1.4
        style.alignment = ALIGN_MAP.get(alignment, ALIGN_MAP["justify"])
        style.spaceAfter = space_after
        if color:
            style.textColor = parse_color(color)
        if bold:
            style.fontName = "Helvetica-Bold"
        if italic:
            style.fontName = "Helvetica-Oblique"
        s.story.append(Paragraph(text, style))
        s.log_element(
            "paragraph",
            replay_kwargs={
                "text": text, "font_size": font_size, "alignment": alignment,
                "bold": bold, "italic": italic, "color": color, "space_after": space_after,
            },
            chars=len(text),
        )
        return _ok({"doc_id": doc_id, "added": "paragraph"})
    except Exception as e:
        return _err(str(e))


def pdf_add_bullet_list(doc_id: str, items: list[str], indent_cm: float = 0.5) -> str:
    """Add an unordered bullet list. items is a list of plain strings."""
    try:
        s = get_session(doc_id)
        style = s.styles["body"]
        for item in items:
            s.story.append(Paragraph(f"• {item}", style))
        s.log_element(
            "bullet_list",
            replay_kwargs={"items": items, "indent_cm": indent_cm},
            count=len(items),
        )
        return _ok({"doc_id": doc_id, "added": "bullet_list", "items": len(items)})
    except Exception as e:
        return _err(str(e))


def pdf_add_numbered_list(doc_id: str, items: list[str]) -> str:
    """Add a numbered (ordered) list. items is a list of plain strings."""
    try:
        s = get_session(doc_id)
        style = s.styles["body"]
        for i, item in enumerate(items, 1):
            s.story.append(Paragraph(f"{i}. {item}", style))
        s.log_element(
            "numbered_list",
            replay_kwargs={"items": items},
            count=len(items),
        )
        return _ok({"doc_id": doc_id, "added": "numbered_list", "items": len(items)})
    except Exception as e:
        return _err(str(e))


def pdf_add_spacer(doc_id: str, height_cm: float = 0.5) -> str:
    """Add vertical whitespace between elements."""
    try:
        s = get_session(doc_id)
        s.story.append(Spacer(1, height_cm * cm))
        s.log_element("spacer", replay_kwargs={"height_cm": height_cm}, height_cm=height_cm)
        return _ok({"doc_id": doc_id, "added": "spacer"})
    except Exception as e:
        return _err(str(e))


def pdf_add_horizontal_line(
    doc_id: str,
    width_percent: float = 100,
    thickness: float = 1,
    color: str = "#e2e8f0",
) -> str:
    """Add a horizontal rule. width_percent: 0–100 relative to content width."""
    try:
        s = get_session(doc_id)
        w = s.content_width() * (width_percent / 100)
        s.story.append(HRFlowable(width=w, thickness=thickness, color=parse_color(color)))
        s.log_element(
            "horizontal_line",
            replay_kwargs={"width_percent": width_percent, "thickness": thickness, "color": color},
        )
        return _ok({"doc_id": doc_id, "added": "horizontal_line"})
    except Exception as e:
        return _err(str(e))


def pdf_add_page_break(doc_id: str) -> str:
    """Insert a page break, forcing subsequent content onto a new page."""
    try:
        s = get_session(doc_id)
        s.story.append(PageBreak())
        s.log_element("page_break", replay_kwargs={})
        return _ok({"doc_id": doc_id, "added": "page_break"})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Images and media
# ===========================================================================

def pdf_insert_image(
    doc_id: str,
    image_path: str,
    width_cm: float | None = None,
    height_cm: float | None = None,
    alignment: Literal["left", "center", "right"] = "center",
    caption: str = "",
) -> str:
    """
    Insert an image inline. Supported formats: PNG, JPEG, GIF, BMP.

    width_cm / height_cm: explicit dimensions in cm (aspect ratio preserved if only one is set).
    caption: optional caption shown below the image.
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return _err(f"Image not found: {image_path}")
        s = get_session(doc_id)
        img = Image(str(path), width=width_cm * cm if width_cm else None, height=height_cm * cm if height_cm else None)
        img.hAlign = alignment.upper()
        flowables = [img]
        if caption:
            flowables.append(Paragraph(caption, s.styles["caption"]))
        s.story.append(KeepTogether(flowables) if len(flowables) > 1 else img)
        s.log_element(
            "insert_image",
            replay_kwargs={
                "image_path": image_path, "width_cm": width_cm, "height_cm": height_cm,
                "alignment": alignment, "caption": caption,
            },
            path=str(path),
        )
        return _ok({"doc_id": doc_id, "added": "image", "path": str(path)})
    except Exception as e:
        return _err(str(e))


def pdf_add_qr_code(
    doc_id: str,
    data: str,
    size_cm: float = 3.0,
    caption: str = "",
) -> str:
    """Generate a QR code from data (URL, text, etc.) and insert it inline."""
    try:
        import io
        import qrcode

        s = get_session(doc_id)
        qr = qrcode.make(data)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        size = size_cm * cm
        img = Image(buf, width=size, height=size)
        img.hAlign = "CENTER"
        flowables: list = [img]
        if caption:
            flowables.append(Paragraph(caption, s.styles["caption"]))
        s.story.append(KeepTogether(flowables))
        s.log_element(
            "qr_code",
            replay_kwargs={"data": data, "size_cm": size_cm, "caption": caption},
            data=data[:80],
        )
        return _ok({"doc_id": doc_id, "added": "qr_code"})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Tables and callouts
# ===========================================================================

def pdf_add_table(
    doc_id: str,
    data: list[list[str]],
    column_widths_cm: list[float] | None = None,
    header_row: bool = True,
    zebra_stripes: bool = True,
) -> str:
    """
    Add a data table.

    data: list of rows; each row is a list of cell strings.
    column_widths_cm: explicit column widths in cm (auto if omitted).
    header_row: style the first row as a header.
    zebra_stripes: alternate row background colors.
    """
    try:
        s = get_session(doc_id)
        if not data:
            return _err("Table data cannot be empty")
        col_widths = [w * cm for w in column_widths_cm] if column_widths_cm else None
        table = Table(data, colWidths=col_widths)
        theme = s.styles["_theme"]
        cmds = [
            ("GRID",         (0, 0), (-1, -1), 0.5, theme["border"]),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("FONTNAME",     (0, 0), (-1, -1), theme["body_font"]),
        ]
        if header_row and data:
            cmds += [
                ("BACKGROUND", (0, 0), (-1, 0), theme["primary"]),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), theme["heading_font"]),
            ]
        if zebra_stripes:
            start = 1 if header_row else 0
            for i in range(start, len(data)):
                if i % 2 == 0:
                    cmds.append(("BACKGROUND", (0, i), (-1, i), theme["background"]))
        table.setStyle(TableStyle(cmds))
        s.story.append(table)
        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "table",
            replay_kwargs={
                "data": data, "column_widths_cm": column_widths_cm,
                "header_row": header_row, "zebra_stripes": zebra_stripes,
            },
            rows=len(data), cols=len(data[0]),
        )
        return _ok({"doc_id": doc_id, "added": "table", "rows": len(data), "cols": len(data[0])})
    except Exception as e:
        return _err(str(e))


def pdf_add_colored_box(
    doc_id: str,
    text: str,
    background_color: str = "#f0f9ff",
    border_color: str = "#3182ce",
    title: str = "",
) -> str:
    """
    Add a highlighted callout / info box.

    Supports minimal HTML in text: <b>, <i>, <br/>.
    """
    try:
        s = get_session(doc_id)
        rows: list[list] = []
        if title:
            rows.append([Paragraph(f"<b>{title}</b>", s.styles["h3"])])
        rows.append([Paragraph(text, s.styles["body"])])
        t = Table(rows, colWidths=[s.content_width()])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), parse_color(background_color)),
            ("BOX",          (0, 0), (-1, -1), 1.5, parse_color(border_color)),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        s.story.append(t)
        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "colored_box",
            replay_kwargs={
                "text": text, "background_color": background_color,
                "border_color": border_color, "title": title,
            },
            title=title,
        )
        return _ok({"doc_id": doc_id, "added": "colored_box"})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Signatures
# ===========================================================================

def pdf_add_signature_placeholder(
    doc_id: str,
    label: str = "Signature",
    name: str = "",
    width_cm: float = 7.0,
    height_cm: float = 2.5,
    count: int = 1,
    layout: Literal["row", "column"] = "row",
) -> str:
    """
    Add signature placeholder box(es) with dashed line and label.

    count: 1–4 signature boxes.
    layout: 'row' places them side-by-side; 'column' stacks them.
    """
    try:
        from pdf_ai_tools.session import SignaturePlaceholder

        s = get_session(doc_id)
        count = max(1, min(count, 4))
        box_w = width_cm * cm
        box_h = height_cm * cm

        boxes = []
        for i in range(count):
            sig_label = label if count == 1 else f"{label} {i + 1}"
            boxes.append(SignatureBox(box_w, box_h, label=sig_label, name=name))
            s.signatures.append(SignaturePlaceholder(label=sig_label, name=name))

        if layout == "row" and count > 1:
            t = Table([boxes], colWidths=[(box_w + 0.5 * cm)] * count)
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            s.story.append(t)
        else:
            for b in boxes:
                s.story.append(b)
                s.story.append(Spacer(1, 0.2 * cm))

        s.log_element(
            "signature_placeholder",
            replay_kwargs={
                "label": label, "name": name, "width_cm": width_cm,
                "height_cm": height_cm, "count": count, "layout": layout,
            },
            count=count, label=label,
        )
        return _ok({"doc_id": doc_id, "added": "signature_placeholder", "count": count})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Advanced decoration tools
# ===========================================================================

def pdf_add_cover_page(
    doc_id: str,
    title: str,
    subtitle: str = "",
    author: str = "",
    date: str = "",
    logo_path: str = "",
    background_color: str = "",
    accent_color: str = "",
    title_color: str = "#ffffff",
    style: Literal["stripe", "split", "minimal"] = "stripe",
    title_font_size: float = 38,
) -> str:
    """
    Add a full-bleed cover page as the first page of the document.

    MUST be called before any other content-adding tools.
    The cover uses the session's palette primary/accent colors by default.

    style options:
      stripe  — horizontal accent band across the page (default)
      split   — right-side accent panel
      minimal — thin top/bottom accent lines, clean layout

    background_color / accent_color: override palette defaults.
    """
    try:
        from pdf_ai_tools.session import CoverPageFlowable

        s = get_session(doc_id)
        if s.story:
            return _err("pdf_add_cover_page must be called before any other content tools.")

        theme = s.styles.get("_theme", {})
        cover = {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "date": date,
            "logo_path": logo_path,
            "background_color": background_color or _color_to_hex(theme.get("primary", parse_color("#1a365d"))),
            "accent_color": accent_color or _color_to_hex(theme.get("accent", parse_color("#3182ce"))),
            "title_color": title_color,
            "style": style,
            "title_font_size": title_font_size,
        }
        s.cover_page = cover
        s.story.append(CoverPageFlowable(s, cover))
        s.log_element(
            "cover_page",
            replay_kwargs={
                "title": title, "subtitle": subtitle, "author": author, "date": date,
                "logo_path": logo_path, "background_color": background_color,
                "accent_color": accent_color, "title_color": title_color,
                "style": style, "title_font_size": title_font_size,
            },
            title=title,
        )
        return _ok({"doc_id": doc_id, "added": "cover_page", "style": style})
    except Exception as e:
        return _err(str(e))


def pdf_add_section_divider(
    doc_id: str,
    title: str,
    style: Literal["line", "bar", "underline", "diamond"] = "line",
    color: str = "",
    accent_color: str = "",
    font_size: float = 13,
) -> str:
    """
    Add a decorative section divider with a title.

    style options:
      line      — ─── TITLE ─── (centred with rules on both sides)
      bar       — ▌ TITLE       (left vertical accent bar)
      underline — TITLE + full-width underline
      diamond   — ◆  TITLE  ◆  (diamond decorations)
    """
    try:
        from pdf_ai_tools.session import SectionDivider

        s = get_session(doc_id)
        theme = s.styles.get("_theme", {})
        pc = parse_color(color) if color else theme.get("primary", parse_color("#1a365d"))
        ac = parse_color(accent_color) if accent_color else theme.get("accent", parse_color("#3182ce"))
        heading_font = theme.get("heading_font", "Helvetica-Bold")

        s.story.append(Spacer(1, 0.4 * cm))
        s.story.append(SectionDivider(
            title=title,
            width=s.content_width(),
            primary_color=pc,
            accent_color=ac,
            font_name=heading_font,
            font_size=font_size,
            div_style=style,
        ))
        s.story.append(Spacer(1, 0.4 * cm))
        s.log_element(
            "section_divider",
            replay_kwargs={"title": title, "style": style, "color": color, "accent_color": accent_color, "font_size": font_size},
            title=title, style=style,
        )
        return _ok({"doc_id": doc_id, "added": "section_divider", "style": style})
    except Exception as e:
        return _err(str(e))


def pdf_add_key_metrics(
    doc_id: str,
    metrics: list[dict],
    columns: int = 3,
) -> str:
    """
    Add a row of highlighted KPI / metric boxes.

    metrics: list of dicts with keys:
      - value   (str)  — the big number/value shown prominently
      - label   (str)  — description below the value
      - color   (str, optional) — override box background color

    columns: how many boxes per row (1–4).

    Example:
      metrics=[
        {"value": "$1.2M",  "label": "Revenue"},
        {"value": "98%",    "label": "Satisfaction"},
        {"value": "142",    "label": "Clients", "color": "#f0fff4"},
      ]
    """
    try:
        s = get_session(doc_id)
        if not metrics:
            return _err("metrics list cannot be empty")

        theme = s.styles.get("_theme", {})
        accent = theme.get("accent", parse_color("#3182ce"))
        bg = theme.get("background", parse_color("#f7fafc"))
        primary = theme.get("primary", parse_color("#1a365d"))
        body_font = theme.get("body_font", "Helvetica")
        heading_font = theme.get("heading_font", "Helvetica-Bold")

        columns = max(1, min(columns, 4))
        col_w = s.content_width() / columns

        # Build cells: each metric is a mini-table inside a cell
        cells = []
        for m in metrics:
            val = m.get("value", "—")
            lbl = m.get("label", "")
            box_bg = parse_color(m["color"]) if m.get("color") else bg

            accent_hex = _color_to_hex(accent)
            val_style = s.styles["body"].clone(f"metric_val_{id(m)}_{len(cells)}")
            val_style.alignment = ALIGN_MAP["center"]
            val_style.spaceAfter = 2
            val_para = Paragraph(
                f'<font name="{heading_font}" size="22" color="{accent_hex}">{val}</font>',
                val_style,
            )

            lbl_style = s.styles["small"].clone(f"metric_lbl_{id(m)}_{len(cells)}")
            lbl_style.alignment = ALIGN_MAP["center"]
            lbl_para = Paragraph(lbl, lbl_style)

            inner_w = max(col_w - 16, 40)
            cell_tbl = Table([[val_para], [lbl_para]], colWidths=[inner_w])
            cell_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, -1), box_bg),
                ("BOX",          (0, 0), (-1, -1), 1, theme["border"]),
                ("TOPPADDING",   (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            cells.append(cell_tbl)

        # Chunk cells into rows of `columns`
        for chunk_start in range(0, len(cells), columns):
            row = cells[chunk_start:chunk_start + columns]
            # Pad with empty cells if last row is short
            while len(row) < columns:
                row.append("")
            t = Table([row], colWidths=[col_w] * columns)
            t.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            s.story.append(t)

        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "key_metrics",
            replay_kwargs={"metrics": metrics, "columns": columns},
            count=len(metrics),
        )
        return _ok({"doc_id": doc_id, "added": "key_metrics", "count": len(metrics)})
    except Exception as e:
        return _err(str(e))


def pdf_add_two_column(
    doc_id: str,
    left_text: str,
    right_text: str,
    left_width_percent: float = 50,
    gap_cm: float = 0.5,
) -> str:
    """
    Lay out two text blocks side by side.

    Both blocks support minimal HTML: <b>, <i>, <br/>.
    left_width_percent: width of the left column (right gets the remainder).
    """
    try:
        s = get_session(doc_id)
        total = s.content_width()
        gap = gap_cm * cm
        lw = total * (left_width_percent / 100) - gap / 2
        rw = total * (1 - left_width_percent / 100) - gap / 2

        style = s.styles["body"]
        left_para = Paragraph(left_text, style)
        right_para = Paragraph(right_text, style)

        t = Table([[left_para, right_para]], colWidths=[lw, rw])
        t.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",(0, 0), (-1, -1), 0),
            ("TOPPADDING",  (0, 0), (-1, -1), 0),
        ]))
        s.story.append(t)
        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "two_column",
            replay_kwargs={
                "left_text": left_text, "right_text": right_text,
                "left_width_percent": left_width_percent, "gap_cm": gap_cm,
            },
        )
        return _ok({"doc_id": doc_id, "added": "two_column"})
    except Exception as e:
        return _err(str(e))


def pdf_add_code_block(
    doc_id: str,
    code: str,
    language: str = "",
    caption: str = "",
    font_size: float = 9,
) -> str:
    """
    Add a monospace code block with subtle background.

    code: the source code or command text (newlines preserved).
    language: optional label shown as caption (e.g. 'Python', 'SQL').
    caption: overrides language label if provided.
    """
    try:
        from pdf_ai_tools.session import CodeBlockFlowable

        s = get_session(doc_id)
        theme = s.styles.get("_theme", {})

        # Choose colors: dark for midnight palette, light otherwise
        bg = theme.get("background", parse_color("#f8fafc"))
        # If background is very dark, use lighter code block
        try:
            lum = (bg.red + bg.green + bg.blue) / 3
        except Exception:
            lum = 1.0
        if lum < 0.3:
            code_bg = parse_color("#1e293b")
            code_fg = parse_color("#e2e8f0")
            border = parse_color("#334155")
        else:
            code_bg = parse_color("#f1f5f9")
            code_fg = parse_color("#1e293b")
            border = parse_color("#cbd5e1")

        cap_text = caption or (f"# {language}" if language else "")
        s.story.append(CodeBlockFlowable(
            code=code,
            width=s.content_width(),
            bg_color=code_bg,
            border_color=border,
            text_color=code_fg,
            font_size=font_size,
            caption=cap_text,
            caption_color=theme.get("muted", parse_color("#718096")),
        ))
        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "code_block",
            replay_kwargs={"code": code, "language": language, "caption": caption, "font_size": font_size},
            lines=len(code.split("\n")),
        )
        return _ok({"doc_id": doc_id, "added": "code_block", "lines": len(code.split("\n"))})
    except Exception as e:
        return _err(str(e))


def pdf_add_banner(
    doc_id: str,
    text: str,
    background_color: str = "",
    text_color: str = "#ffffff",
    font_size: float = 13,
    padding_v: float = 10,
) -> str:
    """
    Add a full-width colored banner strip with centred text.

    Useful for section announcements, call-to-action strips, or chapter titles.
    background_color defaults to the palette's primary color.
    """
    try:
        from pdf_ai_tools.session import BannerFlowable

        s = get_session(doc_id)
        theme = s.styles.get("_theme", {})
        bg = parse_color(background_color) if background_color else theme.get("primary", parse_color("#1a365d"))
        tc = parse_color(text_color)
        heading_font = theme.get("heading_font", "Helvetica-Bold")

        s.story.append(BannerFlowable(
            text=text,
            width=s.content_width(),
            background_color=bg,
            text_color=tc,
            font_name=heading_font,
            font_size=font_size,
            padding_v=padding_v,
        ))
        s.story.append(Spacer(1, 0.3 * cm))
        s.log_element(
            "banner",
            replay_kwargs={"text": text, "background_color": background_color, "text_color": text_color, "font_size": font_size},
            text=text,
        )
        return _ok({"doc_id": doc_id, "added": "banner"})
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# Read existing PDFs
# ===========================================================================

def pdf_read_file_info(path: str) -> str:
    """
    Read metadata and structure from an existing PDF file.

    Returns: page count, encryption status, document metadata, outline.
    """
    try:
        return _ok(read_pdf_info(path))
    except Exception as e:
        return _err(str(e))


def pdf_read_file_text(path: str, pages: str = "") -> str:
    """
    Extract text from an existing PDF.

    pages: comma-separated 1-based page numbers (empty = all pages).
    Example: pages='1,3,5'  — extracts only pages 1, 3, and 5.
    """
    try:
        page_list = None
        if pages.strip():
            page_list = [int(p.strip()) for p in pages.split(",") if p.strip().isdigit()]
        return _ok(read_pdf_text(path, page_numbers=page_list))
    except Exception as e:
        return _err(str(e))


def pdf_read_file_page_sizes(path: str) -> str:
    """Get the media-box dimensions (in points) of each page in an existing PDF."""
    try:
        return _ok(read_pdf_page_dimensions(path))
    except Exception as e:
        return _err(str(e))
