# File: backend/aw_reject_legacy.py
"""Historical A+W reject vocabulary reconciliation helpers.

A+W PROD_BREAKAGE stores numeric lookup codes.  Those codes can outlive rows in
KA_REKLA_GRND / KA_REKLA_ORT, and administrators can later rebuild the lookup
libraries with different labels.  This module keeps historical scanner meaning
stable by matching known legacy recut-log context and translating it into the
current floor-facing vocabulary without writing anything back to A+W.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Iterable


LEGACY_CONTEXT_CUTOVER = "2026-09-29"
LEGACY_CONTEXT_RESOURCE = "aw_reject_legacy_context_v0585.json"

CURRENT_REASON_LABELS = (
    "Broken on Truck",
    "Broke in Machine",
    "Broke While Handling",
    "Broke",
    "Chipped in Machine",
    "Chipped While Handling",
    "Chipped",
    "Scratched in Machine",
    "Scratched While Handling",
    "Scratched",
    "Bad Breakout",
    "Mistagged",
    "Improper Edgework",
    "Missed Edgework",
    "Improper Fabrication",
    "Missed Fabrication",
    "Lost",
    "Machine Malfunction",
    "Operator Error",
    "Fell",
    "Heat Stain",
    "Warp/Bow",
    "Optimization Reject",
    "Supplier Defect",
    "Other/Unknown",
)

CURRENT_LOCATION_LABELS = (
    "Indian Trail/Install",
    "Last Sheet",
    "Cutting Table",
    "Kodiak Polisher",
    "Skiati Polisher",
    "Denver CNC",
    "Waterjet",
    "Denver Washer",
    "Mirror Washer",
    "Seaming Table",
    "Oven Washer",
    "Oven",
    "Quench",
    "Oven Wrapper",
    "Mirror Wrapper",
    "Staging",
    "Framing Table",
    "A Frame Cart",
    "Truck",
    "In Transit",
    "Manufacturer",
    "Other/Unknown",
)

CURRENT_REASON_LOOKUP = {value.casefold(): value for value in CURRENT_REASON_LABELS}
CURRENT_LOCATION_LOOKUP = {value.casefold(): value for value in CURRENT_LOCATION_LABELS}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _upper(value: Any) -> str:
    return _clean(value).upper()


def _normalized_order(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z-]", "", _clean(value))


def _normalized_item(value: Any) -> str:
    text = _clean(value)
    return text.zfill(3) if text.isdigit() else text


def _normalized_job(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean(value)).casefold()


def _date_text(value: Any) -> str:
    return _clean(value)[:10]


def canonical_reason(legacy_reason: Any, legacy_location: Any = "") -> str:
    """Translate one legacy recut reason into the current A+W reason library."""
    reason = _upper(legacy_reason)
    location = _upper(legacy_location)
    if not reason:
        return "Other/Unknown"
    if reason in {"POOR BREAKOUT", "BAD BREAKOUT"}:
        return "Bad Breakout"
    if reason in {"BROKE", "BROKEN"}:
        if location in {"SHIPPING", "TRUCK", "TRUCK LOADING", "IN TRANSIT"}:
            return "Broken on Truck"
        if location in {"HANDLING", "WAREHOUSE", "AIRPORT", "IN HOUSE", "A FRAME", "A FRAME CART", "STAGING"}:
            return "Broke While Handling"
        if location in {
            "CUT TABLE", "CUTTING", "CUTTING TABLE", "POLISHER", "DENVER", "WATERJET", "WASHER",
            "SEAMING TABLE", "OVEN", "QUENCH", "WRAP", "SMART GLAZIER",
        }:
            return "Broke in Machine"
        return "Broke"
    if reason == "CHIPPED":
        if location in {"HANDLING", "WAREHOUSE", "AIRPORT", "IN HOUSE", "SHIPPING", "STAGING", "A FRAME", "A FRAME CART"}:
            return "Chipped While Handling"
        if location in {
            "CUT TABLE", "CUTTING", "CUTTING TABLE", "POLISHER", "DENVER", "WATERJET", "WASHER",
            "SEAMING TABLE", "OVEN", "QUENCH", "WRAP", "SMART GLAZIER",
        }:
            return "Chipped in Machine"
        return "Chipped"
    if reason in {"SCRATCHED", "SCRATCH"}:
        if location in {"HANDLING", "WAREHOUSE", "AIRPORT", "IN HOUSE", "SHIPPING", "STAGING", "A FRAME", "A FRAME CART"}:
            return "Scratched While Handling"
        if location in {
            "CUT TABLE", "CUTTING", "CUTTING TABLE", "POLISHER", "DENVER", "WATERJET", "WASHER",
            "SEAMING TABLE", "OVEN", "QUENCH", "WRAP", "SMART GLAZIER",
        }:
            return "Scratched in Machine"
        return "Scratched"
    direct = CURRENT_REASON_LOOKUP.get(_clean(legacy_reason).casefold())
    if direct:
        return direct
    if reason in {"WRONG LABEL", "MISTAGGED", "MIS-TAGGED", "MISTAG"}:
        return "Mistagged"
    if reason in {"DUPLICATED", "DUPLICATE", "WRONG OPTIMIZATION", "OPTIMIZATION ISSUE", "OPTIMIZATION ERROR"}:
        return "Optimization Reject"
    if reason in {"NO FAB", "NO FABRICATION", "MISSED FAB", "MISSED FABRICATION"}:
        return "Missed Fabrication"
    if reason in {"NO POLISH", "MISSED POLISH", "MISSED EDGEWORK"}:
        return "Missed Edgework"
    if reason in {"FP ON TALL SIDES", "POLISHED", "WRONG POLISH", "BAD POLISH"}:
        return "Improper Edgework"
    if reason in {"WRONG SIZE", "WRONG PROGRAM", "LOGO WRONG SPOT"}:
        return "Improper Fabrication"
    if reason in {"LOADED INCORRECTLY", "MEASURED WRONG", "ORDERED WRONG"}:
        return "Operator Error"
    if reason in {"BAD PAINT"}:
        return "Supplier Defect"
    if reason == "MIRROR BACKING" and location == "MANUFACTURER":
        return "Supplier Defect"
    if reason in {"A&W ERROR", "DAMAGED"}:
        return "Other/Unknown"
    aliases = {
        "IMPROPER EDGEWORK": "Improper Edgework",
        "IMPROPER FABRICATION": "Improper Fabrication",
        "LOST": "Lost",
        "MACHINE MALFUNCTION": "Machine Malfunction",
        "OPERATOR ERROR": "Operator Error",
        "FELL": "Fell",
        "SUPPLIER DEFECT": "Supplier Defect",
        "HEAT STAIN": "Heat Stain",
        "WARP/BOW": "Warp/Bow",
    }
    return aliases.get(reason, "Other/Unknown")


def _specific_machine_location(machine: Any, registration_point: Any = "", work_type: Any = "") -> str:
    text = " ".join((_upper(machine), _upper(registration_point), _upper(work_type)))
    if "KODIAK" in text:
        return "Kodiak Polisher"
    if "SKIATI" in text or "SCHIATTI" in text:
        return "Skiati Polisher"
    if "DENVER" in text and "WASH" in text:
        return "Denver Washer"
    if "MIRROR" in text and "WASH" in text:
        return "Mirror Washer"
    if "OVEN" in text and "WASH" in text:
        return "Oven Washer"
    if "DENVER" in text:
        return "Denver CNC"
    if "WATERJET" in text or re.search(r"\bWJ\b", text):
        return "Waterjet"
    if "SEAM" in text:
        return "Seaming Table"
    if "QUENCH" in text:
        return "Quench"
    if "OVEN" in text and "WRAP" in text:
        return "Oven Wrapper"
    if "MIRROR" in text and "WRAP" in text:
        return "Mirror Wrapper"
    if "FRAM" in text:
        return "Framing Table"
    if "A FRAME" in text or "A-FRAME" in text:
        return "A Frame Cart"
    if "TRUCK" in text:
        return "Truck"
    if "STAG" in text or "WAREHOUSE" in text:
        return "Staging"
    return ""


def canonical_location(
    legacy_location: Any,
    *,
    glass_type: Any = "",
    note: Any = "",
    machine: Any = "",
    registration_point: Any = "",
    work_type: Any = "",
) -> str:
    """Translate a legacy machine/location into the current Complaint Cause list.

    Legacy POLISHER is mapped to Kodiak Polisher because the Skiati polisher was
    acquired only recently and the supplied historical recut log predates that
    machine's meaningful reject history. Other generic names remain conservative
    unless A+W machine/registration context or a strong recut-log clue identifies
    the current destination.
    """
    current = CURRENT_LOCATION_LOOKUP.get(_clean(legacy_location).casefold())
    if current:
        return current
    specific = _specific_machine_location(machine, registration_point, work_type)
    location = _upper(legacy_location)
    glass = _upper(glass_type)
    notes = _upper(note)
    if location in {"CUT TABLE", "CUTTING", "CUTTING TABLE"}:
        return "Cutting Table"
    if location == "DENVER":
        return "Denver CNC"
    if location in {"WATERJET", "WATER JET"}:
        return "Waterjet"
    if location == "SEAMING TABLE":
        return "Seaming Table"
    if location == "OVEN":
        return "Oven"
    if location == "QUENCH":
        return "Quench"
    if location == "FRAMING TABLE":
        return "Framing Table"
    if location == "MANUFACTURER":
        return "Manufacturer"
    if location in {"TRUCK", "TRUCK LOADING"}:
        return "Truck"
    if location == "SHIPPING":
        return "In Transit"
    if location in {"WAREHOUSE", "AIRPORT"}:
        return "Staging"
    if location == "HANDLING":
        if "A FRAME" in notes or "A-FRAME" in notes or "CART" in notes or "CRANE" in notes:
            return "A Frame Cart"
        return specific or "Other/Unknown"
    if location == "POLISHER":
        return "Kodiak Polisher"
    if location == "WASHER":
        if specific in {"Denver Washer", "Mirror Washer", "Oven Washer"}:
            return specific
        if "MIRROR" in glass:
            return "Mirror Washer"
        return "Other/Unknown"
    if location == "WRAP":
        if specific in {"Oven Wrapper", "Mirror Wrapper"}:
            return specific
        return "Mirror Wrapper" if "MIRROR" in glass else "Oven Wrapper"
    if location in {"SMART GLAZIER", "A&W", "OPTIMIZATION", "IN HOUSE", "UNKNOWN", ""}:
        return specific or "Other/Unknown"
    return specific or "Other/Unknown"


def _resource_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / LEGACY_CONTEXT_RESOURCE


@lru_cache(maxsize=1)
def legacy_context_payload() -> dict[str, Any]:
    path = _resource_path()
    if not path.exists():
        return {"entries": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"entries": []}
    return payload if isinstance(payload, dict) else {"entries": []}


@lru_cache(maxsize=1)
def legacy_context_index() -> dict[tuple[str, str, str, str], tuple[dict[str, Any], ...]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in legacy_context_payload().get("entries", []):
        if not isinstance(raw, dict):
            continue
        key = (
            _date_text(raw.get("breakageDate")),
            _normalized_order(raw.get("order")),
            _normalized_item(raw.get("item")),
            _normalized_job(raw.get("originalJob")),
        )
        if key[0] and key[1] and key[2]:
            grouped[key].append(dict(raw))
    return {key: tuple(values) for key, values in grouped.items()}


def context_candidates(
    *,
    breakage_date: Any,
    order_no: Any,
    item_no: Any,
    original_job_number: Any = "",
) -> tuple[dict[str, Any], ...]:
    date_key = _date_text(breakage_date)
    if not date_key or date_key > LEGACY_CONTEXT_CUTOVER:
        return ()
    order_key = _normalized_order(order_no)
    item_key = _normalized_item(item_no)
    job_key = _normalized_job(original_job_number)
    index = legacy_context_index()
    exact = index.get((date_key, order_key, item_key, job_key), ())
    if exact:
        return exact
    # Some hand-maintained recut entries use descriptive text where A+W stores a
    # numeric original job.  Fall back only when the date/order/item identifies a
    # single legacy meaning; otherwise leave it unresolved rather than guess.
    fallback: list[dict[str, Any]] = []
    for (candidate_date, candidate_order, candidate_item, _candidate_job), values in index.items():
        if candidate_date == date_key and candidate_order == order_key and candidate_item == item_key:
            fallback.extend(values)
    return tuple(fallback)


def _distinct_pairs(candidates: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for candidate in candidates:
        pair = (_clean(candidate.get("legacyReason")), _clean(candidate.get("legacyLocation")))
        if pair not in seen:
            seen.add(pair)
            result.append(pair)
    return result


def resolve_legacy_context(
    *,
    breakage_date: Any,
    order_no: Any,
    item_no: Any,
    original_job_number: Any = "",
    reason_hint: Any = "",
    location_hint: Any = "",
    machine: Any = "",
    registration_point: Any = "",
    work_type: Any = "",
) -> dict[str, str]:
    """Resolve one historical event against the supplied recut-log evidence."""
    candidates = list(context_candidates(
        breakage_date=breakage_date,
        order_no=order_no,
        item_no=item_no,
        original_job_number=original_job_number,
    ))
    if not candidates:
        return {}

    clean_reason_hint = _clean(reason_hint).casefold()
    clean_location_hint = _clean(location_hint).casefold()
    if clean_reason_hint:
        reason_matches = [c for c in candidates if _clean(c.get("legacyReason")).casefold() == clean_reason_hint]
        if reason_matches:
            candidates = reason_matches
    if clean_location_hint and len(candidates) > 1:
        location_matches = [c for c in candidates if _clean(c.get("legacyLocation")).casefold() == clean_location_hint]
        if location_matches:
            candidates = location_matches

    pairs = _distinct_pairs(candidates)
    selected: dict[str, Any] | None = None
    resolution = ""
    if len(pairs) == 1:
        selected = candidates[0]
        resolution = "recut-log:exact"
    else:
        specific = _specific_machine_location(machine, registration_point, work_type)
        if specific:
            by_machine = [
                c for c in candidates
                if canonical_location(
                    c.get("legacyLocation"),
                    glass_type=c.get("glassType"), note=c.get("note"), machine=machine,
                    registration_point=registration_point, work_type=work_type,
                ) == specific
            ]
            if len(_distinct_pairs(by_machine)) == 1 and by_machine:
                selected = by_machine[0]
                resolution = "recut-log:machine-context"

    if selected is None:
        canonical_pairs = {
            (
                canonical_reason(c.get("legacyReason"), c.get("legacyLocation")),
                canonical_location(
                    c.get("legacyLocation"), glass_type=c.get("glassType"), note=c.get("note"),
                    machine=machine, registration_point=registration_point, work_type=work_type,
                ),
            )
            for c in candidates
        }
        if len(canonical_pairs) == 1:
            canonical_reason_label, canonical_location_label = next(iter(canonical_pairs))
            return {
                "legacyReason": _clean(candidates[0].get("legacyReason")),
                "legacyLocation": _clean(candidates[0].get("legacyLocation")),
                "canonicalReason": canonical_reason_label,
                "canonicalLocation": canonical_location_label,
                "resolution": "recut-log:equivalent-context",
            }
        return {
            "canonicalReason": "Other/Unknown",
            "canonicalLocation": "Other/Unknown",
            "resolution": "recut-log:ambiguous",
        }

    legacy_reason = _clean(selected.get("legacyReason"))
    legacy_location = _clean(selected.get("legacyLocation"))
    return {
        "legacyReason": legacy_reason,
        "legacyLocation": legacy_location,
        "canonicalReason": canonical_reason(legacy_reason, legacy_location),
        "canonicalLocation": canonical_location(
            legacy_location,
            glass_type=selected.get("glassType"),
            note=selected.get("note"),
            machine=machine,
            registration_point=registration_point,
            work_type=work_type,
        ),
        "resolution": resolution,
    }


def canonical_current_source(reason_label: Any, location_label: Any) -> dict[str, str]:
    """Normalize labels that already belong to the rebuilt current A+W lists."""
    reason = CURRENT_REASON_LOOKUP.get(_clean(reason_label).casefold(), "")
    location = CURRENT_LOCATION_LOOKUP.get(_clean(location_label).casefold(), "")
    if not reason and not location:
        return {}
    return {
        "canonicalReason": reason,
        "canonicalLocation": location,
        "resolution": "source-current",
    }
