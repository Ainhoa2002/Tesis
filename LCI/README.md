# LCI Import Workflow

This folder contains the full openLCA import workflow used by all LCI systems in this repository.

## Scope and Goal

The importer does three things in sequence:

1. Fill UUID and UUID_provider values in ipe files.
2. Create or update openLCA processes from those ipe files.
3. Run a second UUID fill pass using only created-object libraries.

This supports two needs at the same time:

- standard mapping from global ecoinvent libraries
- iterative mapping of project-created flows and providers

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
3. Append-only update of created-object libraries:
   - created_flows_uuid_map.csv
   - created_process_uuid_map.csv
4. Second UUID fill using created-object libraries only.

Important: the created libraries are append-only for new keys and are intended to capture newly created objects that were not already in those files.

## Core Functions and Responsibility

Main entry and orchestration:

- [main](LCI/main.py)
- [iter_system_folders](LCI/main.py)
- [iter_system_csvs](LCI/main.py)
- [resolve_category_name](LCI/main.py)

UUID filling helpers:

- [run_uuid_fill_if_available](LCI/main.py)
- [run_created_uuid_fill_if_available](LCI/main.py)

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

## Practical Notes and Limits

- openLCA IPC must be reachable at localhost:8080 in real mode.
- Direction matching is case-insensitive in CSV readers.
- created_process_uuid_map uses flow reference as key. If two processes share the same output flow name, that key can collide by design.
- created libraries are not intended to mirror all existing database objects; they are intended to record newly created project objects.

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
