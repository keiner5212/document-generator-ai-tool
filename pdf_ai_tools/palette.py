"""Color palette management — load, save, list, and apply palette JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Built-in palettes live next to this package; user palettes can go anywhere.
_BUILTIN_DIR = Path(__file__).resolve().parent.parent / "palettes"


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _default_palette(name: str = "custom") -> dict:
    return {
        "name": name,
        "description": "",
        "colors": {
            "primary": "#1a365d",
            "secondary": "#2c5282",
            "accent": "#3182ce",
            "muted": "#718096",
            "border": "#e2e8f0",
            "background": "#f7fafc",
        },
        "fonts": {
            "body": "Helvetica",
            "heading": "Helvetica-Bold",
        },
        "sizes": {
            "body": 11,
            "h1": 22,
            "h2": 16,
            "h3": 13,
            "caption": 9,
        },
        "document": {
            "page_size": "A4",
            "margins_cm": [2.5, 2.5, 2.5, 2.5],
            "page_numbers": False,
            "watermark": None,
        },
    }


def _validate(data: dict) -> None:
    required_colors = {"primary", "secondary", "accent", "muted", "border", "background"}
    missing = required_colors - set(data.get("colors", {}).keys())
    if missing:
        raise ValueError(f"Palette missing color keys: {missing}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_palette(path: str) -> dict:
    """Load a palette JSON file from an absolute or relative path."""
    p = Path(path)
    if not p.is_absolute():
        # Check built-in dir first
        candidate = _BUILTIN_DIR / path
        if candidate.exists():
            p = candidate
    if not p.exists():
        raise FileNotFoundError(f"Palette not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    _validate(data)
    return data


def load_builtin_palette(name: str) -> dict:
    """Load a built-in palette by name (without .json extension)."""
    p = _BUILTIN_DIR / f"{name}.json"
    if not p.exists():
        available = list_builtin_palettes()
        raise FileNotFoundError(
            f"Built-in palette '{name}' not found. Available: {available}"
        )
    return load_palette(str(p))


def save_palette(palette: dict, path: str) -> Path:
    """Save a palette dict to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(palette, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def list_builtin_palettes() -> list[dict[str, str]]:
    """Return name + description for every palette in the built-in directory."""
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
            })
        except Exception:
            pass
    return result


def list_palettes_in_dir(directory: str) -> list[dict[str, str]]:
    """Return palette summaries from any directory."""
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
            })
        except Exception:
            pass
    return result


def palette_from_session(session) -> dict:
    """Snapshot a session's current styling into a palette dict."""
    # Reverse-engineer the colors from the stored _theme dict
    theme = session.styles.get("_theme", {})

    def hex_or_str(obj) -> str:
        try:
            return f"#{int(obj.red * 255):02x}{int(obj.green * 255):02x}{int(obj.blue * 255):02x}"
        except Exception:
            return "#000000"

    body_style = session.styles.get("body")
    h1_style = session.styles.get("h1")
    h2_style = session.styles.get("h2")
    h3_style = session.styles.get("h3")
    cap_style = session.styles.get("caption")

    return {
        "name": session.theme_name,
        "description": f"Exported from document {session.doc_id}",
        "colors": {
            "primary": hex_or_str(theme.get("primary")),
            "secondary": hex_or_str(theme.get("secondary")),
            "accent": hex_or_str(theme.get("accent")),
            "muted": hex_or_str(theme.get("muted")),
            "border": hex_or_str(theme.get("border")),
            "background": hex_or_str(theme.get("background")),
        },
        "fonts": {
            "body": theme.get("body_font", "Helvetica"),
            "heading": theme.get("heading_font", "Helvetica-Bold"),
        },
        "sizes": {
            "body": getattr(body_style, "fontSize", 11),
            "h1": getattr(h1_style, "fontSize", 22),
            "h2": getattr(h2_style, "fontSize", 16),
            "h3": getattr(h3_style, "fontSize", 13),
            "caption": getattr(cap_style, "fontSize", 9),
        },
        "document": {
            "page_size": session.page_size_name,
            "margins_cm": list(session.margins),
            "page_numbers": session.page_numbers,
            "watermark": session.watermark_text,
        },
    }
