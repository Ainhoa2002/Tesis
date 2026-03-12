# Mass Calculation Software Logic

## Purpose

This folder implements a CSV-first workflow to build component-level inventories, compute quantities and masses, and generate grouped flows for LCA modeling.

## Design decisions

- CSV-only operational model: the pipeline runs from CSV inputs, not from seed scripts.
- Generic subsystem architecture: one pipeline for any subsystem following naming conventions.
- Interactive editing: one script for component parameters and I/O flows.
- Section required, Subsection optional.
- Mass and quantity logic driven by unit context (`kg`, `g`, `m2`, or override path).

## Naming conventions

- Input parameters: `<subsystem>_component_parameters.csv`
- Optional editable I/O table: `<subsystem>_io.csv`
- Component results: `<subsystem>_component_mass_results.csv`
- Component flow rows: `<subsystem>_component_io_flows.csv`
- Grouped flow totals: `<subsystem>_ipe_flows_from_parameters.csv`

## Core scripts

- `Pipeline.py`: executes calculations for a selected subsystem.
- `add_eliminate_component.py`: add, update, or delete rows in component/I/O CSVs.
- `import_component_parameter_or_io.py`: import Excel to CSV or duplicate CSV.
- `export_to_excel.py`: export generated outputs to Excel.

## Pipeline logic

Input source:

- Required per subsystem: `<subsystem>_component_parameters.csv`

Validation:

- `Section` must be present.
- `Subsection` may be empty.

Quantity and amount calculation:

- `kg` or `g`: mass-based amount from datasheet quantity or geometry+density path.
- `m2` with `Has_datasheet_info=YES`: area from `L_mm * W_mm / 1_000_000`.
- Other units: amount from `Ecoinvent_amount_override`.

Outputs:

- `<subsystem>_component_mass_results.csv`
- `<subsystem>_component_io_flows.csv`
- `<subsystem>_ipe_flows_from_parameters.csv`

## Operator workflow

1. Optional input creation or duplication:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Parameter or I/O editing:

`python "Mass calculation\\add_eliminate_component.py"`

3. Pipeline execution:

`python "Mass calculation\\Pipeline.py"`

or explicitly:

`python "Mass calculation\\Pipeline.py" inverter_power_card`

4. Optional export:

`python "Mass calculation\\export_to_excel.py"`

## Integration intent (PLCA/openLCA at UPI)

The intent of this software is to provide consistent, parameterized inventory outputs that can be consumed by the PLCA workstream and openLCA models used at UPI.

In practice, this folder is the data preparation and calculation layer; PLCA notebooks and openLCA modeling are the downstream interpretation and scenario layer.
