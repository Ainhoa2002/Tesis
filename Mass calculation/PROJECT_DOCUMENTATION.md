# Mass Calculation - Project Documentation

## 1. Software Necessity

This software was developed to transform component data into structured inventories ready for LCA modeling.

Problems it solves:

- Maintain editable and traceable entries by subsystem.
- Standardize quantity and mass calculation.
- Generate reproducible outputs for scenario comparison.
- Connect engineering data with PLCA and openLCA at UPI.

## 2. General System Logic

The system follows a CSV-first approach.

1. The user maintains input tables by subsystem.
2. The pipeline calculates quantities, masses, and flows per component.
3. The pipeline groups equivalent flows for aggregated inventory.
4. Outputs are exported as CSV and, optionally, as Excel.

Operational principle:

- Prioritize traceability and repeatability.

## 3. Design Decisions

- CSV-only operational model: the pipeline depends on CSV files.
- Generic architecture per subsystem: single pipeline for multiple subsystems.
- Interactive editing for parameters and I/O.
- Validation rule: `Section` mandatory and `Subsection` optional.
- Quantity/mass logic dependent on unit (`kg`, `g`, `m2`, or override).
- Component library deduplication based on explicit keys (`Casing + Quantity_per_element`, and `Manufacturer + Part_Number`).

## 4. Naming Conventions

Per subsystem:

- Parameter input: `<subsystem>_component_parameters.csv`
- Optional editable I/O table: `<subsystem>_io.csv`
- Component-level results: `<subsystem>_component_mass_results.csv`
- Component flows: `<subsystem>_component_io_flows.csv`
- Grouped flows: `<subsystem>_ipe_flows_from_parameters.csv`

Shared libraries:

- Casing library: `component_library_by_casing.csv`
- Part number library: `component_library_by_part_number.csv`

This convention enables scalability without duplicating code logic.

## 5. Main Features

- Generic subsystem selection in `Pipeline.py`.
- Add/edit/delete operations in `add_eliminate_component.py`.
- Prompts with field examples for component parameters (except comments/notes).
- Excel to CSV import and CSV duplication in `import_component_parameter_or_io.py`.
- Quick CSV selection via numbered list during duplication.
- Default folder for import/duplication in `Mass calculation`.
- Robust numeric parsing, including scientific notation (example: `8e-05`).
- Deduplicated component library generation from all subsystem parameter files.
- Optional Excel export.

## 6. Scripts and Functional Role

- `Pipeline.py`
  - Executes calculations for a subsystem.
  - Accepts optional argument (`Pipeline.py <subsystem>`).
  - Without argument, prompts to select subsystem.
  - Refreshes deduplicated casing/part-number libraries automatically after execution.

- `build_component_libraries.py`
  - Scans all `<subsystem>_component_parameters.csv` files.
  - Builds unique library rows by `(Casing, Quantity_per_element)` and by `Manufacturer + Part_Number`.
  - Avoids repeated entries across subsystems.
  - Keeps first value when repeated keys conflict and reports warnings.

- `add_eliminate_component.py`
  - Component parameters mode.
  - I/O flows mode.
  - Operations: add, update, delete.
  - Refreshes deduplicated libraries automatically after parameter edits.

- `import_component_parameter_or_io.py`
  - Option 1: Excel to CSV.
  - Option 2: duplicate CSV.

- `export_to_excel.py`
  - Exports selected outputs to workbook.

## 7. Input Requirements and Assumptions

Minimum input to run pipeline:

- `<subsystem>_component_parameters.csv`

Validation rules:

- `Section` must have a value.
- `Subsection` can be empty.

Expected key fields:

- Identification and classification: `Designators`, `Casing`, `Section`, `Subsection`, `Category`
- Quantity: `number_elements`, `unit`, `Quantity_per_element`, `Has_datasheet_info`
- Geometry/density: `L_mm`, `W_mm`, `H_mm`, `Volume_cm3_excel`, `Density_min_g_cm3`, `Density_max_g_cm3`, `Metal_extra_g`, `Other_extra_g`
- LCA mapping: `Ecoinvent_flow`, `Ecoinvent_unit`, `Direction`, `Database`, `Database_component_title`
- Optional manual route: `Ecoinvent_amount_override`

## 8. Pipeline Calculation Logic

### 8.1 Quantity/Mass Basis

- Context `kg` or `g`:
  - Mass-based calculation.
  - Datasheet route: `Has_datasheet_info=YES` + `Quantity_per_element` (kg per element).
  - Geometric route: dimensions/volume + density + extras.

- Context `m2` with `Has_datasheet_info=YES`:
  - Quantity by area:
  - `Area per element (m2) = (L_mm * W_mm) / 1,000,000`

- Other units:
  - `Amount` is taken from `Ecoinvent_amount_override`.

### 8.2 Flow Generation

- I/O is generated per component with its `Amount`.
- Grouped by key `(Flow, Unit, Direction)`.

### 8.3 Outputs

- `<subsystem>_component_mass_results.csv`
- `<subsystem>_component_io_flows.csv`
- `<subsystem>_ipe_flows_from_parameters.csv`

### 8.4 Component Library Logic

- Library source files are all `<subsystem>_component_parameters.csv` files.
- Casing library key: `(Casing, Quantity_per_element)`.
- Part-number library key: `(Manufacturer, Part_Number)`.
- If rows share a key and a field is empty in the first row, the value can be filled from later rows.
- If rows share a key and have different non-empty values in a field, the first value is kept and the conflict is reported.
- Components with same `Casing` but different `Quantity_per_element` are intentionally preserved as separate rows in `component_library_by_casing.csv`.
- Grouped IPE outputs remain grouped by `(Flow, Unit, Direction)` and do not include casing-based grouping.

## 9. Recommended Operation Workflow

1. Create or duplicate inputs:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Edit parameters or I/O:

`python "Mass calculation\\add_eliminate_component.py"`

  Notes:
  - Parameter edits trigger automatic library refresh.

3. Run pipeline:

`python "Mass calculation\\Pipeline.py"`

  Notes:
  - Pipeline execution also triggers automatic library refresh.

Or specifying subsystem:

`python "Mass calculation\\Pipeline.py" inverter_power_card`

4. Export results (optional):

`python "Mass calculation\\export_to_excel.py"`

## 10. Integration with PLCA and openLCA (UPI)

This module is the inventory preparation and calculation layer.

Its function in the project:

- Deliver clean, parameterized, and reproducible outputs for:
  - Analysis and scenarios in PLCA.
  - Model construction and impact assessment in openLCA.

Layer summary:

- `Mass calculation`: data engineering and inventory generation.
- `PLCA` and openLCA: modeling, scenario analysis, and interpretation.

## 11. Important Operational Notes

- The pipeline may emit validation warnings when mass data is missing in `kg/g` context.
- The warning does not imply total execution failure, but does indicate a row pending completion.
- To maintain consistency, use the per-subsystem naming convention across all CSVs.
- If parameter CSVs are edited manually outside scripts, run `build_component_libraries.py` (or `Pipeline.py`) to refresh libraries.
