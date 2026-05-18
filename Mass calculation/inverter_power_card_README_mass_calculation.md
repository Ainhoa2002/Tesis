# Parametric Mass + Ecoinvent Workflow

This workflow uses a compact input table so you only edit real per-component input data.
Sorting and grouping columns are computed automatically inside the pipeline.

## Main files

- `inverter_power_card_seed_parameters_from_excel.py`
  - Generates the initial base table from `BoM.xlsx`.
  - This script is optional and should be used only for bootstrap/reset.
  - It is not required in the daily workflow if your parameters CSV is already correct.

- `import_component_parameter_or_io.py`
  - Option 1: import from Excel to CSV.
  - Option 2: duplicate an existing CSV and choose output name/folder.

- `inverter_power_card_component_parameters.csv`
  - Main editable component parameters file.

- `inverter_power_card_io.csv`
  - Editable I/O file when you want to adjust or extend flow rows.

- `add_eliminate_component.py`
  - Interactive editor with two modes:
  - `Component parameters`: add/update/delete component rows.
  - `I/O flows`: add/update/delete I/O rows.

- `inverter_power_card_run_mass_ecoinvent_pipeline.py`
  - Computes quantities and mass depending on unit.
  - Exports component-level and grouped flow outputs.

## Quick workflow

1. Optional bootstrap/reset from Excel (only when needed):

`python "Mass calculation\\inverter_power_card_seed_parameters_from_excel.py"`

2. Optional import/duplicate helper:

`python "Mass calculation\\import_component_parameter_or_io.py"`

3. Daily editing of parameters and/or I/O:

`python "Mass calculation\\add_eliminate_component.py"`

or direct edit of:

`inverter_power_card_component_parameters.csv`

and/or:

`inverter_power_card_io.csv`

4. Run pipeline:

`python "Mass calculation\\inverter_power_card_run_mass_ecoinvent_pipeline.py"`

## Input schema (editable CSV)

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

## Fields computed by the pipeline

Even if they are not in the input CSV, the pipeline computes and adds:

- `Order_index`
- `Category_order`
- `Group_order`
- `Total_quantity`

Notes:

- `Order_index` follows the input row order.
- `Section` and `Subsection` are required for all input rows.

## Mass logic

Mass is only mandatory when flow unit is `kg` or `g`.

If `Ecoinvent_unit` is `kg` or `g`, mass is resolved as:

1. `DATASHEET_QTY_KG`
  - If `Has_datasheet_info=YES` and `Quantity_per_element` is provided, it is interpreted as kg per element.

2. `CALCULATED` or `CALCULATED_FALLBACK`
  - Geometry + density:
  - `Volume_cm3 = (L_mm * W_mm * H_mm) / 1000`
  - If dimensions are missing, fallback to `Volume_cm3_excel`.
  - Effective density priority:
  1. average of `Density_min_g_cm3` and `Density_max_g_cm3`
  2. `Density_min_g_cm3`
  3. `Density_max_g_cm3`
  - `Mass_per_element_g = Volume_cm3 * Density + Metal_extra_g + Other_extra_g`

If mass cannot be resolved for `kg/g`, method is `MISSING_MASS`.

## Area logic for m2

If `Ecoinvent_unit` is `m2` and `Has_datasheet_info=YES`:

- `Quantity_per_element` is calculated from `L_mm` and `W_mm`.
- Conversion used: `m2 = (L_mm * W_mm) / 1_000_000`.
- `Total_quantity = Quantity_per_element * number_elements`.

If `L_mm` or `W_mm` is missing, `Quantity_per_element` from CSV is used as fallback.

## Ecoinvent amount logic

- Unit `kg/g`: uses calculated mass.
- Unit `m2`: uses calculated `Total_quantity` (area-based).
- Other units: uses `Ecoinvent_amount_override`.

## Outputs

- `inverter_power_card_component_mass_results.csv`
  - Full component-level output.
  - The first columns are prioritized for readability:
  - `Designators`, `Section`, `Subsection`, `Ecoinvent_unit`, `unit`, `Total_quantity`, `Ecoinvent_flow`.
  - Uses `Total_quantity` as the unified total quantity field.

- `inverter_power_card_component_io_flows.csv`
  - Component-level flow rows with `Amount`, formula basis, and validation messages.

- `inverter_power_card_ipe_flows_from_parameters.csv`
  - Grouped totals by `(Flow, Unit, Direction)`.
