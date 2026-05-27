README — Annex (LCI)

Short instructions to use the LCI annex included in this repository.

Contents
- The annex includes the cleaned LCI code under `LCI/` and a small set of canonical library CSVs moved to `LCI/archived_libraries/`.
- The original generated outputs are preserved under `LCI/archived_generated_orig/` for inspection.

Quick usage

- Run the smoke harness (dry-run) to validate the annex without needing openLCA IPC:

```powershell
python -u TESIS\annex\LCI\run_smoke.py
```

- Or run the main importer in dry-run mode:

```powershell
python -u TESIS\annex\LCI\main.py --dry-run
```

Notes
- openLCA IPC (`olca_ipc`) is optional for inspection and dry-run; scripts are tolerant to IPC being unavailable. If you want to perform full imports, install and start an openLCA IPC server at localhost:8080.
- Canonical library CSVs were archived to `TESIS/annex/LCI/archived_libraries/`. To restore them to the working annex root, copy the files from `archived_libraries/` back to `TESIS/annex/LCI/`.
- Preserved generated outputs live under `TESIS/annex/LCI/archived_generated_orig/` and were restored from Git history, not regenerated.
- `ANNEX_MANIFEST.md` lists the files included for packaging.

If you want, I can also create a minimal `requirements.txt` that lists runtime dependencies used by the annex.

Contact: repository maintainer (you) — I packaged the annex per your instructions.
