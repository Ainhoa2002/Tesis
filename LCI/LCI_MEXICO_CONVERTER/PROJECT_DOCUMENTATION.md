## 6.1. Mass Visualization Treemaps

The Streamlit visualization app (`mass_visuals_app.py`) provides interactive treemaps for exploring the structure and mass distribution of all components:

- **Treemap: Subsystem > Section > Subsection > Component**
  - Shows the hierarchy from subsystem down to individual components, sized by total mass.
- **Treemap: Section > Subsection > Category > Component (all components, all subsystems)**
  - Shows the hierarchy of all components grouped by Section, Subsection, and Category, regardless of subsystem, sized by total mass.

These visualizations help users understand the distribution of mass and the organization of components across the entire system.
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
- Component library deduplication based on explicit keys:
  - Casing key: `Casing + mass-calculation parameter signature`.
  - Part key: `Manufacturer + Part_Number` plus comparison fields to separate true duplicates from variants.

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
- EcoInvent totals library: `component_library_ecoinvent_totals.csv`
- Systems/subsystems library: `component_library_systems_subsystems.csv`
- Full parameters storage library: `component_library_parameters_all.csv`
- Full mass-results storage library: `component_library_mass_results_all.csv`

This convention enables scalability without duplicating code logic.

## 5. Main Features

- Generic subsystem execution in `Pipeline.py` with:
  - single selection,
  - multi-selection (for example `1 2`),
  - all-subsystems option (`0`, `all`, `todo`, `todos`, `*`).
- Add/edit/delete operations in `add_eliminate_component.py`.
- Prompts with field examples for component parameters (except comments).
- Excel to CSV import and CSV duplication in `import_component_parameter_or_io.py`.
- Quick CSV selection via numbered list during duplication.
- Default folder for import/duplication in `Mass calculation`.
- Robust numeric parsing, including scientific notation (example: `8e-05`).
- Deduplicated component library generation from all subsystem parameter files.
- Optional parameter auto-sync from library to parameter CSV files.
- Optional Excel export.
- Export mode selection in `export_to_excel.py` (single subsystem or all subsystems).
- Total BoM workbook export in all-subsystems mode.
- Automatic short export summary text file (`export_readme_*.txt`).

## 6. Scripts and Functional Role

- `Pipeline.py`
  - Executes calculations for one or more subsystems.
  - Accepts optional arguments (`Pipeline.py <selection...>`), including multiple values.
  - Without arguments, prompts to select subsystem(s), including an ALL option.
  - Auto-sync from library is disabled by default (`MASS_CALC_AUTO_SYNC_FROM_LIBRARY=0`).
  - If enabled, sync only fills empty parameter cells and never overwrites existing user values.
  - Refreshes deduplicated casing/part-number libraries automatically after successful execution.
  - Rebuilds consolidated EcoInvent totals library automatically after successful execution.
  - Library merge warnings follow selected scope:
    - selected subsystem(s): warnings only from those subsystems,
    - `all`: warnings from all subsystems.

- `build_component_libraries.py`
  - Scans all `<subsystem>_component_parameters.csv` files.
  - Builds casing library using `Casing + mass-calculation parameter signature`.
  - Builds part-number library using `Manufacturer + Part_Number` and comparison fields.
  - Builds one consolidated EcoInvent totals library from all subsystem component I/O flows.
  - Builds one systems/subsystems library from `Section` and `Subsection` with source subsystem traceability.
  - Builds full-storage libraries (no deduplication) for parameters and mass results with a `Subsystem` column.
  - For equal casing signatures, keeps one row (filling empty fields from duplicates).
  - For casing variants, keeps multiple rows and reports differing mass parameters.
  - Casing warning fields exclude `Subsection` (it does not trigger casing conflict warnings).
  - Supports sync mode (`--sync-parameters` or `sync`) to fill missing parameter values from the part-number library.

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
  - Supports export mode selection:
    - one subsystem,
    - all subsystems.
  - Lets the user choose output folder and custom output file names.
  - In all-subsystems mode, also exports one total BoM workbook with sheets:
    - `Parameters_All` (from `component_library_parameters_all.csv`),
    - `Mass_Results_All` (from `component_library_mass_results_all.csv`),
    - `Ecoinvent_Totals` (from `component_library_ecoinvent_totals.csv`).
  - Writes a short text summary file in output folder:
    - `export_readme_YYYYMMDD_HHMMSS.txt`.

## 7. Input Requirements and Assumptions

Minimum input to run pipeline:

- `<subsystem>_component_parameters.csv`

Validation rules:

- `Section` must have a value.
- `Ecoinvent_flow` must have a value.
- `Subsection` can be empty.
- For mass context (`kg`/`g`): if `Has_datasheet_info=YES`, `Quantity_per_element` is required.

Expected key fields:

- Identification and classification: `Designators`, `Casing`, `Section`, `Subsection`, `Category`
- Quantity: `number_elements`, `unit`, `Quantity_per_element`, `Has_datasheet_info`
- Geometry/density: `L_mm`, `W_mm`, `H_mm`, `Volume_cm3_excel`, `Density_min_g_cm3`, `Density_max_g_cm3`, `Metal_extra_g`, `mass_space_relation_m2/kg`
- LCA mapping: `Ecoinvent_flow`, `Ecoinvent_unit`, `Direction`, `Database`

## 8. Pipeline Calculation Logic

### 8.1 Quantity/Mass Basis

**MASS UNITS: KG ONLY**

The mass calculation system accepts **only kilogram (kg)** as the unit for mass inputs. Gram unit (`g`) is explicitly rejected at validation time with an error message listing problematic rows.

- Context `kg` (mass-based calculation, **only supported mass unit**):
  - Datasheet route: `Has_datasheet_info=YES` requires `Quantity_per_element` in kg.
  - Geometric route: dimensions/volume + density + extras → calculated directly in kg.
  - Direct calculation avoids intermediate gram conversions.

- Context `m2` with `Has_datasheet_info=YES`:
  - Quantity by area:
  - `Area per element (m2) = (L_mm * W_mm) / 1,000,000`

- Other units:
  - Not supported in this workflow. Use `kg` or `m2`.

### 8.2 Flow Generation

- I/O is generated per component with its `Amount`.
- If `Ecoinvent_flow` contains `+`, it is split into multiple flow components.
  - `N` plus signs generate `N+1` components.
  - Each split component keeps the same component `Amount`.
- Split components are written into component I/O and grouped IPE outputs, and then propagated to the consolidated EcoInvent totals library.
- Direction adjustment for split components:
  - If split flow text starts with `market ` and base direction is `Input`, direction is stored as `previous input`.
  - All other split components keep the base direction.
- Grouped by key `(Flow, Unit, Direction)`.

### 8.3 Outputs

- `<subsystem>_component_mass_results.csv`
- `<subsystem>_component_io_flows.csv`
- `<subsystem>_ipe_flows_from_parameters.csv`

Mass result column details:

- `<subsystem>_component_mass_results.csv` includes **only `Total_mass_kg`** as the mass output column.
- `Total_mass_kg` rules:
  - mass unit context (kg): value follows mass-based total quantity computed directly in kg.
  - `m2` unit context: `Total_mass_kg = Total_quantity * mass_space_relation_m2/kg`.
  - if `mass_space_relation_m2/kg` is empty for `m2` rows, `Total_mass_kg` remains empty.
- **Gram-based columns removed**: Historical columns `Mass_per_element_g` and `Total_mass_g` are no longer exported. All mass reporting is in kilograms.

### 8.4 Component Library Logic

- Library source files are all `<subsystem>_component_parameters.csv` files.
- Casing library key uses `Casing + mass-calculation parameter signature`.
- Casing library includes only rows with non-empty `Casing` (empty values are excluded).
- Casing mass-calculation signature fields are:
  - `unit`, `Quantity_per_element`, `Has_datasheet_info`,
  - `L_mm`, `W_mm`, `H_mm`, `Volume_cm3_excel`,
  - `Density_min_g_cm3`, `Density_max_g_cm3`, `Metal_extra_g`.
- Same casing with equal signature is deduplicated into one row.
- Same casing with different signature is stored as multiple rows.
- Casing warning reports exactly which of the signature fields differ.
- Part-number base key is `(Manufacturer, Part_Number)`.
- Exact duplicates for part-number data are collapsed.
- Variant part rows are preserved and warning lists differing comparison fields.
- Part-number library includes `Subsystems` to show where the part appears.
- Sync from library to parameter files updates only unique part-number matches; ambiguous matches are skipped.
- Grouped IPE outputs remain grouped by `(Flow, Unit, Direction)` and do not include casing-based grouping.
- Full-storage libraries keep the original header order from source CSVs and append `Subsystem` as the last column.

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
  - Interactive prompt supports one, multiple, or all subsystems.
  - Examples of interactive answer: `1`, `1 2`, `all`.
  - Pipeline auto-syncs from library first, then runs selected subsystem(s), then refreshes libraries.
  - Library merge warnings printed after refresh are aligned with the selected subsystem scope.

Or specifying subsystem:

`python "Mass calculation\\Pipeline.py" inverter_power_card`

Or multiple/all selections:

`python "Mass calculation\\Pipeline.py" inverter_power_card fuse_card`

`python "Mass calculation\\Pipeline.py" all`

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

### Mass Units (KG ONLY)

- **All mass inputs must be in kilograms (kg)**. Gram unit inputs are rejected at validation with an explicit error listing problematic rows.
- The pipeline calculates mass directly in kg with no intermediate gram conversions, ensuring consistency and clarity.
- All CSV outputs contain only `Total_mass_kg` column for mass reporting.
- Historical gram-based columns (`Mass_per_element_g`, `Total_mass_g`) are permanently removed from pipeline exports.

### General Operational Notes

- The pipeline may emit validation warnings when mass data is missing or inconsistent in kg context.
- The warning does not imply total execution failure, but does indicate a row pending completion.
- To maintain consistency, use the per-subsystem naming convention across all CSVs.
- If parameter CSVs are edited manually outside scripts, run `build_component_libraries.py` (or `Pipeline.py`) to refresh libraries.
- Runtime toggles:
  - `MASS_CALC_AUTO_SYNC_FROM_LIBRARY=0` disables library-to-parameter sync at pipeline start.
  - `MASS_CALC_AUTO_REFRESH_LIBRARIES=0` disables automatic library rebuild after pipeline execution.

Mass visualization (`mass_visuals_app.py`):

- Uses `Total_mass_kg` as the single authoritative source for all mass charts and totals.
- Includes components with any EcoInvent unit when `Total_mass_kg` is available.
