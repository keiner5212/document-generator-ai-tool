"""PDF document session. Holds mutable state while an agent builds a PDF."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.tableofcontents import TableOfContents

from pdf_ai_tools.paths import resolve_user_path
from pdf_ai_tools.styles import (
    build_styles,
    build_styles_from_palette,
    parse_color,
)

PAGE_SIZES = {
    "A4": A4,
    "LETTER": LETTER,
    "A4_LANDSCAPE": landscape(A4),
    "LETTER_LANDSCAPE": landscape(LETTER),
}

_REGISTRY: dict[str, PDFSession] = {}


# ===========================================================================
# Config dataclasses
# ===========================================================================


@dataclass
class HeaderFooterConfig:
    left: str = ""
    center: str = ""
    right: str = ""
    font_size: float = 9
    color: str = "#718096"
    show_on_first_page: bool = True
    line_below: bool = False

    def as_dict(self) -> dict:
        return {
            "left": self.left,
            "center": self.center,
            "right": self.right,
            "font_size": self.font_size,
            "color": self.color,
            "show_on_first_page": self.show_on_first_page,
            "line_below": self.line_below,
        }


@dataclass
class SignaturePlaceholder:
    label: str
    name: str


# ===========================================================================
# Flowables
# ===========================================================================


class SignatureBox(Flowable):
    """Signature placeholder with dashed line, label, and optional name."""

    def __init__(
        self,
        width: float,
        height: float,
        label: str = "Signature",
        name: str = "",
        border_color=None,
        fill_color=None,
        font_name: str = "Helvetica",
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.label = label
        self.name = name
        self.font_name = font_name
        self.border_color = border_color or colors.HexColor("#cbd5e1")
        self.fill_color = fill_color or colors.HexColor("#f8fafc")

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.border_color)
        c.setFillColor(self.fill_color)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont(self.font_name, 8)
        c.drawString(6, self.height - 14, self.label)
        if self.name:
            c.setFillColor(colors.black)
            c.setFont(self.font_name, 10)
            c.drawString(6, 8, self.name)
        c.setDash(2, 2)
        c.line(6, 22, self.width - 6, 22)
        c.setDash()


def _draw_cover_logo(canv, logo_path: str, x: float, y: float, size: float) -> None:
    try:
        canv.drawImage(
            logo_path,
            x,
            y,
            size,
            size,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        return


class CoverPageFlowable(Flowable):
    """
    Full-bleed cover page drawn at canvas level.

    Fills the frame area but draws outside it by translating to page origin.
    ReportLab automatically starts a new page for subsequent flowables.
    """

    def __init__(self, session: PDFSession, cover: dict):
        super().__init__()
        self._s = session
        self._c = cover
        self.width = session.content_width()
        self.height = session.content_height()

    def draw(self):
        canv = self.canv
        s = self._s
        c = self._c
        pw, ph = s.pagesize
        left_m, _right_m, _top_m, bot_m = s.margins

        canv.saveState()
        # Move to absolute page origin from frame-local coords
        canv.translate(-left_m * cm, -bot_m * cm)

        # --- Background ---
        bg = parse_color(c.get("background_color", "#1a365d"))
        canv.setFillColor(bg)
        canv.rect(0, 0, pw, ph, stroke=0, fill=1)

        # --- Accent stripe (horizontal) ---
        accent = parse_color(c.get("accent_color", "#3182ce"))
        style = c.get("style", "stripe")  # stripe | split | minimal

        if style == "split":
            # Right-side colored panel
            canv.setFillColor(accent)
            canv.rect(pw * 0.52, 0, pw * 0.48, ph, stroke=0, fill=1)
            # Diagonal slash cut using a path
            canv.setFillColor(bg)
            p = canv.beginPath()
            p.moveTo(pw * 0.45, 0)
            p.lineTo(pw * 0.60, 0)
            p.lineTo(pw * 0.55, ph)
            p.lineTo(pw * 0.40, ph)
            p.close()
            canv.drawPath(p, stroke=0, fill=1)
        elif style == "minimal":
            # Thin bottom accent bar
            canv.setFillColor(accent)
            canv.rect(0, 0, pw, ph * 0.008, stroke=0, fill=1)
            canv.rect(0, ph * 0.98, pw, ph * 0.008, stroke=0, fill=1)
        else:  # stripe (default)
            # Horizontal band at ~38% from top
            stripe_y = ph * 0.38
            canv.setFillColor(accent)
            canv.rect(0, stripe_y, pw, ph * 0.007, stroke=0, fill=1)
            # Thin bar at very top
            canv.rect(0, ph - 2, pw, 2, stroke=0, fill=1)

        # --- Logo (if provided) ---
        logo_path = c.get("logo_path", "")
        if logo_path:
            logo = resolve_user_path(logo_path)
            if logo.is_file():
                logo_h = 2.2 * cm
                _draw_cover_logo(canv, str(logo), (pw - logo_h) / 2, ph * 0.78, logo_h)

        # --- Title ---
        title = c.get("title", "")
        title_color = parse_color(c.get("title_color", "#ffffff"))
        title_sz = float(c.get("title_font_size", 38))
        heading_font = s.styles.get("_theme", {}).get("heading_font", "Helvetica-Bold")
        title, heading_font = s.canvas_text(title, heading_font)

        canv.setFillColor(title_color)
        canv.setFont(heading_font, title_sz)
        title_y = ph * 0.57
        # Wrap long titles
        words = title.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if canv.stringWidth(test, heading_font, title_sz) < pw * 0.8:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for i, line in enumerate(lines):
            s.draw_text(
                canv,
                line,
                0,
                title_y - i * (title_sz * 1.25),
                title_sz,
                heading_font,
                align="center",
                width=pw,
            )

        # --- Subtitle ---
        subtitle = c.get("subtitle", "")
        if subtitle:
            sub_sz = float(c.get("subtitle_font_size", 15))
            sub_y = title_y - len(lines) * title_sz * 1.25 - 14
            body_font = s.styles.get("_theme", {}).get("body_font", "Helvetica")
            subtitle, body_font = s.canvas_text(subtitle, body_font)
            canv.setFillColor(parse_color(c.get("subtitle_color", "#a0aec0")))
            s.draw_text(
                canv,
                subtitle,
                0,
                sub_y,
                sub_sz,
                body_font,
                align="center",
                width=pw,
            )

        # --- Author / date (bottom meta strip) ---
        author = c.get("author", "")
        date = c.get("date", "")
        meta = " · ".join(filter(None, [author, date]))
        body_font = s.styles.get("_theme", {}).get("body_font", "Helvetica")
        meta, body_font = s.canvas_text(meta, body_font)
        if meta:
            canv.setFillColor(parse_color(c.get("meta_color", "#94a3b8")))
            s.draw_text(
                canv, meta, 0, ph * 0.1, 10, body_font, align="center", width=pw
            )

        canv.restoreState()


def _draw_diamond(canv, cx: float, cy: float, size: float) -> None:
    """Draw a filled diamond centred on (cx, cy)."""
    path = canv.beginPath()
    path.moveTo(cx, cy + size)
    path.lineTo(cx + size, cy)
    path.lineTo(cx, cy - size)
    path.lineTo(cx - size, cy)
    path.close()
    canv.drawPath(path, stroke=0, fill=1)


class SectionDivider(Flowable):
    """
    Decorative section divider with title.

    styles: 'line' (centred text between rules), 'bar' (left accent bar),
            'underline' (title + full underline), 'diamond' (◆ title ◆).
    """

    def __init__(
        self,
        title: str,
        width: float,
        primary_color,
        accent_color,
        font_name: str = "Helvetica-Bold",
        font_size: float = 13,
        div_style: str = "line",
    ):
        super().__init__()
        self.title = title
        self.width = width
        self.primary_color = primary_color
        self.accent_color = accent_color
        self.font_name = font_name
        self.font_size = font_size
        self.div_style = div_style
        self.height = font_size * 2.4
        self.hAlign = "LEFT"

    def draw(self):
        canv = self.canv
        w = self.width
        h = self.height
        mid = h / 2
        fn, fs = self.font_name, self.font_size
        pc, ac = self.primary_color, self.accent_color

        if self.div_style == "bar":
            # ▌ TITLE
            canv.setFillColor(ac)
            canv.rect(0, mid - fs * 0.6, 3.5, fs * 1.2, stroke=0, fill=1)
            canv.setFont(fn, fs)
            canv.setFillColor(pc)
            canv.drawString(12, mid - fs * 0.32, self.title)

        elif self.div_style == "underline":
            # TITLE
            # ═══════
            canv.setFont(fn, fs)
            canv.setFillColor(pc)
            canv.drawString(0, mid + 4, self.title)
            canv.setStrokeColor(ac)
            canv.setLineWidth(1.5)
            canv.line(0, mid - 2, w, mid - 2)

        elif self.div_style == "diamond":
            # ◆ TITLE ◆
            canv.setFont(fn, fs)
            tw = canv.stringWidth(self.title, fn, fs)
            title_x = (w - tw) / 2
            size = fs * 0.3
            gap = fs * 0.6
            cy = mid - fs * 0.32 + fs * 0.35
            canv.setFillColor(ac)
            _draw_diamond(canv, title_x - gap - size, cy, size)
            canv.setFillColor(pc)
            canv.drawString(title_x, mid - fs * 0.32, self.title)
            canv.setFillColor(ac)
            _draw_diamond(canv, title_x + tw + gap + size, cy, size)

        else:  # "line" (default) — ─── TITLE ───
            canv.setFont(fn, fs)
            tw = canv.stringWidth(self.title, fn, fs)
            gap = 10
            cx = w / 2
            lx1 = cx - tw / 2 - gap
            lx2 = cx + tw / 2 + gap
            canv.setStrokeColor(ac)
            canv.setLineWidth(0.75)
            if lx1 > 0:
                canv.line(0, mid, lx1, mid)
            if lx2 < w:
                canv.line(lx2, mid, w, mid)
            canv.setFillColor(pc)
            canv.drawCentredString(cx, mid - fs * 0.32, self.title)


class BannerFlowable(Flowable):
    """Full-width colored banner strip with centred text."""

    def __init__(
        self,
        text: str,
        width: float,
        background_color,
        text_color,
        font_name: str = "Helvetica-Bold",
        font_size: float = 13,
        padding_v: float = 10,
    ):
        super().__init__()
        self.text = text
        self.width = width
        self.bg = background_color
        self.tc = text_color
        self.fn = font_name
        self.fs = font_size
        self.pv = padding_v
        self.height = font_size + padding_v * 2

    def draw(self):
        canv = self.canv
        canv.setFillColor(self.bg)
        canv.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        canv.setFont(self.fn, self.fs)
        canv.setFillColor(self.tc)
        canv.drawCentredString(self.width / 2, self.pv, self.text)


class CodeBlockFlowable(Flowable):
    """Monospace code block with subtle background and optional caption."""

    def __init__(
        self,
        code: str,
        width: float,
        bg_color,
        border_color,
        text_color,
        font_size: float = 9,
        caption: str = "",
        caption_color=None,
        font_name: str = "Courier",
        caption_font: str = "Helvetica",
    ):
        super().__init__()
        self.code = code
        self.width = width
        self.bg = bg_color
        self.border = border_color
        self.tc = text_color
        self.fs = font_size
        self.caption = caption
        self.cap_color = caption_color or text_color
        self.font_name = font_name
        self.caption_font = caption_font
        self._padding = 10
        lines = code.split("\n")
        line_h = font_size * 1.4
        self.height = len(lines) * line_h + self._padding * 2
        if caption:
            self.height += font_size * 1.6

    def draw(self):
        canv = self.canv
        p = self._padding
        line_h = self.fs * 1.4

        canv.setFillColor(self.bg)
        canv.setStrokeColor(self.border)
        canv.rect(0, 0, self.width, self.height, stroke=1, fill=1)

        if self.caption:
            canv.setFont(self.caption_font, self.fs - 1)
            canv.setFillColor(self.cap_color)
            cap_y = self.height - p + 2
            canv.drawString(p, cap_y, self.caption)

        canv.setFont(self.font_name, self.fs)
        canv.setFillColor(self.tc)
        lines = self.code.split("\n")
        y = self.height - p - line_h
        if self.caption:
            y -= self.fs * 1.6
        for line in lines:
            canv.drawString(p, y, line)
            y -= line_h


# ===========================================================================
# Document template
# ===========================================================================


class _DocTemplate(BaseDocTemplate):
    """Document template that reports headings to the table of contents."""

    def __init__(self, session: PDFSession, *args, **kwargs):
        self._session = session
        super().__init__(*args, **kwargs)

    def beforeDocument(self):
        # Every build pass numbers the headings the same way.
        self._session._toc_counter = 0

    def afterFlowable(self, flowable):
        level = getattr(flowable, "_toc_level", None)
        if level is None or level not in self._session.toc_levels:
            return
        text = flowable.getPlainText().strip()
        if not text:
            return
        key = f"toc{self._session._toc_counter}"
        self._session._toc_counter += 1
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level - 1, closed=False)
        self.notify("TOCEntry", (level - 1, text, self.page, key))


# ===========================================================================
# Session
# ===========================================================================


DEFAULT_FONTS = {
    "body": "Helvetica",
    "heading": "Helvetica-Bold",
    "code": "Courier",
    "bold": "Helvetica-Bold",
    "italic": "Helvetica-Oblique",
    "bold_italic": "Helvetica-BoldOblique",
}

_CJK_RANGES = (
    (0x2E80, 0x2FFF),
    (0x3000, 0x30FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF),
    (0xFF00, 0xFFEF),
)


def _has_cjk(text: str) -> bool:
    """True when the text contains Chinese, Japanese or Korean characters."""
    return any(any(low <= ord(ch) <= high for low, high in _CJK_RANGES) for ch in text)


def _wrap_unsupported(text: str, missing: set[int]) -> str:
    """Wrap the characters the font cannot draw in a font that can."""
    from pdf_ai_tools import fonts as fonts_module

    parts = re.split(r"(<[^>]*>)", text)
    out: list[str] = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            out.append(part)
            continue
        for is_missing, chunk in fonts_module.split_by_coverage(part, missing):
            if not is_missing:
                out.append(chunk)
                continue
            chars = frozenset(ord(c) for c in chunk)
            font_name = fonts_module.font_for_chars(chars)
            if font_name is None:
                sample = "".join(sorted(chunk))[:8]
                raise ValueError(
                    f"No installed font can draw {sample!r}. "
                    "Call pdf_list_fonts(for_text=...) to see what is available."
                )
            safe = chunk.replace("&", "&amp;").replace("<", "&lt;")
            out.append(f'<font name="{font_name}">{safe}</font>')
    return "".join(out)


class PDFSession:
    """Mutable PDF build session."""

    def __init__(
        self,
        output_path: str | Path,
        page_size: str = "A4",
        margins_cm: tuple[float, float, float, float] = (2.5, 2.5, 2.5, 2.5),
    ):
        self.doc_id = str(uuid.uuid4())[:8]
        self.output_path = resolve_user_path(output_path)
        self.page_size_name = page_size.upper().replace("-", "_")
        self.pagesize = PAGE_SIZES.get(self.page_size_name, A4)
        self.margins = margins_cm  # (left, right, top, bottom) in cm
        self.theme_name = "default"
        self.palette_ref: str | None = None
        self.palette: dict | None = None
        self.fonts: dict[str, str] = dict(DEFAULT_FONTS)
        self.styles = build_styles()
        self.story: list = []
        self.header = HeaderFooterConfig()
        self.footer = HeaderFooterConfig()
        self.metadata: dict[str, str] = {}
        self.signatures: list[SignaturePlaceholder] = []
        self.anchors: set[str] = set()
        self.link_targets: list[str] = []
        self.watermark_text: str | None = None
        self.page_numbers: bool = False
        self.page_number_format: str = "page"
        self.total_pages: int | None = None
        self.toc_levels: list[int] = []
        self._toc_counter = 0
        self.cover_page: dict | None = None  # set by pdf_add_cover_page
        self._element_log: list[dict[str, Any]] = []
        self._replay_log: list[dict[str, Any]] = []
        _REGISTRY[self.doc_id] = self

    # ------------------------------------------------------------------

    def log_element(
        self, kind: str, replay_kwargs: dict | None = None, **details: Any
    ) -> None:
        self._element_log.append({"kind": kind, **details})
        if replay_kwargs is not None:
            self._replay_log.append({"kind": kind, "kwargs": replay_kwargs})

    def content_width(self) -> float:
        left, right, _, _ = self.margins
        return self.pagesize[0] - (left + right) * cm

    def content_height(self) -> float:
        _, _, top, bottom = self.margins
        return self.pagesize[1] - (top + bottom) * cm

    def apply_palette(self, palette: dict, ref: str = "") -> None:
        self.palette = palette
        self.theme_name = palette.get("name", "custom")
        self.palette_ref = ref or None
        self.rebuild_styles()

    def rebuild_styles(self) -> None:
        """Rebuild the paragraph styles with the current palette and fonts."""
        if self.palette:
            self.styles = build_styles_from_palette(self.palette, self.fonts)
        else:
            self.styles = build_styles(self.fonts)

    def apply_fonts(
        self,
        body: str = "",
        heading: str = "",
        code: str = "",
        variants: dict[str, str] | None = None,
    ) -> None:
        """Set the fonts used for body, headings and code."""
        if body:
            self.fonts["body"] = body
        if heading:
            self.fonts["heading"] = heading
        if code:
            self.fonts["code"] = code
        for role, name in (variants or {}).items():
            if name:
                self.fonts[role] = name
        if self.palette:
            self.palette["fonts"] = {
                "body": self.fonts["body"],
                "heading": self.fonts["heading"],
            }
        self.rebuild_styles()

    def prepare_text(self, text: str, style) -> str:
        """
        Make a piece of text renderable with the current fonts.

        Characters the font cannot draw are wrapped in a fallback font taken
        from this machine. Raises ValueError when no installed font can draw
        them.
        """
        from pdf_ai_tools import fonts as fonts_module

        # Right to left text is put in visual order first, so the font
        # markup added below is not reordered.
        text = self._prepare_direction(text, style)
        missing = fonts_module.missing_characters(text, style.fontName)
        if missing:
            text = _wrap_unsupported(text, missing)
        if _has_cjk(text):
            style.wordWrap = "CJK"
        if fonts_module.is_shapable(style.fontName):
            style.shaping = 1
        return text

    def _prepare_direction(self, text: str, style) -> str:
        """Handle right to left text."""
        from pdf_ai_tools.bidi import has_bidi_support, has_rtl, reorder_rtl

        if not has_rtl(text):
            return text
        if has_bidi_support():
            style.wordWrap = "RTL"
            return text
        # No bidi support on this machine: put the text in visual order here
        # and leave the letter forms unshaped.
        style.shaping = 0
        return reorder_rtl(text)

    def font_covering(self, text: str, preferred: str) -> str:
        """A registered font that can draw every character of the text."""
        from pdf_ai_tools import fonts as fonts_module

        if not fonts_module.missing_characters(text, preferred):
            return preferred
        chars = {ord(c) for c in text if c not in "\n\r\t"}
        fallback = fonts_module.find_font_for(chars)
        if fallback is None:
            return preferred
        return fonts_module.register_font(fallback.path, subfont=fallback.subfont)

    def canvas_text(self, text: str, preferred: str) -> tuple[str, str]:
        """Text and font for text drawn straight on the canvas."""
        from pdf_ai_tools.bidi import reorder_visual

        return reorder_visual(text), self.font_covering(text, preferred)

    def font_runs(self, text: str, preferred: str) -> list[tuple[str, str]]:
        """
        Split text into runs of one font each.

        Used for text drawn straight on the canvas, where one string can only
        carry one font. Every run gets a font that can draw it.
        """
        from pdf_ai_tools import fonts as fonts_module

        missing = fonts_module.missing_characters(text, preferred)
        if not missing:
            return [(preferred, text)] if text else []
        runs: list[tuple[str, str]] = []
        for is_missing, chunk in fonts_module.split_by_coverage(text, missing):
            if not is_missing:
                runs.append((preferred, chunk))
                continue
            chars = frozenset(ord(c) for c in chunk)
            font_name = fonts_module.font_for_chars(chars) or preferred
            runs.append((font_name, chunk))
        return runs

    def draw_text(
        self,
        canv,
        text: str,
        x: float,
        y: float,
        size: float,
        preferred: str,
        align: str = "left",
        width: float = 0,
    ) -> None:
        """Draw text on the canvas, one font per run."""
        runs = self.font_runs(text, preferred)
        if not runs:
            return
        total = sum(canv.stringWidth(chunk, font, size) for font, chunk in runs)
        if align == "center":
            x = x + width / 2 - total / 2
        elif align == "right":
            x = x + width - total
        for font, chunk in runs:
            canv.setFont(font, size)
            canv.drawString(x, y, chunk)
            x += canv.stringWidth(chunk, font, size)

    def enable_toc(self, levels: list[int]) -> TableOfContents:
        """Insert a table of contents that collects the document headings."""
        self.toc_levels = sorted({level for level in levels if level in (1, 2, 3)})
        body = self.styles["body"]
        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle(
                f"TOCLevel{index}",
                parent=body,
                fontSize=size,
                leading=size * 1.35,
                leftIndent=14 * index,
                alignment=TA_LEFT,
                spaceAfter=2,
            )
            for index, size in enumerate((11, 10, 9))
        ]
        self.story.append(toc)
        return toc

    # ------------------------------------------------------------------
    # Canvas callbacks
    # ------------------------------------------------------------------

    def _draw_header_footer(self, canv: canvas.Canvas, doc) -> None:
        left_m, right_m, top_m, bottom_m = self.margins
        w, h = self.pagesize
        page_num = canv.getPageNumber()

        # Cover page: suppress header/footer on page 1 (cover draws itself)
        if self.cover_page and page_num == 1:
            return

        if self.watermark_text:
            canv.saveState()
            canv.setFont("Helvetica-Bold", 48)
            canv.setFillColor(colors.HexColor("#e2e8f0"))
            canv.translate(w / 2, h / 2)
            canv.rotate(45)
            canv.drawCentredString(0, 0, self.watermark_text)
            canv.restoreState()

        def draw_band(cfg: HeaderFooterConfig, y: float, is_header: bool) -> None:
            if not cfg.show_on_first_page and page_num == 1:
                return
            if not (cfg.left or cfg.center or cfg.right):
                return
            body_font = self.styles.get("_theme", {}).get("body_font", "Helvetica")
            try:
                canv.setFillColor(parse_color(cfg.color))
            except Exception:
                canv.setFillColor(colors.grey)
            if cfg.left:
                left, _ = self.canvas_text(cfg.left, body_font)
                self.draw_text(canv, left, left_m * cm, y, cfg.font_size, body_font)
            if cfg.center:
                center, _ = self.canvas_text(cfg.center, body_font)
                self.draw_text(
                    canv,
                    center,
                    w / 2,
                    y,
                    cfg.font_size,
                    body_font,
                    align="center",
                    width=w,
                )
            if cfg.right:
                right, _ = self.canvas_text(cfg.right, body_font)
                self.draw_text(
                    canv,
                    right,
                    w - right_m * cm,
                    y,
                    cfg.font_size,
                    body_font,
                    align="right",
                    width=right_m * cm,
                )
            if cfg.line_below and is_header:
                canv.saveState()
                canv.setStrokeColor(colors.HexColor("#e2e8f0"))
                canv.line(left_m * cm, y - 4, w - right_m * cm, y - 4)
                canv.restoreState()

        draw_band(self.header, h - top_m * cm + 6, is_header=True)
        footer_y = bottom_m * cm - 6
        draw_band(self.footer, footer_y, is_header=False)

        if self.page_numbers:
            canv.setFont("Helvetica", 8)
            canv.setFillColor(colors.grey)
            if self.page_number_format == "page_of_total" and self.total_pages:
                label = f"Page {page_num} of {self.total_pages}"
            else:
                label = f"Page {page_num}"
            canv.drawCentredString(w / 2, footer_y - 12, label)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> Path:
        missing = [t for t in dict.fromkeys(self.link_targets) if t not in self.anchors]
        if missing:
            raise ValueError(
                f"Link target(s) not found: {missing}. "
                "Create them with pdf_add_anchor(doc_id, 'name')."
            )
        if not self.story:
            raise ValueError(
                "The document has no content. Add at least one content tool "
                "before saving."
            )
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = self._make_doc_template()
        self._run_build(doc)
        if self.page_number_format == "page_of_total":
            self.total_pages = doc.page
            doc = self._make_doc_template()
            self._run_build(doc)
        return self.output_path

    def _make_doc_template(self) -> BaseDocTemplate:
        left, right, top, bottom = self.margins
        frame = Frame(
            left * cm,
            bottom * cm,
            self.pagesize[0] - (left + right) * cm,
            self.pagesize[1] - (top + bottom) * cm,
            id="main",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        def on_page(canv, doc):
            self._draw_header_footer(canv, doc)

        doc = _DocTemplate(
            self,
            str(self.output_path),
            pagesize=self.pagesize,
            title=self.metadata.get("title", ""),
            author=self.metadata.get("author", ""),
            subject=self.metadata.get("subject", ""),
            keywords=self.metadata.get("keywords", ""),
            creator=self.metadata.get("creator", ""),
            lang=self.metadata.get("language", ""),
            leftMargin=left * cm,
            rightMargin=right * cm,
            topMargin=top * cm,
            bottomMargin=bottom * cm,
        )
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
        return doc

    def _run_build(self, doc: BaseDocTemplate) -> None:
        # ReportLab flags a flowable it had to defer. The story is reused when
        # the document is built twice, so the stale flag has to go.
        for flowable in self.story:
            if hasattr(flowable, "_postponed"):
                delattr(flowable, "_postponed")
        if self.toc_levels:
            doc.multiBuild(self.story)
        else:
            doc.build(self.story)

    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "output_path": str(self.output_path),
            "page_size": self.page_size_name,
            "theme": self.theme_name,
            "elements": len(self._element_log),
            "element_log": self._element_log,
            "replay_log": self._replay_log,
            "signatures": [{"label": s.label, "name": s.name} for s in self.signatures],
            "metadata": self.metadata,
            "header": self.header.as_dict(),
            "footer": self.footer.as_dict(),
            "watermark": self.watermark_text,
            "page_numbers": self.page_numbers,
            "page_number_format": self.page_number_format,
            "total_pages": self.total_pages,
            "table_of_contents": bool(self.toc_levels),
            "has_cover": self.cover_page is not None,
        }


# ---------------------------------------------------------------------------


def get_session(doc_id: str) -> PDFSession:
    if doc_id not in _REGISTRY:
        raise KeyError(
            f"No active document '{doc_id}'. Call pdf_create_document first."
        )
    return _REGISTRY[doc_id]


def list_sessions() -> list[dict[str, str]]:
    return [
        {"doc_id": s.doc_id, "output_path": str(s.output_path)}
        for s in _REGISTRY.values()
    ]


def close_session(doc_id: str) -> None:
    _REGISTRY.pop(doc_id, None)
