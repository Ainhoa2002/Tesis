# Mass Calculation

Quick start:

1. Import/duplicate input CSV if needed:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Edit component and I/O data:

`python "Mass calculation\\add_eliminate_component.py"`

3. Run pipeline (libraries refresh automatically):

`python "Mass calculation\\Pipeline.py"`

4. Optional export:

`python "Mass calculation\\export_to_excel.py"`

Optional:

- Force library rebuild manually:

`python "Mass calculation\\build_component_libraries.py"`

- Disable auto-refresh for one command/session:

`$env:MASS_CALC_AUTO_REFRESH_LIBRARIES='0'`

Component library logic:

- Source of truth is all `*_component_parameters.csv` files.
- Casing library uniqueness key is `(Casing, Quantity_per_element)`.
- Part-number library uniqueness key is `(Manufacturer, Part_Number)`.
- If the same key appears more than once, empty fields are completed from later rows.
- If repeated keys have conflicting non-empty values, the first value is kept and a warning is printed.
- Same `Casing` with different `Quantity_per_element` values is stored as separate rows in `component_library_by_casing.csv`.
- Grouped IPE flow output (`*_ipe_flows_from_parameters.csv`) is not grouped by casing.

When libraries refresh:

- Automatically after component-parameter edits using `add_eliminate_component.py`.
- Automatically after running `Pipeline.py`.
- If you edit parameter CSV files manually, run `build_component_libraries.py` (or run `Pipeline.py`) to refresh.

For full project documentation (logic, features, workflow, and PLCA/openLCA integration intent), see:

- `Mass calculation/PROJECT_DOCUMENTATION.md`

