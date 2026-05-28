LCI annex — one-page outline

Purpose: Provide a compact guide for thesis readers and reviewers to understand, validate, and (optionally) re-run the LCI import pipeline located in `TESIS/annex/LCI/`.

Key files

- README.md — canonical description and provenance header (commit hash and pointers).
- THESIS_SUBSECTION.md — draft text for the methods section (this file).
- validate_all.py — automated smoke checks and import-safety tests. Produces `validation_report.json`.
- validation_report.json — results of the last validation run (included for quick verification).
- ARCHIVE_INVENTORY.txt — inventory of preserved CSV inputs and any archived materials.
- main.py — pipeline orchestrator. Use `--systems` or `--ipe-prefixes` to limit scope.
- library_sync.py — UUID and provider filling logic.
- library_sync_cli.py — CLI wrapper for `library_sync` (import-safe).
- results_tools/ — canonical helpers used to read/write results and canonicalize CSV formats.
- LCI_MEXICO_CONVERTER/ (or other converter folders) — sources of CSV generation scripts.

Quick verification commands (Windows PowerShell with the annex root as CWD)

Run the smoke/validation checks (no openLCA required):

```powershell
.\.venv\Scripts\python.exe TESIS\annex\LCI\validate_all.py
```

If you want to run a scoped import (no IPC):

```powershell
.\.venv\Scripts\python.exe TESIS\annex\LCI\main.py --ipe-prefixes SECTION_01 --dry-run
```

To run provider-only filling (safe, idempotent):

```powershell
.\.venv\Scripts\python.exe TESIS\annex\LCI\library_sync_cli.py --fill-only
```

Reproducibility notes

- CSVs included in the annex are the canonical inputs; do not modify them if you want to reproduce published figures.
- `validate_all.py` performs import-time checks without requiring `olca_ipc`; use it to confirm code is import-safe.
- When using openLCA IPC, note that results depend on the state of the openLCA libraries. For exact reproduction, import order and library snapshots should be recorded.

Contact / provenance

- See the top of `README.md` for the commit hash used when generating the attached `validation_report.json`.
- If you want me to produce a short shell script that runs the commonly used sequence (validate → generate → fill → import), I can add it as `run_all.ps1` and include timing logs.