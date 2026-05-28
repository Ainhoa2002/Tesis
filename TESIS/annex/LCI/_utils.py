"""
Role: Small utility helpers used across the LCI annex scripts.

Brief: Common helper functions and lightweight utilities referenced by other
modules. Keep utilities generic and free of side effects.
"""

"""Common helpers for TESIS/annex/LCI scripts.

Contains safe CSV read/write and simple heuristics used by the cleanup scripts.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Tuple, List


# Purpose: Read csv rows.
def read_csv_rows(path: Path) -> Tuple[List[str], List[dict]]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [name for name in list(reader.fieldnames or []) if name]
            rows = list(reader)
        return fieldnames, rows
    except Exception as exc:
        logging.exception("Failed to read CSV %s: %s", path, exc)
        return [], []


# Purpose: Write csv rows.
def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict], encoding: str = "utf-8") -> bool:
    try:
        with open(path, "w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return True
    except Exception as exc:
        logging.exception("Failed to write CSV %s: %s", path, exc)
        return False


# Purpose: Looks like system created mapping.
def looks_like_system_created_mapping(row: dict) -> bool:
    """Heuristic: return True when a mapping row looks like it was produced by the import logic.

    Rules (best-effort):
    - UUID field is a valid UUID-like string, and the flow name contains no obvious user-markers.
    - For provider rows, UUID_provider looks UUID-like and Ecoinvent_process is non-empty.
    This is intentionally conservative; callers should prefer non-destructive updates.
    """
    def _is_uuid_like(value: str) -> bool:
        if not value:
            return False
        v = str(value).strip()
        if len(v) != 36:
            return False
        # Very light check for hyphen positions
        return v.count("-") == 4

    uuid = str(row.get("UUID", "") or "").strip()
    if uuid and _is_uuid_like(uuid):
        return True

    provider = str(row.get("UUID_provider", "") or "").strip()
    proc = str(row.get("Ecoinvent_process", "") or "").strip()
    if provider and proc and _is_uuid_like(provider):
        return True

    return False


# Purpose: Normalize key.
def normalize_key(value: str) -> str:
    """Normalize a human-readable key for mapping/indexing.

    Behavior: lower-case, strip, remove internal whitespace.
    """
    return "".join(str(value or "").strip().lower().split())


# Purpose: Normalize fill key.
def normalize_fill_key(value: str) -> str:
    """Normalize keys used for fill/matching (remove quotes, whitespace, lower-case)."""
    text = str(value or "").replace('"', "").replace("'", "")
    return "".join(text.split()).lower()


# Purpose: To float.
def to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        # support simple ranges like 0.35-0.4
        if "-" in text and not text.startswith("-"):
            parts = text.split("-")
            if len(parts) == 2:
                try:
                    return (float(parts[0].strip()) + float(parts[1].strip())) / 2.0
                except ValueError:
                    return None
        return None


# Purpose: Clean text.
def clean_text(value) -> str:
    return str(value or "").strip()


# Purpose: Normalize direction.
def normalize_direction(direction, database=None) -> str:
    value = str(direction or "").strip()
    lowered = value.casefold()
    if lowered in {"input", "in"}:
        return "Input"
    if lowered in {"output", "out"}:
        return "Output"
    if value == "" and str(database or "").strip().casefold() == "ecoinvent":
        return "Input"
    return value


# Purpose: Round for csv.
def round_for_csv(value, digits: int = 12):
    if value is None:
        return None
    rounded = round(value, digits)
    if rounded == 0.0 and value != 0.0:
        return value
    return rounded


# Purpose: To yes no.
def to_yes_no(value) -> bool:
    text = str(value or "").strip().upper()
    if text in {"YES", "SI", "S", "Y", "M", "TRUE", "1", "T"}:
        return True
    if text in {"NO", "N", "FALSE", "0", "F"}:
        return False
    return False


# Purpose: Sanitize filename part.
def sanitize_filename_part(value) -> str:
    text = clean_text(value)
    if text == "":
        return "UNKNOWN"

    cleaned = []
    previous_was_separator = False
    for char in text:
        if char.isalnum() or char in {"-", "_"}:
            cleaned.append(char)
            previous_was_separator = False
        else:
            if not previous_was_separator:
                cleaned.append("_")
                previous_was_separator = True

    result = "".join(cleaned).strip("_")
    return result or "UNKNOWN"
