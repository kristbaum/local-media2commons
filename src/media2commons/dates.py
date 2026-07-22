"""Date handling for the SMW ``Erstellungsdatum`` property."""

from __future__ import annotations

import re

# Plausible range for a creation year; anything outside is treated as noise.
MIN_YEAR = 1000
MAX_YEAR = 2100

_YEAR_PATTERN = re.compile(r"\b\d{4}\b")


def normalize_smw_date(raw_date: str | None) -> str:
    """Convert an SMW raw date (``1/1754/8/12``) into an ISO-ish prefix.

    SMW encodes dates as slash-separated parts with a leading calendar-model
    digit. Returns ``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD``; input that does not
    fit that shape is returned unchanged.
    """
    if not raw_date:
        return ""

    raw_date = raw_date.strip()
    parts = raw_date.split("/")

    # Drop the leading calendar-model marker.
    if parts and parts[0] == "1":
        parts = parts[1:]

    match len(parts):
        case 1:
            return parts[0]
        case 2:
            return f"{parts[0]}-{parts[1].zfill(2)}"
        case 3:
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        case _:
            return raw_date


def extract_year(date_str: str | None) -> int | None:
    """Pull a plausible 4-digit year out of a date string, or ``None``."""
    if not date_str:
        return None

    text = str(date_str).strip()
    if not text:
        return None

    if text.isdigit() and len(text) == 4 and MIN_YEAR <= int(text) <= MAX_YEAR:
        return int(text)

    # YYYY-MM / YYYY-MM-DD as produced by normalize_smw_date.
    head = text.split("-")[0]
    if head.isdigit() and len(head) == 4 and MIN_YEAR <= int(head) <= MAX_YEAR:
        return int(head)

    for match in _YEAR_PATTERN.finditer(text):
        year = int(match.group())
        if MIN_YEAR <= year <= MAX_YEAR:
            return year

    return None


def year_string(date_str: str | None) -> str:
    """Like :func:`extract_year` but returns ``""`` instead of ``None``."""
    year = extract_year(date_str)
    return str(year) if year else ""
