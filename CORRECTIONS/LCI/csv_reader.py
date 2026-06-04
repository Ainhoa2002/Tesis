import csv

"""CSV reader helpers for IPE files.

Provides simple helpers to extract input/output rows from CSV files
following the project's `*_ipe_flows_from_parameters.csv` conventions.
"""


def read_input_rows(path):
    """Return a list of rows where `Direction` is 'Input'."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("Direction", "")).strip().lower() == "input":
                rows.append(row)
    return rows


def read_output_rows(path):
    """Return a list of rows where `Direction` is 'Output'."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("Direction", "")).strip().lower() == "output":
                rows.append(row)
    return rows


def read_output_row(path):
    """Return the first output row from the CSV, or None if none found."""
    rows = read_output_rows(path)
    return rows[0] if rows else None

