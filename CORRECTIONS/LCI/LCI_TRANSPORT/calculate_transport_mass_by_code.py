import argparse
import csv
from collections import defaultdict
from pathlib import Path


def _normalize_text(value):
    return str(value or "").strip()


def _parse_codes(raw_codes):
    text = _normalize_text(raw_codes)
    if text == "":
        return []

    codes = []
    for part in text.split(","):
        code = _normalize_text(part)
        if code:
            codes.append(code)
    return codes


def _to_float(value):
    if value is None:
        return None
    text = _normalize_text(value).replace(",", ".")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _unit_to_kg(amount, unit):
    if amount is None:
        return None

    unit_norm = _normalize_text(unit).lower()
    if unit_norm == "kg":
        return amount
    if unit_norm == "g":
        return amount / 1000.0
    if unit_norm == "mg":
        return amount / 1_000_000.0
    if unit_norm in {"t", "ton", "tons", "tonne", "tonnes"}:
        return amount * 1000.0

    return None


def _iter_ipe_files(root_dir):
    for path in sorted(Path(root_dir).rglob("*_ipe_flows_from_parameters.csv")):
        if path.is_file():
            yield path


def _module_name_from_ipe_path(csv_path):
    suffix = "_ipe_flows_from_parameters.csv"
    name = Path(csv_path).name
    if not name.endswith(suffix):
        return ""
    return name[: -len(suffix)]


def _is_pcb_flow(flow_name):
    return "printed wiring board production" in _normalize_text(flow_name).lower()


def _load_pcb_mass_from_results(csv_path):
    """Load PCB/OCB mass (kg) from sibling *_component_results.csv for one module."""
    module = _module_name_from_ipe_path(csv_path)
    if module == "":
        return 0.0

    results_path = Path(csv_path).with_name(f"{module}_component_results.csv")
    if not results_path.exists():
        return 0.0

    pcb_mass_kg = 0.0
    with open(results_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            designator = _normalize_text(row.get("Designators")).upper()
            if designator not in {"PCB", "OCB"}:
                continue
            mass_kg = _to_float(row.get("Total_mass_kg"))
            if mass_kg is not None:
                pcb_mass_kg += mass_kg

    return pcb_mass_kg


def _collect_pcb_codes_from_ipe(csv_path):
    """Collect transport codes present on PCB rows in one *_ipe file."""
    codes = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "Transport_phase_codes" not in reader.fieldnames:
            return codes
        for row in reader:
            if _normalize_text(row.get("Direction")).lower() == "output":
                continue
            if not _is_pcb_flow(row.get("Flow")):
                continue
            for code in _parse_codes(row.get("Transport_phase_codes", "")):
                codes.add(code)
    return codes


def _load_mexico_subsystem_units(root_dir):
    """Load Quantity_per_subsystem map for LCI_MEXICO_CONVERTER."""
    units_path = Path(root_dir) / "LCI_MEXICO_CONVERTER" / "subsystem_units.csv"
    units_map = {}

    if not units_path.exists():
        return units_map

    with open(units_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            subsystem = _normalize_text(row.get("Subsystem"))
            qty = _to_float(row.get("Quantity_per_subsystem"))
            if subsystem == "":
                continue
            units_map[subsystem] = qty if (qty is not None and qty > 0) else 1.0

    return units_map


def _load_system_units(root_dir):
    """Load system-level LU multipliers from LCI_SYSTEM/system_ipe_flows_from_parameters.csv."""
    system_path = Path(root_dir) / "LCI_SYSTEM" / "system_ipe_flows_from_parameters.csv"
    units_map = {}

    if not system_path.exists():
        return units_map

    with open(system_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            flow = _normalize_text(row.get("Flow"))
            unit = _normalize_text(row.get("Unit")).lower()
            direction = _normalize_text(row.get("Direction")).lower()
            amount = _to_float(row.get("Amount"))

            if flow == "" or amount is None:
                continue
            if unit != "lu":
                continue
            if direction not in {"", "input"}:
                continue

            units_map[flow.lower()] = amount if amount > 0 else 1.0

    return units_map


def _get_mass_multiplier_for_file(root_dir, csv_path, mexico_units_map):
    """Return mass multiplier for one *_ipe file.

    In LCI_MEXICO_CONVERTER, only subsystem files listed in subsystem_units.csv
    are considered, and each one is scaled by Quantity_per_subsystem.
    """
    rel_parts = Path(csv_path).resolve().relative_to(Path(root_dir).resolve()).parts
    if not rel_parts:
        return 1.0, True

    if rel_parts[0] != "LCI_MEXICO_CONVERTER":
        return 1.0, True

    suffix = "_ipe_flows_from_parameters.csv"
    name = Path(csv_path).name
    if not name.endswith(suffix):
        return 1.0, False

    subsystem = name[: -len(suffix)]
    if subsystem not in mexico_units_map:
        # Skip aggregate/system files in this folder (e.g., MEXICO_ipe...).
        return 1.0, False

    return mexico_units_map[subsystem], True


def _get_system_multiplier_for_file(root_dir, csv_path, system_units_map):
    """Return system-level multiplier for one *_ipe file based on system_ipe LU rows."""
    if not system_units_map:
        return 1.0

    rel_parts = Path(csv_path).resolve().relative_to(Path(root_dir).resolve()).parts
    if not rel_parts:
        return 1.0

    top_folder = rel_parts[0]
    suffix = "_ipe_flows_from_parameters.csv"
    name = Path(csv_path).name
    stem = name[: -len(suffix)] if name.endswith(suffix) else Path(csv_path).stem

    folder_to_system_flow = {
        "LCI_MEXICO_CONVERTER": "MEXICO_CONVERTER",
        "LCI_MAGNET": "magnet",
        "LCI_CONNECTION": "connector_system",
        "LCI_TRANSPORT": "transport",
    }

    candidates = [
        stem,
        _subsystem_name_from_path(root_dir, csv_path),
        folder_to_system_flow.get(top_folder, ""),
    ]

    for candidate in candidates:
        key = _normalize_text(candidate).lower()
        if key and key in system_units_map:
            return system_units_map[key]

    return 1.0


def _subsystem_name_from_path(root_dir, csv_path):
    """Resolve subsystem name from a file path relative to the LCI root."""
    rel_parts = Path(csv_path).resolve().relative_to(Path(root_dir).resolve()).parts
    if not rel_parts:
        return "unknown"

    top = rel_parts[0]
    if top.startswith("LCI_") and len(top) > 4:
        return top[4:].lower()
    return top.lower()


def calculate_total_mass_by_transport_code(root_dir, include_pcb_mass_from_results=False):
    """Calculate total mass in kg aggregated by Transport_phase_codes.

    Rules:
    - Reads all *_ipe_flows_from_parameters.csv files recursively.
    - Uses only rows with non-empty Transport_phase_codes.
    - Supports kg, g, mg, t/ton/tonne units.
    - If a row has multiple codes (comma-separated), its full mass is added to each code.
    
    NOTE: IPE file amounts are already multiplied by subsystem_units in Pipeline,
    so we use them as-is without further multiplication.
    """
    totals_kg = defaultdict(float)

    # Load system-level multipliers
    system_units_map = _load_system_units(root_dir)

    for csv_path in _iter_ipe_files(root_dir):
        system_multiplier = _get_system_multiplier_for_file(root_dir, csv_path, system_units_map)
        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                continue
            if "Transport_phase_codes" not in reader.fieldnames:
                continue

            for row in reader:
                codes = _parse_codes(row.get("Transport_phase_codes", ""))
                if not codes:
                    continue

                amount = _to_float(row.get("Amount"))
                mass_kg = _unit_to_kg(amount, row.get("Unit"))
                if mass_kg is None:
                    continue

                # Apply system-level multiplier
                mass_kg_scaled = mass_kg * system_multiplier

                for code in codes:
                    totals_kg[code] += mass_kg_scaled

    if include_pcb_mass_from_results:
        for csv_path in _iter_ipe_files(root_dir):
            pcb_mass_kg = _load_pcb_mass_from_results(csv_path)
            if pcb_mass_kg <= 0:
                continue
            pcb_codes = _collect_pcb_codes_from_ipe(csv_path)
            system_multiplier = _get_system_multiplier_for_file(root_dir, csv_path, system_units_map)
            pcb_mass_kg_scaled = pcb_mass_kg * system_multiplier
            for code in pcb_codes:
                totals_kg[code] += pcb_mass_kg_scaled

    return dict(sorted(totals_kg.items(), key=lambda kv: kv[0].lower()))


def calculate_total_mass_by_transport_code_per_subsystem(root_dir, include_pcb_mass_from_results=False):
    """Calculate total mass in kg per subsystem and Transport_phase_codes.
    
    NOTE: IPE file amounts are already multiplied by subsystem_units in Pipeline,
    so we use them as-is without further multiplication.
    """
    subsystem_totals = defaultdict(lambda: defaultdict(float))
    subsystem_total_coded_mass_kg = defaultdict(float)

    # Load system-level multipliers
    system_units_map = _load_system_units(root_dir)

    for csv_path in _iter_ipe_files(root_dir):
        subsystem = _subsystem_name_from_path(root_dir, csv_path)
        system_multiplier = _get_system_multiplier_for_file(root_dir, csv_path, system_units_map)

        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                continue
            if "Transport_phase_codes" not in reader.fieldnames:
                continue

            for row in reader:
                codes = _parse_codes(row.get("Transport_phase_codes", ""))
                if not codes:
                    continue

                amount = _to_float(row.get("Amount"))
                mass_kg = _unit_to_kg(amount, row.get("Unit"))
                if mass_kg is None:
                    continue

                # Apply system-level multiplier
                mass_kg_scaled = mass_kg * system_multiplier

                subsystem_total_coded_mass_kg[subsystem] += mass_kg_scaled

                for code in codes:
                    subsystem_totals[subsystem][code] += mass_kg_scaled

    if include_pcb_mass_from_results:
        for csv_path in _iter_ipe_files(root_dir):
            pcb_mass_kg = _load_pcb_mass_from_results(csv_path)
            if pcb_mass_kg <= 0:
                continue

            pcb_codes = _collect_pcb_codes_from_ipe(csv_path)
            if not pcb_codes:
                continue

            subsystem = _subsystem_name_from_path(root_dir, csv_path)
            system_multiplier = _get_system_multiplier_for_file(root_dir, csv_path, system_units_map)
            pcb_mass_kg_scaled = pcb_mass_kg * system_multiplier
            subsystem_total_coded_mass_kg[subsystem] += pcb_mass_kg_scaled
            for code in pcb_codes:
                subsystem_totals[subsystem][code] += pcb_mass_kg_scaled

    ordered = {}
    for subsystem in sorted(subsystem_totals.keys()):
        codes = subsystem_totals[subsystem]
        ordered[subsystem] = {
            "codes": dict(sorted(codes.items(), key=lambda kv: kv[0].lower())),
            "total_coded_mass_kg": subsystem_total_coded_mass_kg[subsystem],
        }
    return ordered


def calculate_mass_breakdown_by_subsystem(root_dir):
    """Calculate coded and uncoded mass totals per subsystem.

    This is a diagnostic view: it keeps the current transport-code behavior intact,
    but makes it visible how much mass is excluded because Transport_phase_codes
    is blank or missing.
    """
    coded_totals = defaultdict(float)
    uncoded_totals = defaultdict(float)
    all_totals = defaultdict(float)
    row_counts = defaultdict(lambda: {"coded_rows": 0, "uncoded_rows": 0})
    mexico_units_map = _load_mexico_subsystem_units(root_dir)
    system_units_map = _load_system_units(root_dir)

    for csv_path in _iter_ipe_files(root_dir):
        subsystem_multiplier, include_file = _get_mass_multiplier_for_file(root_dir, csv_path, mexico_units_map)
        if not include_file:
            continue
        system_multiplier = _get_system_multiplier_for_file(root_dir, csv_path, system_units_map)
        multiplier = subsystem_multiplier * system_multiplier
        subsystem = _subsystem_name_from_path(root_dir, csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                continue
            if "Amount" not in reader.fieldnames:
                continue

            for row in reader:
                amount = _to_float(row.get("Amount"))
                mass_kg = _unit_to_kg(amount, row.get("Unit"))
                if mass_kg is None:
                    continue

                mass_kg = mass_kg * multiplier
                all_totals[subsystem] += mass_kg

                codes = _parse_codes(row.get("Transport_phase_codes", ""))
                if codes:
                    coded_totals[subsystem] += mass_kg
                    row_counts[subsystem]["coded_rows"] += 1
                else:
                    uncoded_totals[subsystem] += mass_kg
                    row_counts[subsystem]["uncoded_rows"] += 1

    ordered = {}
    for subsystem in sorted(all_totals.keys()):
        ordered[subsystem] = {
            "coded_mass_kg": coded_totals[subsystem],
            "uncoded_mass_kg": uncoded_totals[subsystem],
            "total_mass_kg": all_totals[subsystem],
            "coded_rows": row_counts[subsystem]["coded_rows"],
            "uncoded_rows": row_counts[subsystem]["uncoded_rows"],
        }
    return ordered


def main():
    parser = argparse.ArgumentParser(
        description="Calculate total mass (kg) per Transport_phase_codes from *_ipe_flows_from_parameters.csv files."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Root directory to scan recursively (default: LCI/)"
    )
    parser.add_argument(
        "--overall",
        action="store_true",
        help="Print overall totals across all subsystems (legacy behavior).",
    )
    parser.add_argument(
        "--breakdown",
        action="store_true",
        help="Print coded/uncoded mass breakdown per subsystem.",
    )
    parser.add_argument(
        "--include-pcb-mass-from-results",
        action="store_true",
        help="Include PCB/OCB kg mass from *_component_results.csv using PCB transport codes from IPE rows.",
    )
    args = parser.parse_args()

    if args.breakdown:
        breakdown = calculate_mass_breakdown_by_subsystem(args.root)
        if not breakdown:
            print("No rows found.")
            return
        for subsystem, payload in breakdown.items():
            print(
                f"{subsystem}: coded={payload['coded_mass_kg']:.12g} kg, "
                f"uncoded={payload['uncoded_mass_kg']:.12g} kg, total={payload['total_mass_kg']:.12g} kg, "
                f"coded_rows={payload['coded_rows']}, uncoded_rows={payload['uncoded_rows']}"
            )
        return

    if args.overall:
        totals = calculate_total_mass_by_transport_code(
            args.root,
            include_pcb_mass_from_results=args.include_pcb_mass_from_results,
        )

        if not totals:
            print("No coded mass rows found.")
            return

        for code, mass_kg in totals.items():
            print(f"{code}: {mass_kg:.12g} kg")
        return

    per_subsystem = calculate_total_mass_by_transport_code_per_subsystem(
        args.root,
        include_pcb_mass_from_results=args.include_pcb_mass_from_results,
    )
    if not per_subsystem:
        print("No coded mass rows found.")
        return

    global_total_coded_mass_kg = 0.0
    for subsystem, payload in per_subsystem.items():
        codes = payload["codes"]
        total_coded_mass_kg = payload["total_coded_mass_kg"]
        if not codes:
            continue
        code_chunks = [f"{mass_kg:.12g}kg {code}" for code, mass_kg in codes.items()]
        print(f"{subsystem}: " + ", ".join(code_chunks) + f" | total={total_coded_mass_kg:.12g}kg")
        global_total_coded_mass_kg += total_coded_mass_kg

    print(f"TOTAL_CODED_MASS_ALL_SUBSYSTEMS: {global_total_coded_mass_kg:.12g}kg")


if __name__ == "__main__":
    main()
