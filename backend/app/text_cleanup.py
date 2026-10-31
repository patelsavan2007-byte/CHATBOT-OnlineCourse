"""Safe display cleanup for assistant text."""
from __future__ import annotations

import re

_URL = re.compile(r"https?://[^\s)]+", re.I)
_ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\u2060\uFEFF]")
_SPACES = re.compile(r"[\u00A0\u202F\u2009\u200A\u2007]")
_TABLE_DASH = re.compile(r"(?<=\|)\s*—\s*(?=\|)")


def clean_answer_text(text: str) -> str:
    """Remove invisible characters while preserving literal URLs unchanged."""
    def clean_segment(segment: str) -> str:
        segment = _ZERO_WIDTH.sub("", segment)
        segment = _SPACES.sub(" ", segment)
        segment = _TABLE_DASH.sub(" N/A ", segment)
        return segment.replace("—", ", ")

    parts = []
    cursor = 0
    for match in _URL.finditer(text or ""):
        parts.append(clean_segment((text or "")[cursor:match.start()]))
        parts.append(match.group(0))
        cursor = match.end()
    parts.append(clean_segment((text or "")[cursor:]))
    return "".join(parts)
