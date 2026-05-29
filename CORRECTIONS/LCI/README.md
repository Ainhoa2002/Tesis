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

- Converter pipelines (`LCI/LCI_MEXICO_CONVERTER/Pipeline.py`) calculate the unit and mass distribution for each subsystem and write three main CSV outputs per module:
	- `*_component_parameters.csv` — module parameter values;
	- `*_component_io_flows.csv` — component input/output flow table;
	- `*_ipe_flows_from_parameters.csv` — the IPE rows calculated from those parameters and mass distributions.

	The `*_ipe_flows_from_parameters.csv` file is the main converter output. It contains the automatically generated IPE entries, including transport codes, amounts, and PCB/OCB mass rows when applicable. Downstream tools such as `library_sync`, `process_builder`, and the product-system builders read this file to fill UUIDs and continue the import flow.

	The converter also relies on library CSVs that store UUID and provider mappings. The main ones are `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv`, `created_flows_uuid_map.csv`, and `created_process_uuid_map.csv`. These files keep the converter outputs matched with the openLCA database and with project-created objects.

	Auxiliary scripts in `LCI_MEXICO_CONVERTER/` support this converter but are secondary to the main pipeline. The main helper scripts are `build_component_libraries.py`, `import_component_parameter_or_io.py`, `add_eliminate_component.py`, `find_component.py`, `export_to_excel.py`, and `fill_ipe_columns_from_library.py`.
	`update_ipe_with_uuid.py` is not referenced by the current code flow, so it is omitted from the active helper list.

- Magnet pipeline (example: `LCI/LCI_MAGNET/Pipeline.py`): follows the same pattern as the converter — it computes per-component masses and writes `*_ipe_flows_from_parameters.csv`. Domain-specific adjustments happen inside the Magnet pipeline, but IPE creation is automated.


- Connector modules: the connector has being implemented in openLCA because it has waste products as outputs and as commented that is a limitation to the tool.

- Auxiliary components: some modules are auxiliary components created directly without a mass-calculation step. These modules are represented by small CSVs or module files that define component entries and include the IPE rows directly (no `Pipeline` computation). They are used for helper parts, fixed connectors or library-only items where parameterised mass distributions are unnecessary. Downstream tools (`library_sync`, `process_builder`, `product_system_builder`) treat them the same way: UUIDs are filled and processes are imported via IPC.

- Mass visualization across subsystems is handled by `mass_visuals_app.py`. It is a Streamlit app that reads the `*_component_mass_results.csv` files from the converter outputs, lets you filter by subsystem and component, and shows bar charts and treemaps so you can inspect the mass distribution per subsystem interactively.

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
`product_system_builder.py` is a standalone CLI and module used to create product systems in openLCA for given process names or UUIDs. It supports parameter-driven defaults and optional interactive prompting.

Key parameters and configuration
--------------------------------
- `product_systems_prefer_defaults` — list of process names that should prefer default providers.
- `product_systems_module` — dict with `components` entries providing per-process `provider_linking` hints.
- `product_systems_interactive_mode` — 0 (silent) or 1 (interactive). When silent, prompts are suppressed and parameter values drive behavior.

Main behavior and functions
--------------------------
- `create_product_systems_for_processes(client, process_inputs, strategy, prefer_defaults_processes, component_mode_map)` — main entry that iterates inputs and calls `create_or_update_product_system` for each.
- `create_or_update_product_system(client, process_input, strategy, ...)` — resolves input (name or UUID), selects provider linking mode via `_select_provider_linking`, checks for existing product system, and creates one with `client.create_product_system(process_ref, LinkingConfig(...))` when needed. Returns `ProductSystemCreationReport`.

Provider linking selection logic
-------------------------------
- When `strategy='parameter'` the selection order is:
	1) explicit `product_systems_module.components` entry for the process;
	2) membership in `product_systems_prefer_defaults`;
	3) fallback to `ONLY_DEFAULTS`.

CLI flags and examples
----------------------
- `--process-names` — comma-separated names or UUIDs to build product systems for.
- `--provider-linking` — override linking strategy (`parameter`, `prefer-defaults`, `only-defaults`, `ignore-defaults`).
- `--interactive` — prompt user for process names and linking choice.
- `--set-module-components` / `--set-prefer-default-processes` / `--set-interactive-mode` — CLI helpers to update parameter library entries.

Integration with the orchestrator
---------------------------------
- `LCI/main.py` can optionally create product systems after it finishes importing processes.
- This happens only when `--product-systems` is not `none`.
- If you use `--product-systems imported`, `main.py` takes the process names that were successfully imported in the first pass and sends those names to `create_product_systems_for_processes`.
- If you use `--product-systems names`, you must also provide the list of process names with `--product-system-names`.
- In short: `main.py` does the import first, then it asks `product_system_builder.py` to create product systems for the selected processes.

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



