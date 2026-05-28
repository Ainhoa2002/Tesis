"""
Role: Add or remove components from the Mexico converter component set.

Brief: CLI helpers to include or exclude components when building converter
product systems or generating IPE files.
"""

#!/usr/bin/env python3
"""
add_eliminate_component.py
Current scope:
1) Discover subsystem parameter CSV files.
2) Let user choose one subsystem.
3) Add, update, or eliminate components interactively.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import logging

# interactive-safe output helper
_IS_TTY = sys.stdout.isatty()
# Purpose: Out.
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        getattr(logging, level)(msg)


BASE_DIR = Path(__file__).parent
AUDIT_LOG = BASE_DIR / "add_eliminate_component_audit.log"
MAX_SELECTION_ATTEMPTS = 3


class SelectionAborted(RuntimeError):
    pass


class SaveVerificationError(RuntimeError):
    pass


# Purpose: Fail or abort selection.
def fail_or_abort_selection(attempts: int) -> None:
    _out("Invalid selection. Try again.", level="warning")
    if attempts >= MAX_SELECTION_ATTEMPTS:
        raise SelectionAborted("Too many invalid attempts. Operation canceled.")


# Purpose: Prompt menu choice.
def _prompt_menu_choice(prompt: str, choices: Dict[str, str], invalid_message: str) -> str:
    attempts = 0
    while True:
        raw = input(prompt).strip().lower()
        if raw in choices:
            return choices[raw]
        attempts += 1
        _out(invalid_message, level="warning")
        if attempts >= MAX_SELECTION_ATTEMPTS:
            raise SelectionAborted("Too many invalid attempts. Operation canceled.")


# Purpose: Prompt index choice.
def _prompt_index_choice(prompt: str, option_count: int, *, allow_cancel: bool = False) -> int | None:
    attempts = 0
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
        attempts += 1
        fail_or_abort_selection(attempts)

KEY_FIELD_ORDER = [
    "Designators",
    "Casing",
    "Section",
    "Subsection",
    "Category",
    "Manufacturer",
    "Part_Number",
    "Description",
    "number_elements",
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
    "mass_space_relation_m2/kg",
    "Database",
    "Ecoinvent_flow",
    "Ecoinvent_unit",
    "Direction",
    "Ecoinvent_amount_override",
    "Comments",
    "Notes",
]

AUTO_FIELDS = {
    "Order_index",
    "Category_order",
    "Group_order",
    "Total_quantity",
    "Datasheet_required_flag",
    "Mass_datasheet_g",
    "Scale_with_mass_flag",
    "Other_possible_models",
    "Reliability",
    "Completeness",
    "Temporal_correlation",
}

FIELD_EXAMPLES = {
    "Designators": "R1, R2",
    "Casing": "TO-220, SOIC-8, 1206",
    "Section": "Passives",
    "Subsection": "Resistors",
    "Category": "AUTO",
    "Manufacturer": "Infineon",
    "Part_Number": "IKW25N120H3",
    "Description": "1200V 50A IGBT",
    "number_elements": "4",
    "unit": "kg",
    "Quantity_per_element": "0.0001",
    "Has_datasheet_info": "YES",
    "L_mm": "10",
    "W_mm": "5",
    "H_mm": "2",
    "Volume_cm3_excel": "0.1",
    "Density_min_g_cm3": "1.2",
    "Density_max_g_cm3": "1.4",
    "Metal_extra_g": "0.01",
    "mass_space_relation_m2/kg": "",
    "Database": "EcoInvent",
    "Ecoinvent_flow": "integrated circuit production, logic type",
    "Ecoinvent_unit": "kg",
    "Direction": "Input",
    "Ecoinvent_amount_override": "0.5",
}


# Purpose: Prompt label with example.
def prompt_label_with_example(header: str) -> str:
    if header in {"Comments", "Notes"}:
        return header
    example = FIELD_EXAMPLES.get(header)
    if not example:
        return header
    return f"{header} (e.g. {example})"


# Purpose: Choose mode.
def choose_mode() -> str:
    _out("\nWhat do you want to edit?")
    _out("  1. Component parameters")
    _out("  2. I/O flows")
    return _prompt_menu_choice(
        "Mode [1/2]: ",
        {
            "1": "parameters",
            "parameters": "parameters",
            "params": "parameters",
            "p": "parameters",
            "component": "parameters",
            "2": "io",
            "io": "io",
            "i/o": "io",
            "flows": "io",
            "i": "io",
        },
        "Invalid option. Enter 1 or 2.",
    )


# Purpose: Discover csv files.
def discover_csv_files(base_dir: Path, suffix: str) -> Dict[str, Path]:
    return {
        p.name[: -len(suffix)]: p
        for p in sorted(base_dir.glob(f"*{suffix}"))
    }


# Kept as aliases so external callers (export_to_excel, etc.) continue to work.
def discover_subsystem_files(base_dir: Path) -> Dict[str, Path]:
    return discover_csv_files(base_dir, "_component_parameters.csv")


# Purpose: Discover io files.
def discover_io_files(base_dir: Path) -> Dict[str, Path]:
    return discover_csv_files(base_dir, "_io.csv")


# Purpose: Choose from mapping.
def choose_from_mapping(mapping: Dict[str, Path], label: str, empty_error: str) -> Tuple[str, Path]:
    # Presents a numbered list and returns the chosen (name, path) pair.
    names = list(mapping.keys())
    if not names:
        raise RuntimeError(empty_error)

    names_by_lower = {name.lower(): name for name in names}

    _out(f"Available {label}:")
    for i, name in enumerate(names, start=1):
        _out(f"  {i}. {name}")

    attempts = 0
    while True:
        raw = input(f"Choose {label} number or name: ").strip()
        if not raw:
            attempts += 1
            fail_or_abort_selection(attempts)
            continue

        if raw in mapping:
            return raw, mapping[raw]

        lowered = raw.lower()
        if lowered in names_by_lower:
            chosen = names_by_lower[lowered]
            return chosen, mapping[chosen]

        try:
            idx = int(raw)
        except ValueError:
            idx = -1

        if 1 <= idx <= len(names):
            chosen = names[idx - 1]
            return chosen, mapping[chosen]

        attempts += 1
        fail_or_abort_selection(attempts)


# Kept as aliases so external callers continue to work.
def choose_subsystem(subsystems: Dict[str, Path]) -> Tuple[str, Path]:
    return choose_from_mapping(subsystems, "subsystems", "No *_component_parameters.csv files found in this folder.")


# Purpose: Choose io file.
def choose_io_file(io_files: Dict[str, Path]) -> Tuple[str, Path]:
    return choose_from_mapping(io_files, "I/O files", "No *_io.csv files found in this folder.")

# Loads the CSV file and returns headers (categories) and rows (info inside the categories). 
def load_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = list(reader.fieldnames or [])

    if not headers:
        raise RuntimeError(f"CSV has no headers: {path}")

    return headers, rows


# Purpose: Normalize text.
def normalize_text(value: str) -> str:
    return value.strip().lower()


# Purpose: Prompt yes no.
def prompt_yes_no(message: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        raw = input(message + suffix).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "ys", "s", "si", "true", "t", "1"}:
            return True
        if raw in {"n", "no", "false", "f"}:
            return False
        _out("Please answer y or n.", level="warning")


# Purpose: Choose action.
def choose_action() -> str:
    _out("\nChoose action:")
    _out("  1. Add or update component")
    _out("  2. Eliminate component")
    return _prompt_menu_choice(
        "Action [1/2]: ",
        {
            "1": "add_update",
            "add": "add_update",
            "update": "add_update",
            "a": "add_update",
            "u": "add_update",
            "2": "delete",
            "delete": "delete",
            "eliminate": "delete",
            "remove": "delete",
            "d": "delete",
            "e": "delete",
            "r": "delete",
        },
        "Invalid action. Choose 1 or 2.",
    )

# Purpose: Find row index.
def find_row_index(rows: List[Dict[str, str]], field: str, value: str) -> int:
    #Returns the index of the first row where row[field] matches value, or -1.
    target = normalize_text(value)
    for i, row in enumerate(rows):
        if normalize_text(row.get(field, "")) == target:
            return i
    return -1


# Kept as alias so existing call sites keep working.
def find_row_index_by_designators(rows: List[Dict[str, str]], designators: str) -> int:
    return find_row_index(rows, "Designators", designators)

#it prints the information of the component.
def print_component_preview(row: Dict[str, str], headers: List[str]) -> None:
    preview_order = [
        "Designators",
        "Casing",
        "Manufacturer",
        "Part_Number",
        "Description",
        "Ecoinvent_unit",
        "Ecoinvent_flow",
    ]
    _out("\nCurrent component preview:")
    for field in preview_order:
        if field in headers:
            _out(f"  {field}: {row.get(field, '')}")


# Purpose: Component label.
def component_label(row: Dict[str, str]) -> str:
    designators = row.get("Designators", "")
    casing = row.get("Casing", "")
    manufacturer = row.get("Manufacturer", "")
    part_number = row.get("Part_Number", "")
    description = row.get("Description", "")
    if len(description) > 60:
        description = description[:57] + "..."
    return f"{designators} | {casing} | {manufacturer} | {part_number} | {description}"


# Purpose: Choose search field.
def choose_search_field(headers: List[str]) -> str | None:
    preferred_fields = [
        "Designators",
        "Casing",
        "Manufacturer",
        "Part_Number",
        "Description",
        "Ecoinvent_flow",
        "Comments",
        "Notes",
    ]
    searchable_fields = [field for field in preferred_fields if field in headers]
    if not searchable_fields:
        return None

    _out("\nChoose section/field to search:")
    for i, field in enumerate(searchable_fields, start=1):
        _out(f"  {i}. {field}")

    idx = _prompt_index_choice("Field number: ", len(searchable_fields))
    return searchable_fields[idx - 1] if idx is not None else None


# Purpose: Search component indices.
def search_component_indices(rows: List[Dict[str, str]], field: str, keyword: str) -> List[int]:
    target = normalize_text(keyword)
    matches: List[int] = []
    for i, row in enumerate(rows):
        value = normalize_text(str(row.get(field, "")))
        if target in value:
            matches.append(i)
    return matches


# Purpose: Choose component from candidates.
def choose_component_from_candidates(rows: List[Dict[str, str]], candidate_indices: List[int], title: str) -> int | None:
    if not candidate_indices:
        return None

    _out(f"\n{title}")
    for i, row_idx in enumerate(candidate_indices, start=1):
        _out(f"  {i}. {component_label(rows[row_idx])}")

    idx = _prompt_index_choice("Choose component number (Enter to cancel): ", len(candidate_indices), allow_cancel=True)
    if idx is None:
        return None
    return candidate_indices[idx - 1]


# Purpose: Find component for delete.
def find_component_for_delete(headers: List[str], rows: List[Dict[str, str]]) -> int:
    while True:
        reference = input("Enter component reference (Designators). Press Enter if unknown: ").strip()
        if reference:
            idx = find_row_index_by_designators(rows, reference)
            if idx >= 0:
                return idx
            _out("Component not found by Designators.", level="warning")

        preview_indices = list(range(len(rows)))
        selected = choose_component_from_candidates(
            rows,
            preview_indices,
            f"Component list ({len(rows)} total):",
        )
        if selected is not None:
            return selected

        if not prompt_yes_no("Search by keyword in a selected section?", default=True):
            return -1

        field = choose_search_field(headers)
        if not field:
            _out("No searchable fields available.", level="warning")
            return -1

        keyword = input(f"Keyword for {field}: ").strip()
        if not keyword:
            _out("Keyword cannot be empty.", level="warning")
            continue

        matches = search_component_indices(rows, field, keyword)
        if not matches:
            _out("Not found relevant info.", level="warning")
            continue

        top_matches = matches[:5]
        selected = choose_component_from_candidates(
            rows,
            top_matches,
            f"Found {len(matches)} matches. Showing top {len(top_matches)}:",
        )
        if selected is not None:
            return selected

        if not prompt_yes_no("Try another search?", default=True):
            return -1

#It prompts the user to enter the information of the component, if the component already exist it shows the current information and ask if you want to modify it, if you want to modify it, it will ask for each field, if not it will keep the current value. If the component does not exist, it will ask for all the fields.
def prompt_component_row(
    headers: List[str],
    designators: str,
    existing_row: Dict[str, str] | None = None,
) -> Dict[str, str]:
    is_update = existing_row is not None
    if is_update:
        new_row = {header: (existing_row.get(header, "") or "") for header in headers}
    else:
        new_row = {header: "" for header in headers}

    if "Designators" in new_row:
        new_row["Designators"] = designators

    ordered_headers = [h for h in KEY_FIELD_ORDER if h in headers]
    ordered_headers.extend([h for h in headers if h not in ordered_headers and h not in AUTO_FIELDS])

    for header in ordered_headers:
        current_value = new_row.get(header, "")
        label = prompt_label_with_example(header)
        prompt = f"{label} [{current_value}]: " if current_value else f"{label}: "
        user_value = input(prompt).strip()

        if user_value == "__blank__":
            new_row[header] = ""
        elif user_value:
            new_row[header] = user_value

    # Section is required; Subsection is optional.
    if "Section" in headers:
        while not str(new_row.get("Section", "")).strip():
            new_row["Section"] = input("Section is required (e.g. Passives): ").strip()

    return new_row

# Purpose: Find row index by flow.
def find_row_index_by_flow(rows: List[Dict[str, str]], flow: str) -> int:
    return find_row_index(rows, "Flow", flow)


# Purpose: Prompt io row.
def prompt_io_row(
    headers: List[str],
    existing_row: Dict[str, str] | None = None,
) -> Dict[str, str]:
    is_update = existing_row is not None
    new_row = {header: existing_row.get(header, "") if is_update else "" for header in headers}

    for header in headers:
        current_value = new_row.get(header, "")
        prompt = f"{header} [{current_value}]: " if current_value else f"{header}: "
        user_value = input(prompt).strip()

        if user_value == "__blank__":
            new_row[header] = ""
        elif user_value:
            new_row[header] = user_value

    # Flow is the key field and is required.
    while not str(new_row.get("Flow", "")).strip():
        new_row["Flow"] = input("Flow is required: ").strip()

    return new_row


# Purpose: Io row label.
def io_row_label(row: Dict[str, str]) -> str:
    flow = row.get("Flow", "")
    unit = row.get("Unit", "")
    amount = row.get("Amount", "")
    direction = row.get("Direction", "")
    label = flow if len(flow) <= 70 else flow[:67] + "..."
    return f"{label} | {unit} | {amount} | {direction}"


# Purpose: Find io row for delete.
def find_io_row_for_delete(headers: List[str], rows: List[Dict[str, str]]) -> int:
    while True:
        keyword = input("Enter keyword to search in Flow (or Enter to list all): ").strip()

        if keyword:
            matches = [i for i, row in enumerate(rows)
                       if normalize_text(keyword) in normalize_text(row.get("Flow", ""))]
        else:
            matches = list(range(len(rows)))

        if not matches:
            _out("No matching flows found.", level="warning")
            if not prompt_yes_no("Try again?", default=True):
                return -1
            continue

        _out(f"\nFound {len(matches)} flow(s):")
        for i, row_idx in enumerate(matches, start=1):
            _out(f"  {i}. {io_row_label(rows[row_idx])}")

        idx = _prompt_index_choice("Choose number to delete (Enter to cancel): ", len(matches), allow_cancel=True)
        if idx is None:
            return -1
        return matches[idx - 1]


#Saves the CSV file directly (no automatic backup files).
def save_csv(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    # Keep BOM for better compatibility when opening edited CSVs with Excel.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# Purpose: Verify saved row.
def verify_saved_row(path: Path, key_field: str, key_value: str) -> Tuple[bool, int]:
    """Reload file and verify the target key value exists after save."""
    _, persisted_rows = load_csv(path)
    target = normalize_text(key_value)
    exists = any(normalize_text(str(row.get(key_field, ""))) == target for row in persisted_rows)
    return exists, len(persisted_rows)


# Purpose: Append audit log.
def append_audit_log(
    csv_path: Path,
    action: str,
    key_field: str,
    key_value: str,
    expected_present: bool,
    found_present: bool,
    row_count: int,
    status: str,
) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    expected = "present" if expected_present else "absent"
    found = "present" if found_present else "absent"
    line = (
        f"[{timestamp}] {status} action={action} file={csv_path.resolve()} "
        f"{key_field}='{key_value}' expected={expected} found={found} rows={row_count}\n"
    )
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(line)


# Purpose: Auto refresh component libraries.
def _auto_refresh_component_libraries(
    base_dir: Path,
    reason: str,
    warning_scope_subsystems: set[str] | None = None,
) -> None:
    """Refresh deduplicated libraries unless explicitly disabled.

    Set MASS_CALC_AUTO_REFRESH_LIBRARIES=0 to skip automatic refresh.
    """
    enabled = str(os.getenv("MASS_CALC_AUTO_REFRESH_LIBRARIES", "1")).strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        _out("Library refresh skipped: MASS_CALC_AUTO_REFRESH_LIBRARIES is disabled.", level="info")
        return

    try:
        try:
            from .build_component_libraries import build_libraries
        except ImportError:
            from build_component_libraries import build_libraries

        (
            casing_count,
            part_count,
            conflict_count,
            system_subsystem_count,
            parameters_storage_count,
            results_storage_count,
        ) = build_libraries(base_dir, warning_scope_subsystems)
        _out(
            "Library refresh completed"
            f" ({reason}): casing={casing_count}, part_number={part_count}, "
            f"systems_subsystems={system_subsystem_count}, "
            f"storage_parameters={parameters_storage_count}, "
            f"storage_results={results_storage_count}, "
            f"conflicts={conflict_count}",
            level="info",
        )
    except Exception as exc:
        _out(f"Warning: library refresh failed ({reason}): {exc}", level="warning")


# Purpose: Run parameters workflow.
def _run_parameters_workflow() -> None:
    subsystems = discover_csv_files(BASE_DIR, "_component_parameters.csv")
    subsystem_name, csv_path = choose_from_mapping(subsystems, "subsystems", "No *_component_parameters.csv files found in this folder.")

    headers, rows = load_csv(csv_path)

    _out("\nSelection summary")
    _out(f"Subsystem: {subsystem_name}")
    _out(f"File: {csv_path.name}")
    _out(f"Columns: {len(headers)}")
    _out(f"Rows: {len(rows)}")

    action_mode = choose_action()
    verification_key = ""
    should_exist_after_save = False

    if action_mode == "delete":
        row_index = find_component_for_delete(headers, rows)
        if row_index < 0:
            _out("No changes made.", level="info")
            return

        existing_row = rows[row_index]
        verification_key = str(existing_row.get("Designators", "")).strip()
        print_component_preview(existing_row, headers)
        if not prompt_yes_no("Confirm eliminate component?", default=False):
            _out("No changes made.", level="info")
            return

        del rows[row_index]
        action = "deleted"
        should_exist_after_save = False
    else:
        while True:
            designators = input("Enter Designators to add or update: ").strip()
            if designators:
                break
            _out("Designators cannot be empty.", level="warning")

        row_index = find_row_index(rows, "Designators", designators)

        if row_index >= 0:
            existing_row = rows[row_index]
            print_component_preview(existing_row, headers)
            if not prompt_yes_no("Component exists. Update this row?", default=True):
                _out("No changes made.", level="info")
                return

            rows[row_index] = prompt_component_row(
                headers=headers,
                designators=designators,
                existing_row=existing_row,
            )
            verification_key = str(rows[row_index].get("Designators", designators)).strip() or designators
            action = "updated"
        else:
            _out("Component not found. Creating a new row.", level="info")
            new_row = prompt_component_row(
                headers=headers,
                designators=designators,
                existing_row=None,
            )
            rows.append(new_row)
            verification_key = str(new_row.get("Designators", designators)).strip() or designators
            action = "added"
        should_exist_after_save = True

    save_csv(csv_path, headers, rows)
    exists_after_save, persisted_count = verify_saved_row(csv_path, "Designators", verification_key)
        if verification_key:
        state_ok = exists_after_save == should_exist_after_save
        status = "OK" if state_ok else "FAIL"
        expected = "present" if should_exist_after_save else "absent"
        found = "present" if exists_after_save else "absent"
        append_audit_log(
            csv_path=csv_path,
            action=action,
            key_field="Designators",
            key_value=verification_key,
            expected_present=should_exist_after_save,
            found_present=exists_after_save,
            row_count=persisted_count,
            status=status,
        )
        if not state_ok:
            raise SaveVerificationError(
                f"Save verification FAILED for Designators='{verification_key}'. "
                f"Expected {expected}, found {found}. File: {csv_path.resolve()}"
            )
        _out(
            f"Save verification [OK]: Designators='{verification_key}' "
            f"expected {expected}, found {found}. Rows now: {persisted_count}",
            level="info",
        )
    _out(f"\nComponent {action} successfully.")
    _out(f"Updated file: {csv_path.resolve()}")
    _out(f"Audit log: {AUDIT_LOG.resolve()}")
    _auto_refresh_component_libraries(
        BASE_DIR,
        "add_eliminate_component parameters",
        {subsystem_name},
    )


# Purpose: Run io workflow.
def _run_io_workflow() -> None:
    io_files = discover_csv_files(BASE_DIR, "_io.csv")
    io_name, csv_path = choose_from_mapping(io_files, "I/O files", "No *_io.csv files found in this folder.")

    headers, rows = load_csv(csv_path)

    _out("\nSelection summary")
    _out(f"I/O file: {io_name}")
    _out(f"File: {csv_path.name}")
    _out(f"Columns: {len(headers)}")
    _out(f"Rows: {len(rows)}")

    action_mode = choose_action()

    if action_mode == "delete":
        row_index = find_io_row_for_delete(headers, rows)
        if row_index < 0:
            _out("No changes made.", level="info")
            return

        _out(f"\nAbout to delete: {io_row_label(rows[row_index])}")
        if not prompt_yes_no("Confirm eliminate flow?", default=False):
            _out("No changes made.", level="info")
            return

        del rows[row_index]
        action = "deleted"
    else:
        existing_flow = input("Enter Flow name to add or update (or Enter to add new): ").strip()

        if existing_flow:
            row_index = find_row_index(rows, "Flow", existing_flow)
        else:
            row_index = -1

        if row_index >= 0:
            _out(f"\nCurrent: {io_row_label(rows[row_index])}")
            if not prompt_yes_no("Flow exists. Update this row?", default=True):
                _out("No changes made.", level="info")
                return
            rows[row_index] = prompt_io_row(headers, existing_row=rows[row_index])
            action = "updated"
        else:
            _out("Flow not found. Creating a new row.", level="info")
            rows.append(prompt_io_row(headers, existing_row=None))
            action = "added"

    save_csv(csv_path, headers, rows)
    _out(f"\nI/O flow {action} successfully.")
    _out(f"Updated file: {csv_path.resolve()}")


# Purpose: Main.
def main() -> None:
    try:
        mode = choose_mode()
        if mode == "parameters":
            _run_parameters_workflow()
        else:
            _run_io_workflow()
    except SelectionAborted as exc:
        _out(str(exc), level="error")
        _out("No changes made.", level="info")
    except SaveVerificationError as exc:
        _out(f"ERROR: {exc}", level="error")
        _out("No library refresh executed because save verification failed.", level="warning")


if __name__ == "__main__":
    main()

