from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOTALS_FILE = BASE_DIR / "component_library_ecoinvent_totals.csv"
SECTION_FILES = sorted(BASE_DIR.glob("SECTION_*_ipe_flows_from_parameters.csv"))
OUTPUT_CSV = BASE_DIR / "comparison_library_totals_vs_mexico_sections_bg.csv"
OUTPUT_MD = BASE_DIR / "comparison_library_totals_vs_mexico_sections_bg.md"
CREATED_FLOWS_FILE = BASE_DIR / "created_flows_uuid_map.csv"


def _to_float(value: str | None) -> float:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _load_created_flows() -> set[str]:
    created = set()
    if not CREATED_FLOWS_FILE.exists():
        return created
    with CREATED_FLOWS_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if row:
                created.add(str(row[0]).strip())
    return created


def _load_library_totals(created_flows: set[str]) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    with TOTALS_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if str(row.get("Direction", "")).strip().lower() != "input":
                continue
            flow = str(row.get("Ecoinvent_flow", "") or "").strip()
            unit = str(row.get("Ecoinvent_unit", "") or "").strip()
            if not flow or flow in created_flows:
                continue
            amount = _to_float(row.get("Total_mass_kg"))
            if amount == 0.0:
                amount = _to_float(row.get("Total_amount"))
            totals[(flow, unit)] += amount
    return totals


def _load_section_totals(created_flows: set[str]) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for path in SECTION_FILES:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if str(row.get("Direction", "")).strip().lower() != "input":
                    continue
                flow = str(row.get("Flow", "") or row.get("Ecoinvent_flow", "") or "").strip()
                unit = str(row.get("Unit", "") or row.get("Ecoinvent_unit", "") or "").strip()
                if not flow or flow in created_flows:
                    continue
                totals[(flow, unit)] += _to_float(row.get("Amount") or row.get("Total_mass_kg"))
    return totals


def _summarize_deltas(rows: list[dict[str, object]]) -> tuple[int, int, int, int]:
    same_nonzero = sum(1 for row in rows if row["MEXICO_MODULES_BG"] != 0 and row["MEXICO_SECTIONS_BG"] != 0 and abs(row["Delta"]) < 1e-12)
    only_modules = sum(1 for row in rows if row["MEXICO_MODULES_BG"] != 0 and row["MEXICO_SECTIONS_BG"] == 0)
    only_sections = sum(1 for row in rows if row["MEXICO_MODULES_BG"] == 0 and row["MEXICO_SECTIONS_BG"] != 0)
    different = sum(1 for row in rows if abs(row["Delta"]) >= 1e-12)
    return same_nonzero, only_modules, only_sections, different


def main() -> None:
    created_flows = _load_created_flows()
    library_totals = _load_library_totals(created_flows)
    section_totals = _load_section_totals(created_flows)

    all_keys = sorted(set(library_totals) | set(section_totals))
    rows: list[dict[str, object]] = []
    for flow, unit in all_keys:
        library_value = library_totals.get((flow, unit), 0.0)
        section_value = section_totals.get((flow, unit), 0.0)
        rows.append(
            {
                "Flow": flow,
                "Unit": unit,
                "MEXICO_MODULES_BG": library_value,
                "MEXICO_SECTIONS_BG": section_value,
                "Delta": section_value - library_value,
            }
        )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Flow", "Unit", "MEXICO_MODULES_BG", "MEXICO_SECTIONS_BG", "Delta"])
        writer.writeheader()
        writer.writerows(rows)

    same_nonzero, only_modules, only_sections, different = _summarize_deltas(rows)

    lines = ["# LIBRARY_TOTALS vs MEXICO_SECTIONS_BG", ""]
    lines.append("Comparison scope: input rows only. The left side is built from component_library_ecoinvent_totals.csv.")
    lines.append("")
    lines.append(f"- TOTAL_KEYS: {len(rows)}")
    lines.append(f"- SAME_NONZERO: {same_nonzero}")
    lines.append(f"- ONLY_MODULES: {only_modules}")
    lines.append(f"- ONLY_SECTIONS: {only_sections}")
    lines.append(f"- DIFFERENT: {different}")
    lines.append("")
    lines.append("| Flow | Unit | MEXICO_MODULES_BG | MEXICO_SECTIONS_BG | Delta |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for row in sorted(rows, key=lambda item: abs(item["Delta"]), reverse=True):
        lines.append(
            f"| {row['Flow']} | {row['Unit']} | {row['MEXICO_MODULES_BG']:.12g} | {row['MEXICO_SECTIONS_BG']:.12g} | {row['Delta']:.12g} |"
        )

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_MD)
    print(OUTPUT_CSV)
    print(f"TOTAL_KEYS={len(rows)} SAME_NONZERO={same_nonzero} ONLY_MODULES={only_modules} ONLY_SECTIONS={only_sections} DIFFERENT={different}")


if __name__ == "__main__":
    main()
