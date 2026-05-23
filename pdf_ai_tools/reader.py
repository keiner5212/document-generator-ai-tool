"""Read and inspect existing PDF files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def read_pdf_info(path: str | Path) -> dict[str, Any]:
    """Extract metadata, page count, and outline from a PDF."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    meta = reader.metadata
    info: dict[str, Any] = {
        "path": str(path.resolve()),
        "page_count": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "metadata": {},
    }
    if meta:
        for key in ("/Title", "/Author", "/Subject", "/Creator", "/Producer", "/CreationDate"):
            val = meta.get(key)
            if val:
                info["metadata"][key.lstrip("/")] = str(val)

    outline = []
    if reader.outline:
        def walk(items, depth=0):
            for item in items:
                if isinstance(item, list):
                    walk(item, depth + 1)
                else:
                    outline.append({"title": item.title, "depth": depth})
        walk(reader.outline)
    info["outline"] = outline
    return info


def read_pdf_text(
    path: str | Path,
    page_numbers: list[int] | None = None,
    max_chars: int = 50000,
) -> dict[str, Any]:
    """Extract text from PDF pages (1-based page numbers)."""
    path = Path(path)
    reader = PdfReader(str(path))
    total = len(reader.pages)

    if page_numbers:
        indices = [p - 1 for p in page_numbers if 1 <= p <= total]
    else:
        indices = range(total)

    pages_out = []
    total_chars = 0
    for i in indices:
        text = reader.pages[i].extract_text() or ""
        if total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            text = text[:remaining] + "\n...[truncated]"
            pages_out.append({"page": i + 1, "text": text, "truncated": True})
            break
        pages_out.append({"page": i + 1, "text": text, "truncated": False})
        total_chars += len(text)

    return {
        "path": str(path.resolve()),
        "page_count": total,
        "pages": pages_out,
        "total_chars": total_chars,
    }


def read_pdf_page_dimensions(path: str | Path) -> dict[str, Any]:
    """Return media box dimensions per page."""
    path = Path(path)
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        box = page.mediabox
        pages.append({
            "page": i + 1,
            "width_pt": float(box.width),
            "height_pt": float(box.height),
        })
    return {"path": str(path.resolve()), "pages": pages}
