# LCI Import Workflow

This folder contains the orchestration layer that rebuilds LCI CSVs, fills openLCA UUID fields, creates or updates processes, and refreshes the created-object libraries used by later passes.

## Overview

The importer runs multiple coordinated passes:

1. Regenerate system CSVs through optional per-system pipelines.
2. Fill UUID and UUID_provider values in ipe files from global libraries.
3. Create or update openLCA processes from those ipe files.
4. Run a second UUID fill pass using created-object libraries.
5. Re-import the same ipe files so second-pass UUID and provider updates are persisted in openLCA.
6. Run a third targeted UUID fill for system aggregate files when available.

This supports two needs at the same time:

- standard mapping from global ecoinvent libraries
- iterative mapping of project-created flows and providers

## Workflow At A Glance

1. Optional per-system pipelines regenerate source CSVs.
2. Global UUID libraries fill the first pass of each ipe file.
3. openLCA processes are created or overwritten from those ipe files.
4. Created-object libraries are upserted from the import results.
5. A second UUID fill uses the created-object libraries and overwrites both UUID and provider fields.
6. A third targeted fill refreshes aggregate system files when available.

## Folder Layout

Each first-level folder under this LCI folder is treated as one system source.

Current examples:

- LCI_CONNECTION
- LCI_MAGNET
- LCI_MEXICO_CONVERTER

Supported input discovery patterns per system:

- system_root/*.csv
- system_root/LCI/*.csv

Only files ending with *_ipe_flows_from_parameters.csv are imported.

## Main Execution Dynamics

Main orchestration is implemented in [LCI/main.py](LCI/main.py).

Per system, the runtime sequence is:

1. First UUID fill using global libraries:
   - component_library_ecoinvent_uuid_map.csv
   - component_library_ecoinvent_uuid_provider_map.csv
2. Process import for each ipe file:
   - create new process when missing
   - overwrite existing process when already present
3. Upsert update of created-object libraries:
   - created_flows_uuid_map.csv
   - created_process_uuid_map.csv
4. Second UUID fill using created-object libraries only:
   - no provider-library sync from openLCA
   - overwrite UUID enabled
   - overwrite provider enabled
5. Re-import all processed files to apply second-pass updates immediately.
6. Third UUID fill for system aggregate files:
   - target: LCI_SYSTEM/system_ipe_flows_from_parameters.csv
   - source: created_flows_uuid_map.csv + created_process_uuid_map.csv
   - overwrite UUID and UUID_provider enabled

Important: created libraries are updated by key. Existing stale process/provider mappings are replaced, not only appended.

## Core Functions and Responsibility

Main entry and orchestration:

- [main](LCI/main.py)
- [iter_system_folders](LCI/main.py)
- [iter_system_csvs](LCI/main.py)
- [resolve_category_name](LCI/main.py)

UUID filling helpers:

- [run_uuid_fill_if_available](LCI/main.py)
- [run_created_uuid_fill_if_available](LCI/main.py)
- [run_final_system_uuid_fill_if_available](LCI/main.py)
- [run_system_pipeline_if_available](LCI/main.py)

Created-library updates:

- [_upsert_created_flows_library](LCI/main.py)
- [_upsert_created_process_library](LCI/main.py)

Process construction and persistence:

- [process_csv](LCI/process_builder.py)
- [build_process_from_inputs](LCI/process_builder.py)
- [_find_or_create_output_flow](LCI/process_builder.py)

## Process Creation Rules

Process names are derived from file names before _ipe.

Example:

- connector_system_ipe_flows_from_parameters.csv -> connector_system

If a process with that name exists, it is reused and overwritten (exchanges rebuilt). If not, it is created.

Category mapping rule:

- folder names starting with LCI_ lose that prefix when mapped to openLCA category
- example: LCI_MEXICO_CONVERTER -> MEXICO_CONVERTER

## Input and Output Exchange Rules

Input rows:

- UUID is required to resolve the flow
- Amount must be numeric
- UUID_provider is optional and, if valid, is assigned as exchange default provider

Output rows:

1. Output row with UUID:
   - use existing flow by UUID
   - set output exchange amount directly from Amount

2. Output row without UUID:
   - find flow by name or create it
   - if created, configure Number as reference flow property and Mass as secondary property
   - use conversion Amount as kg per 1 LU
   - write quantitative reference output exchange with amount 1.0

## UUID Fill Script Behavior

Shared script: [fill_ipe_columns_from_library.py](LCI/fill_ipe_columns_from_library.py)

Behavior summary:

- fills UUID and UUID_provider by matching Flow
- skips Direction=Output rows
- can auto-sync provider mappings from openLCA unless disabled

Typical command:

```powershell
.\.venv\Scripts\python.exe .\LCI\fill_ipe_columns_from_library.py
```

Single target file:

```powershell
.\.venv\Scripts\python.exe .\LCI\fill_ipe_columns_from_library.py --target-file .\LCI\LCI_CONNECTION\connector_system_ipe_flows_from_parameters.csv
```

Disable provider auto-sync:

```powershell
--no-sync-provider-library
```

Overwrite provider and UUID values:

```powershell
--overwrite-provider --overwrite-uuid
```

Third-round single target example (system aggregate file):

```powershell
.\.venv\Scripts\python.exe .\LCI\fill_ipe_columns_from_library.py --library .\LCI\created_flows_uuid_map.csv --provider-library .\LCI\created_process_uuid_map.csv --target-file .\LCI\LCI_SYSTEM\system_ipe_flows_from_parameters.csv --overwrite-uuid --overwrite-provider --no-sync-provider-library
```

## Running the Workflow

From repository root:

Dry run:

```powershell
.\.venv\Scripts\python.exe .\LCI\main.py --dry-run
```

Real import:

```powershell
.\.venv\Scripts\python.exe .\LCI\main.py
```

## Transport Validation and PCB Handling

Transport aggregation is implemented in [LCI/LCI_TRANSPORT/calculate_transport_mass_by_code.py](LCI/LCI_TRANSPORT/calculate_transport_mass_by_code.py).

Validation checks that should pass after a normal run:

1. No double multiplication in transport:
   - IPE Amount values are already produced by each pipeline and are consumed as-is.
2. Coded totals are stable:
   - `--overall` prints one mass total per transport code.
3. Per-subsystem coded totals are available:
   - default mode prints per subsystem + code and total coded mass.

Important modeling detail:

- PCB/OCB rows in several converter cards are modeled as `m2` flows.
- Component mass totals are in `kg` in `*_component_results.csv`.
- If comparing transport against converter mass on a `kg` basis, PCB/OCB can be added from results using the dedicated flag below.

Commands:

Overall coded mass by transport code:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_TRANSPORT\calculate_transport_mass_by_code.py --root .\LCI --overall
```

Per-subsystem coded mass (default mode):

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_TRANSPORT\calculate_transport_mass_by_code.py --root .\LCI
```

Coded/uncoded diagnostic breakdown:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_TRANSPORT\calculate_transport_mass_by_code.py --root .\LCI --breakdown
```

Include PCB/OCB `kg` mass from component results in transport totals:

```powershell
.\.venv\Scripts\python.exe .\LCI\LCI_TRANSPORT\calculate_transport_mass_by_code.py --root .\LCI --overall --include-pcb-mass-from-results
```

How the PCB/OCB option works:

1. Reads PCB/OCB `Total_mass_kg` from each module `*_component_results.csv`.
2. Reads PCB transport code(s) from each module `*_ipe_flows_from_parameters.csv` PCB flow row.
3. Adds that PCB mass to those same transport code totals.

This avoids duplicating the PCB `m2 -> kg` conversion logic in the transport script and keeps the pipeline result as the single source of truth for PCB mass.

## Practical Notes and Limits

- openLCA IPC must be reachable at localhost:8080 in real mode.
- Direction matching is case-insensitive in CSV readers.
- created_process_uuid_map uses flow reference as key. If two processes share the same output flow name, that key can collide by design.
- created libraries are not intended to mirror all existing database objects; they are intended to record and refresh project-created object mappings.

## Global Parameter Library

The project now includes a general parameter library for cross-folder reuse.

Files:

- [LCI/global_parameters.json](LCI/global_parameters.json)
- [LCI/parameter_library.py](LCI/parameter_library.py)
- [LCI/params.py](LCI/params.py)

Purpose:

- Store shared parameters (for example: masa_patatas) in one place.
- Expose get/set helpers for any script under the repository.
- Store execution scope keys for orchestration control:
   - execution.run_scope: all | single
   - execution.target_system: e.g., MEXICO

## Troubleshooting Patterns

Common messages and meaning:

- Flow with UUID ... not found, skipping.
  - UUID not found in the connected openLCA database.

- Output flow UUID ... not found for ..., skipping output.
  - output row references missing flow UUID.

- no UUID mapping found for ...
  - current library set has no mapping for that flow key.

## Related Files

- [LCI/process_builder.py](LCI/process_builder.py)
- [LCI/csv_reader.py](LCI/csv_reader.py)
- [LCI/fill_ipe_columns_from_library.py](LCI/fill_ipe_columns_from_library.py)
- [LCI/diagnosis.py](LCI/diagnosis.py)
- [LCI/finder.py](LCI/finder.py)
