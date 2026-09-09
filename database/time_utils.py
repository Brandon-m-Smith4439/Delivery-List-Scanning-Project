# File: database/time_utils.py
"""Canonical timestamp parsing and serialization helpers.

Scanner-authored timestamps are stored as aware UTC. A+W/SQL Server ``datetime``
values are different: they are plant-local wall-clock values and normally arrive
without an offset. Keep those two contracts separate so a 05:04 A+W event in
Monroe, NC does not become 01:04/05:04 on screen after an incorrect UTC guess.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python 3.9+ is maintained.
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment,misc]


_FRACTION_PATTERN = re.compile(r"^(?P<prefix>.*?\.)(?P<fraction>\d{7,})(?P<suffix>Z|[+-]\d{2}:?\d{2})?$")
PLANT_TIME_ZONE_NAME = "America/New_York"


def _trim_sql_fraction(text: str) -> str:
    match = _FRACTION_PATTERN.match(text)
    if not match:
        return text
    return f"{match.group('prefix')}{match.group('fraction')[:6]}{match.group('suffix') or ''}"


def _us_eastern_fallback(local_value: datetime) -> timezone:
    """Return the historical US Eastern offset when IANA tzdata is unavailable.

    The application targets current BFS production data (2007+ US DST rules):
    daylight time starts on the second Sunday in March at 02:00 and ends on the
    first Sunday in November at 02:00. This fallback matters mainly on Windows
    Python installations without an IANA tzdata package.
    """
    year = int(local_value.year)

    def nth_sunday(month: int, occurrence: int) -> int:
        first = datetime(year, month, 1)
        first_sunday = 1 + ((6 - first.weekday()) % 7)
        return first_sunday + (occurrence - 1) * 7

    dst_start = datetime(year, 3, nth_sunday(3, 2), 2, 0, 0)
    dst_end = datetime(year, 11, nth_sunday(11, 1), 2, 0, 0)
    offset_hours = -4 if dst_start <= local_value.replace(tzinfo=None) < dst_end else -5
    return timezone(timedelta(hours=offset_hours), name="America/New_York")


def plant_time_zone(local_value: datetime | None = None):
    """Return the maintained Monroe/Charlotte plant timezone.

    ``ZoneInfo`` supplies full DST history when available. The explicit fallback
    avoids depending on the workstation's current offset, which can be wrong for
    an event that occurred on the other side of a daylight-saving transition.
    """
    if ZoneInfo is not None:
        try:
            return ZoneInfo(PLANT_TIME_ZONE_NAME)
        except ZoneInfoNotFoundError:
            pass
    return _us_eastern_fallback(local_value or datetime.now())


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
    text = _trim_sql_fraction(text)
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


def parse_aw_plant_timestamp(value: Any) -> datetime:
    """Parse an A+W/SQL Server timestamp and return an aware UTC datetime.

    Offset-free A+W values are plant-local (Monroe, NC / America/New_York).
    Offset-aware values are already absolute and are never shifted a second time.
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError("Timestamp is required")
    text = _trim_sql_fraction(text)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=plant_time_zone(parsed))
    return parsed.astimezone(timezone.utc)


def normalize_aw_plant_timestamp(value: Any, *, allow_empty: bool = True) -> str:
    """Store A+W plant-local clock values as canonical second-precision UTC."""
    text = str(value or "").strip()
    if not text and allow_empty:
        return ""
    return parse_aw_plant_timestamp(text).isoformat(timespec="seconds")


def reinterpret_legacy_aw_utc_clock_as_plant(value: Any, *, allow_empty: bool = True) -> str:
    """Repair v0.507 rows whose local A+W clock was incorrectly tagged UTC.

    Migration 18 canonicalized several A+W reject columns before the source
    timezone distinction was known. For those *specific legacy A+W columns*, the
    stored clock component is the original plant wall time; discard the erroneous
    offset and localize that clock to America/New_York exactly once.
    """
    text = str(value or "").strip()
    if not text and allow_empty:
        return ""
    text = _trim_sql_fraction(text)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    local_clock = parsed.replace(tzinfo=None)
    return local_clock.replace(tzinfo=plant_time_zone(local_clock)).astimezone(timezone.utc).isoformat(timespec="seconds")
