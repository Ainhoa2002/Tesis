#!/usr/bin/env python3
"""Build deduplicated component libraries from all *_component_parameters.csv files.

Creates:
- component_library_by_casing.csv
- component_library_by_part_number.csv

Rules:
- Each library stores unique keys only once.
- Casing library uniqueness key is (Casing, unit, Quantity_per_element).
- If duplicate keys are found, empty fields are filled from later rows.
- Conflicting non-empty values keep the first value and are reported.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple


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

PART_FIELDS = [
    "Manufacturer",
    "Part_Number",
    "Casing",
    "Description",
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


def _load_parameter_rows(base_dir: Path) -> List[Tuple[str, Dict[str, str]]]:
    rows: List[Tuple[str, Dict[str, str]]] = []
    for path in sorted(base_dir.glob("*_component_parameters.csv")):
        subsystem = path.name[: -len("_component_parameters.csv")]
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append((subsystem, row))
    return rows


def _row_subset(row: Dict[str, str], fields: List[str]) -> Dict[str, str]:
    return {field: _clean(row.get(field)) for field in fields}


def _merge_unique(
    target: Dict[str, str],
    incoming: Dict[str, str],
    key_label: str,
    conflicts: List[str],
) -> None:
    for field, new_value in incoming.items():
        old_value = _clean(target.get(field))
        if old_value == "" and new_value != "":
            target[field] = new_value
            continue
        if old_value != "" and new_value != "" and old_value != new_value:
            conflicts.append(
                f"{key_label}: field '{field}' has conflict ('{old_value}' vs '{new_value}')"
            )


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_libraries(base_dir: Path) -> Tuple[int, int, int]:
    raw_rows = _load_parameter_rows(base_dir)

    casing_map: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    part_map: Dict[str, Dict[str, str]] = {}
    conflicts: List[str] = []

    for subsystem, row in raw_rows:
        casing = _clean(row.get("Casing"))
        if casing:
            unit = _clean(row.get("unit"))
            quantity_per_element = _clean(row.get("Quantity_per_element"))
            casing_key = (
                casing.casefold(),
                unit.casefold(),
                _normalize_quantity_key(quantity_per_element),
            )
            incoming_casing = _row_subset(row, CASING_FIELDS)
            if casing_key not in casing_map:
                casing_map[casing_key] = incoming_casing
            else:
                _merge_unique(
                    casing_map[casing_key],
                    incoming_casing,
                    (
                        f"Casing '{casing}' | unit '{unit}' | "
                        f"Quantity_per_element '{quantity_per_element}' "
                        f"(subsystem '{subsystem}')"
                    ),
                    conflicts,
                )

        part_number = _clean(row.get("Part_Number"))
        if part_number:
            manufacturer = _clean(row.get("Manufacturer"))
            part_key = f"{manufacturer.casefold()}::{part_number.casefold()}"
            incoming_part = _row_subset(row, PART_FIELDS)
            if part_key not in part_map:
                part_map[part_key] = incoming_part
            else:
                _merge_unique(
                    part_map[part_key],
                    incoming_part,
                    f"Part '{manufacturer} {part_number}' (subsystem '{subsystem}')",
                    conflicts,
                )

    casing_rows = sorted(
        casing_map.values(),
        key=lambda r: (
            r["Casing"].casefold(),
            _clean(r.get("unit")).casefold(),
            _normalize_quantity_key(r.get("Quantity_per_element")),
        ),
    )
    part_rows = sorted(
        part_map.values(),
        key=lambda r: (r["Manufacturer"].casefold(), r["Part_Number"].casefold()),
    )

    _write_csv(base_dir / CASING_LIBRARY_NAME, CASING_FIELDS, casing_rows)
    _write_csv(base_dir / PART_LIBRARY_NAME, PART_FIELDS, part_rows)

    if conflicts:
        print("Library merge warnings (first value kept when conflicts exist):")
        for line in conflicts[:20]:
            print(f"- {line}")
        if len(conflicts) > 20:
            print(f"- ... and {len(conflicts) - 20} more")

    return len(casing_rows), len(part_rows), len(conflicts)


def main() -> None:
    casing_count, part_count, conflict_count = build_libraries(BASE_DIR)
    print(f"Created {CASING_LIBRARY_NAME}: {casing_count} unique casing rows")
    print(f"Created {PART_LIBRARY_NAME}: {part_count} unique part-number rows")
    print(f"Conflicts detected: {conflict_count}")


if __name__ == "__main__":
    main()
