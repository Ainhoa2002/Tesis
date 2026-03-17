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

    print(f"\nFound {len(results)} row(s) for '{part_number}':\n")
    last_subsystem = None
    for subsystem, fieldnames, row in results:
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


if __name__ == "__main__":
    main()
