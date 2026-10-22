"""
Right to left text handling.

ReportLab reorders right to left text when the optional `rlbidi` package is
installed, and it does that after shaping, which is the correct order. This
module is the fallback for the machines where `rlbidi` is missing: it puts the
text in visual order before the text reaches ReportLab. Shaping is then
skipped for that text, because shaping a string that is already in visual
order produces the wrong letter forms.
"""

from __future__ import annotations

_RTL_RANGES = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0700, 0x074F),  # Syriac
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0780, 0x07BF),  # Thaana
    (0x07C0, 0x08FF),  # Arabic Extended-A
    (0xFB1D, 0xFDFF),  # Hebrew and Arabic presentation forms
    (0xFE70, 0xFEFF),  # Arabic presentation forms-B
    (0x10800, 0x10FFF),  # Ancient RTL scripts
    (0x1E800, 0x1EFFF),  # Arabic math
)


def is_rtl_char(char: str) -> bool:
    code = ord(char)
    return any(low <= code <= high for low, high in _RTL_RANGES)


def has_rtl(text: str) -> bool:
    """True when the text contains right to left characters."""
    return any(is_rtl_char(char) for char in text)


def has_bidi_support() -> bool:
    """True when ReportLab can reorder right to left text itself."""
    try:
        import rlbidi  # noqa: F401
    except ImportError:
        return False
    return True


def _runs(text: str) -> list[tuple[bool, str]]:
    """Split the text into runs of right to left and other characters."""
    runs: list[tuple[bool, str]] = []
    for char in text:
        rtl = is_rtl_char(char)
        if runs and runs[-1][0] == rtl:
            runs[-1] = (rtl, runs[-1][1] + char)
        else:
            runs.append((rtl, char))
    return runs


def base_direction(text: str) -> str:
    """The direction of the paragraph, from its first strong character."""
    for char in text:
        if is_rtl_char(char):
            return "RTL"
        if char.isalpha():
            return "LTR"
    return "LTR"


def reorder_rtl(text: str) -> str:
    """
    Put right to left text in visual order.

    Every right to left run is reversed and, when the paragraph reads right to
    left, the runs are put in reverse order as well.
    """
    if not has_rtl(text):
        return text
    runs = _runs(text)
    pieces = [(rtl, chunk[::-1] if rtl else chunk) for rtl, chunk in runs]
    if base_direction(text) == "RTL":
        pieces.reverse()
    return "".join(chunk for _, chunk in pieces)


def reorder_visual(text: str) -> str:
    """
    Put text in visual order.

    Uses the bidirectional algorithm of the bidi support that is installed and
    falls back to the simplified reordering above.
    """
    if not has_rtl(text):
        return text
    if has_bidi_support():
        try:
            import rlbidi

            return rlbidi.log2vis(text, None, clean=True)
        except (ImportError, ValueError, TypeError):
            pass
    return reorder_rtl(text)
