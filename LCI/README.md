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

For each CSV file:

1. It creates/updates one process in openLCA.
2. The process name is taken from the file name before `_ipe`.
3. Inputs are built from rows where `Direction == Input`.

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

- `Skipping <SYSTEM>: no *_ipe_flows_from_parameters.csv files found.`
  - The system folder is present but has no import CSV files yet.

## Related Scripts

- `process_builder.py`: Builds process exchanges and saves processes.
- `csv_reader.py`: Reads only input rows from CSV files.
- `diagnosis.py`: Utility script for UUID troubleshooting.
- `finder.py`: Utility script to search flows in openLCA.
