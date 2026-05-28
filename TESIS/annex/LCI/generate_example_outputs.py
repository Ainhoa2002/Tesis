"""
Role: Generate example output files and minimal result samples for testing.

Brief: Produces small, synthetic output files (CSV/JSON) to exercise the
extraction and visualization pipelines during testing or documentation.
"""

#!/usr/bin/env python3
"""Generate example CSV outputs for the annex (non-destructive).

This script uses the same tiny fixture as `LCI_MEXICO_CONVERTER/smoke_test.py`
to produce representative `*_component_results.csv`, `*_component_io_flows.csv`
and `<subsystem>_ipe_flows_from_parameters.csv` files under
`LCI/archived_generated_examples/` so readers can inspect how outputs look.
"""
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from LCI_MEXICO_CONVERTER.Pipeline import run_pipeline

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "archived_generated_examples"
OUT_DIR.mkdir(exist_ok=True)

FIXTURE_ROWS = [
    {
        "Designators": "example_part",
        "Section": "Example",
        "Subsection": "Demo",
        "Casing": "",
        "Part_Number": "EX-001",
        "Database": "ecoinvent",
        "Ecoinvent_flow": "market for copper, cathode",
        "Ecoinvent_unit": "kg",
        "Direction": "Input",
        "unit": "kg",
        "Has_datasheet_info": "YES",
        "Quantity_per_element": "2.5",
        "number_elements": "2",
        "L_mm": "",
        "W_mm": "",
        "H_mm": "",
        "Volume_cm3_excel": "",
        "Density_min_g_cm3": "",
        "Density_max_g_cm3": "",
        "mass_space_relation_m2/kg": "",
        "Metal_extra_g": "",
        "Category": "",
        "Group_order": "",
        "Category_order": "",
        "Order_index": "",
    }
]


# Purpose: Write csv.
def _write_csv(path: Path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# Purpose: Main.
def main():
    input_csv = OUT_DIR / "example_component_parameters.csv"
    results_csv = OUT_DIR / "example_component_results.csv"
    io_csv = OUT_DIR / "example_component_io_flows.csv"
    grouped_csv = OUT_DIR / "example_ipe_flows_from_parameters.csv"

    fieldnames = list(FIXTURE_ROWS[0].keys())
    _write_csv(input_csv, fieldnames, FIXTURE_ROWS)

    results, component_flows, grouped_flows, errors = run_pipeline(
        str(input_csv),
        str(results_csv),
        str(io_csv),
        str(grouped_csv),
        subsystem_name="example",
        subsystem_units=1.0,
    )

    if errors:
        logging.warning("Pipeline reported errors: %s", errors)
    else:
        logging.info("Example outputs written to %s", OUT_DIR)


if __name__ == "__main__":
    main()
