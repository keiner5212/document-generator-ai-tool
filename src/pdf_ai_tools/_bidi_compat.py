"""
Compatibility layer for ReportLab's optional right to left support.

ReportLab imports a module named `rlbidi` to reorder right to left text. That
package is not on PyPI, so this module provides the one function ReportLab
uses, `log2vis`, on top of `python-bidi`, and installs itself under the name
`rlbidi` when the real package is missing.

The shim is only installed when it passes a self test. When it is not
installed, ReportLab draws right to left text in logical order and the session
puts the text in visual order itself, without joining the letters.
"""

from __future__ import annotations

import re
import sys

_WORD_RE = re.compile(r"\S+")


def _strip_controls(text: str) -> str:
    """Remove the bidirectional formatting characters."""
    return "".join(
        char
        for char in text
        if ord(char) not in range(0x202A, 0x202F)
        and ord(char) not in range(0x2066, 0x206A)
    )


def _fill_positions(logical: str, visual: str, out: list) -> None:
    """
    Fill the list with the logical index of every visual character.

    Words are matched by content, so a word that is mirrored in the visual
    text still points at the right place in the logical text.
    """
    logical_words = [
        (m.start(), m.end(), m.group(0)) for m in _WORD_RE.finditer(logical)
    ]
    visual_words = [(m.start(), m.end(), m.group(0)) for m in _WORD_RE.finditer(visual)]
    remaining = list(logical_words)
    mapping: dict[int, int] = {}
    for start, end, word in visual_words:
        match = None
        for index, (_, _, candidate) in enumerate(remaining):
            if candidate == word or candidate[::-1] == word:
                match = index
                break
        if match is None:
            break
        word_start, word_end, candidate = remaining.pop(match)
        if candidate == word:
            for offset in range(len(word)):
                mapping[start + offset] = word_start + offset
        else:
            for offset in range(len(word)):
                mapping[start + offset] = word_end - 1 - offset
    # The characters between the words keep their order.
    fillers = [i for i in range(len(logical)) if not _WORD_RE.match(logical, i)]
    spare = [i for i in range(len(visual)) if i not in mapping]
    for visual_index, logical_index in zip(spare, fillers, strict=False):
        mapping[visual_index] = logical_index
    out.extend(mapping.get(index, index) for index in range(len(visual)))


def log2vis(
    text: str,
    base_direction: str | None = None,
    clean: bool = False,
    positions_V_to_L: list | None = None,
) -> str:
    """Put a piece of text in visual order."""
    from bidi import get_display

    direction = None
    if base_direction:
        direction = "R" if str(base_direction).upper() == "RTL" else "L"
    visual = get_display(text, base_dir=direction)
    if clean:
        visual = _strip_controls(visual)
    if positions_V_to_L is not None:
        _fill_positions(_strip_controls(text), visual, positions_V_to_L)
    return visual


def _self_test() -> bool:
    """Check the shim against known right to left results."""
    try:
        from bidi import get_display
    except ImportError:
        return False
    cases = [
        ("abc", "abc"),
        ("ا ب", "ب ا"),
        ("العنوان العربي", "يبرعلا ناونعلا"),
    ]
    for text, expected in cases:
        try:
            if get_display(text) != expected:
                return False
            if log2vis(text, base_direction="RTL") != expected:
                return False
        except Exception:
            return False
    positions: list[int] = []
    log2vis("ا ب", base_direction="RTL", positions_V_to_L=positions)
    if len(positions) != 3:
        return False
    return positions[0] == 2 and positions[2] == 0


def install() -> bool:
    """
    Make the shim available to ReportLab as `rlbidi`.

    Returns True when right to left support is available, either from the real
    package or from the shim.
    """
    if "rlbidi" in sys.modules:
        return True
    try:
        import rlbidi  # noqa: F401

        return True
    except ImportError:
        pass
    try:
        import bidi  # noqa: F401
    except ImportError:
        return False
    if not _self_test():
        return False
    sys.modules["rlbidi"] = sys.modules[__name__]
    return True


# Importing this module puts the shim in place, before ReportLab is imported.
install()
