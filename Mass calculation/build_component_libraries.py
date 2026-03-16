#!/usr/bin/env python3
"""Build deduplicated component libraries from all *_component_parameters.csv files.

Creates:
- component_library_by_casing.csv
- component_library_by_part_number.csv

Rules:
- Each library stores unique keys only once.
- Casing library uniqueness key is (Casing, Quantity_per_element).
- If duplicate keys are found, empty fields are filled from later rows.
- Conflicting non-empty values keep the first value and are reported.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple


BASE_DIR = Path(__file__).parent

CASING_LIBRARY_NAME = "component_library_by_casing.csv"
PART_LIBRARY_NAME = "component_library_by_part_number.csv"

CASING_FIELDS = [
    "Casing",
    "Section",
    "Subsection",
    "unit",
    "Quantity_per_element",
    "L_mm",
    "W_mm",
    "H_mm",
    "Volume_cm3_excel",
    "Density_min_g_cm3",
    "Density_max_g_cm3",
    "Metal_extra_g",
    "Other_extra_g",
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
    "Database",
    "Database_component_title",
]

CASING_WARNING_FIELDS = {
    "L_mm",
    "W_mm",
    "H_mm",
    "Density_min_g_cm3",
    "Density_max_g_cm3",
    "Metal_extra_g",
}

FIELD_LABELS = {
    "unit": "UNIT",
    "Quantity_per_element": "QUANTITY_PER_ELEMENT",
    "Has_datasheet_info": "HAS_DATASHEET_INFO",
    "L_mm": "L",
    "W_mm": "W",
    "H_mm": "H",
    "Volume_cm3_excel": "VOLUME_CM3",
    "Density_min_g_cm3": "DENSITY_MIN",
    "Density_max_g_cm3": "DENSITY_MAX",
    "Metal_extra_g": "EXTRA_MASS_METAL",
    "Other_extra_g": "EXTRA_MASS_OTHER",
    "Database": "DATABASE",
    "Ecoinvent_flow": "ECOINVENT_FLOW",
    "Ecoinvent_unit": "ECOINVENT_UNIT",
    "Direction": "DIRECTION",
}

PART_FIELDS = [
    "Manufacturer",
    "Part_Number",
    "Casing",
    "Description",
    "Section",
    "Subsection",
    "unit",
    "Quantity_per_element",
    "Has_datasheet_info",
    "L_mm",
    "W_mm",
    "H_mm",
    "Volume_cm3_excel",
    "Density_min_g_cm3",
    "Density_max_g_cm3",
    "Metal_extra_g",
    "Other_extra_g",
    "Database",
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
    "Database_component_title",
]

# Fields used to decide whether two rows with the same (Manufacturer, Part_Number)
# are true duplicates (all equal → one entry, no warning) or conflicting variants
# (any differ → both entries kept + warning).
PART_COMPARISON_FIELDS = [
    "unit",
    "Quantity_per_element",
    "Has_datasheet_info",
    "L_mm",
    "W_mm",
    "H_mm",
    "Volume_cm3_excel",
    "Density_min_g_cm3",
    "Density_max_g_cm3",
    "Metal_extra_g",
    "Other_extra_g",
    "Database",
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
]

ROW_MATCH_FIELDS = [
    "Designators",
    "Manufacturer",
    "Part_Number",
    "Casing",
    "Section",
    "Subsection",
]


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _normalize_quantity_key(value: str | None) -> str:
    """Normalize numeric strings so equivalent quantities map to the same key."""
    text = _clean(value)
    if text == "":
        return ""

    try:
        return format(float(text.replace(",", ".")), ".12g")
    except ValueError:
        return text.casefold()


def _row_match_key(row: Dict[str, str]) -> Tuple[str, ...]:
    return tuple(_clean(row.get(field)).casefold() for field in ROW_MATCH_FIELDS)


def _load_result_quantity_map(base_dir: Path, subsystem: str) -> Dict[Tuple[str, ...], str]:
    result_path = base_dir / f"{subsystem}_component_mass_results.csv"
    if not result_path.exists():
        return {}

    quantity_map: Dict[Tuple[str, ...], str] = {}
    with open(result_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            quantity_value = _clean(row.get("Quantity_per_element"))
            if quantity_value == "":
                continue
            quantity_map[_row_match_key(row)] = quantity_value
    return quantity_map


def _load_parameter_rows(base_dir: Path) -> List[Tuple[str, Dict[str, str]]]:
    rows: List[Tuple[str, Dict[str, str]]] = []
    for path in sorted(base_dir.glob("*_component_parameters.csv")):
        subsystem = path.name[: -len("_component_parameters.csv")]
        result_quantity_map = _load_result_quantity_map(base_dir, subsystem)
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                merged_row = dict(row)
                result_quantity = result_quantity_map.get(_row_match_key(row), "")
                if result_quantity != "":
                    merged_row["Quantity_per_element"] = result_quantity
                rows.append((subsystem, merged_row))
    return rows


def _row_subset(row: Dict[str, str], fields: List[str]) -> Dict[str, str]:
    return {field: _clean(row.get(field)) for field in fields}


def _merge_unique(
    target: Dict[str, str],
    incoming: Dict[str, str],
    conflict_kind: str,
    reference: str,
    source_file: str,
    folder: str,
    casing_conflicts: Dict[Tuple[str, str, str, str], Set[str]],
    conflict_fields: Set[str] | None = None,
) -> int:
    conflict_count = 0
    for field, new_value in incoming.items():
        old_value = _clean(target.get(field))
        if old_value == "" and new_value != "":
            target[field] = new_value
            continue
        if old_value != "" and new_value != "" and old_value != new_value:
            if conflict_fields is None or field in conflict_fields:
                key = (conflict_kind, reference, source_file, folder)
                casing_conflicts.setdefault(key, set()).add(field)
                conflict_count += 1
    return conflict_count


def _print_conflict_summary(
    casing_conflicts: Dict[Tuple[str, str, str, str], Set[str]],
    part_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]],
) -> None:
    if not casing_conflicts and not part_conflicts:
        return

    print("Library merge warnings:")
    for kind, reference, source_file, folder in sorted(casing_conflicts):
        raw_fields = sorted(casing_conflicts[(kind, reference, source_file, folder)])
        fields = ", ".join(FIELD_LABELS.get(f, f) for f in raw_fields)
        print(
            f"- {kind} '{reference}' has different values across components. "
            f"Differing fields: {fields}. Source file: {source_file}. Folder: {folder}"
        )
    for base_key in sorted(part_conflicts):
        reference, subsystems, diff_fields = part_conflicts[base_key]
        fields = ", ".join(FIELD_LABELS.get(f, f) for f in sorted(diff_fields))
        subs_text = " and ".join(f"{s} subsystem" for s in sorted(subsystems))
        print(
            f"- Part '{reference}' has different values across components. "
            f"Differing fields: {fields}. Between {subs_text}."
        )


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_libraries(base_dir: Path) -> Tuple[int, int, int]:
    """Rebuild both libraries from scratch on every call.

    Casing library:
      - Key: (Casing, Quantity_per_element)
      - Same key → deduplicate (one entry).
      - Different Quantity_per_element for the same Casing → both entries kept.
      - Conflicting geometry/density fields → warning.

    Part-number library:
      - Key: (Manufacturer, Part_Number) + all PART_COMPARISON_FIELDS
      - All fields equal → one entry, no warning.
      - Same (Manufacturer, Part_Number) but any comparison field differs
        → BOTH entries kept + warning listing the differing fields.
    """
    raw_rows = _load_parameter_rows(base_dir)

    casing_map: Dict[Tuple[str, str], Dict[str, str]] = {}
    # Part tracking: full dedup key → skip exact duplicates
    part_full_seen: set = set()
    # First added row per base key, used for diff comparison
    part_first_rows: Dict[str, Dict[str, str]] = {}
    part_rows_list: List[Dict[str, str]] = []

    casing_conflicts: Dict[Tuple[str, str, str, str], Set[str]] = {}
    # base_key → (reference_label, subsystems_set, differing_fields_set)
    part_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]] = {}
    # First subsystem per base key
    part_first_subsystem: Dict[str, str] = {}
    conflict_count = 0
    folder_name = base_dir.name

    for subsystem, row in raw_rows:
        source_file = f"{subsystem}_component_parameters.csv"
        casing = _clean(row.get("Casing"))
        if casing:
            quantity_per_element = _clean(row.get("Quantity_per_element"))
            casing_key = (
                casing.casefold(),
                _normalize_quantity_key(quantity_per_element),
            )
            incoming_casing = _row_subset(row, CASING_FIELDS)
            if casing_key not in casing_map:
                casing_map[casing_key] = incoming_casing
            else:
                conflict_count += _merge_unique(
                    casing_map[casing_key],
                    incoming_casing,
                    "Casing",
                    f"{casing} | Quantity_per_element={quantity_per_element}",
                    source_file,
                    folder_name,
                    casing_conflicts,
                    conflict_fields=CASING_WARNING_FIELDS,
                )

        part_number = _clean(row.get("Part_Number"))
        if part_number:
            manufacturer = _clean(row.get("Manufacturer"))
            base_key = f"{manufacturer.casefold()}::{part_number.casefold()}"
            incoming_part = _row_subset(row, PART_FIELDS)

            # Build a full deduplication key from the comparison fields.
            full_key = (base_key,) + tuple(
                _normalize_quantity_key(incoming_part.get(f))
                if f == "Quantity_per_element"
                else _clean(incoming_part.get(f))
                for f in PART_COMPARISON_FIELDS
            )

            if full_key in part_full_seen:
                # True duplicate – skip silently.
                continue
            part_full_seen.add(full_key)

            if base_key in part_first_rows:
                # Same (Manufacturer, Part_Number) but different data → warn.
                first_row = part_first_rows[base_key]
                differing: Set[str] = set()
                for f in PART_COMPARISON_FIELDS:
                    v1 = _clean(first_row.get(f))
                    v2 = _clean(incoming_part.get(f))
                    if f == "Quantity_per_element":
                        match = _normalize_quantity_key(v1) == _normalize_quantity_key(v2)
                    else:
                        match = v1 == v2
                    if not match:
                        differing.add(f)
                if differing:
                    reference = f"{manufacturer} {part_number}"
                    if base_key not in part_conflicts:
                        part_conflicts[base_key] = (
                            reference,
                            {part_first_subsystem[base_key], subsystem},
                            differing,
                        )
                    else:
                        _, existing_subs, existing_fields = part_conflicts[base_key]
                        existing_subs.add(subsystem)
                        existing_fields.update(differing)
                    conflict_count += 1
            else:
                part_first_rows[base_key] = incoming_part
                part_first_subsystem[base_key] = subsystem

            part_rows_list.append(incoming_part)

    casing_rows = sorted(
        casing_map.values(),
        key=lambda r: (
            r["Casing"].casefold(),
            _clean(r.get("unit")).casefold(),
            _normalize_quantity_key(r.get("Quantity_per_element")),
        ),
    )
    part_rows = sorted(
        part_rows_list,
        key=lambda r: (r["Manufacturer"].casefold(), r["Part_Number"].casefold()),
    )

    # Always overwrite from scratch to avoid stale residual entries.
    _write_csv(base_dir / CASING_LIBRARY_NAME, CASING_FIELDS, casing_rows)
    _write_csv(base_dir / PART_LIBRARY_NAME, PART_FIELDS, part_rows)

    _print_conflict_summary(casing_conflicts, part_conflicts)

    return len(casing_rows), len(part_rows), conflict_count


def main() -> None:
    casing_count, part_count, conflict_count = build_libraries(BASE_DIR)
    print(f"Created {CASING_LIBRARY_NAME}: {casing_count} unique casing rows")
    print(f"Created {PART_LIBRARY_NAME}: {part_count} unique part-number rows")
    print(f"Conflicts detected: {conflict_count}")


if __name__ == "__main__":
    main()
