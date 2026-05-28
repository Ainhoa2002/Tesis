"""
Role: Smoke tests for Mexico converter workflows.

Brief: Lightweight checks that run a subset of the Mexico converter pipeline to
ensure outputs are generated and basic invariants hold.
"""

#!/usr/bin/env python3
"""Local smoke test for the Mexico converter pipeline.

This test runs `Pipeline.run_pipeline` against a tiny CSV fixture written to a
temporary directory. It avoids openLCA entirely and checks the local mass and
flow calculations still work after cleanup changes.
"""

from __future__ import annotations

import csv
import math
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

# interactive-safe output helper
import logging
_IS_TTY = sys.stdout.isatty()
# Purpose: Out.
def _out(msg: str, level: str = "info") -> None:
    if _IS_TTY:
        print(msg)
    else:
        getattr(logging, level)(msg)

from Pipeline import run_pipeline


FIXTURE_ROWS = [
    {
        "Designators": "smoke_part",
        "Section": "Smoke",
        "Subsection": "Test",
        "Casing": "",
        "Part_Number": "SMK-001",
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


# Purpose: Write fixture csv.
def _write_fixture_csv(path: Path) -> None:
    fieldnames = list(FIXTURE_ROWS[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(FIXTURE_ROWS)


# Purpose: Read csv rows.
def _read_csv_rows(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


# Purpose: Run smoke test.
def run_smoke_test() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_csv = temp_path / "smoke_component_parameters.csv"
        results_csv = temp_path / "smoke_component_results.csv"
        io_csv = temp_path / "smoke_component_io_flows.csv"
        grouped_csv = temp_path / "smoke_ipe_flows_from_parameters.csv"

        _write_fixture_csv(input_csv)

        results, component_flows, grouped_flows, errors = run_pipeline(
            str(input_csv),
            str(results_csv),
            str(io_csv),
            str(grouped_csv),
            subsystem_name="smoke",
            subsystem_units=1.0,
        )

        assert errors == [], f"Unexpected pipeline errors: {errors}"
        assert len(results) == 1, f"Expected 1 result row, got {len(results)}"
        assert len(component_flows) == 1, f"Expected 1 component flow, got {len(component_flows)}"
        assert len(grouped_flows) == 1, f"Expected 1 grouped flow returned by run_pipeline, got {len(grouped_flows)}"

        result_rows = _read_csv_rows(results_csv)
        io_rows = _read_csv_rows(io_csv)
        grouped_rows = _read_csv_rows(grouped_csv)

        assert len(result_rows) == 1, "Results CSV should contain one row"
        assert len(io_rows) == 1, "I/O CSV should contain one row"
        assert len(grouped_rows) == 2, "Grouped flows CSV should contain two rows"

        result_row = result_rows[0]
        assert result_row["Designators"] == "smoke_part"
        assert math.isclose(float(result_row["Total_mass_kg"]), 5.0, rel_tol=1e-9)
        assert result_row["Validation_error"] in {"", None}

        grouped_by_flow = {row["Flow"]: row for row in grouped_rows}
        assert math.isclose(float(grouped_by_flow["market for copper, cathode"]["Amount"]), 5.0, rel_tol=1e-9)
        assert math.isclose(float(grouped_by_flow["smoke"]["Amount"]), 5.0, rel_tol=1e-9)

        _out("Smoke test passed.")


if __name__ == "__main__":
    run_smoke_test()