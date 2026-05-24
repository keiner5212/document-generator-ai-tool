"""PDF document session — holds mutable state while an AI agent builds a PDF."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.platypus.flowables import Flowable

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
    page_hint: int | None = None


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
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.label = label
        self.name = name
        self.border_color = border_color or colors.HexColor("#cbd5e1")
        self.fill_color = fill_color or colors.HexColor("#f8fafc")

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.border_color)
        c.setFillColor(self.fill_color)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica", 8)
        c.drawString(6, self.height - 14, self.label)
        if self.name:
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            c.drawString(6, 8, self.name)
        c.setDash(2, 2)
        c.line(6, 22, self.width - 6, 22)
        c.setDash()


class CoverPageFlowable(Flowable):
    """
    Full-bleed cover page drawn at canvas level.

    Fills the frame area but draws outside it by translating to page origin.
    ReportLab automatically starts a new page for subsequent flowables.
    """

    def __init__(self, session: "PDFSession", cover: dict):
        super().__init__()
        self._s = session
        self._c = cover
        self.width = session.content_width()
        self.height = session.content_height()

    def draw(self):  # noqa: C901
        canv = self.canv
        s = self._s
        c = self._c
        pw, ph = s.pagesize
        left_m, right_m, top_m, bot_m = s.margins

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
        if logo_path and Path(logo_path).exists():
            logo_h = 2.2 * cm
            logo_x = (pw - logo_h) / 2
            logo_y = ph * 0.78
            try:
                canv.drawImage(
                    logo_path, logo_x, logo_y, logo_h, logo_h,
                    preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                pass

        # --- Title ---
        title = c.get("title", "")
        title_color = parse_color(c.get("title_color", "#ffffff"))
        title_sz = float(c.get("title_font_size", 38))
        heading_font = s.styles.get("_theme", {}).get("heading_font", "Helvetica-Bold")

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
            canv.drawCentredString(pw / 2, title_y - i * (title_sz * 1.25), line)

        # --- Subtitle ---
        subtitle = c.get("subtitle", "")
        if subtitle:
            sub_sz = float(c.get("subtitle_font_size", 15))
            sub_y = title_y - len(lines) * title_sz * 1.25 - 14
            body_font = s.styles.get("_theme", {}).get("body_font", "Helvetica")
            canv.setFont(body_font, sub_sz)
            canv.setFillColor(parse_color(c.get("subtitle_color", "#a0aec0")))
            canv.drawCentredString(pw / 2, sub_y, subtitle)

        # --- Author / date (bottom meta strip) ---
        author = c.get("author", "")
        date = c.get("date", "")
        meta = " · ".join(filter(None, [author, date]))
        if meta:
            canv.setFont("Helvetica", 10)
            canv.setFillColor(parse_color(c.get("meta_color", "#94a3b8")))
            canv.drawCentredString(pw / 2, ph * 0.1, meta)

        canv.restoreState()


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
            deco = "◆  "
            dw = canv.stringWidth(deco, fn, fs)
            total = tw + dw * 2
            x0 = (w - total) / 2
            canv.setFillColor(ac)
            canv.drawString(x0, mid - fs * 0.32, deco)
            canv.setFillColor(pc)
            canv.drawString(x0 + dw, mid - fs * 0.32, self.title)
            canv.setFillColor(ac)
            canv.drawString(x0 + dw + tw, mid - fs * 0.32, "  ◆")

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
            canv.setFont("Helvetica", self.fs - 1)
            canv.setFillColor(self.cap_color)
            cap_y = self.height - p + 2
            canv.drawString(p, cap_y, self.caption)

        canv.setFont("Courier", self.fs)
        canv.setFillColor(self.tc)
        lines = self.code.split("\n")
        y = self.height - p - line_h
        if self.caption:
            y -= self.fs * 1.6
        for line in lines:
            canv.drawString(p, y, line)
            y -= line_h


# ===========================================================================
# Session
# ===========================================================================

class PDFSession:
    """Mutable PDF build session."""

    def __init__(
        self,
        output_path: str | Path,
        page_size: str = "A4",
        margins_cm: tuple[float, float, float, float] = (2.5, 2.5, 2.5, 2.5),
        theme: str = "default",
    ):
        self.doc_id = str(uuid.uuid4())[:8]
        self.output_path = Path(output_path)
        self.page_size_name = page_size.upper().replace("-", "_")
        self.pagesize = PAGE_SIZES.get(self.page_size_name, A4)
        self.margins = margins_cm  # (left, right, top, bottom) in cm
        self.theme_name = theme
        self.styles = build_styles(theme)
        self.story: list = []
        self.header = HeaderFooterConfig()
        self.footer = HeaderFooterConfig()
        self.metadata: dict[str, str] = {}
        self.signatures: list[SignaturePlaceholder] = []
        self.watermark_text: str | None = None
        self.page_numbers: bool = False
        self.cover_page: dict | None = None  # set by pdf_add_cover_page
        self._element_log: list[dict[str, Any]] = []
        self._replay_log: list[dict[str, Any]] = []
        _REGISTRY[self.doc_id] = self

    # ------------------------------------------------------------------

    def log_element(self, kind: str, replay_kwargs: dict | None = None, **details: Any) -> None:
        self._element_log.append({"kind": kind, **details})
        if replay_kwargs is not None:
            self._replay_log.append({"kind": kind, "kwargs": replay_kwargs})

    def content_width(self) -> float:
        left, right, _, _ = self.margins
        return self.pagesize[0] - (left + right) * cm

    def content_height(self) -> float:
        _, _, top, bottom = self.margins
        return self.pagesize[1] - (top + bottom) * cm

    def apply_palette(self, palette: dict) -> None:
        self.styles = build_styles_from_palette(palette)
        self.theme_name = palette.get("name", "custom")

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
            canv.setFont("Helvetica", cfg.font_size)
            try:
                canv.setFillColor(parse_color(cfg.color))
            except Exception:
                canv.setFillColor(colors.grey)
            if cfg.left:
                canv.drawString(left_m * cm, y, cfg.left)
            if cfg.center:
                canv.drawCentredString(w / 2, y, cfg.center)
            if cfg.right:
                canv.drawRightString(w - right_m * cm, y, cfg.right)
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
            canv.drawCentredString(w / 2, footer_y - 12, f"Page {page_num}")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        left, right, top, bottom = self.margins
        frame = Frame(
            left * cm, bottom * cm,
            self.pagesize[0] - (left + right) * cm,
            self.pagesize[1] - (top + bottom) * cm,
            id="main",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )

        def on_page(canv, doc):
            self._draw_header_footer(canv, doc)

        doc = BaseDocTemplate(
            str(self.output_path),
            pagesize=self.pagesize,
            title=self.metadata.get("title", ""),
            author=self.metadata.get("author", ""),
            subject=self.metadata.get("subject", ""),
            leftMargin=left * cm,
            rightMargin=right * cm,
            topMargin=top * cm,
            bottomMargin=bottom * cm,
        )
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
        doc.build(self.story)
        return self.output_path

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
            "signatures": [
                {"label": s.label, "name": s.name, "page_hint": s.page_hint}
                for s in self.signatures
            ],
            "metadata": self.metadata,
            "header": self.header.as_dict(),
            "footer": self.footer.as_dict(),
            "watermark": self.watermark_text,
            "page_numbers": self.page_numbers,
            "has_cover": self.cover_page is not None,
        }


# ---------------------------------------------------------------------------

def get_session(doc_id: str) -> PDFSession:
    if doc_id not in _REGISTRY:
        raise KeyError(f"No active document '{doc_id}'. Call pdf_create_document first.")
    return _REGISTRY[doc_id]


def list_sessions() -> list[dict[str, str]]:
    return [{"doc_id": s.doc_id, "output_path": str(s.output_path)} for s in _REGISTRY.values()]


def close_session(doc_id: str) -> None:
    _REGISTRY.pop(doc_id, None)
