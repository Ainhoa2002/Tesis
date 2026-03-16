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

Optional:

- Force library rebuild manually:

`python "Mass calculation\\build_component_libraries.py"`

- Disable auto parameter sync for one command/session:

`$env:MASS_CALC_AUTO_SYNC_FROM_LIBRARY='0'`

- Disable auto-refresh for one command/session:

`$env:MASS_CALC_AUTO_REFRESH_LIBRARIES='0'`

Component library logic:

- Source of truth is all `*_component_parameters.csv` files.
- Casing library uniqueness key is `Casing + mass-calculation parameters`:
	- `unit`, `Quantity_per_element`, `Has_datasheet_info`,
	- `L_mm`, `W_mm`, `H_mm`, `Volume_cm3_excel`,
	- `Density_min_g_cm3`, `Density_max_g_cm3`, `Metal_extra_g`.
- Part-number library uniqueness key is `(Manufacturer, Part_Number)`.
- For casing rows with identical mass parameters, only one row is kept and empty fields are completed from other duplicates.
- For same casing with different mass parameters, multiple rows are kept and a warning is printed with the differing parameters.
- Part-number library includes `Subsystems` and keeps multiple rows only when `(Manufacturer, Part_Number)` has conflicting comparison fields.
- Reverse sync (library to parameter files) updates rows only when `Part_Number` has a unique library match; ambiguous repeated part numbers are skipped.
- Grouped IPE flow output (`*_ipe_flows_from_parameters.csv`) is not grouped by casing.

When libraries refresh:

- Parameter files can be auto-synced from libraries at the beginning of `Pipeline.py`.
- Libraries are auto-refreshed after successful `Pipeline.py` runs.
- Automatically after component-parameter edits using `add_eliminate_component.py`.
- If you edit parameter CSV files manually, run `build_component_libraries.py` (or run `Pipeline.py`) to refresh.

For full project documentation (logic, features, workflow, and PLCA/openLCA integration intent), see:

- `Mass calculation/PROJECT_DOCUMENTATION.md`

