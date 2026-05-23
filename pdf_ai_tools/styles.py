"""Named style presets, palette helpers, and ReportLab style builders."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm

ALIGN_MAP = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
}

# Built-in named themes (kept for backward compat; palettes extend this idea)
THEMES = {
    "default": {
        "primary": "#1a365d",
        "secondary": "#2c5282",
        "accent": "#3182ce",
        "muted": "#718096",
        "border": "#e2e8f0",
        "background": "#f7fafc",
        "body_font": "Helvetica",
        "heading_font": "Helvetica-Bold",
        "sizes": {"body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9},
    },
    "corporate": {
        "primary": "#1e3a5f",
        "secondary": "#334155",
        "accent": "#0ea5e9",
        "muted": "#64748b",
        "border": "#cbd5e1",
        "background": "#f8fafc",
        "body_font": "Helvetica",
        "heading_font": "Helvetica-Bold",
        "sizes": {"body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9},
    },
    "minimal": {
        "primary": "#000000",
        "secondary": "#333333",
        "accent": "#555555",
        "muted": "#888888",
        "border": "#dddddd",
        "background": "#ffffff",
        "body_font": "Helvetica",
        "heading_font": "Helvetica-Bold",
        "sizes": {"body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9},
    },
    "elegant": {
        "primary": "#2d1b4e",
        "secondary": "#4a306d",
        "accent": "#9b59b6",
        "muted": "#7f8c8d",
        "border": "#d5c4e0",
        "background": "#faf8fc",
        "body_font": "Times-Roman",
        "heading_font": "Times-Bold",
        "sizes": {"body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9},
    },
}


def parse_color(value: str):
    """Parse hex (#RRGGBB / #RGB), named color, or 'r,g,b' float string."""
    value = value.strip()
    if value.startswith("#"):
        return colors.HexColor(value)
    if "," in value:
        parts = [float(x.strip()) for x in value.split(",")]
        if len(parts) == 3:
            return colors.Color(parts[0], parts[1], parts[2])
    named = getattr(colors, value.replace(" ", "_"), None)
    if named is not None:
        return named
    raise ValueError(f"Cannot parse color: {value!r}")


def _resolve(theme_dict: dict, key: str):
    """Return a ReportLab color from theme dict entry (hex string)."""
    return parse_color(theme_dict[key])


def _build_paragraph_styles(theme: dict) -> dict:
    """
    Build paragraph style dict from a normalized theme dict.

    theme keys required: primary, secondary, accent, muted, border,
    background, body_font, heading_font, sizes (dict with body/h1/h2/h3/caption).
    """
    base = getSampleStyleSheet()
    sz = theme.get("sizes", {})
    body_sz = sz.get("body", 11)
    h1_sz = sz.get("h1", 22)
    h2_sz = sz.get("h2", 16)
    h3_sz = sz.get("h3", 13)
    cap_sz = sz.get("caption", 9)

    styles = {
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=theme["body_font"],
            fontSize=body_sz,
            leading=body_sz * 1.4,
            textColor=_resolve(theme, "secondary"),
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=theme["heading_font"],
            fontSize=h1_sz,
            leading=h1_sz * 1.2,
            textColor=_resolve(theme, "primary"),
            spaceBefore=12,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=theme["heading_font"],
            fontSize=h2_sz,
            leading=h2_sz * 1.25,
            textColor=_resolve(theme, "primary"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=theme["heading_font"],
            fontSize=h3_sz,
            leading=h3_sz * 1.3,
            textColor=_resolve(theme, "accent"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName=theme["body_font"],
            fontSize=cap_sz,
            leading=cap_sz * 1.35,
            textColor=_resolve(theme, "muted"),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName=theme["body_font"],
            fontSize=cap_sz,
            leading=cap_sz * 1.35,
            textColor=_resolve(theme, "muted"),
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["Normal"],
            fontName=theme["body_font"],
            fontSize=body_sz - 1,
            leading=(body_sz - 1) * 1.4,
            textColor=_resolve(theme, "secondary"),
            leftIndent=cm,
            borderColor=_resolve(theme, "accent"),
            borderWidth=2,
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=6,
        ),
    }
    # Store resolved ReportLab color objects for reuse in table styles etc.
    styles["_theme"] = {
        "primary": _resolve(theme, "primary"),
        "secondary": _resolve(theme, "secondary"),
        "accent": _resolve(theme, "accent"),
        "muted": _resolve(theme, "muted"),
        "border": _resolve(theme, "border"),
        "background": _resolve(theme, "background"),
        "body_font": theme["body_font"],
        "heading_font": theme["heading_font"],
    }
    return styles


def build_styles(theme_name: str = "default") -> dict:
    """Build paragraph styles for a built-in named theme."""
    theme = THEMES.get(theme_name, THEMES["default"])
    return _build_paragraph_styles(theme)


def build_styles_from_palette(palette: dict) -> dict:
    """
    Build paragraph styles from a palette dict (as stored in palette JSON files).

    Palette format::

        {
            "colors": {"primary": "#...", "secondary": "#...", ...},
            "fonts":  {"body": "Helvetica", "heading": "Helvetica-Bold"},
            "sizes":  {"body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9},
        }
    """
    c = palette.get("colors", {})
    f = palette.get("fonts", {})
    theme = {
        "primary": c.get("primary", "#1a365d"),
        "secondary": c.get("secondary", "#2c5282"),
        "accent": c.get("accent", "#3182ce"),
        "muted": c.get("muted", "#718096"),
        "border": c.get("border", "#e2e8f0"),
        "background": c.get("background", "#f7fafc"),
        "body_font": f.get("body", "Helvetica"),
        "heading_font": f.get("heading", "Helvetica-Bold"),
        "sizes": palette.get("sizes", {}),
    }
    return _build_paragraph_styles(theme)
