"""Transport CSV preparation workflow used before openLCA import.

This module prepares transport-specific *_ipe_flows_from_parameters.csv files
and amount fields. It does not create openLCA entities directly.
"""

from __future__ import annotations

import csv
import re
import sys
import logging
from pathlib import Path


def _normalize_text(value: str) -> str:
    return str(value or "").strip()


def _to_float(value):
    text = _normalize_text(value).replace(",", ".")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _distance_to_km(distance, unit):
    distance_value = _to_float(distance)
    if distance_value is None:
        return None

    unit_norm = _normalize_text(unit).lower()
    if unit_norm in {"", "km", "kilometer", "kilometers", "kilometre", "kilometres"}:
        return distance_value
    if unit_norm in {"m", "meter", "meters", "metre", "metres"}:
        return distance_value / 1000.0
    if unit_norm in {"mi", "mile", "miles"}:
        return distance_value * 1.609344
    return None


def _safe_code_name(code: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", _normalize_text(code))
    cleaned = cleaned.strip("_")
    return cleaned if cleaned else "unknown"


def _create_transport_unit_process_files(base_dir: Path, dry_run: bool = False):
    """Create one transport code unit-process file per code from code_transport.csv."""
    transport_dir = base_dir / "LCI_TRANSPORT"
    source = transport_dir / "code_transport.csv"
    if not source.exists():
        logging.warning("Transport code library not found: %s", source)
        return 0

    with open(source, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    grouped = {}
    for row in rows:
        code = _normalize_text(row.get("Transport_phase_codes"))
        flow = _normalize_text(row.get("Ecoinvent_flow"))
        flow_uuid = _normalize_text(row.get("UUID"))
        provider_uuid = _normalize_text(row.get("UUID provider") or row.get("UUID_provider"))

        if code == "" or flow == "" or flow_uuid == "":
            continue

        distance_km = _distance_to_km(row.get("Distance"), row.get("Unit"))
        if distance_km is None or distance_km <= 0:
            continue

        amount_tkm_per_lu = distance_km / 1000.0
        key = (code, flow, flow_uuid, provider_uuid)
        grouped[key] = grouped.get(key, 0.0) + amount_tkm_per_lu

    by_code = {}
    for (code, flow, flow_uuid, provider_uuid), amount in grouped.items():
        by_code.setdefault(code, []).append(
            {
                "Flow": flow,
                "UUID": flow_uuid,
                "Unit": "tkm",
                "Amount": f"{amount:.12g}",
                "Direction": "Input",
                "UUID_provider": provider_uuid,
            }
        )

    generated = 0
    for code, input_rows in sorted(by_code.items(), key=lambda kv: kv[0].lower()):
        safe_code = _safe_code_name(code)
        target = transport_dir / f"transport_code_{safe_code}_ipe_flows_from_parameters.csv"
        fieldnames = ["Flow", "UUID", "Unit", "Amount", "Direction", "UUID_provider"]

        if dry_run:
            generated += 1
            logging.info("[DRY-RUN] Would generate transport code unit file: %s", target.name)
            continue

        with open(target, "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sorted(input_rows, key=lambda r: r["Flow"].lower()))
            writer.writerow(
                {
                    "Flow": code,
                    "UUID": "",
                    "Unit": "tkm",
                    "Amount": "1",
                    "Direction": "Output",
                    "UUID_provider": "",
                }
            )
        generated += 1

    if generated:
        logging.info("Transport unit process files generated: %s", generated)
    return generated


def _load_tkm_per_kg_by_code(base_dir: Path):
    """Load transport intensity map: code -> tkm per 1 kg."""
    transport_dir = base_dir / "LCI_TRANSPORT"
    source = transport_dir / "code_transport.csv"
    if not source.exists():
        return {}

    per_code = {}
    with open(source, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = _normalize_text(row.get("Transport_phase_codes"))
            if code == "":
                continue

            distance_km = _distance_to_km(row.get("Distance"), row.get("Unit"))
            if distance_km is None or distance_km <= 0:
                continue

            share = _to_float(row.get("tkm_share"))
            if share is None:
                share = 1.0
            if share <= 0:
                continue

            per_code[code] = per_code.get(code, 0.0) + (distance_km / 1000.0) * share

    return per_code


def _fill_transport_parent_amounts(base_dir: Path, dry_run: bool = False):
    """Fill Amount in *_transport_ipe files from mass-by-code per subsystem."""
    tools_dir = base_dir / "LCI_TRANSPORT"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    try:
        from calculate_transport_mass_by_code import (
            calculate_total_mass_by_transport_code,
            calculate_total_mass_by_transport_code_per_subsystem,
        )
    except Exception as exc:
        logging.warning("Could not load mass-by-code calculator: %s", exc)
        return 0

    totals_by_code = calculate_total_mass_by_transport_code(str(base_dir))
    totals_by_code_ci = {k.lower(): v for k, v in totals_by_code.items()}
    masses = calculate_total_mass_by_transport_code_per_subsystem(str(base_dir))
    subsystem_codes = {k.lower(): v.get("codes", {}) for k, v in masses.items()}
    tkm_per_kg_by_code = _load_tkm_per_kg_by_code(base_dir)
    tkm_per_kg_by_code_ci = {k.lower(): v for k, v in tkm_per_kg_by_code.items()}

    subsystem_file_map = {
        "magnet": "magnet_transport_ipe_flows_from_parameters.csv",
        "connection": "connector_system_transport_ipe_flows_from_parameters.csv",
        "connector_system": "connector_system_transport_ipe_flows_from_parameters.csv",
        "mexico_converter": "mexico_transport_ipe_flows_from_parameters.csv",
    }

    updates = 0
    for subsystem_key, file_name in subsystem_file_map.items():
        path = tools_dir / file_name
        if not path.exists():
            continue

        code_mass = subsystem_codes.get(subsystem_key, {})

        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                continue
            rows = list(reader)
            fieldnames = list(reader.fieldnames)

        if "Amount" not in fieldnames:
            fieldnames.append("Amount")

        changed = False
        total_output_tkm = 0.0
        has_output_tkm_row = False

        for row in rows:
            direction = _normalize_text(row.get("Direction")).lower()
            flow_name = _normalize_text(row.get("Flow"))
            if flow_name == "":
                continue

            if direction in {"output"}:
                unit = _normalize_text(row.get("Unit")).lower()
                if unit == "tkm":
                    has_output_tkm_row = True
                continue

            if direction not in {"", "input"}:
                continue

            mass_value = code_mass.get(flow_name)
            if mass_value is None:
                mass_value = code_mass.get(flow_name.upper())
            if mass_value is None:
                mass_value = code_mass.get(flow_name.lower())
            if mass_value is None:
                mass_value = totals_by_code.get(flow_name)
            if mass_value is None:
                mass_value = totals_by_code_ci.get(flow_name.lower())
            if mass_value is None:
                continue

            row["Amount"] = f"{mass_value:.12g}"
            changed = True

            tkm_factor = tkm_per_kg_by_code.get(flow_name)
            if tkm_factor is None:
                tkm_factor = tkm_per_kg_by_code_ci.get(flow_name.lower())
            if tkm_factor is not None and tkm_factor > 0:
                total_output_tkm += mass_value * tkm_factor

        if has_output_tkm_row and total_output_tkm > 0:
            for row in rows:
                direction = _normalize_text(row.get("Direction")).lower()
                unit = _normalize_text(row.get("Unit")).lower()
                if direction == "output" and unit == "tkm":
                    row["Amount"] = f"{total_output_tkm:.12g}"
                    changed = True
                    break

        if not changed:
            continue

        if dry_run:
            updates += 1
            logging.info("[DRY-RUN] Would fill transport amounts in: %s", path.name)
            continue

        with open(path, "w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        updates += 1

    if updates:
        logging.info("Transport parent files with Amount updated: %s", updates)
    return updates


def prepare_transport_unit_processes(base_dir: Path, dry_run: bool = False):
    """Prepare transport unit process CSVs before standard import passes."""
    logging.info("Preparing transport unit processes from code_transport.csv...")
    generated = _create_transport_unit_process_files(base_dir, dry_run=dry_run)
    updated = _fill_transport_parent_amounts(base_dir, dry_run=dry_run)
    if generated == 0 and updated == 0:
        logging.info("No transport unit process updates were needed.")
