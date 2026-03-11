#!/usr/bin/env python3
"""Export subsystem results to a single Excel workbook.

This script reuses subsystem selection from add_eliminate_component.py.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from add_eliminate_component import SelectionAborted, choose_subsystem, discover_subsystem_files

BASE_DIR = Path(r"c:\Users\alorzaga\Git\tesis\Mass calculation")


def load_csv_optional(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return [], []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = list(reader.fieldnames or [])
    return headers, rows


def write_sheet(ws, headers: List[str], rows: List[Dict[str, str]]) -> None:
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])


def export_subsystem_results_to_excel(base_dir: Path, subsystem: str) -> Path | None:
    try:
        from openpyxl import Workbook
    except ImportError:
        print("openpyxl is required for Excel export.")
        print("Install it with: .\\.venv\\Scripts\\python.exe -m pip install openpyxl")
        return None

    sources = [
        ("Parameters", base_dir / f"{subsystem}_component_parameters.csv"),
        ("Mass_Results", base_dir / f"{subsystem}_component_mass_results.csv"),
        ("Component_IO", base_dir / f"{subsystem}_component_io_flows.csv"),
        ("Grouped_Flows", base_dir / f"{subsystem}_ipe_flows_from_parameters.csv"),
    ]

    workbook = Workbook()
    workbook.remove(workbook.active)
    exported = 0

    for sheet_name, csv_path in sources:
        headers, rows = load_csv_optional(csv_path)
        if not headers:
            continue
        ws = workbook.create_sheet(sheet_name[:31])
        write_sheet(ws, headers, rows)
        exported += 1

    if exported == 0:
        print("No data found to export for this subsystem.")
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = base_dir / f"{subsystem}_results_export_{stamp}.xlsx"
    workbook.save(output_path)
    return output_path


def main() -> None:
    try:
        subsystems = discover_subsystem_files(BASE_DIR)
        subsystem_name, _ = choose_subsystem(subsystems)

        output = export_subsystem_results_to_excel(BASE_DIR, subsystem_name)
        if output is not None:
            print(f"\nExport completed: {output}")
    except SelectionAborted as exc:
        print(str(exc))


if __name__ == "__main__":
    main()
