#!/usr/bin/env python3
"""
Run parametric mass + ecoinvent pipeline for one or more selected subsystems.
Subsystem names are resolved from files named <subsystem>_component_parameters.csv.
"""

import csv
import os
import sys
from collections import OrderedDict
from pathlib import Path


MAX_SELECTION_ATTEMPTS = 3

# Converts the inputs in correct format, float. changes coma for dot, averages ranges, returns none if it is empty.
def to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", ".")
    if text == "":
        return None

    try:
        return float(text)
    except ValueError:
        pass

    # Support ranges like 0.35-0.4 after normal float parsing.
    # This avoids misreading scientific notation (e.g. 8e-05) as a range.
    if "-" in text and not text.startswith("-"):
        parts = text.split("-")
        if len(parts) == 2:
            try:
                return (float(parts[0].strip()) + float(parts[1].strip())) / 2.0
            except ValueError:
                return None

    return None

#Yes or no when input is in different formats
def to_yes_no(value):
    text = str(value or "").strip().upper()
    if text in {"YES", "SI", "S", "Y", "TRUE", "1", "yes", "Yes", "true", "T"}:
        return True
    if text in {"NO", "N", "FALSE", "0", "FALSE", "no", "No", "false", "F"}:
        return False
    return False

#Reorders the colums
def _sort_key(row):
    category_order = to_float(row.get("Category_order"))
    group_order = to_float(row.get("Group_order"))
    order_idx = to_float(row.get("Order_index"))

    # Keep original BOM grouping/order while still sorting by category/subsection groups.
    if category_order is None:
        category_order = 10**9
    if group_order is None:
        group_order = 10**9
    if order_idx is None:
        order_idx = 10**9

    return (category_order, group_order, order_idx)


def _clean_text(value):
    return str(value or "").strip()


def _build_row_metadata(rows):
    """Compute sortable/groupable metadata using user-provided grouping parameters."""
    category_order_map = OrderedDict()
    group_order_map = OrderedDict()
    metadata = []

    for pos, row in enumerate(rows, start=1):
        category = _clean_text(row.get("Category")) or "AUTO"
        section = _clean_text(row.get("Section"))
        subsection = _clean_text(row.get("Subsection"))

        if category not in category_order_map:
            category_order_map[category] = len(category_order_map) + 1

        group_key = (category, section, subsection)
        if group_key not in group_order_map:
            group_order_map[group_key] = len(group_order_map) + 1

        metadata.append(
            {
                "Order_index": str(pos),
                "Category_order": str(category_order_map[category]),
                "Group_order": str(group_order_map[group_key]),
                "Category": category,
                "Section": section,
                "Subsection": subsection,
            }
        )

    return metadata


def _validate_required_grouping_fields(raw_rows):
    missing = []
    for idx, row in raw_rows:
        section = _clean_text(row.get("Section"))
        if section == "":
            missing.append((idx, _clean_text(row.get("Designators")), section))
    return missing


def _validate_input_consistency(raw_rows):
    conflicts = []
    geometry_density_fields = [
        "L_mm",
        "W_mm",
        "H_mm",
        "Volume_cm3_excel",
        "Density_min_g_cm3",
        "Density_max_g_cm3",
    ]

    for idx, row in raw_rows:
        designators = _clean_text(row.get("Designators")) or "no designator"
        unit = _get_quantity_context_unit(row)
        has_datasheet_info = to_yes_no(row.get("Has_datasheet_info"))
        quantity_per_element = _clean_text(row.get("Quantity_per_element"))

        if has_datasheet_info and is_mass_unit(unit):
            if quantity_per_element == "":
                conflicts.append(
                    (
                        idx,
                        designators,
                        "datasheet_mass_missing_quantity",
                        ["Quantity_per_element"],
                    )
                )

            filled = [field for field in geometry_density_fields if _clean_text(row.get(field)) != ""]
            if filled:
                conflicts.append(
                    (
                        idx,
                        designators,
                        "datasheet_mass_has_geometry",
                        filled,
                    )
                )

        has_lwh = all(_clean_text(row.get(field)) != "" for field in ["L_mm", "W_mm", "H_mm"])
        has_volume = _clean_text(row.get("Volume_cm3_excel")) != ""
        if has_lwh and has_volume:
            conflicts.append(
                (
                    idx,
                    designators,
                    "lwh_and_volume",
                    ["L_mm", "W_mm", "H_mm", "Volume_cm3_excel"],
                )
            )

    return conflicts

#For calculating the density
def _resolve_density(row):
    """Resolve effective density for mass calculation.
    Priority:
    1) average(Density_min_g_cm3, Density_max_g_cm3)
    2) Density_min_g_cm3
    3) Density_max_g_cm3
    """
    density_min = to_float(row.get("Density_min_g_cm3"))
    density_max = to_float(row.get("Density_max_g_cm3"))

    if density_min is not None and density_max is not None:
        return (density_min + density_max) / 2.0, "MIN_MAX_AVG"
    if density_min is not None:
        return density_min, "MIN_ONLY"
    if density_max is not None:
        return density_max, "MAX_ONLY"

    return None, "MISSING"


def _get_number_elements(row):
    return to_float(row.get("number_elements"))


def _get_unit(row):
    return str(row.get("unit") or "").strip()


def _get_quantity_context_unit(row):
    primary = str(row.get("Ecoinvent_unit") or "").strip().lower()
    fallback = _get_unit(row).strip().lower()

    if primary == "m2" or is_mass_unit(primary):
        return primary
    if fallback == "m2" or is_mass_unit(fallback):
        return fallback
    return primary or fallback


def _compute_total_quantity(row):
    number_elements = _get_number_elements(row)
    quantity_per_element = to_float(row.get("Quantity_per_element"))
    if number_elements is None or quantity_per_element is None:
        return None
    return number_elements * quantity_per_element


def _try_area_quantity_m2(row):
    """Compute area-based quantity for m2 context using only L and W (mm -> m2)."""
    l_mm = to_float(row.get("L_mm"))
    w_mm = to_float(row.get("W_mm"))
    if l_mm is None or w_mm is None:
        return None
    return (l_mm * w_mm) / 1_000_000.0


def _build_quantity_data(row, mass_data):
    """Resolve Quantity_per_element and Total_quantity for reporting and flow amount logic."""
    number_elements = _get_number_elements(row)
    number_elements = 1.0 if number_elements is None else number_elements

    unit = _get_quantity_context_unit(row)
    has_datasheet_info = to_yes_no(row.get("Has_datasheet_info"))
    input_qty_per_element = to_float(row.get("Quantity_per_element"))

    if unit == "m2" and has_datasheet_info:
        area_per_element_m2 = _try_area_quantity_m2(row)
        if area_per_element_m2 is None:
            if input_qty_per_element is None:
                return None
            area_per_element_m2 = input_qty_per_element
            method = "AREA_FROM_INPUT"
        else:
            method = "AREA_LW_MM_TO_M2"

        return {
            "Quantity_per_element": area_per_element_m2,
            "Total_quantity": area_per_element_m2 * number_elements,
            "Method": method,
        }

    if is_mass_unit(unit) and mass_data is not None:
        if unit == "kg":
            qty_per_element = mass_data["Mass_per_element_g"] / 1000.0
            total_quantity = mass_data["Total_mass_kg"]
        else:
            qty_per_element = mass_data["Mass_per_element_g"]
            total_quantity = mass_data["Total_mass_g"]

        return {
            "Quantity_per_element": qty_per_element,
            "Total_quantity": total_quantity,
            "Method": "MASS_DERIVED",
        }

    if input_qty_per_element is not None:
        return {
            "Quantity_per_element": input_qty_per_element,
            "Total_quantity": input_qty_per_element * number_elements,
            "Method": "INPUT_QTY",
        }

    return None


def _ordered_result_fieldnames(row):
    """Return result CSV field order with key visualization columns first."""
    preferred_front = [
        "Designators",
        "Casing",
        "Section",
        "Subsection",
        "Ecoinvent_unit",
        "unit",
        "Total_quantity",
        "Ecoinvent_flow",
    ]
    fields = list(row.keys())
    front = [name for name in preferred_front if name in fields]
    tail = [name for name in fields if name not in front]
    return front + tail

#CALCULATE THE MASS OF THE COMPONENTS
def _try_geometry_mass(row, metal_extra_g, other_extra_g):
    l_mm = to_float(row.get("L_mm"))
    w_mm = to_float(row.get("W_mm"))
    h_mm = to_float(row.get("H_mm"))
    density_g_cm3, density_source = _resolve_density(row)

    if density_g_cm3 is None:
        return None, None, None, density_source

    if l_mm is not None and w_mm is not None and h_mm is not None:
        volume_cm3 = (l_mm * w_mm * h_mm) / 1000.0
    else:
        volume_cm3 = to_float(row.get("Volume_cm3_excel"))

    if volume_cm3 is None:
        return None, None, None, density_source

    mass_per_element_g = (volume_cm3 * density_g_cm3) + metal_extra_g + other_extra_g
    return volume_cm3, mass_per_element_g, density_g_cm3, density_source


def compute_component_mass(row):
    """Try to compute mass. Returns None if data is insufficient (not an error
    unless the ecoinvent unit is kg/g, which is checked separately)."""
    quantity = _get_number_elements(row)
    quantity = 1.0 if quantity is None else quantity

    has_datasheet_info = to_yes_no(row.get("Has_datasheet_info"))
    qty_per_element = to_float(row.get("Quantity_per_element"))
    unit_context = _get_quantity_context_unit(row)
    is_mass_context = is_mass_unit(unit_context)

    metal_extra_g = to_float(row.get("Metal_extra_g")) or 0.0
    other_extra_g = to_float(row.get("Other_extra_g")) or 0.0

    volume_cm3, mass_from_geometry_g, density_used_g_cm3, density_source = _try_geometry_mass(
        row,
        metal_extra_g,
        other_extra_g,
    )

    if has_datasheet_info and is_mass_context and qty_per_element is not None:
        mass_per_element_g = qty_per_element * 1000.0
        method = "DATASHEET_QTY_KG"
        volume_cm3 = None
    elif (not has_datasheet_info) and (mass_from_geometry_g is not None):
        mass_per_element_g = mass_from_geometry_g
        method = "CALCULATED"
    elif mass_from_geometry_g is not None:
        mass_per_element_g = mass_from_geometry_g
        method = "CALCULATED_FALLBACK"
    else:
        return None  # No mass data yet — only an error if unit is kg/g

    total_mass_g = mass_per_element_g * quantity
    total_mass_kg = total_mass_g / 1000.0

    return {
        "Method": method,
        "Volume_cm3": volume_cm3,
        "Mass_per_element_g": mass_per_element_g,
        "Total_mass_g": total_mass_g,
        "Total_mass_kg": total_mass_kg,
        "Density_used_g_cm3": density_used_g_cm3,
        "Density_source": density_source,
    }


def is_mass_unit(unit):
    return str(unit or "").strip().lower() in {"kg", "g"}


def ecoinvent_amount(row, mass_data, quantity_data):
    """Compute the ecoinvent flow amount for a component row.
    - kg/g units  → taken from calculated mass (mass_data must not be None)
    - m2 unit     → taken from calculated area quantity (quantity_data must not be None)
    """
    flow = str(row.get("Ecoinvent_flow") or "").strip()
    unit = _get_quantity_context_unit(row) or "kg"
    direction = str(row.get("Direction") or "").strip() or "Input"

    if flow == "":
        return None

    if is_mass_unit(unit):
        if mass_data is None:
            raise ValueError(
                f"Unit is '{unit}' but mass data is missing — fill Quantity_per_element (kg, with Has_datasheet_info=YES) or geometry + density"
            )
        amount = mass_data["Total_mass_kg"] if unit.lower() == "kg" else mass_data["Total_mass_g"]
    elif unit.lower() == "m2":
        if quantity_data is None:
            raise ValueError(
                "Unit is 'm2' but area quantity is missing — fill L_mm and W_mm (Has_datasheet_info=YES) or Quantity_per_element"
            )
        amount = quantity_data["Total_quantity"]
    else:
        raise ValueError(
            f"Unsupported unit '{unit}'. Use kg/g for mass-based flows or m2 for area-based flows."
        )

    return {
        "Flow": flow,
        "Unit": unit,
        "Direction": direction,
        "Amount": amount,
    }

##RECEIVES THE INPUTS FROM THE EXCEL AND CREATES THE CSV WITH THE PARAMETERS TO BE USED IN THE PIPELINE
def run_pipeline(input_csv, results_csv, component_flows_csv, grouped_flows_csv):
    sorted_rows = []
    component_results = []
    component_flows = []
    grouped_flows = OrderedDict()
    errors = []

    raw_rows = []
    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        input_headers = list(reader.fieldnames or [])
        for idx, row in enumerate(reader, start=2):
            raw_rows.append((idx, row))

    required_grouping_headers = ["Section"]
    missing_headers = [h for h in required_grouping_headers if h not in input_headers]
    if missing_headers:
        raise ValueError(
            "Input CSV is missing required column(s): "
            + ", ".join(missing_headers)
            + ". Add them as input parameters in *_component_parameters.csv."
        )

    missing_grouping_rows = _validate_required_grouping_fields(raw_rows)
    if missing_grouping_rows:
        preview = "; ".join(
            [f"row {idx} ({designators or 'no designator'})" for idx, designators, _ in missing_grouping_rows[:10]]
        )
        raise ValueError(
            "Section is a required input parameter for all rows. "
            f"Missing values found in: {preview}"
        )

    input_conflicts = _validate_input_consistency(raw_rows)
    if input_conflicts:
        preview_lines = []
        for idx, designators, conflict_type, fields in input_conflicts[:10]:
            if conflict_type == "datasheet_mass_missing_quantity":
                preview_lines.append(
                    f"row {idx} ({designators}): Has_datasheet_info=YES with mass unit requires Quantity_per_element"
                )
            elif conflict_type == "datasheet_mass_has_geometry":
                preview_lines.append(
                    f"row {idx} ({designators}): Has_datasheet_info=YES with mass unit cannot include {', '.join(fields)}"
                )
            else:
                preview_lines.append(
                    f"row {idx} ({designators}): L_mm, W_mm and H_mm are filled, so Volume_cm3_excel must be blank"
                )
        preview = "; ".join(preview_lines)
        raise ValueError(
            "Contradictory input values found in *_component_parameters.csv. "
            f"Fix these rows before running the pipeline: {preview}"
        )

    row_metadata = _build_row_metadata([row for _, row in raw_rows])

    for (idx, row), meta in zip(raw_rows, row_metadata):
        merged_row = dict(row)
        for key, value in meta.items():
            if _clean_text(merged_row.get(key)) == "":
                merged_row[key] = value
        sorted_rows.append((idx, merged_row, meta))

    sorted_rows.sort(key=lambda item: _sort_key(item[1]))

    for idx, row, meta in sorted_rows:
        result_row = dict(row)
        mass_data = compute_component_mass(row)  # returns None if data missing — not an error yet
        quantity_data = _build_quantity_data(row, mass_data)
        if quantity_data is not None:
            result_row["Quantity_per_element"] = round(quantity_data["Quantity_per_element"], 12)
            result_row["Total_quantity"] = round(quantity_data["Total_quantity"], 12)
        else:
            result_row["Total_quantity"] = ""

        unit = _get_quantity_context_unit(row)
        needs_mass = is_mass_unit(unit)
        needs_area = unit.lower() == "m2"
        validation_error = ""

        if mass_data is not None:
            result_row.update(
                {
                    "Method": mass_data["Method"],
                    "Volume_cm3": "" if mass_data["Volume_cm3"] is None else round(mass_data["Volume_cm3"], 9),
                    "Mass_per_element_g": round(mass_data["Mass_per_element_g"], 6),
                    "Density_used_g_cm3": ""
                    if mass_data["Density_used_g_cm3"] is None
                    else round(mass_data["Density_used_g_cm3"], 6),
                    "Density_source": mass_data["Density_source"],
                    "Validation_error": "",
                }
            )
        else:
            result_row.update(
                {
                    "Method": "PENDING" if not needs_mass else "MISSING_MASS",
                    "Volume_cm3": "",
                    "Mass_per_element_g": "",
                    "Density_used_g_cm3": "",
                    "Density_source": "",
                    "Validation_error": "Mass data not yet filled" if needs_mass else "",
                }
            )
            if needs_mass:
                validation_error = "Mass data not yet filled (unit is kg/g — fill Quantity_per_element in kg with Has_datasheet_info=YES, or geometry + density)"
                errors.append({"row": idx, "component": row.get("Designators", ""), "error": validation_error})

        if needs_area and quantity_data is None:
            area_error = "Area data not yet filled (unit is m2 — fill L_mm and W_mm with Has_datasheet_info=YES, or Quantity_per_element)"
            result_row["Validation_error"] = area_error
            errors.append({"row": idx, "component": row.get("Designators", ""), "error": area_error})
        elif needs_area and quantity_data is not None:
            result_row["Method"] = quantity_data["Method"]

        component_results.append(result_row)

        flow = str(row.get("Ecoinvent_flow") or "").strip()
        if flow:
            flow_entry = {
                "Order_index": meta["Order_index"],
                "Category_order": meta["Category_order"],
                "Group_order": meta["Group_order"],
                "Category": meta["Category"],
                "Section": meta["Section"],
                "Subsection": meta["Subsection"],
                "Designators": row.get("Designators", ""),
                "Casing": row.get("Casing") or "",
                "Part_Number": row.get("Part_Number", ""),
                "Database": row.get("Database", ""),
                "Database_component_title": row.get("Database_component_title", ""),
                "Ecoinvent_flow": flow,
                "Ecoinvent_unit": unit,
                "Direction": str(row.get("Direction") or "Input").strip(),
                "Amount": "",
                "Mass_per_element_g": "" if mass_data is None else round(mass_data["Mass_per_element_g"], 6),
                "Total_mass_g": "" if mass_data is None else round(mass_data["Total_mass_g"], 6),
                "Total_mass_kg": "" if mass_data is None else round(mass_data["Total_mass_kg"], 12),
                "Formula_basis": "",
                "Validation_error": "",
            }

            try:
                flow_row = ecoinvent_amount(row, mass_data, quantity_data)
                flow_entry["Amount"] = round(flow_row["Amount"], 12)
                if is_mass_unit(unit):
                    flow_entry["Formula_basis"] = "mass-based"
                elif unit.lower() == "m2":
                    flow_entry["Formula_basis"] = "area-based"
                key = (flow_row["Flow"], flow_row["Unit"], flow_row["Direction"])
                grouped_flows[key] = grouped_flows.get(key, 0.0) + flow_row["Amount"]
            except Exception as exc:
                flow_entry["Validation_error"] = str(exc)
                # Only add to errors if not already reported above (missing mass for kg unit)
                if not (needs_mass and mass_data is None):
                    errors.append({"row": idx, "component": row.get("Designators", ""), "error": str(exc)})

            component_flows.append(flow_entry)

    if component_results:
        fieldnames = _ordered_result_fieldnames(component_results[0])
        with open(results_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(component_results)

    flow_fieldnames = [
        "Order_index",
        "Category_order",
        "Group_order",
        "Category",
        "Section",
        "Subsection",
        "Designators",
        "Casing",
        "Part_Number",
        "Database",
        "Database_component_title",
        "Ecoinvent_flow",
        "Ecoinvent_unit",
        "Direction",
        "Amount",
        "Mass_per_element_g",
        "Total_mass_g",
        "Total_mass_kg",
        "Formula_basis",
        "Validation_error",
    ]
    with open(component_flows_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flow_fieldnames)
        writer.writeheader()
        if component_flows:
            writer.writerows(component_flows)

    with open(grouped_flows_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Flow", "Unit", "Amount", "Direction"])
        for (flow, unit, direction), amount in grouped_flows.items():
            writer.writerow([flow, unit, round(amount, 12), direction])

    return component_results, component_flows, grouped_flows, errors


def _discover_subsystems(base_dir):
    mapping = {}
    for path in sorted(base_dir.glob("*_component_parameters.csv")):
        name = path.name[: -len("_component_parameters.csv")]
        mapping[name] = path
    return mapping


def _selection_tokens(raw):
    if raw is None:
        return []
    return [token for token in str(raw).replace(",", " ").split() if token]


def _parse_selection(raw, names, subsystems, names_by_lower):
    tokens = _selection_tokens(raw)
    if not tokens:
        raise ValueError("No subsystem selection was provided.")

    has_all = False
    selected = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"all", "todo", "todos", "*", "0"}:
            has_all = True
            continue

        if token in subsystems:
            chosen = token
        elif lowered in names_by_lower:
            chosen = names_by_lower[lowered]
        else:
            try:
                idx = int(token)
            except ValueError:
                idx = -1

            if 1 <= idx <= len(names):
                chosen = names[idx - 1]
            else:
                raise ValueError(
                    f"Subsystem '{token}' not found. Available: {', '.join(names)}"
                )

        if chosen not in selected:
            selected.append(chosen)

    if has_all:
        return list(names)

    if not selected:
        raise ValueError("No valid subsystem was selected.")

    return selected


def _choose_subsystems(subsystems, requested=None):
    names = list(subsystems.keys())
    if not names:
        raise ValueError("No *_component_parameters.csv files were found in the folder.")

    names_by_lower = {name.lower(): name for name in names}

    if requested:
        if isinstance(requested, (list, tuple)):
            combined = " ".join(str(item) for item in requested)
        else:
            combined = str(requested)
        return _parse_selection(combined, names, subsystems, names_by_lower)

    if len(names) == 1:
        return [names[0]]

    print("Available subsystems:")
    print("  0. ALL")
    for i, name in enumerate(names, start=1):
        print(f"  {i}. {name}")

    attempts = 0
    while True:
        raw = input("Choose subsystem number/name (you can provide multiple, e.g. '1 2' or 'all'): ").strip()
        try:
            return _parse_selection(raw, names, subsystems, names_by_lower)
        except ValueError:
            attempts += 1
            print("Invalid selection. Try again.")
        if attempts >= MAX_SELECTION_ATTEMPTS:
            raise ValueError("Too many invalid attempts. Operation canceled.")


def _build_subsystem_paths(base_dir, subsystem):
    input_csv = base_dir / f"{subsystem}_component_parameters.csv"
    results_csv = base_dir / f"{subsystem}_component_mass_results.csv"
    component_flows_csv = base_dir / f"{subsystem}_component_io_flows.csv"
    grouped_flows_csv = base_dir / f"{subsystem}_ipe_flows_from_parameters.csv"
    return input_csv, results_csv, component_flows_csv, grouped_flows_csv


def _auto_refresh_component_libraries(base_dir):
    """Refresh deduplicated libraries unless explicitly disabled.

    Set MASS_CALC_AUTO_REFRESH_LIBRARIES=0 to skip automatic refresh.
    """
    enabled = str(os.getenv("MASS_CALC_AUTO_REFRESH_LIBRARIES", "1")).strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        print("Library refresh skipped: MASS_CALC_AUTO_REFRESH_LIBRARIES is disabled.")
        return

    try:
        from build_component_libraries import build_libraries

        casing_count, part_count, conflict_count = build_libraries(base_dir)
        print(
            "Library refresh completed"
            f": casing={casing_count}, part_number={part_count}, conflicts={conflict_count}"
        )
    except Exception as exc:
        print(f"Warning: library refresh failed: {exc}")


def _auto_sync_parameters_from_libraries(base_dir):
    """Sync library values back into all parameter files unless disabled.

    Set MASS_CALC_AUTO_SYNC_FROM_LIBRARY=0 to skip automatic sync.
    """
    enabled = str(os.getenv("MASS_CALC_AUTO_SYNC_FROM_LIBRARY", "1")).strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        print("Parameter sync skipped: MASS_CALC_AUTO_SYNC_FROM_LIBRARY is disabled.")
        return

    try:
        from build_component_libraries import sync_parameter_files_from_libraries

        files_changed, rows_changed, skipped_ambiguous = sync_parameter_files_from_libraries(base_dir)
        print(
            "Parameter sync completed"
            f": files_changed={files_changed}, rows_changed={rows_changed}, skipped_ambiguous={skipped_ambiguous}"
        )
    except Exception as exc:
        print(f"Warning: parameter sync from libraries failed: {exc}")


def main():
    base = Path(__file__).parent

    _auto_sync_parameters_from_libraries(base)

    requested_selection = sys.argv[1:] if len(sys.argv) > 1 else None
    try:
        subsystems = _discover_subsystems(base)
        selected_subsystems = _choose_subsystems(subsystems, requested_selection)
    except ValueError as exc:
        print(f"Validation error: {exc}")
        return

    all_errors = []
    failed_subsystems = []
    completed_subsystems = []

    for subsystem in selected_subsystems:
        input_csv, results_csv, component_flows_csv, grouped_flows_csv = _build_subsystem_paths(
            base,
            subsystem,
        )

        print(f"\nRunning subsystem: {subsystem}")

        try:
            results, component_flows, grouped_flows, errors = run_pipeline(
                input_csv,
                results_csv,
                component_flows_csv,
                grouped_flows_csv,
            )
        except ValueError as exc:
            failed_subsystems.append((subsystem, str(exc)))
            print(f"Validation error in subsystem '{subsystem}': {exc}")
            continue

        completed_subsystems.append(subsystem)

        print(f"Processed component rows: {len(results)}")
        print(f"Component IO rows: {len(component_flows)}")
        print(f"Exported grouped flows: {len(grouped_flows)}")
        print(f"Results file: {results_csv}")
        print(f"Component IO file: {component_flows_csv}")
        print(f"Grouped flows file: {grouped_flows_csv}")

        for err in errors:
            all_errors.append((subsystem, err))

    if completed_subsystems:
        _auto_refresh_component_libraries(base)

    if all_errors:
        print("\nValidation warnings/errors found:")
        for subsystem, err in all_errors:
            print(f"- [{subsystem}] Row {err['row']} ({err['component']}): {err['error']}")

    if failed_subsystems:
        print("\nSubsystems with validation errors:")
        for subsystem, message in failed_subsystems:
            print(f"- {subsystem}: {message}")

    if not completed_subsystems:
        print("No subsystem completed successfully.")


if __name__ == "__main__":
    main()
