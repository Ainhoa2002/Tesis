import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DEFAULT_DENSITY = {
    "MLCC": 6.50,
    "TANTALUM": 5.50,
    "FILM_SMALL": 1.35,
    "FILM_LARGE": 1.35,
    "IGBT_TO247": 1.40,
    "POWER_THT": 1.40,
    "DCDC_MODULE": 1.40,
}


def to_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def round_mass(mass_g, technology):
    tech = (technology or "").strip().upper()

    if tech == "MLCC":
        return quantize(mass_g, "0.0001")
    if tech == "TANTALUM":
        if mass_g < 0.1:
            return quantize(mass_g, "0.0001")
        return quantize(mass_g, "0.001")
    if tech == "FILM_SMALL":
        return quantize(mass_g, "0.0001")
    if tech in {"FILM_LARGE", "IGBT_TO247", "POWER_THT", "DCDC_MODULE"}:
        return quantize(mass_g, "0.01")

    if mass_g < 0.1:
        return quantize(mass_g, "0.0001")
    if mass_g < 1:
        return quantize(mass_g, "0.001")
    return quantize(mass_g, "0.01")


def quantize(value, step):
    return float(Decimal(str(value)).quantize(Decimal(step), rounding=ROUND_HALF_UP))


def get_density(row):
    override = to_float(row.get("Density_override_g_cm3"))
    if override is not None:
        return override

    tech = (row.get("Technology") or "").strip().upper()
    return DEFAULT_DENSITY.get(tech)


def compute_volume_cm3(w_mm, h_mm, l_mm):
    volume_mm3 = w_mm * h_mm * l_mm
    return volume_mm3 / 1000.0


def build_calculation(row):
    technology = (row.get("Technology") or "").strip().upper()
    mass_datasheet = to_float(row.get("Mass_datasheet_g"))

    if mass_datasheet is not None:
        mass_final = round_mass(mass_datasheet, technology)
        return {
            "has_datasheet_mass": "SI",
            "volume_cm3": "",
            "density": "",
            "mass_final_g": mass_final,
            "notes": "Used direct datasheet mass.",
        }

    w_mm = to_float(row.get("W_mm"))
    h_mm = to_float(row.get("H_mm"))
    l_mm = to_float(row.get("L_mm"))

    if w_mm is None or h_mm is None or l_mm is None:
        return {
            "has_datasheet_mass": "NO",
            "volume_cm3": "",
            "density": "",
            "mass_final_g": "",
            "notes": "Missing dimensions and no datasheet mass.",
        }

    density = get_density(row)
    if density is None:
        return {
            "has_datasheet_mass": "NO",
            "volume_cm3": "",
            "density": "",
            "mass_final_g": "",
            "notes": "Missing density mapping for technology.",
        }

    volume_cm3 = compute_volume_cm3(w_mm, h_mm, l_mm)
    mass_raw = density * volume_cm3
    mass_final = round_mass(mass_raw, technology)

    return {
        "has_datasheet_mass": "NO",
        "volume_cm3": quantize(volume_cm3, "0.0000001"),
        "density": density,
        "mass_final_g": mass_final,
        "notes": "Computed from W x H x L and composite density.",
    }


def format_dims(row):
    w_mm = row.get("W_mm", "")
    h_mm = row.get("H_mm", "")
    l_mm = row.get("L_mm", "")
    return f"W={w_mm}; H={h_mm}; L={l_mm}"


def build_output_row(row, calc):
    return {
        "Componente": row.get("Designator", ""),
        "Part number": row.get("Part_number", ""),
        "Fabricante": row.get("Vendor", ""),
        "Encapsulado": row.get("Package", ""),
        "Dimensiones (mm)": format_dims(row),
        "Volumen (cm3)": calc["volume_cm3"],
        "Densidad usada (g/cm3)": calc["density"],
        "Correccion metalica": "incluida en densidad compuesta",
        "Masa en datasheet?": calc["has_datasheet_mass"],
        "Masa final (g)": calc["mass_final_g"],
        "Similar component used": row.get("Similar_component_used", ""),
        "BibKey": row.get("BibKey", ""),
        "Datasheet ref": row.get("Datasheet_reference", ""),
        "Calculation notes": merge_notes(row.get("Notes", ""), calc["notes"]),
    }


def merge_notes(user_notes, calc_notes):
    text_a = (user_notes or "").strip()
    text_b = (calc_notes or "").strip()
    if text_a and text_b:
        return text_a + " | " + text_b
    if text_a:
        return text_a
    return text_b


def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_bib(path, rows):
    lines = []
    for row in rows:
        bibkey = (row.get("BibKey") or "").strip()
        if not bibkey:
            continue
        vendor = (row.get("Vendor") or "Unknown").strip()
        part = (row.get("Part_number") or "Unknown").strip()
        ref = (row.get("Datasheet_reference") or "Datasheet").strip()

        lines.append(f"@misc{{{bibkey},")
        lines.append(f"  author = {{{vendor}}},")
        lines.append(f"  title = {{{part} datasheet}},")
        lines.append("  year = {2026},")
        lines.append(f"  note = {{{ref}}},")
        lines.append("}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")


def run(input_path, output_path, bib_path):
    input_rows = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            input_rows.append(row)

    output_rows = []
    for row in input_rows:
        calc = build_calculation(row)
        output_rows.append(build_output_row(row, calc))

    write_csv(output_path, output_rows)
    write_bib(bib_path, input_rows)

    total = len(output_rows)
    with_datasheet = sum(1 for r in output_rows if r["Masa en datasheet?"] == "SI")
    computed = total - with_datasheet

    print(f"Processed rows: {total}")
    print(f"Used datasheet mass: {with_datasheet}")
    print(f"Computed mass: {computed}")
    print(f"Output CSV: {output_path}")
    print(f"Output BIB: {bib_path}")


def main():
    parser = argparse.ArgumentParser(description="Component mass calculator")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--bib", required=True, help="Output BibTeX path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    bib_path = Path(args.bib)

    run(input_path, output_path, bib_path)


if __name__ == "__main__":
    main()
