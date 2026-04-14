import argparse
import csv
import subprocess
import sys
from pathlib import Path

IPE_FIELDS = ["Flow", "UUID", "Unit", "Amount", "Direction", "UUID_provider", "Transport_phase_codes"]


def normalize_text(value):
    return str(value or "").strip()


def to_float(value, default=0.0):
    try:
        text = str(value or "").strip().replace(",", ".")
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def read_parameters(parameters_path):
    if not parameters_path.exists():
        raise FileNotFoundError(f"Parameters file not found: {parameters_path}")

    with open(parameters_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    return fieldnames, rows


def read_existing_ipe_rows(ipe_path):
    if not ipe_path.exists():
        return []

    with open(ipe_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _row_key(flow, unit, direction):
    return (normalize_text(flow), normalize_text(unit) or "kg", normalize_direction(direction))


def split_flows(flow_value):
    text = normalize_text(flow_value)
    if text == "":
        return []
    return [part.strip() for part in text.split("+") if part.strip()]


def normalize_direction(value):
    text = normalize_text(value).lower()
    if text.startswith("input") or text.startswith("inpu"):
        return "Input"
    if text.startswith("output") or text.startswith("out"):
        return "Output"
    return "Input" if text == "" else normalize_text(value)


def build_ipe_rows(parameter_rows):
    aggregated = {}
    existing_rows_by_key = {}
    skipped = 0
    total_mass_kg = 0.0
    component_count = 0

    # Preserve user-managed columns from the previous IPE file when rerunning
    # the pipeline so Transport_phase_codes are not erased.
    existing_ipe_rows = read_existing_ipe_rows(Path(__file__).resolve().parent / "magnet_ipe_flows_from_parameters.csv")
    for row in existing_ipe_rows:
        key = _row_key(row.get("Flow"), row.get("Unit"), row.get("Direction"))
        if key not in existing_rows_by_key:
            existing_rows_by_key[key] = row

    for row in parameter_rows:
        direction = normalize_direction(row.get("Direction"))
        ecoinvent_flows = split_flows(row.get("Ecoinvent_flow"))
        if not ecoinvent_flows:
            skipped += 1
            continue

        unit = normalize_text(row.get("unit")) or "kg"
        quantity_per_element = to_float(row.get("Quantity_per_element"), 0.0)
        number_elements = to_float(row.get("number_elements"), 1.0)
        amount = quantity_per_element * number_elements
        component_count += 1
        total_mass_kg += amount

        for flow in ecoinvent_flows:
            key = (flow, unit, direction)
            if key not in aggregated:
                existing_row = existing_rows_by_key.get(key, {})
                aggregated[key] = {
                    "Flow": flow,
                    "UUID": normalize_text(existing_row.get("UUID")),
                    "Unit": unit,
                    "Amount": 0.0,
                    "Direction": direction,
                    "UUID_provider": normalize_text(existing_row.get("UUID_provider")),
                    "Transport_phase_codes": normalize_text(existing_row.get("Transport_phase_codes")),
                }
            aggregated[key]["Amount"] += amount

    ipe_rows = list(aggregated.values())
    return ipe_rows, skipped, total_mass_kg, component_count


def preserve_existing_output_rows(existing_rows):
    preserved = []
    for row in existing_rows:
        direction = normalize_direction(row.get("Direction"))
        if direction != "Output":
            continue

        preserved.append(
            {
                "Flow": normalize_text(row.get("Flow")),
                "UUID": normalize_text(row.get("UUID")),
                "Unit": normalize_text(row.get("Unit")) or "kg",
                "Amount": normalize_text(row.get("Amount")),
                "Direction": "Output",
                "UUID_provider": normalize_text(row.get("UUID_provider")),
                "Transport_phase_codes": normalize_text(row.get("Transport_phase_codes")),
            }
        )
    return preserved


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)



def run_fill(ipe_path):
    fill_script = Path(__file__).resolve().parent.parent / "fill_ipe_columns_from_library.py"
    if not fill_script.exists():
        print(f"[Warning] Fill helper not found: {fill_script}")
        return

    subprocess.run(
        [
            sys.executable,
            str(fill_script),
            "--target-file",
            str(ipe_path),
        ],
        check=True,
    )



def main():
    parser = argparse.ArgumentParser(description="Minimal pipeline for LCI_MAGNET.")
    parser.add_argument(
        "--parameters",
        default="magnet_component_parameters.csv",
        help="Input parameters CSV (default: magnet_component_parameters.csv)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report what would be written")
    parser.add_argument("--skip-fill", action="store_true", help="Skip UUID/provider fill step")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    parameters_path = (base_dir / args.parameters).resolve()
    ipe_path = base_dir / "magnet_ipe_flows_from_parameters.csv"

    _, parameter_rows = read_parameters(parameters_path)
    ipe_rows, skipped, total_mass_kg, component_count = build_ipe_rows(parameter_rows)
    existing_ipe_rows = read_existing_ipe_rows(ipe_path)
    preserved_output_rows = preserve_existing_output_rows(existing_ipe_rows)

    if preserved_output_rows:
        ipe_rows.extend(preserved_output_rows)

    if args.dry_run:
        print(f"[DRY-RUN] parameter rows read: {len(parameter_rows)}")
        print(f"[DRY-RUN] parameter rows skipped: {skipped}")
        print(f"[DRY-RUN] component rows with EcoInvent flows: {component_count}")
        print(f"[DRY-RUN] total mass (no double count): {total_mass_kg}")
        print(f"[DRY-RUN] preserved existing output rows: {len(preserved_output_rows)}")
        print(f"[DRY-RUN] ipe rows to write: {len(ipe_rows)}")
        return

    write_csv(ipe_path, IPE_FIELDS, ipe_rows)
    print(f"Written: {ipe_path.name} ({len(ipe_rows)} rows)")
    print(f"Component rows with EcoInvent flows: {component_count}")
    print(f"Total mass (kg): {total_mass_kg}")
    print(f"Preserved existing output rows: {len(preserved_output_rows)}")
    print(f"EcoInvent flow lines written: {len(ipe_rows) - len(preserved_output_rows)}")

    if not args.skip_fill:
        try:
            run_fill(ipe_path)
            print("UUID/provider fill completed for magnet IPE.")
        except Exception as exc:
            print(f"[Warning] UUID/provider fill failed: {exc}")


if __name__ == "__main__":
    main()
