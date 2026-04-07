# LCI Import Workflow

This folder contains the Python importer that reads system CSV files and creates openLCA processes.

## Folder Structure

Each system must be a subfolder inside this `LCI` folder.

Expected current pattern:

- `LCI_CONNECTION/`
- `LCI_MAGNET/`
- `LCI_MEXICO_CONVERTER/`

Inside each system folder, place one or more CSV files with names ending in:

- `*_ipe_flows_from_parameters.csv`

Optional subfolder pattern also supported:

- `<SYSTEM>/LCI/*.csv`

If `<SYSTEM>/LCI/` exists, the importer reads from that subfolder.
If not, it reads CSV files directly from `<SYSTEM>/`.

## What main.py Does

`main.py` now scans all system folders under this directory and imports all matching CSV files.

Before importing a system, `main.py` can auto-run UUID enrichment when the system folder contains:

- `fill_ipe_columns_from_library.py`
- `component_library_ecoinvent_uuid_map.csv`
- optional `component_library_ecoinvent_uuid_provider_map.csv`

This prevents the common failure mode where inputs exist but are skipped because UUIDs are empty.

For each CSV file:

1. It creates/updates one process in openLCA.
2. The process name is taken from the file name before `_ipe`.
3. Inputs are built from rows where `Direction == Input`.
4. Outputs are built from rows where `Direction == Output`.

`Direction` matching is case-insensitive in `csv_reader.py` (`input`, `Input`, `INPUT`, etc.).

## Output Handling Logic

Output rows are handled in two modes:

1. Output row with UUID:
- The existing flow is retrieved from openLCA using that UUID.
- A normal output exchange is added with `amount = Amount` from the CSV.
- No new flow is created.

2. Output row without UUID:
- A product flow is created (or reused by name).
- The flow is configured with two flow properties:
  - Number (reference, factor 1.0)
  - Mass (conversion factor = `Amount`, interpreted as kg per 1 LU)
- The process output exchange is created as quantitative reference with `amount = 1.0`.

This means your CSV can mix both patterns in the same file, and each output row is treated accordingly.

## openLCA Category Mapping

Processes are stored in openLCA using `Process.category`.

Category name comes from the system folder name:

- If folder starts with `LCI_`, that prefix is removed.
- Example: `LCI_MEXICO_CONVERTER` -> category `MEXICO_CONVERTER`.

In this workspace's `olca_schema` version, process category must be a string path (not `o.Category`).

## How To Run

From repository root:

```powershell
.\.venv\Scripts\python.exe .\LCI\main.py --dry-run
```

Dry run only reports detected files and target categories.

Real import:

```powershell
.\.venv\Scripts\python.exe .\LCI\main.py
```

## Common Warnings

- `Flow with UUID ... not found, skipping.`
  - The UUID does not exist in the connected openLCA database.
  - Import continues with the remaining valid inputs.

- `Output flow UUID ... not found for '...', skipping output.`
  - The output row had `Direction=Output` and UUID, but that flow was not found in openLCA.
  - The process is still created if it has other valid exchanges.

- `Skipping <SYSTEM>: no *_ipe_flows_from_parameters.csv files found.`
  - The system folder is present but has no import CSV files yet.

## Provider Assignment

If an input row contains `UUID_provider`, importer logic assigns a default provider to that exchange.

Implementation details in `process_builder.py`:

1. The provider UUID is resolved as an openLCA `Process`.
2. `Exchange.default_provider` is set using `o.Ref` with `ref_type = o.RefType.Process`.

Using `o.Ref` is required for stable persistence of provider links in this workspace's `olca_schema` version.

## Related Scripts

- `process_builder.py`: Builds process exchanges and saves processes (inputs + outputs).
- `csv_reader.py`: Reads input rows and output rows from CSV files.
- `diagnosis.py`: Utility script for UUID troubleshooting.
- `finder.py`: Utility script to search flows in openLCA.
