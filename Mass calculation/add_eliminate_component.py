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
    "Category",
    "Section",
    "Subsection",
    "Total_quantity",
    "Datasheet_required_flag",
    "Mass_datasheet_g",
    "Scale_with_mass_flag",
    "Other_possible_models",
    "Reliability",
    "Completeness",
    "Temporal_correlation",
}

# It discovers the subsystems that we have files for.
def discover_subsystem_files(base_dir: Path) -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    for path in sorted(base_dir.glob("*_component_parameters.csv")):
        subsystem = path.name[: -len("_component_parameters.csv")]
        mapping[subsystem] = path
    return mapping

#For choosing the subsystem, it can be written or you can choose for the list of available possibilities
def choose_subsystem(subsystems: Dict[str, Path]) -> Tuple[str, Path]:
    names = list(subsystems.keys())
    if not names:
        raise RuntimeError("No *_component_parameters.csv files found in this folder.")

    names_by_lower = {name.lower(): name for name in names}

    print("Available subsystems:")
    for i, name in enumerate(names, start=1):
        print(f"  {i}. {name}")

    attempts = 0
    while True:
        raw = input("Choose subsystem number or name: ").strip()
        if not raw:
            attempts += 1
            fail_or_abort_selection(attempts)
            continue

        if raw in subsystems:
            return raw, subsystems[raw]

        lowered = raw.lower()
        if lowered in names_by_lower:
            chosen = names_by_lower[lowered]
            return chosen, subsystems[chosen]

        try:
            idx = int(raw)
        except ValueError:
            idx = -1

        if 1 <= idx <= len(names):
            chosen = names[idx - 1]
            return chosen, subsystems[chosen]

        attempts += 1
        fail_or_abort_selection(attempts)

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

#Search if the component exist in the file by its designators, if it exist it returns the index of the row, if not it returns -1
def find_row_index_by_designators(rows: List[Dict[str, str]], designators: str) -> int:
    target = normalize_text(designators)
    for i, row in enumerate(rows):
        if normalize_text(row.get("Designators", "")) == target:
            return i
    return -1

#it prints the information of the component.
def print_component_preview(row: Dict[str, str], headers: List[str]) -> None:
    preview_order = [
        "Designators",
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
    manufacturer = row.get("Manufacturer", "")
    part_number = row.get("Part_Number", "")
    description = row.get("Description", "")
    if len(description) > 60:
        description = description[:57] + "..."
    return f"{designators} | {manufacturer} | {part_number} | {description}"


def choose_search_field(headers: List[str]) -> str | None:
    preferred_fields = [
        "Designators",
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
        new_row = {header: existing_row.get(header, "") for header in headers}
    else:
        new_row = {header: "" for header in headers}

    if "Designators" in new_row:
        new_row["Designators"] = designators

    ordered_headers = [h for h in KEY_FIELD_ORDER if h in headers]
    ordered_headers.extend([h for h in headers if h not in ordered_headers and h not in AUTO_FIELDS])

    for header in ordered_headers:
        current_value = new_row.get(header, "")
        prompt = f"{header} [{current_value}]: " if current_value else f"{header}: "
        user_value = input(prompt).strip()

        if user_value == "__blank__":
            new_row[header] = ""
        elif user_value:
            new_row[header] = user_value

    return new_row

#Saves the CSV file directly (no automatic backup files).
def save_csv(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    try:
        subsystems = discover_subsystem_files(BASE_DIR)
        subsystem_name, csv_path = choose_subsystem(subsystems)

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

            row_index = find_row_index_by_designators(rows, designators)

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
    except SelectionAborted as exc:
        print(str(exc))
        print("No changes made.")


if __name__ == "__main__":
    main()

