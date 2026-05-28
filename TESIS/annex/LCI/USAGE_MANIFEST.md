# USAGE MANIFEST — `annex/LCI`

Brief summary: this document lists the main scripts inside `LCI/`, the most relevant dependencies (modules), and the data files (CSV/JSON) they read or produce. It is useful for cleaning the annex and for identifying which files to keep, archive, or document.

Format: Script — Relevant imports — Data files read/written

- `diagnosis.py` — imports: `csv`, `olca_ipc`, `olca_schema` — reads: `LCI_CONNECTION/.../4Q_output_control_card_ipe_flows_from_parameters.csv` (path is hardcoded in the file)
- `parameter_library.py` — imports: `json`, `json5`, `pathlib` — reads/writes: `global_parameters.json`
- `csv_reader.py` — imports: `csv` — helper functions: `read_input_rows`, `read_output_rows`; used by the import workflow to parse `*_ipe_flows_from_parameters.csv`
- `mass_distribution.py` — imports: `matplotlib` — contains hardcoded mass values; writes: `mass_distribution_bar.png`, `mass_distribution_pie.png`
- `create_product_systems.py` — imports: `argparse`, `olca_ipc`, `olca_schema`, `pathlib` — scans folders under `LCI/` and uses `*_ipe_flows_from_parameters.csv` files inside subsystem folders
- `main.py` — imports: `olca_ipc`, and local modules (`library_sync`, `process_builder`, `product_system_builder`, `transport_workflow`) — orchestrates the import pipeline; reads `*_ipe_flows_from_parameters.csv` using `iter_system_csvs`
- `library_sync_cli.py` / `fill_ipe_columns_from_library.py` — imports: `library_sync` — rely on mapping CSVs: `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv` — operate on `*_ipe_flows_from_parameters.csv`
- `library_sync.py` — imports: `csv`, `re`, `pathlib` — reads/updates mapping files: `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv`; writes: `created_flows_uuid_map.csv`, `created_process_uuid_map.csv`
- `product_system_builder.py` — imports: `olca_ipc`, `olca_schema`, `parameter_library` — obtains parameters via `parameter_library.get_param`
- `process_builder.py` — imports: `olca_schema`, `csv_reader` — reads `*_ipe_flows_from_parameters.csv` (through `csv_reader` helpers), writes openLCA entities via IPC
- `result_extraction.py` — imports: `pandas`, `json5`, `olca_ipc` — reads config from `global_parameters.json` and (optionally) `RESULTS/result_calculation_explained.py`; writes CSV outputs into `RESULTS/Deterministic results` (these outputs were removed from the annex copy)
- `transport_workflow.py` — imports: `csv`, `pathlib` — reads: `LCI_TRANSPORT/code_transport.csv` and generates transport `*_ipe_flows_from_parameters.csv` files under `LCI_TRANSPORT`
- `finder.py` — imports: `olca_ipc`, `olca_schema` — helper to search openLCA for flows/processes
- `fill_ipe_columns_from_library.py` — small CLI wrapper that calls `library_sync.run_fill_ipe_columns_from_library`

Cleanup recommendations
- Keep: all `*.py` in `LCI/`, `global_parameters.json`, `component_library_ecoinvent_*.csv`, `transport_phase_legs_library.csv`, and any `created_*_uuid_map.csv` files that are relevant
- Consider removing or archiving outside the annex: large/generated outputs (`RESULTS/`), plots (`*.png`), HTML exports, and any remaining `__pycache__`/`.pyc` files (already cleaned)
- Fix: hardcoded absolute paths in `diagnosis.py` (replace with relative paths or configuration parameters)

Proposed next steps
1. Optionally generate a minimal `requirements.txt` from the environment.
2. Detect and parametrize absolute paths (e.g. in `diagnosis.py`).
3. Add docstrings/comments at entry points (`main.py`, `create_product_systems.py`, `library_sync.py`) and add small tests or dry-run flags to identify required files.

If you want, I can now generate a tentative `requirements.txt` and/or convert the detected absolute paths into references read from `global_parameters.json` or CLI arguments.
