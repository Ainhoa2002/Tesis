# Mass Calculation

Quick start:

1. Import/duplicate input CSV if needed:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Edit component and I/O data:

`python "Mass calculation\\add_eliminate_component.py"`

3. Rebuild deduplicated component libraries (by casing and part number):

`python "Mass calculation\\build_component_libraries.py"`

4. Run pipeline:

`python "Mass calculation\\Pipeline.py"`

5. Optional export:

`python "Mass calculation\\export_to_excel.py"`

For full project documentation (logic, features, workflow, and PLCA/openLCA integration intent), see:

- `Mass calculation/PROJECT_DOCUMENTATION.md`

