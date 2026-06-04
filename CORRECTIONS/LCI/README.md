## Annex — Code used for the project

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
- CSV files named `*_ipe_flows_from_parameters.csv` are the main inputs and outputs for the pipelines. Keep the CSVs in place.
- Some features require an active openLCA IPC server (localhost:8080) and the `olca_ipc` Python bindings; when openLCA is not running the import/IPC steps will fail with connection errors.
- The converter pipelines support interactive and non-interactive runs (see `Pipeline.py` flags). Use `--yes`, `--dry-run`, or subsystem selection options to run unattended.

Structure and missions
----------------------
This codebase implements three connected missions. The paragraphs below expand the first mission (preparation) showing how `_ipe_` flows are created inside `LCI` and summarise the other two missions.

1) Preparation — how `_ipe_` flows are created

- For each module, one input file, `*_component_parameters.csv`, is used to generate three main CSV files:
	- `*_component_results.csv`, containing the calculated mass per component;
	- `*_component_io_flows.csv`, containing the component input/output flow table;
	- `*_ipe_flows_from_parameters.csv`, containing the inventory rows calculated from the component parameters and mass distributions.

	The `*_ipe_flows_from_parameters.csv` file is the main converter output. It contains the automatically generated IPE entries, including transport codes, amounts, and PCB/OCB mass rows when applicable. Downstream tools such as `library_sync`, `process_builder`, and the product-system builders read this file to fill UUIDs and continue the import flow.

	The converter also relies on library CSVs that store UUID and provider mappings. The main ones are `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv`, `created_flows_uuid_map.csv`, and `created_process_uuid_map.csv`. These files keep the converter outputs matched with the openLCA database and with project-created objects.

	Auxiliary scripts in `LCI_MEXICO_CONVERTER/` support this converter but are secondary to the main pipeline. The main helper scripts are `build_component_libraries.py`, `import_component_parameter_or_io.py`, `add_eliminate_component.py`, `find_component.py`, `export_to_excel.py`, and `fill_ipe_columns_from_library.py`.

- Mass visualization across subsystems is handled by `mass_visuals_app.py`. It is a Streamlit app that reads the `*_component_mass_results.csv` files from the converter outputs, lets you filter by subsystem and component, and shows bar charts and treemaps so you can inspect the mass distribution per subsystem interactively.

- Magnet pipeline (example: `LCI/LCI_MAGNET/Pipeline.py`): follows the same pattern as the converter — it computes per-component masses and writes `*_ipe_flows_from_parameters.csv`. Domain-specific adjustments happen inside the Magnet pipeline, but IPE creation is automated.


- Cable/Connector modules: the connector has being implemented in openLCA because it has waste products as outputs and as commented that is a limitation to the tool.

- Auxiliary components: the `LCI_AUXILIARY_COMPONENTS/` folder contains modules that are created directly without a mass-calculation step. These are small CSV-based modules that already include the IPE rows, so there is no `Pipeline` computation for them. For example, `TEN_6-2415N_ipe_flows_from_parameters.csv` is stored directly in `LCI_AUXILIARY_COMPONENTS/`

- Transport phase: transport aggregation scripts (`LCI/LCI_TRANSPORT/calculate_transport_mass_by_code.py`) read the `*_ipe_flows_from_parameters.csv` rows, group by transport code, and produce overall and per-subsystem summaries. 

- Use phase: use-stage masses are calculated by the repository's use-phase scripts; after calculation the corresponding IPE row is added (by hand) into the module `*_ipe_flows_from_parameters.csv`. This applies to both scenarios.

2) Communication — orchestrator (`LCI/main.py`) and product system builder

Overview
--------
`LCI/main.py` is the orchestrator for the import workflow. It runs a multi-phase pipeline that regenerates system CSVs when applicable, attempts multiple UUID fills, imports processes into openLCA, updates local created-object libraries, and re-imports to resolve newly created mappings. The orchestrator supports `--dry-run`, selective `--systems` and `--ipe-prefixes`, and connects to openLCA IPC only when available.

High-level phases (as implemented in `LCI/main.py`)
------------------------------------------------
- Phase 0: Transport preprocessing
	- Calls `prepare_transport_unit_processes(BASE_DIR, dry_run=args.dry_run)` from `LCI/transport_workflow.py` to prepare transport unit processes and any transport preprocessing.

- Phase 1: First fill + first import
	- Enumerates system folders (`iter_system_folders`) and (optionally) runs `Pipeline.py` per system via `run_system_pipeline_if_available` to regenerate `*_ipe_flows_from_parameters.csv` (special cases: `LCI_MEXICO_CONVERTER` runs with `all` and auto-declines optional summaries; `LCI_MAGNET` uses `--skip-fill`).
	- Finds IPE CSVs via `iter_system_csvs` and attempts an initial fill using `run_uuid_fill_if_available` (library_sync).
	- Imports each CSV with `process_csv(client, csv_path, category_name)` (from `process_builder.py`), collecting `ProcessImportReport`s and library rows for later created-library updates.

- Phase 2: Update created libraries
	- Calls `update_created_libraries(BASE_DIR, flow_rows=..., process_rows=...)` to persist `created_flows_uuid_map.csv` and `created_process_uuid_map.csv` built from the first import.

- Phase 3: Second fill + re-import
	- Runs `run_created_uuid_fill_if_available` to apply the newly created-library mappings.
	- Re-imports CSVs with `process_csv` to update processes now that additional UUIDs may be available (second-round reimport).

- Phase 4: Third targeted fill and aggregate re-import
	- Executes final fills for system and transport (`run_final_system_uuid_fill_if_available`, `run_final_transport_uuid_fill_if_available`) and processes aggregate CSVs if present (e.g., `LCI_SYSTEM/system_ipe_flows_from_parameters.csv`, `LCI_TRANSPORT/transport_ipe_flows_from_parameters.csv`).

IPC client and dry-run behavior
--------------------------------
- `--dry-run` lists targets and skips IPC and subprocess operations that would write to openLCA or execute pipelines.
- When not a dry run the script ensures the openLCA IPC server is reachable (`ensure_ipc_server_available`) and constructs `ipc.Client(8080)`.

Auxiliary modules and functions used by `main.py`
-------------------------------------------------
- `transport_workflow.prepare_transport_unit_processes` — transport preprocessing (Phase 0).
- `run_system_pipeline_if_available` — local helper that executes a system `Pipeline.py` when present to regenerate CSVs.
- `library_sync.run_uuid_fill_if_available`, `run_created_uuid_fill_if_available`, `run_final_system_uuid_fill_if_available`, `run_final_transport_uuid_fill_if_available`, `update_created_libraries` — progressive UUID-fill helpers used across phases.
- `process_builder.process_csv` — parses a CSV and creates/updates openLCA `Process` objects; returns `ProcessImportReport` used for summaries and created-library rows.
- `create_product_systems_for_processes` (from `product_system_builder`) — builds product systems after imports when `--product-systems` is requested.

Error handling and resilience
----------------------------
- Major steps are guarded with try/except blocks so one system's failure doesn't abort the entire workflow. Per-file `ProcessImportReport`s are collected in `ImportWorkflowState` for inspection.

Product system builder (`product_system_builder.py`)
	--------------------------------------------------
	Purpose
	-------
	`product_system_builder.py` creates product systems in openLCA from selected process names or UUIDs. It supports default-provider selection and optional interactive prompting, and the orchestrator can call it after importing processes.

	Key points
	---------
	- It can work from the processes imported in the first pass or from an explicit list of names/UUIDs.
	- It can prefer default providers or use component-specific linking hints from the parameter library.
	- `LCI/main.py` calls it after import when `--product-systems` is enabled.
	- If you use `--product-systems imported`, `main.py` sends the successfully imported process names to `create_product_systems_for_processes`.
	- If you use `--product-systems names`, you must also provide the list of process names with `--product-system-names`.

3) Extraction & visualization

Extraction is handled by `LCI/RESULTS/result_calculation.py`. This script connects to openLCA through IPC, calculates each configured product system with the selected LCIA method, and extracts the main outputs from the result object.

What it extracts and where it stores it
--------------------------------------
- Raw impact results are stored as `*_impacts.csv` inside `LCI/RESULTS/Deterministic results/`.
- Normalized impact results are stored as `*_impacts_normalized.csv` in the same folder when normalization is enabled.
- Total inventory flows are stored as `*_inventory.csv`.
- Upstream contribution tables are stored as `*_upstream.csv`, one file per impact category, with the top contributors only.
- Optional data quality information can be stored as `*_data_quality.json` when that export is enabled.
- Optional upstream process trees are stored as `*_process_tree.json`.
- When export is enabled, the same files are also copied to `LCI/RESULTS_export/`.

What the extraction script does
------------------------------
1. Finds the product system in openLCA.
2. Creates a calculation setup with the selected LCIA method.
3. Runs the calculation with timeout protection.
4. Extracts total impacts, normalized impacts, inventory flows, impact contributions, and optional data quality information.
5. Saves the extracted tables and JSON files to the results folders.

The visualization step is handled by `LCI/RESULTS/visualize_results.py`. Its mission is to compare the extracted impact CSVs across multiple product systems and show the results in several graph styles.

Working procedure
-----------------
1. The script scans `LCI/RESULTS/Deterministic results/` for files named `*_impacts.csv`.
2. It loads all available impact tables into pandas.
3. It asks the user to choose:
	- the impact categories to analyze,
	- the product systems to compare,
	- the graph types to generate,
	- whether graphs should be exported.
4. It then generates the selected plots.

Available graph options
-----------------------
- Relative Impact: compares each impact as a percentage of the maximum system value.
- Normalized Comparison: compares normalized values across systems.
- Absolute Impact Comparison: creates one raw-value graph per impact category.
- Horizontal versions of the relative and normalized graphs are also available.

Exporting procedure
-------------------
- If export is enabled, the script writes PNG files to the chosen external folder.
- It also stores the underlying graph data in Excel format so the values can be reused or edited later.
- When exporting, local PNGs in `LCI/RESULTS/` are cleaned up so the exported folder becomes the main output location.

In short: `result_calculation.py` produces the result tables, and `visualize_results.py` reads those tables and turns them into comparison graphs.



