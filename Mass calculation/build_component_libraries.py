#!/usr/bin/env python3
"""Build deduplicated component libraries from all *_component_parameters.csv files.

Creates:
- component_library_by_casing.csv
- component_library_by_part_number.csv
- component_library_ecoinvent_totals.csv
- component_library_systems_subsystems.csv

Rules:
- Each library stores unique keys only once.
- Casing library uniqueness key is (Casing + mass-calculation parameters).
- If duplicate keys are found, empty fields are filled from later rows.
- Conflicting non-empty values keep the first value and are reported.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


BASE_DIR = Path(__file__).parent

CASING_LIBRARY_NAME = "component_library_by_casing.csv"
PART_LIBRARY_NAME = "component_library_by_part_number.csv"
ECOINVENT_TOTALS_LIBRARY_NAME = "component_library_ecoinvent_totals.csv"
SYSTEM_SUBSYSTEM_LIBRARY_NAME = "component_library_systems_subsystems.csv"

SYSTEM_SUBSYSTEM_FIELDS = [
    "System",
    "Subsystem",
    "Source_subsystems",
    "Component_rows",
]

ECOINVENT_TOTALS_FIELDS = [
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
    "Total_amount",
    "Total_mass_kg",
    "Subsystems",
]

CASING_FIELDS = [
    "Casing",
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
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
    "Database",
    "Database_component_title",
]

CASING_MASS_COMPARISON_FIELDS = [
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
]

CASING_NUMERIC_FIELDS = {
    "Quantity_per_element",
    "L_mm",
    "W_mm",
    "H_mm",
    "Volume_cm3_excel",
    "Density_min_g_cm3",
    "Density_max_g_cm3",
    "Metal_extra_g",
}

FIELD_LABELS = {
    "Section": "SECTION",
    "Subsection": "SUBSECTION",
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
    "Database_component_title": "DATABASE_COMPONENT_TITLE",
}

PART_FIELDS = [
    "Manufacturer",
    "Part_Number",
    "Subsystems",
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

PART_SYNC_FIELDS = [
    "Manufacturer",
    "Part_Number",
    "Casing",
    "Description",
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

PART_MASS_DIMENSION_FIELDS = ["L_mm", "W_mm", "H_mm"]

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


def _normalize_direction(value: str | None, database: str | None = None) -> str:
    text = _clean(value)
    lowered = text.casefold()
    if lowered in {"input", "in"}:
        return "Input"
    if lowered in {"output", "out"}:
        return "Output"

    # For EcoInvent rows, an empty direction is almost always intended as Input.
    if text == "" and _clean(database).casefold() == "ecoinvent":
        return "Input"

    return text


def _normalize_ecoinvent_fields(row: Dict[str, str]) -> Dict[str, str]:
    """Normalize common EcoInvent field inconsistencies in CSV rows.

    Handles cases where Ecoinvent_unit is accidentally filled with Input/Output
    and direction is missing, by recovering the unit from the generic `unit` field.
    """
    normalized = dict(row)

    database = _clean(normalized.get("Database"))
    ecoinvent_unit = _clean(normalized.get("Ecoinvent_unit"))
    direction = _clean(normalized.get("Direction"))
    fallback_unit = _clean(normalized.get("unit"))

    unit_token = ecoinvent_unit.casefold()
    direction_token = direction.casefold()

    # Recover shifted values when unit accidentally contains direction text.
    if unit_token in {"input", "output", "in", "out"} and direction == "":
        direction = ecoinvent_unit
        ecoinvent_unit = fallback_unit

    # If both fields contain direction-like values, prefer fallback unit.
    if (
        ecoinvent_unit.casefold() in {"input", "output", "in", "out"}
        and direction_token in {"input", "output", "in", "out"}
        and fallback_unit != ""
    ):
        ecoinvent_unit = fallback_unit

    normalized["Ecoinvent_unit"] = ecoinvent_unit
    normalized["Direction"] = _normalize_direction(direction, database)
    return normalized


def _discover_parameter_subsystems(base_dir: Path) -> Set[str]:
    return {
        path.name[: -len("_component_parameters.csv")]
        for path in sorted(base_dir.glob("*_component_parameters.csv"))
    }


def _normalize_quantity_key(value: str | None) -> str:
    """Normalize numeric strings so equivalent quantities map to the same key."""
    text = _clean(value)
    if text == "":
        return ""

    try:
        return format(float(text.replace(",", ".")), ".12g")
    except ValueError:
        return text.casefold()


def _normalized_part_mass_value(field: str, value: str | None) -> str:
    if field in {"Quantity_per_element", "L_mm", "W_mm", "H_mm", "Volume_cm3_excel"}:
        return _normalize_quantity_key(value)
    if field == "Has_datasheet_info":
        return "YES" if _to_yes_no(value) else "NO"
    return _clean(value).casefold()


def _is_m2_unit(value: str | None) -> bool:
    return _clean(value).lower() == "m2"


def _has_any_dimensions(row: Dict[str, str]) -> bool:
    return any(_clean(row.get(field)) != "" for field in PART_MASS_DIMENSION_FIELDS)


def _has_complete_dimensions(row: Dict[str, str]) -> bool:
    return all(_clean(row.get(field)) != "" for field in PART_MASS_DIMENSION_FIELDS)


def _component_reference(row: Dict[str, str]) -> Tuple[str, str]:
    designators = _clean(row.get("Designators")) or "no designator"
    part_number = _clean(row.get("Part_Number")) or "no part number"
    return designators, part_number


def _missing_mass_reason(row: Dict[str, str]) -> str | None:
    unit = _clean(row.get("unit"))
    if not _is_mass_unit(unit):
        return None

    has_datasheet_info = _to_yes_no(row.get("Has_datasheet_info"))
    quantity_per_element = _clean(row.get("Quantity_per_element"))

    if has_datasheet_info:
        if quantity_per_element == "":
            return "Has_datasheet_info=YES requires Quantity_per_element"
        return None

    has_complete_dimensions = _has_complete_dimensions(row)
    has_volume = _clean(row.get("Volume_cm3_excel")) != ""
    has_density = (
        _clean(row.get("Density_min_g_cm3")) != ""
        or _clean(row.get("Density_max_g_cm3")) != ""
    )

    missing_parts: List[str] = []
    if not has_complete_dimensions and not has_volume:
        if _has_any_dimensions(row):
            missing_parts.append("incomplete L_mm/W_mm/H_mm (or provide Volume_cm3_excel)")
        else:
            missing_parts.append("missing L_mm/W_mm/H_mm and Volume_cm3_excel")
    if not has_density:
        missing_parts.append("missing Density_min_g_cm3/Density_max_g_cm3")

    if missing_parts:
        return "; ".join(missing_parts)
    return None


def _part_mass_warning_fields(first_row: Dict[str, str], incoming_row: Dict[str, str]) -> Set[str]:
    differing: Set[str] = set()

    first_has_datasheet = _to_yes_no(first_row.get("Has_datasheet_info"))
    incoming_has_datasheet = _to_yes_no(incoming_row.get("Has_datasheet_info"))
    if first_has_datasheet != incoming_has_datasheet:
        differing.add("Has_datasheet_info")

    # Area components are excluded from mass warning comparisons.
    if _is_m2_unit(first_row.get("unit")) and _is_m2_unit(incoming_row.get("unit")):
        return differing

    if not (_is_mass_unit(first_row.get("unit")) and _is_mass_unit(incoming_row.get("unit"))):
        return differing

    if first_has_datasheet and incoming_has_datasheet:
        if _normalized_part_mass_value(
            "Quantity_per_element", first_row.get("Quantity_per_element")
        ) != _normalized_part_mass_value("Quantity_per_element", incoming_row.get("Quantity_per_element")):
            differing.add("Quantity_per_element")
        return differing

    if (not first_has_datasheet) and (not incoming_has_datasheet):
        first_uses_dimensions = _has_any_dimensions(first_row)
        incoming_uses_dimensions = _has_any_dimensions(incoming_row)

        if first_uses_dimensions or incoming_uses_dimensions:
            for field in PART_MASS_DIMENSION_FIELDS:
                if _normalized_part_mass_value(field, first_row.get(field)) != _normalized_part_mass_value(
                    field, incoming_row.get(field)
                ):
                    differing.add(field)
        else:
            if _normalized_part_mass_value(
                "Volume_cm3_excel", first_row.get("Volume_cm3_excel")
            ) != _normalized_part_mass_value("Volume_cm3_excel", incoming_row.get("Volume_cm3_excel")):
                differing.add("Volume_cm3_excel")

    return differing


def _row_match_key(row: Dict[str, str]) -> Tuple[str, ...]:
    return tuple(_clean(row.get(field)).casefold() for field in ROW_MATCH_FIELDS)


def _normalized_mass_value(field: str, value: str | None) -> str:
    text = _clean(value)
    if field in CASING_NUMERIC_FIELDS:
        return _normalize_quantity_key(text)
    if field == "Has_datasheet_info":
        return "YES" if _to_yes_no(text) else "NO"
    return text.casefold()


def _mass_field_matches(field: str, row_a: Dict[str, str], row_b: Dict[str, str]) -> bool:
    return _normalized_mass_value(field, row_a.get(field)) == _normalized_mass_value(field, row_b.get(field))


def _casing_mass_signature(row: Dict[str, str]) -> Tuple[str, ...]:
    return tuple(_normalized_mass_value(field, row.get(field)) for field in CASING_MASS_COMPARISON_FIELDS)


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
                merged_row = _normalize_ecoinvent_fields(dict(row))
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
    casing_variant_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]],
    part_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]],
    missing_section_warnings: List[Tuple[str, str, str]],
    missing_mass_data_warnings: List[Tuple[str, str, str, str]],
) -> None:
    if (
        not casing_conflicts
        and not casing_variant_conflicts
        and not part_conflicts
        and not missing_section_warnings
        and not missing_mass_data_warnings
    ):
        return

    print("Library merge warnings:")
    for kind, reference, source_file, folder in sorted(casing_conflicts):
        raw_fields = sorted(casing_conflicts[(kind, reference, source_file, folder)])
        fields = ", ".join(FIELD_LABELS.get(f, f) for f in raw_fields)
        print(
            f"- {kind} '{reference}' has different values across components. "
            f"Differing fields: {fields}. Source file: {source_file}. Folder: {folder}"
        )
    for casing in sorted(casing_variant_conflicts):
        casing_label, subsystems, diff_fields = casing_variant_conflicts[casing]
        fields = ", ".join(FIELD_LABELS.get(f, f) for f in sorted(diff_fields))
        subs_text = " and ".join(f"{s} subsystem" for s in sorted(subsystems))
        print(
            f"- Casing '{casing_label}' appears with multiple variants across components. "
            f"Differing fields: {fields}. Between {subs_text}."
        )
    for base_key in sorted(part_conflicts):
        reference, subsystems, diff_fields = part_conflicts[base_key]
        fields = ", ".join(FIELD_LABELS.get(f, f) for f in sorted(diff_fields))
        subs_text = " and ".join(f"{s} subsystem" for s in sorted(subsystems))
        print(
            f"- Part '{reference}' has different values across components. "
            f"Differing fields: {fields}. Between {subs_text}."
        )
    for subsystem, designators, part_number in sorted(missing_section_warnings):
        print(
            f"- Missing required Section. Subsystem: {subsystem}. "
            f"Element: {designators}. Part_Number: {part_number}."
        )
    for subsystem, designators, part_number, reason in sorted(missing_mass_data_warnings):
        print(
            f"- Missing mass inputs. Subsystem: {subsystem}. "
            f"Element: {designators}. Part_Number: {part_number}. Reason: {reason}."
        )


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_float(value: float) -> str:
    return format(value, ".12g")


def build_ecoinvent_totals_library(base_dir: Path) -> int:
    """Build one consolidated Ecoinvent library from all *_component_io_flows.csv files.

    Each output row represents one unique (Ecoinvent_flow, Ecoinvent_unit, Direction)
    across all subsystems, with:
    - Total_amount: summed in the original Ecoinvent unit
    - Total_mass_kg: summed only when unit is kg/g (blank otherwise)
    - Subsystems: comma-separated subsystem list where the flow appears
    """
    totals: Dict[Tuple[str, str, str], Dict[str, object]] = {}

    active_subsystems = _discover_parameter_subsystems(base_dir)

    for path in sorted(base_dir.glob("*_component_io_flows.csv")):
        subsystem = path.name[: -len("_component_io_flows.csv")]
        # Ignore orphan flow files from removed/renamed subsystems.
        if subsystem not in active_subsystems:
            continue

        parameter_path = base_dir / f"{subsystem}_component_parameters.csv"
        if parameter_path.exists() and path.stat().st_mtime < parameter_path.stat().st_mtime:
            # Prevent stale totals when parameters were edited but pipeline was not rerun.
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                normalized = _normalize_ecoinvent_fields(dict(row))
                database = _clean(normalized.get("Database"))
                flow = _clean(normalized.get("Ecoinvent_flow") or normalized.get("Flow"))
                unit = _clean(normalized.get("Ecoinvent_unit") or normalized.get("Unit"))
                direction = _clean(normalized.get("Direction"))
                amount_text = _clean(row.get("Amount"))

                # Keep only rows explicitly marked as EcoInvent.
                if database.casefold() != "ecoinvent":
                    continue

                if flow == "" or unit == "" or direction == "" or amount_text == "":
                    continue

                try:
                    amount = float(amount_text.replace(",", "."))
                except ValueError:
                    continue

                key = (flow, unit, direction)
                if key not in totals:
                    totals[key] = {
                        "Ecoinvent_flow": flow,
                        "Ecoinvent_unit": unit,
                        "Direction": direction,
                        "Total_amount": 0.0,
                        "Total_mass_kg": 0.0,
                        "Subsystems": set(),
                    }

                entry = totals[key]
                entry["Total_amount"] = float(entry["Total_amount"]) + amount

                unit_l = unit.lower()
                if unit_l == "kg":
                    entry["Total_mass_kg"] = float(entry["Total_mass_kg"]) + amount
                elif unit_l == "g":
                    entry["Total_mass_kg"] = float(entry["Total_mass_kg"]) + (amount / 1000.0)

                entry["Subsystems"].add(subsystem)

    rows: List[Dict[str, str]] = []
    for key in sorted(totals.keys(), key=lambda k: (k[0].casefold(), k[1].casefold(), k[2].casefold())):
        entry = totals[key]
        unit = str(entry["Ecoinvent_unit"])
        unit_l = unit.lower()
        mass_text = ""
        if unit_l in {"kg", "g"}:
            mass_text = _format_float(float(entry["Total_mass_kg"]))

        rows.append(
            {
                "Ecoinvent_flow": str(entry["Ecoinvent_flow"]),
                "Ecoinvent_unit": unit,
                "Direction": str(entry["Direction"]),
                "Total_amount": _format_float(float(entry["Total_amount"])),
                "Total_mass_kg": mass_text,
                "Subsystems": ", ".join(sorted(entry["Subsystems"])),
            }
        )

    _write_csv(base_dir / ECOINVENT_TOTALS_LIBRARY_NAME, ECOINVENT_TOTALS_FIELDS, rows)
    return len(rows)


def build_system_subsystem_library(
    base_dir: Path,
    raw_rows: List[Tuple[str, Dict[str, str]]],
) -> int:
    """Build a library of systems and their subsystems from parameter files.

    - System is read from `Section`.
    - Subsystem is read from `Subsection` (can be blank).
    - Source_subsystems stores the component parameter files where the pair appears.
    - Component_rows stores the total number of component rows for the pair.
    """
    pair_map: Dict[Tuple[str, str], Dict[str, object]] = {}

    for source_subsystem, row in raw_rows:
        system = _clean(row.get("Section"))
        subsystem = _clean(row.get("Subsection"))

        # Keep only valid system labels.
        if system == "":
            continue

        key = (system.casefold(), subsystem.casefold())
        if key not in pair_map:
            pair_map[key] = {
                "System": system,
                "Subsystem": subsystem,
                "Source_subsystems": set(),
                "Component_rows": 0,
            }

        entry = pair_map[key]
        entry["Source_subsystems"].add(source_subsystem)
        entry["Component_rows"] = int(entry["Component_rows"]) + 1

    rows: List[Dict[str, str]] = []
    for key in sorted(pair_map.keys(), key=lambda pair: (pair[0], pair[1])):
        entry = pair_map[key]
        rows.append(
            {
                "System": str(entry["System"]),
                "Subsystem": str(entry["Subsystem"]),
                "Source_subsystems": ", ".join(sorted(entry["Source_subsystems"])),
                "Component_rows": str(entry["Component_rows"]),
            }
        )

    _write_csv(base_dir / SYSTEM_SUBSYSTEM_LIBRARY_NAME, SYSTEM_SUBSYSTEM_FIELDS, rows)
    return len(rows)


def _load_library_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _normalize_part_number_key(part_number: str) -> str:
    return _clean(part_number).casefold()


def _to_yes_no(value: str | None) -> bool:
    return _clean(value).upper() in {"YES", "SI", "S", "Y", "M", "TRUE", "1", "T"}


def _is_mass_unit(value: str | None) -> bool:
    return _clean(value).lower() in {"kg", "g"}


def _resolved_sync_value(field: str, source_row: Dict[str, str]) -> str:
    if field != "Quantity_per_element":
        return _clean(source_row.get(field))

    unit = _clean(source_row.get("unit")).lower()
    has_datasheet_info = _to_yes_no(source_row.get("Has_datasheet_info"))
    has_area_dimensions = _clean(source_row.get("L_mm")) != "" and _clean(source_row.get("W_mm")) != ""

    # Keep inputs clean: calculated quantities must not be written back.
    if _is_mass_unit(unit) and not has_datasheet_info:
        return ""
    if unit == "m2" and has_area_dimensions:
        return ""

    return _clean(source_row.get(field))


def _apply_row_updates(
    target_row: Dict[str, str],
    source_row: Dict[str, str],
    fields: List[str],
) -> bool:
    changed = False
    for field in fields:
        if field not in target_row:
            continue
        new_value = _resolved_sync_value(field, source_row)
        old_value = _clean(target_row.get(field))

        # Never overwrite existing user values.
        # Sync acts as a "fill missing values" helper only.
        if old_value != "":
            continue

        if new_value == "":
            continue

        if old_value != new_value:
            target_row[field] = new_value
            changed = True
    return changed


def sync_parameter_files_from_libraries(base_dir: Path) -> Tuple[int, int, int]:
    """Apply library values to all *_component_parameters.csv files.

    Rows are updated only when Part_Number has a unique entry in the
    part-number library. If a Part_Number appears more than once in the
    library, that Part_Number is skipped to avoid ambiguous updates.

    When the match is unique, input fields are updated from the library,
    including identifying text fields like Manufacturer, Part_Number,
    Casing and Description.
    """
    part_rows = _load_library_rows(base_dir / PART_LIBRARY_NAME)

    if not part_rows:
        return 0, 0, 0

    part_index: Dict[str, List[Dict[str, str]]] = {}
    for row in part_rows:
        key = _normalize_part_number_key(row.get("Part_Number", ""))
        if key == "":
            continue
        part_index.setdefault(key, []).append(row)

    files_changed = 0
    rows_changed = 0
    skipped_ambiguous = 0

    for path in sorted(base_dir.glob("*_component_parameters.csv")):
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = [{key: value for key, value in dict(row).items() if key is not None} for row in reader]

        file_changed = False

        for row in rows:
            library_row = None
            sync_fields: List[str] = []

            part_key = _normalize_part_number_key(row.get("Part_Number", ""))
            if part_key != "":
                matches = part_index.get(part_key, [])
                if len(matches) == 1:
                    library_row = matches[0]
                    sync_fields = PART_SYNC_FIELDS
                elif len(matches) > 1:
                    skipped_ambiguous += 1

            if library_row is not None and _apply_row_updates(row, library_row, sync_fields):
                rows_changed += 1
                file_changed = True

        if file_changed:
            temp_path = path.with_suffix(path.suffix + ".tmp")
            with open(temp_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            temp_path.replace(path)
            files_changed += 1

    return files_changed, rows_changed, skipped_ambiguous


def build_libraries(base_dir: Path) -> Tuple[int, int, int, int]:
    """Rebuild both libraries from scratch on every call.

    Casing library:
            - Key: (Casing + all mass-calculation parameters)
            - Same mass parameters → deduplicate (one entry).
            - Different mass parameters for the same Casing → keep multiple entries.
            - Variant warning lists which mass parameters differ.

    Part-number library:
      - Key: (Manufacturer, Part_Number) + all PART_COMPARISON_FIELDS
      - All fields equal → one entry, no warning.
      - Same (Manufacturer, Part_Number) but any comparison field differs
        → BOTH entries kept + warning listing the differing fields.
    """
    raw_rows = _load_parameter_rows(base_dir)

    casing_map: Dict[Tuple[str, Tuple[str, ...]], Dict[str, str]] = {}
    # Part tracking: full dedup key → skip exact duplicates
    part_full_seen: set = set()
    # First added row per base key, used for diff comparison
    part_first_rows: Dict[str, Dict[str, str]] = {}
    part_rows_list: List[Dict[str, str]] = []
    part_subsystems: Dict[str, Set[str]] = {}

    casing_conflicts: Dict[Tuple[str, str, str, str], Set[str]] = {}
    casing_variant_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]] = {}
    casing_first_rows: Dict[str, Dict[str, str]] = {}
    casing_first_subsystem: Dict[str, str] = {}
    # base_key → (reference_label, subsystems_set, differing_fields_set)
    part_conflicts: Dict[str, Tuple[str, Set[str], Set[str]]] = {}
    missing_section_warnings: List[Tuple[str, str, str]] = []
    missing_mass_data_warnings: List[Tuple[str, str, str, str]] = []
    # First subsystem per base key
    part_first_subsystem: Dict[str, str] = {}
    conflict_count = 0
    folder_name = base_dir.name

    for subsystem, row in raw_rows:
        source_file = f"{subsystem}_component_parameters.csv"
        designators, part_reference = _component_reference(row)
        if _clean(row.get("Section")) == "":
            missing_section_warnings.append((subsystem, designators, part_reference))
            conflict_count += 1

        missing_mass_reason = _missing_mass_reason(row)
        if missing_mass_reason is not None:
            missing_mass_data_warnings.append((subsystem, designators, part_reference, missing_mass_reason))
            conflict_count += 1

        casing = _clean(row.get("Casing"))
        casing_signature = _casing_mass_signature(row)
        incoming_casing = _row_subset(row, CASING_FIELDS)

        if casing:
            casing_base_key = casing.casefold()
            casing_key = (casing_base_key, casing_signature)

            if casing_base_key in casing_first_rows:
                first_row = casing_first_rows[casing_base_key]
                differing: Set[str] = set()
                for field in CASING_MASS_COMPARISON_FIELDS:
                    if not _mass_field_matches(field, first_row, row):
                        differing.add(field)
                if differing:
                    if casing_base_key not in casing_variant_conflicts:
                        casing_variant_conflicts[casing_base_key] = (
                            casing,
                            {casing_first_subsystem[casing_base_key], subsystem},
                            differing,
                        )
                        conflict_count += 1
                    else:
                        _, existing_subsystems, existing_fields = casing_variant_conflicts[casing_base_key]
                        existing_subsystems.add(subsystem)
                        existing_fields.update(differing)
            else:
                casing_first_rows[casing_base_key] = dict(row)
                casing_first_subsystem[casing_base_key] = subsystem

            if casing_key not in casing_map:
                casing_map[casing_key] = incoming_casing
            else:
                # True duplicate in mass-calculation terms: keep one row and complete missing values.
                existing = casing_map[casing_key]
                for field, new_value in incoming_casing.items():
                    if _clean(existing.get(field)) == "" and new_value != "":
                        existing[field] = new_value

        part_number = _clean(row.get("Part_Number"))
        if part_number:
            manufacturer = _clean(row.get("Manufacturer"))
            base_key = f"{manufacturer.casefold()}::{part_number.casefold()}"
            part_subsystems.setdefault(base_key, set()).add(subsystem)
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
                differing = _part_mass_warning_fields(first_row, incoming_part)
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

    for row in part_rows_list:
        manufacturer = _clean(row.get("Manufacturer"))
        part_number = _clean(row.get("Part_Number"))
        base_key = f"{manufacturer.casefold()}::{part_number.casefold()}"
        subsystems = sorted(part_subsystems.get(base_key, set()))
        row["Subsystems"] = ", ".join(subsystems)

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
    build_ecoinvent_totals_library(base_dir)
    system_subsystem_count = build_system_subsystem_library(base_dir, raw_rows)

    _print_conflict_summary(
        casing_conflicts,
        casing_variant_conflicts,
        part_conflicts,
        missing_section_warnings,
        missing_mass_data_warnings,
    )

    return len(casing_rows), len(part_rows), conflict_count, system_subsystem_count


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1].strip().lower() in {"--sync-parameters", "sync"}:
        files_changed, rows_changed, skipped_ambiguous = sync_parameter_files_from_libraries(BASE_DIR)
        print(
            "Parameter sync completed"
            f": files_changed={files_changed}, rows_changed={rows_changed}, skipped_ambiguous={skipped_ambiguous}"
        )
        return

    casing_count, part_count, conflict_count, system_subsystem_count = build_libraries(BASE_DIR)
    print(f"Created {CASING_LIBRARY_NAME}: {casing_count} unique casing rows")
    print(f"Created {PART_LIBRARY_NAME}: {part_count} unique part-number rows")
    print(f"Created {SYSTEM_SUBSYSTEM_LIBRARY_NAME}: {system_subsystem_count} system/subsystem rows")
    print(f"Conflicts detected: {conflict_count}")


if __name__ == "__main__":
    main()
