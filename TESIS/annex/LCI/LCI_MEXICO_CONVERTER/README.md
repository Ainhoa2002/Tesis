# LCI_MEXICO_CONVERTER Workflow

This folder turns component-level parameters into subsystem mass outputs, grouped ipe files, and the converter-level import files consumed by [LCI/main.py](LCI/main.py).

## Overview

The converter workflow transforms subsystem component parameters into:

1. subsystem component mass results
2. subsystem component input-output flow rows
3. grouped subsystem ipe rows ready for UUID filling and openLCA import
4. one converter-level ipe file synchronized from subsystem units

## Main Files

Pipeline and helpers:

- [LCI/LCI_MEXICO_CONVERTER/Pipeline.py](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)
- [LCI/library_sync.py](LCI/library_sync.py)
- [LCI/library_sync_cli.py](LCI/library_sync_cli.py)

Important data files:

- [LCI/LCI_MEXICO_CONVERTER/subsystem_units.csv](LCI/LCI_MEXICO_CONVERTER/subsystem_units.csv)
- [LCI/LCI_MEXICO_CONVERTER/MEXICO_ipe_flows_from_parameters.csv](LCI/LCI_MEXICO_CONVERTER/MEXICO_ipe_flows_from_parameters.csv)

Per-subsystem patterns:

- input: subsystem_component_parameters.csv
- outputs:
  - subsystem_component_results.csv
  - subsystem_component_io_flows.csv
  - subsystem_ipe_flows_from_parameters.csv

## Workflow At A Glance

1. Discover subsystem parameter files.
2. Sync subsystem unit multipliers.
3. Rebuild the converter-level MEXICO aggregate file from subsystem units.
4. Run each selected subsystem pipeline.
5. Fill UUID and UUID_provider for each generated subsystem ipe file.

## Quick Run

From repository root:

Run interactive selection:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py
```

Run all subsystems:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py all
```

Run specific subsystems:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_MEXICO_CONVERTER\Pipeline.py fuse_card inverter_power_card
```

Optional tools:

- add or remove components with [LCI/LCI_MEXICO_CONVERTER/add_eliminate_component.py](LCI/LCI_MEXICO_CONVERTER/add_eliminate_component.py)
- export to Excel with [LCI/LCI_MEXICO_CONVERTER/export_to_excel.py](LCI/LCI_MEXICO_CONVERTER/export_to_excel.py)

## Execution Dynamics

Main runtime sequence in [LCI/LCI_MEXICO_CONVERTER/Pipeline.py](LCI/LCI_MEXICO_CONVERTER/Pipeline.py):

1. Discover subsystems from files ending with _component_parameters.csv.
2. Synchronize subsystem units table:
   - [_sync_subsystem_units_file](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)
3. Synchronize converter-level ipe from subsystem units:
   - [_sync_mexico_ipe_from_subsystem_units](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)
4. Execute selected subsystem pipelines:
   - [run_pipeline](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)
5. Fill UUID and UUID_provider for each generated subsystem ipe:
   - [_fill_uuid_for_subsystem_ipe](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)

## Subsystem Units Behavior

File: [LCI/LCI_MEXICO_CONVERTER/subsystem_units.csv](LCI/LCI_MEXICO_CONVERTER/subsystem_units.csv)

Columns:

- Subsystem
- Quantity_per_subsystem

Rules:

- New discovered subsystems are added with default value 1.
- Removed subsystems are removed from this file on sync.
- Existing subsystem values are preserved.
- Invalid, empty, or non-positive values fallback to 1.0 via [_parse_subsystem_units](LCI/LCI_MEXICO_CONVERTER/Pipeline.py).

Scaling effect:

- Quantity_per_subsystem scales total_quantity, total_mass_kg, and grouped flow amounts.
- Quantity_per_element remains per-component and is not scaled.

## MEXICO ipe Sync Behavior

File: [LCI/LCI_MEXICO_CONVERTER/MEXICO_ipe_flows_from_parameters.csv](LCI/LCI_MEXICO_CONVERTER/MEXICO_ipe_flows_from_parameters.csv)

Function: [_sync_mexico_ipe_from_subsystem_units](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)

Current rules:

- Flow is filled from Subsystem.
- Amount is filled from Quantity_per_subsystem.
- Unit is forced to LU for subsystem-managed rows.
- Direction is forced to Input for subsystem-managed rows.
- Existing matching flow rows are reused, not duplicated.
- Free rows are filled first; new rows are appended only if needed.
- Non-target rows and additional columns are preserved.

## Mass Calculation and Total Mass Reporting

Reusable helper:

- [calculate_subsystem_total_mass](LCI/LCI_MEXICO_CONVERTER/Pipeline.py)

What it does:

- reads subsystem_component_results.csv
- sums Total_mass_kg

Where used:

1. Per-subsystem output row in subsystem ipe files
2. Overall runtime summary print for total mass across selected subsystems

Important practical note:

- The overall total mass shown in terminal summary is currently printed, not persisted into a dedicated summary csv by this pipeline.

## UUID Fill Behavior in Converter Pipeline

During converter pipeline execution, each generated subsystem ipe file is enriched through [LCI/library_sync.py](LCI/library_sync.py) using `run_fill_ipe_columns_from_library`.

Default mapping libraries used by converter pipeline:

- [LCI/component_library_ecoinvent_uuid_map.csv](LCI/component_library_ecoinvent_uuid_map.csv)
- [LCI/component_library_ecoinvent_uuid_provider_map.csv](LCI/component_library_ecoinvent_uuid_provider_map.csv)

Direction=Output rows are intentionally skipped by UUID fill logic.

## Global Import Integration

After converter pipeline outputs are ready, [LCI/main.py](LCI/main.py) imports all ipe files to openLCA.

Global main.py currently performs:

1. First fill pass using global libraries.
2. Process create or overwrite.
3. Upsert update of created libraries.
4. Second fill pass using created libraries:
   - [LCI/created_flows_uuid_map.csv](LCI/created_flows_uuid_map.csv)
   - [LCI/created_process_uuid_map.csv](LCI/created_process_uuid_map.csv)
   - overwrite UUID enabled
   - overwrite provider enabled

## Validation and Guardrails

Current validation highlights in [LCI/LCI_MEXICO_CONVERTER/Pipeline.py](LCI/LCI_MEXICO_CONVERTER/Pipeline.py):

- Section and Ecoinvent_flow are required.
- g is rejected for mass context; kg is required for mass-based inputs.
- subsystem-level failures do not force all subsystems to fail.

Optional environment flags:

- MASS_CALC_AUTO_SYNC_FROM_LIBRARY
- MASS_CALC_AUTO_REFRESH_LIBRARIES
- MASS_CALC_CLEAR_OUTPUTS_ON_FAILURE

## Related Utilities

- [LCI/LCI_MEXICO_CONVERTER/build_component_libraries.py](LCI/LCI_MEXICO_CONVERTER/build_component_libraries.py)
- [LCI/LCI_MEXICO_CONVERTER/find_component.py](LCI/LCI_MEXICO_CONVERTER/find_component.py)
- [LCI/LCI_MEXICO_CONVERTER/mass_visuals_app.py](LCI/LCI_MEXICO_CONVERTER/mass_visuals_app.py)

