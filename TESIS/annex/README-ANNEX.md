README — Annex (LCI)

This README explains the working logic of the annexed LCI system and how data moves from source CSVs to openLCA entities and result-analysis outputs.

System purpose
--------------
- Build or refresh process input CSVs per subsystem.
- Fill UUID/provider mappings in `*_ipe_flows_from_parameters.csv` files from library maps.
- Import processes into openLCA.
- Update created-object libraries for iterative reruns.
- Extract and visualize deterministic LCIA results.

Core workflow (end-to-end)
--------------------------
1. Source generation (optional, per subsystem)
	- Subsystem pipelines can regenerate CSV inputs before import.

2. UUID/provider enrichment
	- `library_sync` fills `UUID` and `UUID_provider` by flow/provider mapping libraries.

3. Process import
	- `main.py` orchestrates import of all selected `*_ipe_flows_from_parameters.csv` files.
	- Existing processes can be updated; missing ones are created.

4. Created-library update
	- New flows/processes discovered during import are persisted into created-object maps.

5. Optional second/final fill
	- Follow-up passes can re-apply UUID/provider data using created-object libraries.

6. Result analysis and visualization
	- `results_tools/result_calculation_explained.py` creates deterministic impact/inventory outputs.
	- Visualization scripts generate comparison charts and Sankey HTML outputs.

Main entry points
-----------------
- Import orchestration: `TESIS/annex/LCI/main.py`
- Smoke validation: `TESIS/annex/LCI/run_smoke.py`
- Result extraction/visualization guide: `TESIS/annex/LCI/results_tools/RESULTS_TOOLS_GUIDE.md`
- Import workflow details: `TESIS/annex/LCI/README.md`

Quick usage
-----------
Dry-run validation (no openLCA write operations):

```powershell
python -u TESIS\annex\LCI\run_smoke.py
python -u TESIS\annex\LCI\main.py --dry-run
```

CSV preservation policy
-----------------------
- CSV datasets are part of the reproducible annex inputs/outputs and are intended to be preserved.
- Deterministic cleanup helpers are configured to keep `.csv` files unless an explicit include-CSV option is used.

Notes
-----
- openLCA IPC (`olca_ipc`) is optional for inspection and dry-run. For full imports, run an openLCA IPC server at `localhost:8080`.
- `ANNEX_MANIFEST.md` lists packaging contents.

Contact
-------
- Repository maintainer.
