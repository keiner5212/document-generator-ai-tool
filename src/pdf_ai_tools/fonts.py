"""
Host font discovery, registration and character coverage.

The built-in ReportLab fonts (Helvetica, Times, Courier) only cover WinAnsi,
so any other script needs a font file from the machine. This module finds
those files, reads their family and style without a full font parser, and
answers two questions the tools need:

  - which fonts are installed on this machine
  - which of them can draw a given set of characters

Fonts are read straight from the file, so nothing is copied or bundled.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import unicode2T1
from reportlab.pdfbase.ttfonts import TTFont

FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
ENV_FONT_DIRS = "PDF_AI_TOOLS_FONT_DIRS"

# Families preferred when several fonts cover the same characters. The
# generic ones come first, the script specific ones after, so Arabic text
# lands on an Arabic face and Japanese text on a CJK face.
PREFERRED_FAMILIES = (
    "noto sans",
    "noto serif",
    "noto sans mono",
    "noto sans cjk",
    "noto serif cjk",
    "noto sans arabic",
    "noto naskh arabic",
    "noto sans hebrew",
    "noto sans devanagari",
    "noto sans thai",
    "noto sans kr",
    "noto sans tc",
    "source han",
    "droid sans fallback",
    "unifont",
    "amiri",
    "dejavu sans",
    "dejavu serif",
    "dejavu sans mono",
    "liberation sans",
    "liberation serif",
    "liberation mono",
    "freesans",
    "freeserif",
    "free mono",
    "lato",
    "ubuntu",
    "roboto",
    "open sans",
    "source sans pro",
    "arial",
    "times new roman",
    "courier new",
)


def font_directories(extra: str = "") -> list[Path]:
    """Directories to look for font files in."""
    dirs: list[Path] = []
    if extra:
        dirs.extend(Path(p).expanduser() for p in extra.split(os.pathsep) if p)
    env = os.environ.get(ENV_FONT_DIRS, "")
    if env:
        dirs.extend(Path(p).expanduser() for p in env.split(os.pathsep) if p)
    home = Path.home()
    candidates = [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path("/opt/homebrew/share/fonts"),
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        home / ".fonts",
        home / ".local/share/fonts",
        home / "Library/Fonts",
        Path("C:/Windows/Fonts"),
    ]
    dirs.extend(candidates)
    seen: set[str] = set()
    unique: list[Path] = []
    for d in dirs:
        key = str(d)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


# ---------------------------------------------------------------------------
# Minimal sfnt reader: name table and cmap
# ---------------------------------------------------------------------------


class SfntFile:
    """Lazy reader for the name and cmap tables of a font file."""

    def __init__(self, path: Path, index: int = 0) -> None:
        self.path = path
        self.index = index
        self._tables: dict[bytes, tuple[int, int]] | None = None
        self._names: dict[int, str] | None = None
        self._cmap: dict[int, int] | None = None
        self._cmap_formats: list[tuple[int, int]] = []

    def _load_tables(self) -> dict[bytes, tuple[int, int]]:
        if self._tables is not None:
            return self._tables
        tables: dict[bytes, tuple[int, int]] = {}
        try:
            with self.path.open("rb") as fh:
                head = fh.read(12)
                if len(head) < 12:
                    self._tables = tables
                    return tables
                tag = head[:4]
                if tag == b"ttcf":
                    count = struct.unpack(">I", fh.read(4))[0]
                    if not count:
                        self._tables = tables
                        return tables
                    offsets = struct.unpack(f">{count}I", fh.read(4 * count))
                    if self.index >= len(offsets):
                        self._tables = tables
                        return tables
                    fh.seek(offsets[self.index])
                    header = fh.read(12)
                else:
                    header = head
                num_tables = struct.unpack(">H", header[4:6])[0]
                directory = fh.read(16 * num_tables)
                for i in range(num_tables):
                    entry = directory[i * 16 : (i + 1) * 16]
                    if len(entry) < 16:
                        break
                    name, _checksum, offset, length = struct.unpack(">4sIII", entry)
                    tables[name] = (offset, length)
        except (OSError, struct.error, ValueError):
            pass
        self._tables = tables
        return tables

    def _table_bytes(self, tag: bytes) -> bytes:
        entry = self._load_tables().get(tag)
        if entry is None:
            return b""
        offset, length = entry
        try:
            with self.path.open("rb") as fh:
                fh.seek(offset)
                return fh.read(length)
        except OSError:
            return b""

    # -- names ------------------------------------------------------------

    def _load_names(self) -> dict[int, str]:
        if self._names is not None:
            return self._names
        names: dict[int, str] = {}
        data = self._table_bytes(b"name")
        if len(data) >= 6:
            count, string_offset = struct.unpack(">HH", data[2:6])
            for i in range(count):
                start = 6 + i * 12
                record = data[start : start + 12]
                if len(record) < 12:
                    break
                platform, _encoding, _lang, name_id, length, offset = struct.unpack(
                    ">HHHHHH", record
                )
                raw = data[string_offset + offset : string_offset + offset + length]
                if not raw:
                    continue
                if platform == 1:
                    text = raw.decode("mac_roman", "replace")
                else:
                    text = raw.decode("utf-16-be", "replace")
                text = text.replace("\x00", "").strip()
                if not text:
                    continue
                if name_id not in names or platform == 3:
                    names[name_id] = text
        self._names = names
        return names

    @property
    def family(self) -> str:
        names = self._load_names()
        return names.get(16) or names.get(1) or self.path.stem

    @property
    def style(self) -> str:
        names = self._load_names()
        return names.get(17) or names.get(2) or "Regular"

    @property
    def has_glyph_outlines(self) -> bool:
        """True for TrueType outlines. PostScript outlines cannot be embedded."""
        return b"glyf" in self._load_tables()

    # -- cmap -------------------------------------------------------------

    def _load_cmap(self) -> None:
        if self._cmap is not None:
            return
        table: dict[int, int] = {}
        formats: list[tuple[int, int]] = []
        data = self._table_bytes(b"cmap")
        if len(data) >= 4:
            count = struct.unpack(">H", data[2:4])[0]
            for i in range(count):
                start = 4 + i * 8
                record = data[start : start + 8]
                if len(record) < 8:
                    break
                platform, encoding, offset = struct.unpack(">HHI", record)
                if offset >= len(data):
                    continue
                fmt = struct.unpack(">H", data[offset : offset + 2])[0]
                formats.append((platform, encoding))
                if fmt == 12:
                    table.update(self._parse_format12(data, offset))
                elif fmt == 4:
                    table.update(self._parse_format4(data, offset))
                elif fmt == 6:
                    table.update(self._parse_format6(data, offset))
        self._cmap = table
        self._cmap_formats = formats

    @staticmethod
    def _parse_format12(data: bytes, offset: int) -> dict[int, int]:
        result: dict[int, int] = {}
        if len(data) < offset + 16:
            return result
        groups = struct.unpack(">I", data[offset + 12 : offset + 16])[0]
        pos = offset + 16
        for _ in range(min(groups, 20000)):
            if pos + 12 > len(data):
                break
            start, end, first_glyph = struct.unpack(">III", data[pos : pos + 12])
            pos += 12
            if end - start > 0x10000:
                end = start + 0x10000
            for cp in range(start, end + 1):
                result[cp] = first_glyph + (cp - start)
        return result

    @staticmethod
    def _parse_format6(data: bytes, offset: int) -> dict[int, int]:
        result: dict[int, int] = {}
        if len(data) < offset + 10:
            return result
        first, count = struct.unpack(">HH", data[offset + 6 : offset + 10])
        for i in range(count):
            pos = offset + 10 + i * 2
            if pos + 2 > len(data):
                break
            glyph = struct.unpack(">H", data[pos : pos + 2])[0]
            result[first + i] = glyph
        return result

    @staticmethod
    def _parse_format4(data: bytes, offset: int) -> dict[int, int]:
        result: dict[int, int] = {}
        if len(data) < offset + 14:
            return result
        seg_x2 = struct.unpack(">H", data[offset + 6 : offset + 8])[0]
        segs = seg_x2 // 2
        ends = offset + 14
        starts = ends + seg_x2 + 2
        deltas = starts + seg_x2
        ranges = deltas + seg_x2
        for i in range(segs):
            end = struct.unpack(">H", data[ends + i * 2 : ends + i * 2 + 2])[0]
            start = struct.unpack(">H", data[starts + i * 2 : starts + i * 2 + 2])[0]
            if start > end or end == 0xFFFF and start == 0xFFFF:
                continue
            delta = struct.unpack(">h", data[deltas + i * 2 : deltas + i * 2 + 2])[0]
            range_offset = struct.unpack(
                ">H", data[ranges + i * 2 : ranges + i * 2 + 2]
            )[0]
            for cp in range(start, min(end, 0xFFFE) + 1):
                if range_offset == 0:
                    glyph = (cp + delta) & 0xFFFF
                else:
                    pos = ranges + i * 2 + range_offset + (cp - start) * 2
                    if pos + 2 > len(data):
                        continue
                    glyph = struct.unpack(">H", data[pos : pos + 2])[0]
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                if glyph:
                    result[cp] = glyph
        return result

    def covers(self, chars: set[int]) -> bool:
        """True when the font has a glyph for every character."""
        if not chars:
            return True
        self._load_cmap()
        table = self._cmap or {}
        return all(cp in table for cp in chars)


# ---------------------------------------------------------------------------
# Font files on this machine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FontFile:
    path: Path
    family: str
    style: str
    format: str
    subfont: int = 0
    embeddable: bool = True

    def as_dict(self) -> dict[str, str | int | bool]:
        return {
            "family": self.family,
            "style": self.style,
            "path": str(self.path),
            "format": self.format,
            "subfont": self.subfont,
            "embeddable": self.embeddable,
        }


_scan_cache: dict[str, list[FontFile]] = {}
_sfnt_cache: dict[str, SfntFile] = {}


def _sfnt(path: Path, index: int = 0) -> SfntFile:
    key = f"{path}#{index}"
    if key not in _sfnt_cache:
        _sfnt_cache[key] = SfntFile(path, index)
    return _sfnt_cache[key]


def subfont_count(path: Path) -> int:
    """How many fonts a collection file holds. 1 for a plain font file."""
    try:
        with path.open("rb") as fh:
            head = fh.read(12)
            if len(head) < 12 or head[:4] != b"ttcf":
                return 1
            fh.read(4)
            count = struct.unpack(">I", fh.read(4))[0]
            return max(1, min(count, 64))
    except (OSError, struct.error, ValueError):
        return 1


def scan_fonts(directory: str = "") -> list[FontFile]:
    """Every font file installed on this machine."""
    roots = font_directories(directory)
    key = "|".join(str(r) for r in roots)
    if key in _scan_cache:
        return _scan_cache[key]

    found: list[FontFile] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            paths = sorted(
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in FONT_SUFFIXES
            )
        except OSError:
            continue
        for path in paths:
            resolved = str(path)
            if resolved in seen:
                continue
            seen.add(resolved)
            for index in range(subfont_count(path)):
                sfnt = _sfnt(path, index)
                family = sfnt.family
                if not family:
                    continue
                found.append(
                    FontFile(
                        path=path,
                        family=family,
                        style=sfnt.style,
                        format=path.suffix.lower().lstrip("."),
                        subfont=index,
                        embeddable=sfnt.has_glyph_outlines,
                    )
                )
    _scan_cache[key] = found
    return found


def list_fonts(query: str = "", directory: str = "") -> list[dict[str, str]]:
    """Installed fonts, optionally filtered by family, style or path."""
    needle = query.strip().lower()
    rows = []
    for font in scan_fonts(directory):
        if (
            needle
            and needle not in font.family.lower()
            and needle not in font.style.lower()
            and needle not in str(font.path).lower()
        ):
            continue
        rows.append(font.as_dict())
    return rows


def fonts_covering(text: str, directory: str = "") -> list[dict[str, str]]:
    """Installed fonts that can draw every character of the text."""
    chars = {ord(c) for c in text if c not in "\n\r\t"}
    if not chars:
        return []
    rows = []
    for font in scan_fonts(directory):
        if font.embeddable and _sfnt(font.path, font.subfont).covers(chars):
            rows.append(font.as_dict())
    return rows


def find_font_for(chars: set[int], directory: str = "") -> FontFile | None:
    """The best installed font that can draw every character."""
    if not chars:
        return None
    available = [f for f in scan_fonts(directory) if f.embeddable]
    for preference in PREFERRED_FAMILIES:
        group = [
            f
            for f in available
            if f.family.lower().startswith(preference)
            and _sfnt(f.path, f.subfont).covers(chars)
        ]
        if group:
            return min(group, key=_font_rank)
    for font in available:
        if _sfnt(font.path, font.subfont).covers(chars):
            return font
    return None


def _font_rank(font: FontFile) -> tuple:
    family = font.family.lower()
    preference = len(PREFERRED_FAMILIES)
    for index, name in enumerate(PREFERRED_FAMILIES):
        if family.startswith(name):
            preference = index
            break
    regular = 0 if font.style.lower() in ("regular", "book", "roman", "") else 1
    try:
        size = font.path.stat().st_size
    except OSError:
        size = 0
    return (preference, regular, size, font.family.lower())


def find_family(family: str, style: str = "", directory: str = "") -> FontFile | None:
    """A font file by family name, or by family and style."""
    needle = family.strip().lower()
    style_needle = style.strip().lower()
    matches = [
        f
        for f in scan_fonts(directory)
        if f.family.lower() == needle or needle in f.family.lower()
    ]
    if not matches:
        return None
    exact = [f for f in matches if f.family.lower() == needle]
    pool = exact or matches
    if style_needle:
        for f in pool:
            if f.style.lower() == style_needle:
                return f
    usable = [f for f in pool if f.embeddable]
    pool = usable or pool
    regular = [f for f in pool if f.style.lower() in ("regular", "book", "roman", "")]
    return min(regular or pool, key=_font_rank)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_registered: dict[str, str] = {}
_register_counter = 0


def _safe_name(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text)[:40] or "Font"


def register_font(path: str | Path, name: str = "", subfont: int = 0) -> str:
    """Register a font file with ReportLab and return the registered name."""
    global _register_counter
    file_path = Path(path).expanduser()
    key = f"{file_path}#{subfont}"
    if not name and key in _registered:
        return _registered[key]
    if not file_path.is_file():
        raise FileNotFoundError(f"Font file not found: {file_path}")
    _register_counter += 1
    registered = name or f"{_safe_name(file_path.stem)}_{_register_counter}"
    font = TTFont(registered, str(file_path), subfontIndex=subfont)
    pdfmetrics.registerFont(font)
    if not name:
        _registered[key] = registered
    return registered


def register_family(path: str | Path, directory: str = "") -> dict[str, str]:
    """
    Register a font file and its bold, italic and bold-italic siblings.

    Returns the registered names by role.
    """
    file_path = Path(path).expanduser()
    family = _sfnt(file_path).family
    roles = {"regular": register_font(file_path)}
    siblings = [
        f
        for f in scan_fonts(directory)
        if f.family.lower() == family.lower() and f.path != file_path
    ]
    for sibling in siblings:
        style = sibling.style.lower()
        if "bold italic" in style or "italic bold" in style:
            roles.setdefault(
                "bold_italic", register_font(sibling.path, subfont=sibling.subfont)
            )
        elif "bold" in style:
            roles.setdefault(
                "bold", register_font(sibling.path, subfont=sibling.subfont)
            )
        elif "italic" in style or "oblique" in style:
            roles.setdefault(
                "italic", register_font(sibling.path, subfont=sibling.subfont)
            )
    return roles


# ---------------------------------------------------------------------------
# Coverage of a font that is already in use
# ---------------------------------------------------------------------------

_standard_coverage_cache: dict[str, set[int]] = {}


def standard_coverage(font_name: str) -> set[int]:
    """Characters the built-in Type 1 fonts can draw."""
    if font_name in _standard_coverage_cache:
        return _standard_coverage_cache[font_name]
    try:
        font = pdfmetrics.getFont(font_name)
    except Exception:
        return set()
    covered: set[int] = set()
    for cp in range(0x10000):
        char = chr(cp)
        if char in "\n\r\t":
            continue
        try:
            result = unicode2T1(char, [font])
        except (KeyError, ValueError, TypeError):
            continue
        if not result:
            continue
        mapped_font, byte = result[0]
        if isinstance(byte, bytes):
            byte = byte[0]
        if mapped_font is font:
            if 0x20 <= byte <= 0xFF and byte != 0x7F:
                covered.add(cp)
        elif 0x80 <= cp <= 0x9F:
            # ReportLab draws these with the Symbol font.
            covered.add(cp)
    _standard_coverage_cache[font_name] = covered
    return covered


def coverage(font_name: str) -> set[int]:
    """Characters a registered font can draw."""
    try:
        font = pdfmetrics.getFont(font_name)
    except Exception:
        return set()
    face = getattr(font, "face", None)
    chars = getattr(face, "charToGlyph", None)
    if chars:
        return set(chars)
    return standard_coverage(font_name)


def missing_characters(text: str, font_name: str) -> set[int]:
    """Characters in the text that the font cannot draw."""
    supported = coverage(font_name)
    return {ord(c) for c in text if c not in "\n\r\t" and ord(c) not in supported}


STANDARD_FONTS = {
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
    "Symbol",
    "ZapfDingbats",
}


_fallback_cache: dict[int, str] = {}
_font_for_chars_cache: dict[frozenset[int], str] = {}


def font_for_chars(chars: frozenset[int]) -> str | None:
    """A registered font that can draw every character of the set."""
    if not chars:
        return None
    if chars in _font_for_chars_cache:
        return _font_for_chars_cache[chars]
    font = find_font_for(set(chars))
    if font is None:
        return None
    name = register_font(font.path, subfont=font.subfont)
    _font_for_chars_cache[chars] = name
    return name


def split_by_coverage(text: str, missing: set[int]) -> list[tuple[bool, str]]:
    """Split the text into runs of missing characters and runs of the rest."""
    segments: list[tuple[bool, str]] = []
    current = ""
    current_missing = False
    for char in text:
        is_missing = ord(char) in missing
        if current and is_missing != current_missing:
            segments.append((current_missing, current))
            current = ""
        current_missing = is_missing
        current += char
    if current:
        segments.append((current_missing, current))
    return segments


def fallback_font(char: str) -> str | None:
    """A registered font that can draw the character."""
    code = ord(char)
    if code in _fallback_cache:
        return _fallback_cache[code]
    font = find_font_for({code})
    if font is None:
        return None
    name = register_font(font.path, subfont=font.subfont)
    _fallback_cache[code] = name
    return name


def is_registered(font_name: str) -> bool:
    """True for the built-in fonts and for fonts already registered."""
    if font_name in STANDARD_FONTS:
        return True
    try:
        return font_name in pdfmetrics.getRegisteredFontNames()
    except Exception:
        return False


def bullet_marker(font_name: str) -> str:
    """A bullet character the font can actually draw."""
    supported = coverage(font_name)
    for candidate in (0x2022, 0x0095, 0x25AA, 0x00B7):
        if candidate in supported:
            return chr(candidate)
    return "\u2022"


def is_shapable(font_name: str) -> bool:
    """True when the font can shape complex scripts."""
    try:
        return bool(pdfmetrics.getFont(font_name).shapable)
    except Exception:
        return False
