"""
Role: Find components in the parameter library and component CSVs.

Brief: Search helpers used by converter tools and the CLI to locate component
definitions across CSVs and the parameter library.
"""

#!/usr/bin/env python3
"""Search for a part number across component parameter data.

Usage:
    python find_component.py <part_number> [scope]
    python find_component.py

Scope:
    - all (default): uses component_library_parameters_all.csv when available.
    - one or more subsystem names separated by spaces/commas.

Interactive mode defaults to all scope.

Output: matching rows printed as CSV lines ready to paste into a new component.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).parent
STORAGE_LIBRARY_NAME = "component_library_parameters_all.csv"

import logging
import sys

# interactive-safe output helper
_IS_TTY = sys.stdout.isatty()
# Purpose: Out.
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        getattr(logging, level)(msg)


# Purpose: Clean.
def _clean(value: object) -> str:
    return str(value or "").strip()


# Purpose: Prompt int choice.
def _prompt_int_choice(prompt: str, option_count: int, *, allow_cancel: bool = False) -> int | None:
    while True:
        raw = input(prompt).strip()
        if allow_cancel and not raw:
            return None
        try:
            idx = int(raw)
        except ValueError:
            idx = -1
        if 1 <= idx <= option_count:
            return idx
        _out("Invalid selection.", level="warning")


# Purpose: Discover subsystem files.
def _discover_subsystem_files() -> Dict[str, Path]:
    return {
        path.name[: -len("_component_parameters.csv")]: path
        for path in sorted(BASE_DIR.glob("*_component_parameters.csv"))
    }


# Purpose: Read fieldnames.
def _read_fieldnames(path: Path) -> List[str]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [field for field in list(reader.fieldnames or []) if field]


# Purpose: Parse scope.
def _parse_scope(scope_raw: str, subsystem_files: Dict[str, Path]) -> Optional[Set[str]]:
    """Return selected subsystem names, or None for all."""
    if _clean(scope_raw) == "":
        return None

    tokens = [tok for tok in _clean(scope_raw).replace(",", " ").split() if tok]
    if not tokens:
        return None

    if len(tokens) == 1 and tokens[0].casefold() in {"all", "*", "0", "todo", "todos"}:
        return None

    names_by_lower = {name.casefold(): name for name in subsystem_files.keys()}
    selected: Set[str] = set()
    unknown: List[str] = []

    for token in tokens:
        key = token.casefold()
        if key in names_by_lower:
            selected.add(names_by_lower[key])
        else:
            unknown.append(token)

    if unknown:
        raise ValueError(f"Unknown subsystem(s): {', '.join(unknown)}")

    return selected


# Purpose: Find part by scan.
def _find_part_by_scan(
    part_number: str,
    subsystem_files: Dict[str, Path],
    selected_subsystems: Optional[Set[str]],
) -> List[Tuple[str, List[str], Dict[str, str]]]:
    needle = _clean(part_number).casefold()
    results: List[Tuple[str, List[str], Dict[str, str]]] = []

    for subsystem, path in sorted(subsystem_files.items()):
        if selected_subsystems is not None and subsystem not in selected_subsystems:
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [field for field in list(reader.fieldnames or []) if field]
            for row in reader:
                if _clean(row.get("Part_Number")).casefold() == needle:
                    results.append((subsystem, fieldnames, dict(row)))

    return results


# Purpose: Find part in storage library.
def _find_part_in_storage_library(
    part_number: str,
    subsystem_files: Dict[str, Path],
    selected_subsystems: Optional[Set[str]],
) -> Optional[List[Tuple[str, List[str], Dict[str, str]]]]:
    """Search in full-storage library and return source-compatible rows.

    Returns:
    - None when storage library is unavailable or incompatible.
    - [] or matches list when search executed against the storage library.
    """
    storage_path = BASE_DIR / STORAGE_LIBRARY_NAME
    if not storage_path.exists():
        return None

    try:
        with open(storage_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            storage_fields = [field for field in list(reader.fieldnames or []) if field]
            if "Part_Number" not in storage_fields or "Subsystem" not in storage_fields:
                return None

            subsystem_headers: Dict[str, List[str]] = {}
            for subsystem, path in subsystem_files.items():
                subsystem_headers[subsystem] = _read_fieldnames(path)

            needle = _clean(part_number).casefold()
            results: List[Tuple[str, List[str], Dict[str, str]]] = []

            for row in reader:
                subsystem = _clean(row.get("Subsystem"))
                if subsystem == "" or subsystem not in subsystem_files:
                    continue
                if selected_subsystems is not None and subsystem not in selected_subsystems:
                    continue
                if _clean(row.get("Part_Number")).casefold() != needle:
                    continue

                source_fieldnames = subsystem_headers.get(subsystem) or []
                if not source_fieldnames:
                    continue

                projected_row = {field: _clean(row.get(field)) for field in source_fieldnames}
                results.append((subsystem, source_fieldnames, projected_row))

            return results
    except Exception as exc:
        # If any error occurs reading the storage library, treat it as unavailable.
        return None


# Purpose: Find part.
def find_part(part_number: str, scope_raw: str) -> Tuple[List[Tuple[str, List[str], Dict[str, str]]], str]:
    """Return matching rows and search mode used (library or scan)."""
    subsystem_files = _discover_subsystem_files()
    if not subsystem_files:
        return [], "scan"

    selected_subsystems = _parse_scope(scope_raw, subsystem_files)

    library_results = _find_part_in_storage_library(part_number, subsystem_files, selected_subsystems)
    if library_results is not None:
        return library_results, "library"

    return _find_part_by_scan(part_number, subsystem_files, selected_subsystems), "scan"


# Purpose: Row to csv line.
def _row_to_csv_line(fieldnames: List[str], row: Dict[str, str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="")
    writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buf.getvalue()


# Purpose: Collect display fieldnames.
def _collect_display_fieldnames(results: List[Tuple[str, List[str], Dict[str, str]]]) -> List[str]:
    """Return a unified ordered list of columns across all matching rows."""
    ordered: List[str] = ["Subsystem"]
    for _, fieldnames, _ in results:
        for field in fieldnames:
            if field == "Subsystem":
                continue
            if field not in ordered:
                ordered.append(field)
    return ordered


# Purpose: Display results.
def _display_results(results: List[Tuple[str, List[str], Dict[str, str]]], mode: str) -> None:
    _out(f"\nFound {len(results)} row(s) using {mode} search.\n")
    display_fieldnames = _collect_display_fieldnames(results)
    last_subsystem = None
    for subsystem, _, row in results:
        if subsystem != last_subsystem:
            _out(f"--- {subsystem} ---")
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=display_fieldnames, lineterminator="")
            writer.writeheader()
            _out(buf.getvalue())
            last_subsystem = subsystem
        display_row = dict(row)
        display_row["Subsystem"] = subsystem
        _out(_row_to_csv_line(display_fieldnames, display_row))


# Purpose: Rows match by fieldnames.
def _rows_match_by_fieldnames(
    candidate_row: Dict[str, str],
    reference_row: Dict[str, str],
    fieldnames: List[str],
) -> bool:
    for field in fieldnames:
        if _clean(candidate_row.get(field)) != _clean(reference_row.get(field)):
            return False
    return True


# Purpose: Sanitize row for write.
def _sanitize_row_for_write(row: Dict[str, str], fieldnames: List[str]) -> Dict[str, str]:
    """Return a row containing only known columns, with cleaned string values."""
    return {field: _clean(row.get(field, "")) for field in fieldnames}


# Purpose: Update csv row.
def _update_csv_row(
    subsystem: str,
    fieldnames: List[str],
    old_row: Dict[str, str],
    field_name: str,
    new_value: str,
) -> bool:
    """Update a specific field in a subsystem component-parameter CSV file."""
    csv_path = BASE_DIR / f"{subsystem}_component_parameters.csv"
    if not csv_path.exists():
        _out(f"Could not find source file: {csv_path.name}", level="warning")
        return False

    rows_to_write: List[Dict[str, str]] = []
    found = False

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        source_fieldnames = [field for field in list(reader.fieldnames or fieldnames) if field]

        if field_name not in source_fieldnames:
            _out(f"Field {field_name} not found in {csv_path.name}.", level="warning")
            return False

        for row in reader:
            row_dict = dict(row)
            if not found and _rows_match_by_fieldnames(row_dict, old_row, source_fieldnames):
                row_dict[field_name] = new_value
                found = True
            rows_to_write.append(_sanitize_row_for_write(row_dict, source_fieldnames))

    if not found:
        _out("Could not find the exact row to update.", level="warning")
        return False

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=source_fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)

    _out(f"Updated {field_name} to '{new_value}' in {csv_path.name}")
    return True


# Purpose: Update storage library row.
def _update_storage_library_row(
    subsystem: str,
    fieldnames: List[str],
    reference_row: Dict[str, str],
    field_name: str,
    new_value: str,
) -> int:
    """Update master library row to match source file change."""
    storage_path = BASE_DIR / STORAGE_LIBRARY_NAME
    if not storage_path.exists():
        return 0

    rows_to_write: List[Dict[str, str]] = []
    updated_count = 0

    try:
        with open(storage_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            storage_fieldnames = [field for field in list(reader.fieldnames or []) if field]

            if field_name not in storage_fieldnames:
                return 0

            match_fields = [field for field in fieldnames if field in storage_fieldnames and field != "Subsystem"]

            for row in reader:
                row_dict = dict(row)
                same_subsystem = _clean(row_dict.get("Subsystem")) == subsystem
                same_component = all(
                    _clean(row_dict.get(field)) == _clean(reference_row.get(field))
                    for field in match_fields
                )
                if same_subsystem and same_component:
                    row_dict[field_name] = new_value
                    updated_count += 1
                rows_to_write.append(_sanitize_row_for_write(row_dict, storage_fieldnames))

        if updated_count == 0:
            return 0

        with open(storage_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=storage_fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_write)

        return updated_count
    except Exception as exc:
        logging.exception("Bulk update failed: %s", exc)
        return 0


# Purpose: Bulk update all rows.
def _bulk_update_all_rows(results: List[Tuple[str, List[str], Dict[str, str]]]) -> None:
    """Update one or more fields in all found rows."""
    _out("\n" + "=" * 80)
    _out("BULK UPDATE (ALL ROWS)")
    _out("=" * 80)

    all_fields: List[str] = []
    for _, fieldnames, _ in results:
        for field in fieldnames:
            if field not in all_fields:
                all_fields.append(field)

    for idx, field in enumerate(all_fields, 1):
        _out(f"[{idx}] {field}")

    selection = input("Choose field number(s) to update in all rows (for example 3 or 3,4,10): ").strip()
    if not selection:
        _out("No fields selected.", level="warning")
        return

    selected_fields: List[str] = []
    for token in selection.split(","):
        value = token.strip()
        if not value.isdigit():
            _out("Invalid selection.", level="warning")
            return
        field_idx = int(value)
        if not 1 <= field_idx <= len(all_fields):
            _out("Invalid selection.", level="warning")
            return
        field_name = all_fields[field_idx - 1]
        if field_name not in selected_fields:
            selected_fields.append(field_name)

    updates: Dict[str, str] = {}
    for field_name in selected_fields:
        updates[field_name] = input(f"New value for {field_name}: ").strip()

    total_field_updates = 0
    updated_rows = 0
    storage_updates = 0
    changed_operations: List[Tuple[str, List[str], Dict[str, str], str, str]] = []

    for subsystem, fieldnames, row in results:
        row_updated = False
        for field_name, new_value in updates.items():
            if field_name not in fieldnames:
                continue
            current_value = _clean(row.get(field_name, ""))
            if new_value == current_value:
                continue
            reference_row = dict(row)
            if _update_csv_row(subsystem, fieldnames, row, field_name, new_value):
                row[field_name] = new_value
                total_field_updates += 1
                row_updated = True
                changed_operations.append((subsystem, fieldnames, reference_row, field_name, new_value))

        if row_updated:
            updated_rows += 1

    _out(f"\nApplied {total_field_updates} field update(s) across {updated_rows} row(s).")

    if updated_rows > 0:
        sync_response = input("\nUpdate master library for all changed rows? (yes/y): ").strip().lower()
        if sync_response in {"yes", "y"}:
            for subsystem, fieldnames, reference_row, field_name, new_value in changed_operations:
                storage_updates += _update_storage_library_row(
                    subsystem,
                    fieldnames,
                    reference_row,
                    field_name,
                    new_value,
                )
            _out(f"✓ Master library synchronized: {storage_updates} field(s) updated.")
        else:
            _out("Master library not updated. Source files only.")


# Purpose: Interactive edit.
def _interactive_edit(results: List[Tuple[str, List[str], Dict[str, str]]]) -> None:
    """Allow user to edit fields in the found components."""
    display_fieldnames = _collect_display_fieldnames(results)

    while True:
        change_response = input("\nDo you want to change something? (yes/y): ").strip().lower()
        if change_response not in {"yes", "y"}:
            _out("No changes made. Exiting.")
            return

        _out("\n" + "=" * 80)
        _out("SELECT WHICH ROW TO MODIFY")
        _out("=" * 80)
        for idx, (subsystem, _, row) in enumerate(results, 1):
            _out(f"\n[{idx}] {subsystem}:")
            _out(_row_to_csv_line(display_fieldnames, row))

        row_choice = input(f"\nEnter row number to modify (1-{len(results)}) or 'all': ").strip()

        if row_choice.casefold() == "all":
            _bulk_update_all_rows(results)
            another = input("\nMake another change? (yes/y): ").strip().lower()
            if another not in {"yes", "y"}:
                _out("Done. Exiting.")
                break
            continue

        row_idx = _prompt_int_choice(f"\nEnter row number to modify (1-{len(results)}): ", len(results))
        if row_idx is None:
            continue
        row_idx -= 1
        if not 0 <= row_idx < len(results):
            _out("Invalid selection.", level="warning")
            continue

        subsystem, fieldnames, row = results[row_idx]

        _out("\n" + "=" * 80)
        _out("AVAILABLE FIELDS TO CHANGE")
        _out("=" * 80)
        for col_idx, field in enumerate(fieldnames, 1):
            current_value = _clean(row.get(field, ""))
            _out(f"[{col_idx}] {field}: '{current_value}'")

        field_idx = _prompt_int_choice(f"\nEnter field number to modify (1-{len(fieldnames)}): ", len(fieldnames))
        if field_idx is None:
            continue
        field_idx -= 1
        if not 0 <= field_idx < len(fieldnames):
            _out("Invalid selection.", level="warning")
            continue

        field_name = fieldnames[field_idx]
        current_value = _clean(row.get(field_name, ""))

        _out(f"\nCurrent value: '{current_value}'")
        new_value = input(f"Enter new value for {field_name}: ").strip()

        if new_value == current_value:
            _out("Value is the same. No changes made.")
            continue

        reference_row = dict(row)
        if _update_csv_row(subsystem, fieldnames, row, field_name, new_value):
            row[field_name] = new_value
            _out("\nChange saved successfully in source file.")
            
            # Ask if user wants to sync to master library
            sync_response = input("Update master library as well? (yes/y): ").strip().lower()
            if sync_response in {"yes", "y"}:
                synced = _update_storage_library_row(
                    subsystem,
                    fieldnames,
                    reference_row,
                    field_name,
                    new_value,
                )
                if synced > 0:
                    _out(f"✓ Master library synchronized for {subsystem} ({synced} row(s)).")
                else:
                    _out("⚠ Master library not updated (may not exist or component not found).", level="warning")

        another = input("\nMake another change? (yes/y): ").strip().lower()
        if another not in {"yes", "y"}:
            _out("Done. Exiting.")
            break


# Purpose: Main.
def main() -> None:
    if len(sys.argv) > 1:
        part_number = _clean(sys.argv[1])
        scope_raw = " ".join(sys.argv[2:])
    else:
        part_number = input("Enter Part_Number to search: ").strip()
        scope_raw = ""

    if not part_number:
        _out("No part number provided.")
        return

    try:
        results, mode = find_part(part_number, scope_raw)
    except ValueError as exc:
        _out(f"Invalid scope: {exc}", level="warning")
        return

    if not results:
        _out(f"No rows found for Part_Number '{part_number}'.")
        return

    _display_results(results, mode)
    _interactive_edit(results)


if __name__ == "__main__":
    main()
