# Mass Calculation

Quick start:

1. Import/duplicate input CSV if needed:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Edit component and I/O data:

`python "Mass calculation\\add_eliminate_component.py"`

3. Run pipeline:

`python "Mass calculation\\Pipeline.py"`

Subsystem selection options in `Pipeline.py`:

- Interactive menu supports:
	- one subsystem (for example: `1` or `inverter_power_card`)
	- multiple subsystems (for example: `1 2` or `fuse_card inverter_power_card`)
	- all subsystems (`0`, `all`, `todo`, `todos`, or `*`)
- CLI arguments also support multiple selections:
	- `python "Mass calculation\\Pipeline.py" all`
	- `python "Mass calculation\\Pipeline.py" fuse_card inverter_power_card`

4. Optional export:

`python "Mass calculation\\export_to_excel.py"`

Export options in `export_to_excel.py`:

- Interactive menu supports:
	- one subsystem export
	- all-subsystems export
- You can choose the output folder.
- You can set custom output names (`.xlsx`) for each export.
- In all-subsystems mode, it also creates one total BoM workbook with:
	- `Parameters_All` (from `component_library_parameters_all.csv`)
	- `Mass_Results_All` (from `component_library_mass_results_all.csv`)
	- `Ecoinvent_Totals` (from `component_library_ecoinvent_totals.csv`)
- A short export summary text file is generated in the output folder:
	- `export_readme_YYYYMMDD_HHMMSS.txt`

Optional:

- Force library rebuild manually:

`python "Mass calculation\\build_component_libraries.py"`

- Search/edit a part across all subsystems (uses full-storage library when scope is all):

`python "Mass calculation\\find_component.py" <part_number> all`

- Disable auto parameter sync for one command/session:

`$env:MASS_CALC_AUTO_SYNC_FROM_LIBRARY='0'`

- Disable auto-refresh for one command/session:

`$env:MASS_CALC_AUTO_REFRESH_LIBRARIES='0'`

Component library logic:

- Source of truth is all `*_component_parameters.csv` files.
- Full-storage libraries (no deduplication) are also generated automatically:
	- `component_library_parameters_all.csv` (same input headers as `*_component_parameters.csv` + `Subsystem`)
	- `component_library_mass_results_all.csv` (same output headers as `*_component_mass_results.csv` + `Subsystem`)
- Systems/subsystems library is generated from `Section` and `Subsection`:
	- Output file: `component_library_systems_subsystems.csv`.
	- Includes source subsystem files where each pair appears and row counts.
- Casing library uniqueness key is `Casing + mass-calculation parameters`:
	- `unit`, `Quantity_per_element`, `Has_datasheet_info`,
	- `L_mm`, `W_mm`, `H_mm`, `Volume_cm3_excel`,
	- `Density_min_g_cm3`, `Density_max_g_cm3`, `Metal_extra_g`.
- Casing library only includes rows where `Casing` is non-empty (empty values like `""` are excluded).
- Part-number library uniqueness key is `(Manufacturer, Part_Number)`.
- For casing rows with identical mass parameters, only one row is kept and empty fields are completed from other duplicates.
- For same casing with different mass parameters, multiple rows are kept and a warning is printed with the differing parameters.
- Casing warnings ignore `Subsection` as a conflict field.
- Part-number library includes `Subsystems` and keeps multiple rows only when `(Manufacturer, Part_Number)` has conflicting comparison fields.
- Reverse sync (library to parameter files) updates rows only when `Part_Number` has a unique library match; ambiguous repeated part numbers are skipped.
- Grouped IPE flow output (`*_ipe_flows_from_parameters.csv`) is not grouped by casing.
- Compound EcoInvent flows containing `+` are split into multiple components in:
	- `<subsystem>_component_io_flows.csv`
	- `<subsystem>_ipe_flows_from_parameters.csv`
	- `component_library_ecoinvent_totals.csv`
- Split rule:
	- `1 +` creates 2 flow components, `2 +` creates 3 components, etc.
	- each split component keeps the same amount as the original component flow amount.
- Direction rule for split components:
	- if a split component starts with `market ` and original direction is `Input`, the split direction is `previous input`.
	- other split components keep the original direction.
- `find_component.py` in `all` scope reads `component_library_parameters_all.csv` first and falls back to direct file scanning if the storage library is missing.

Validation behavior in `Pipeline.py`:

- `Section` and `Ecoinvent_flow` are required for all rows.
- If either is empty in any row, pipeline stops that subsystem and reports the row numbers.
- Library merge warnings are scoped to the selected subsystem set:
	- selecting specific subsystem(s) shows warnings only for that selection
	- selecting `all` shows warnings across all subsystems

Mass result column `Total_mass_kg`:

- `*_component_mass_results.csv` now includes `Total_mass_kg` right after `Total_quantity`.
- For mass context rows (`kg`/`g`), `Total_mass_kg` follows `Total_quantity` in kg context.
- For `m2` context rows, `Total_mass_kg` is calculated from:
	- `Total_mass_kg = Total_quantity * mass_space_relation_m2/kg`
- If `mass_space_relation_m2/kg` is empty in `m2` rows, `Total_mass_kg` remains empty.


Mass visualization logic (`mass_visuals_app.py`):

- Visualizations use `Total_mass_kg` as the single mass source.
- Components with non-mass EcoInvent units are included whenever `Total_mass_kg` is available.
- Includes:
	- Horizontal bar chart: Top components by mass
	- Treemap: Subsystem > Section > Subsection > Component
	- Treemap: Section > Subsection > Category > Component (all components, all subsystems)
	- Stacked bar chart: Subsystem bars (stacked by Component or Section)

When libraries refresh:

- Parameter files can be auto-synced from libraries at the beginning of `Pipeline.py`.
- Libraries are auto-refreshed after successful `Pipeline.py` runs.
- Automatically after component-parameter edits using `add_eliminate_component.py`.
- If you edit parameter CSV files manually, run `build_component_libraries.py` (or run `Pipeline.py`) to refresh.

For full project documentation (logic, features, workflow, and PLCA/openLCA integration intent), see:

- `Mass calculation/PROJECT_DOCUMENTATION.md`

