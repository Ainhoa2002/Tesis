# Mass Calculation Workspace Guide

This README describes the full workflow for all subsystems in this folder, not only inverter power card.

## Scope

The folder supports a reusable pattern:

- editable subsystem input CSVs
- interactive add/update/delete tools
- optional import/duplicate helpers
- pipeline scripts that compute component and grouped flow outputs

## Naming convention

Use consistent names per subsystem:

- Input parameters: `<subsystem>_component_parameters.csv`
- Optional editable I/O table: `<subsystem>_io.csv`
- Component results: `<subsystem>_component_mass_results.csv`
- Component flow rows: `<subsystem>_component_io_flows.csv`
- Grouped flow totals: `<subsystem>_ipe_flows_from_parameters.csv`

Current examples in this repository:

- `inverter_power_card_component_parameters.csv`
- `fuse_card_component_parameters.csv`
- `inverter_power_card_io.csv`

## Main scripts

- `import_component_parameter_or_io.py`
  - Option 1: import from Excel to CSV.
  - Option 2: duplicate an existing CSV with chosen output name/folder.

- `add_eliminate_component.py`
  - Interactive editor with two modes:
  - `Component parameters` mode for `<subsystem>_component_parameters.csv`.
  - `I/O flows` mode for `<subsystem>_io.csv`.

- `export_to_excel.py`
  - Exports subsystem results to one Excel workbook.
  - Lets user choose destination folder and output filename.

- `Pipeline.py`
  - Generic pipeline entry point for any subsystem with `<subsystem>_component_parameters.csv`.
  - Accepts an optional subsystem argument; if omitted, it prompts for selection.

## Recommended daily workflow

1. If needed, import from Excel or duplicate CSV:

`python "Mass calculation\\import_component_parameter_or_io.py"`

2. Edit parameters and/or I/O interactively:

`python "Mass calculation\\add_eliminate_component.py"`

3. Run the pipeline:

`python "Mass calculation\\Pipeline.py"`

or pass subsystem explicitly:

`python "Mass calculation\\Pipeline.py" inverter_power_card`

4. Optional export to Excel:

`python "Mass calculation\\export_to_excel.py"`

## CSV-only policy

The pipeline depends on CSV files as inputs.

- Required input per subsystem: `<subsystem>_component_parameters.csv`
- Optional manual I/O table: `<subsystem>_io.csv`
- Excel is optional and only used through `import_component_parameter_or_io.py` when needed.

## Input schema (component parameters CSV)

Expected columns:

- `Designators`
- `Manufacturer`
- `Part_Number`
- `Description`
- `Category`
- `Section`
- `Subsection`
- `number_elements`
- `unit`
- `Quantity_per_element`
- `Has_datasheet_info`
- `L_mm`
- `W_mm`
- `H_mm`
- `Volume_cm3_excel`
- `Density_min_g_cm3`
- `Density_max_g_cm3`
- `Metal_extra_g`
- `Other_extra_g`
- `Database`
- `Database_component_title`
- `Ecoinvent_flow`
- `Ecoinvent_unit`
- `Direction`
- `Ecoinvent_amount_override`
- `Comments`
- `Notes`

## Validation and computed fields

Common computed fields in pipeline outputs:

- `Order_index`
- `Category_order`
- `Group_order`
- `Total_quantity`

Important validation rule:

- `Section` is required in input rows.
- `Subsection` can be empty.

## Quantity and amount logic (current generic pipeline)

The current implementation in `Pipeline.py` applies:

- Unit `kg/g`:
  - Uses mass-based calculation (datasheet or geometry+density).

- Unit `m2` with `Has_datasheet_info=YES`:
  - Computes area from `L_mm` and `W_mm`.
  - Conversion: `m2 = (L_mm * W_mm) / 1_000_000`.
  - Uses this as `Quantity_per_element` and `Total_quantity`.

- Other units:
  - Uses `Ecoinvent_amount_override`.

## Outputs

Per subsystem, pipelines write:

- `<subsystem>_component_mass_results.csv`
- `<subsystem>_component_io_flows.csv`
- `<subsystem>_ipe_flows_from_parameters.csv`

In the current inverter results CSV, key readability columns are placed first:

- `Designators`
- `Section`
- `Subsection`
- `Ecoinvent_unit`
- `unit`
- `Total_quantity`
- `Ecoinvent_flow`
