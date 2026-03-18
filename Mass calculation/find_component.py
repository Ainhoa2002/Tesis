#!/usr/bin/env python3
"""Search for a part number across all *_component_parameters.csv files.

Usage:
    python find_component.py <part_number>
    python find_component.py          (interactive mode)

Output: matching rows printed as CSV lines ready to paste into a new component.
"""

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent


def _clean(value):
    return str(value or "").strip()


def find_part(part_number: str) -> list:
    """Return list of (subsystem, fieldnames, row_dict) for every matching row."""
    needle = part_number.strip().casefold()
    results = []
    for path in sorted(BASE_DIR.glob("*_component_parameters.csv")):
        subsystem = path.name[: -len("_component_parameters.csv")]
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if _clean(row.get("Part_Number")).casefold() == needle:
                    results.append((subsystem, fieldnames, dict(row)))
    return results


def _row_to_csv_line(fieldnames: list, row: dict) -> str:
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="")
    writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


def _display_results(results):
    """Display all results in a formatted way."""
    print(f"\nFound {len(results)} row(s):\n")
    last_subsystem = None
    for idx, (subsystem, fieldnames, row) in enumerate(results):
        if subsystem != last_subsystem:
            print(f"--- {subsystem} ---")
            # Print header so the user knows field positions
            import io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="")
            writer.writeheader()
            print(buf.getvalue())
            last_subsystem = subsystem
        print(_row_to_csv_line(fieldnames, row))


def _update_csv_row(subsystem: str, fieldnames: list, old_row: dict, field_name: str, new_value: str):
    """Update a specific field in a component CSV file."""
    csv_path = BASE_DIR / f"{subsystem}_component_parameters.csv"
    rows_to_write = []
    found = False
    
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row == old_row:
                row[field_name] = new_value
                found = True
            rows_to_write.append(row)
    
    if found:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_write)
        print(f"✓ Updated {field_name} to '{new_value}' in {subsystem}_component_parameters.csv")
        return True
    else:
        print("✗ Could not find the exact row to update.")
        return False


def _bulk_update_all_rows(results):
    """Update one or more fields in all found rows."""
    print("\n" + "=" * 80)
    print("BULK UPDATE (ALL ROWS)")
    print("=" * 80)
    all_fields = []
    for _, fieldnames, _ in results:
        for field in fieldnames:
            if field not in all_fields:
                all_fields.append(field)

    for idx, field in enumerate(all_fields, 1):
        print(f"[{idx}] {field}")

    selection = input(
        "Choose field number(s) to update in all rows (e.g. 3 or 3,4,10): "
    ).strip()
    if not selection:
        print("No fields selected.")
        return

    selected_fields = []
    for token in selection.split(","):
        value = token.strip()
        if not value.isdigit():
            print("Invalid selection.")
            return
        field_idx = int(value) - 1
        if not 0 <= field_idx < len(all_fields):
            print("Invalid selection.")
            return
        field_name = all_fields[field_idx]
        if field_name not in selected_fields:
            selected_fields.append(field_name)

    updates = {}
    for field_name in selected_fields:
        updates[field_name] = input(f"New value for {field_name}: ").strip()

    total_field_updates = 0
    updated_rows = 0
    for subsystem, fieldnames, row in results:
        row_updated = False
        for field_name, new_value in updates.items():
            if field_name not in fieldnames:
                continue
            current_value = _clean(row.get(field_name, ""))
            if new_value == current_value:
                continue
            if _update_csv_row(subsystem, fieldnames, row, field_name, new_value):
                row[field_name] = new_value
                total_field_updates += 1
                row_updated = True

        if row_updated:
            updated_rows += 1

    print(
        f"\nApplied {total_field_updates} field update(s) across {updated_rows} row(s)."
    )


def _interactive_edit(results):
    """Allow user to edit fields in the found components."""
    while True:
        change_response = input("\n¿Do you want to change something? (yes/y/Y): ").strip().lower()
        
        if change_response not in ["yes", "y"]:
            print("No changes made. Exiting.")
            return
        
        # Show results again with numbering
        print("\n" + "="*80)
        print("SELECT WHICH ROW TO MODIFY:")
        print("="*80)
        for idx, (subsystem, fieldnames, row) in enumerate(results, 1):
            print(f"\n[{idx}] {subsystem}:")
            print(_row_to_csv_line(fieldnames, row))
        
        # Ask which row to modify
        row_choice = input(
            f"\nEnter row number to modify (1-{len(results)}) or 'all': "
        ).strip()

        if row_choice.casefold() == "all":
            _bulk_update_all_rows(results)
            another = input("\nMake another change? (yes/y): ").strip().lower()
            if another not in ["yes", "y"]:
                print("Done. Exiting.")
                break
            continue

        try:
            row_idx = int(row_choice) - 1
            if not 0 <= row_idx < len(results):
                print("Invalid selection.")
                continue
        except ValueError:
            print("Invalid input.")
            continue
        
        subsystem, fieldnames, row = results[row_idx]
        
        # Show available fields
        print("\n" + "="*80)
        print("AVAILABLE FIELDS TO CHANGE:")
        print("="*80)
        for col_idx, field in enumerate(fieldnames, 1):
            current_value = _clean(row.get(field, ""))
            print(f"[{col_idx}] {field}: '{current_value}'")
        
        # Ask which field to modify
        field_choice = input(f"\nEnter field number to modify (1-{len(fieldnames)}): ").strip()
        try:
            field_idx = int(field_choice) - 1
            if not 0 <= field_idx < len(fieldnames):
                print("Invalid selection.")
                continue
        except ValueError:
            print("Invalid input.")
            continue
        
        field_name = fieldnames[field_idx]
        current_value = _clean(row.get(field_name, ""))
        
        # Ask for new value
        print(f"\nCurrent value: '{current_value}'")
        new_value = input(f"Enter new value for {field_name}: ").strip()
        
        if new_value == current_value:
            print("Value is the same. No changes made.")
            continue
        
        # Update directly without confirmation
        if _update_csv_row(subsystem, fieldnames, row, field_name, new_value):
            row[field_name] = new_value  # Update in-memory row
            print("\n✓ Change saved successfully!")
        
        # Ask if more changes
        another = input("\nMake another change? (yes/y): ").strip().lower()
        if another not in ["yes", "y"]:
            print("Done. Exiting.")
            break


def main():
    if len(sys.argv) > 1:
        part_number = " ".join(sys.argv[1:]).strip()
    else:
        part_number = input("Enter Part_Number to search: ").strip()

    if not part_number:
        print("No part number provided.")
        return

    results = find_part(part_number)

    if not results:
        print(f"No rows found for Part_Number '{part_number}'.")
        return

    _display_results(results)
    _interactive_edit(results)


if __name__ == "__main__":
    main()
