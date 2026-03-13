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
from pathlib import Path
from typing import Dict, List, Tuple


BASE_DIR = Path(r"c:\Users\alorzaga\Git\tesis\Mass calculation")
MAX_SELECTION_ATTEMPTS = 3


class SelectionAborted(RuntimeError):
    pass


def fail_or_abort_selection(attempts: int) -> None:
    print("Invalid selection. Try again.")
    if attempts >= MAX_SELECTION_ATTEMPTS:
        raise SelectionAborted("Too many invalid attempts. Operation canceled.")

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
    "Other_extra_g",
    "Database",
    "Database_component_title",
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
    "Other_extra_g": "0",
    "Database": "EcoInvent",
    "Database_component_title": "Infineon IKW40N120H3",
    "Ecoinvent_flow": "integrated circuit production, logic type",
    "Ecoinvent_unit": "kg",
    "Direction": "Input",
    "Ecoinvent_amount_override": "0.5",
}


def prompt_label_with_example(header: str) -> str:
    if header in {"Comments", "Notes"}:
        return header
    example = FIELD_EXAMPLES.get(header)
    if not example:
        return header
    return f"{header} (e.g. {example})"

def choose_mode() -> str:
    print("\nWhat do you want to edit?")
    print("  1. Component parameters")
    print("  2. I/O flows")
    attempts = 0
    while True:
        raw = input("Mode [1/2]: ").strip().lower()
        if raw in {"1", "parameters", "params", "p", "component"}:
            return "parameters"
        if raw in {"2", "io", "i/o", "flows", "i"}:
            return "io"
        attempts += 1
        print("Invalid option. Enter 1 or 2.")
        if attempts >= MAX_SELECTION_ATTEMPTS:
            raise SelectionAborted("Too many invalid attempts. Operation canceled.")


def discover_csv_files(base_dir: Path, suffix: str) -> Dict[str, Path]:
    return {
        p.name[: -len(suffix)]: p
        for p in sorted(base_dir.glob(f"*{suffix}"))
    }


# Kept as aliases so external callers (export_to_excel, etc.) continue to work.
def discover_subsystem_files(base_dir: Path) -> Dict[str, Path]:
    return discover_csv_files(base_dir, "_component_parameters.csv")


def discover_io_files(base_dir: Path) -> Dict[str, Path]:
    return discover_csv_files(base_dir, "_io.csv")


def choose_from_mapping(mapping: Dict[str, Path], label: str, empty_error: str) -> Tuple[str, Path]:
    #Presents a numbered list and returns the chosen (name, path) pair.
    names = list(mapping.keys())
    if not names:
        raise RuntimeError(empty_error)

    names_by_lower = {name.lower(): name for name in names}

    print(f"Available {label}:")
    for i, name in enumerate(names, start=1):
        print(f"  {i}. {name}")

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


def normalize_text(value: str) -> str:
    return value.strip().lower()


def prompt_yes_no(message: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        raw = input(message + suffix).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "ys", "s", "si", "Y", "YES", "Yes", "SI", "S", "TRUE", "true", "True", "T", "1"}:
            return True
        if raw in {"n", "no", "NO", "No", "FALSE", "false", "False", "F"}:
            return False
        print("Please answer y or n.")


def choose_action() -> str:
    print("\nChoose action:")
    print("  1. Add or update component")
    print("  2. Eliminate component")
    attempts = 0
    while True:
        raw = input("Action [1/2]: ").strip().lower()
        if raw in {"1", "add", "update", "a", "u"}:
            return "add_update"
        if raw in {"2", "delete", "eliminate", "remove", "d", "e", "r"}:
            return "delete"
        attempts += 1
        print("Invalid action. Choose 1 or 2.")
        if attempts >= MAX_SELECTION_ATTEMPTS:
            raise SelectionAborted("Too many invalid attempts. Operation canceled.")

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
    print("\nCurrent component preview:")
    for field in preview_order:
        if field in headers:
            print(f"  {field}: {row.get(field, '')}")


def component_label(row: Dict[str, str]) -> str:
    designators = row.get("Designators", "")
    casing = row.get("Casing", "")
    manufacturer = row.get("Manufacturer", "")
    part_number = row.get("Part_Number", "")
    description = row.get("Description", "")
    if len(description) > 60:
        description = description[:57] + "..."
    return f"{designators} | {casing} | {manufacturer} | {part_number} | {description}"


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

    print("\nChoose section/field to search:")
    for i, field in enumerate(searchable_fields, start=1):
        print(f"  {i}. {field}")

    attempts = 0
    while True:
        raw = input("Field number: ").strip()
        try:
            idx = int(raw)
        except ValueError:
            idx = -1
        if 1 <= idx <= len(searchable_fields):
            return searchable_fields[idx - 1]
        attempts += 1
        fail_or_abort_selection(attempts)


def search_component_indices(rows: List[Dict[str, str]], field: str, keyword: str) -> List[int]:
    target = normalize_text(keyword)
    matches: List[int] = []
    for i, row in enumerate(rows):
        value = normalize_text(str(row.get(field, "")))
        if target in value:
            matches.append(i)
    return matches


def choose_component_from_candidates(rows: List[Dict[str, str]], candidate_indices: List[int], title: str) -> int | None:
    if not candidate_indices:
        return None

    print(f"\n{title}")
    for i, row_idx in enumerate(candidate_indices, start=1):
        print(f"  {i}. {component_label(rows[row_idx])}")

    attempts = 0
    while True:
        raw = input("Choose component number (Enter to cancel): ").strip()
        if not raw:
            return None
        try:
            idx = int(raw)
        except ValueError:
            idx = -1
        if 1 <= idx <= len(candidate_indices):
            return candidate_indices[idx - 1]
        attempts += 1
        fail_or_abort_selection(attempts)


def find_component_for_delete(headers: List[str], rows: List[Dict[str, str]]) -> int:
    while True:
        reference = input("Enter component reference (Designators). Press Enter if unknown: ").strip()
        if reference:
            idx = find_row_index_by_designators(rows, reference)
            if idx >= 0:
                return idx
            print("Component not found by Designators.")

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
            print("No searchable fields available.")
            return -1

        keyword = input(f"Keyword for {field}: ").strip()
        if not keyword:
            print("Keyword cannot be empty.")
            continue

        matches = search_component_indices(rows, field, keyword)
        if not matches:
            print("Not found relevant info.")
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

def find_row_index_by_flow(rows: List[Dict[str, str]], flow: str) -> int:
    return find_row_index(rows, "Flow", flow)


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


def io_row_label(row: Dict[str, str]) -> str:
    flow = row.get("Flow", "")
    unit = row.get("Unit", "")
    amount = row.get("Amount", "")
    direction = row.get("Direction", "")
    label = flow if len(flow) <= 70 else flow[:67] + "..."
    return f"{label} | {unit} | {amount} | {direction}"


def find_io_row_for_delete(headers: List[str], rows: List[Dict[str, str]]) -> int:
    while True:
        keyword = input("Enter keyword to search in Flow (or Enter to list all): ").strip()

        if keyword:
            matches = [i for i, row in enumerate(rows)
                       if normalize_text(keyword) in normalize_text(row.get("Flow", ""))]
        else:
            matches = list(range(len(rows)))

        if not matches:
            print("No matching flows found.")
            if not prompt_yes_no("Try again?", default=True):
                return -1
            continue

        print(f"\nFound {len(matches)} flow(s):")
        for i, row_idx in enumerate(matches, start=1):
            print(f"  {i}. {io_row_label(rows[row_idx])}")

        attempts = 0
        while True:
            raw = input("Choose number to delete (Enter to cancel): ").strip()
            if not raw:
                return -1
            try:
                idx = int(raw)
            except ValueError:
                idx = -1
            if 1 <= idx <= len(matches):
                return matches[idx - 1]
            attempts += 1
            fail_or_abort_selection(attempts)


#Saves the CSV file directly (no automatic backup files).
def save_csv(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _run_parameters_workflow() -> None:
    subsystems = discover_csv_files(BASE_DIR, "_component_parameters.csv")
    subsystem_name, csv_path = choose_from_mapping(subsystems, "subsystems", "No *_component_parameters.csv files found in this folder.")

    headers, rows = load_csv(csv_path)

    print("\nSelection summary")
    print(f"Subsystem: {subsystem_name}")
    print(f"File: {csv_path.name}")
    print(f"Columns: {len(headers)}")
    print(f"Rows: {len(rows)}")

    action_mode = choose_action()

    if action_mode == "delete":
        row_index = find_component_for_delete(headers, rows)
        if row_index < 0:
            print("No changes made.")
            return

        existing_row = rows[row_index]
        print_component_preview(existing_row, headers)
        if not prompt_yes_no("Confirm eliminate component?", default=False):
            print("No changes made.")
            return

        del rows[row_index]
        action = "deleted"
    else:
        while True:
            designators = input("Enter Designators to add or update: ").strip()
            if designators:
                break
            print("Designators cannot be empty.")

        row_index = find_row_index(rows, "Designators", designators)

        if row_index >= 0:
            existing_row = rows[row_index]
            print_component_preview(existing_row, headers)
            if not prompt_yes_no("Component exists. Update this row?", default=True):
                print("No changes made.")
                return

            rows[row_index] = prompt_component_row(
                headers=headers,
                designators=designators,
                existing_row=existing_row,
            )
            action = "updated"
        else:
            print("Component not found. Creating a new row.")
            rows.append(
                prompt_component_row(
                    headers=headers,
                    designators=designators,
                    existing_row=None,
                )
            )
            action = "added"

    save_csv(csv_path, headers, rows)
    print(f"\nComponent {action} successfully.")
    print(f"Updated file: {csv_path.name}")


def _run_io_workflow() -> None:
    io_files = discover_csv_files(BASE_DIR, "_io.csv")
    io_name, csv_path = choose_from_mapping(io_files, "I/O files", "No *_io.csv files found in this folder.")

    headers, rows = load_csv(csv_path)

    print("\nSelection summary")
    print(f"I/O file: {io_name}")
    print(f"File: {csv_path.name}")
    print(f"Columns: {len(headers)}")
    print(f"Rows: {len(rows)}")

    action_mode = choose_action()

    if action_mode == "delete":
        row_index = find_io_row_for_delete(headers, rows)
        if row_index < 0:
            print("No changes made.")
            return

        print(f"\nAbout to delete: {io_row_label(rows[row_index])}")
        if not prompt_yes_no("Confirm eliminate flow?", default=False):
            print("No changes made.")
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
            print(f"\nCurrent: {io_row_label(rows[row_index])}")
            if not prompt_yes_no("Flow exists. Update this row?", default=True):
                print("No changes made.")
                return
            rows[row_index] = prompt_io_row(headers, existing_row=rows[row_index])
            action = "updated"
        else:
            print("Flow not found. Creating a new row.")
            rows.append(prompt_io_row(headers, existing_row=None))
            action = "added"

    save_csv(csv_path, headers, rows)
    print(f"\nI/O flow {action} successfully.")
    print(f"Updated file: {csv_path.name}")


def main() -> None:
    try:
        mode = choose_mode()
        if mode == "parameters":
            _run_parameters_workflow()
        else:
            _run_io_workflow()
    except SelectionAborted as exc:
        print(str(exc))
        print("No changes made.")


if __name__ == "__main__":
    main()

