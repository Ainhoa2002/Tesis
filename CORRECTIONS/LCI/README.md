## Annex — Code used for the thesis

Purpose
-------

Quickstart
----------
1. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies (if present):

```powershell
pip install -r requirements.txt  # if present
```

3. Run the main orchestrator from repository root:

```powershell
.\.venv\Scripts\python.exe .\LCI\main.py --help
```

Included
--------
- `LCI/` — source code and CSV data required to reproduce analyses (converter folders, library CSVs, and result tools)
- `global_parameters.json` — default runtime parameters

Notes & repro tips
------------------
- CSV files named `*_ipe_flows_from_parameters.csv` are the primary inputs/outputs for the pipelines. The annex preserves CSVs; do not delete them.
- Some features require an active openLCA IPC server (localhost:8080) and the `olca_ipc` Python bindings; when openLCA is not running the import/IPC steps will fail with connection errors.
- The converter pipelines support interactive and non-interactive runs (see `Pipeline.py` flags). Use `--yes`, `--dry-run`, or subsystem selection options to run unattended.

Structure and missions
----------------------
This codebase implements three connected missions:

1. Preparation: unit and mass calculations that produce openLCA-ready tables (Mexico converter and helper tools).
2. Communication: multi-pass UUID filling, openLCA process creation, and product-system building.
3. Extraction & visualization: extract deterministic impacts, contribution analyses, and generate comparative visualizations.



