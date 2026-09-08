# File: database/time_utils.py
"""Canonical UTC timestamp parsing and serialization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


_FRACTION_PATTERN = re.compile(r"^(?P<prefix>.*?\.)(?P<fraction>\d{7,})(?P<suffix>Z|[+-]\d{2}:?\d{2})?$")


def parse_utc_timestamp(value: Any) -> datetime:
    """Parse an ISO/SQL timestamp and return an aware UTC datetime.

    SQL Server commonly emits seven fractional-second digits and may omit an
    offset. Existing scanner behavior treats offset-free source values as UTC;
    retaining that convention repairs the storage contract without shifting
    historical operator-visible times.
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError("Timestamp is required")
    match = _FRACTION_PATTERN.match(text)
    if match:
        text = f"{match.group('prefix')}{match.group('fraction')[:6]}{match.group('suffix') or ''}"
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_utc_timestamp(value: Any, *, allow_empty: bool = True) -> str:
    """Return canonical second-precision UTC ISO text for database storage."""
    text = str(value or "").strip()
    if not text and allow_empty:
        return ""
    return parse_utc_timestamp(text).isoformat(timespec="seconds")
