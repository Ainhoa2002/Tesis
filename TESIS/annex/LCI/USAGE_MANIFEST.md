# USAGE MANIFEST — `annex/LCI`

Resumen breve: este archivo lista los scripts principales dentro de `LCI/`, las dependencias (módulos) más relevantes y los archivos de datos (CSV/JSON) que consumen o generan. Útil para limpieza y para identificar qué archivos eliminar o documentar.

Format: Script — Imports relevantes — Data files read/written

- `diagnosis.py` — imports: `csv`, `olca_ipc`, `olca_schema` — reads: `LCI_CONNECTION/.../4Q_output_control_card_ipe_flows_from_parameters.csv` (hardcoded path in file)
- `parameter_library.py` — imports: `json`, `json5`, `pathlib` — reads/writes: `global_parameters.json`
- `csv_reader.py` — imports: `csv` — helper functions: `read_input_rows`, `read_output_rows`, used by import workflow to parse `*_ipe_flows_from_parameters.csv`
- `mass_distribution.py` — imports: `matplotlib` — reads none (contains hardcoded mass values), writes: `mass_distribution_bar.png`, `mass_distribution_pie.png`
- `create_product_systems.py` — imports: `argparse`, `olca_ipc`, `olca_schema`, `pathlib` — scans folders under `LCI/` and uses `*_ipe_flows_from_parameters.csv` files inside system folders
- `main.py` — imports: `olca_ipc`, and local modules (`library_sync`, `process_builder`, `product_system_builder`, `transport_workflow`) — orchestrates whole import pipeline; reads `*_ipe_flows_from_parameters.csv` via `iter_system_csvs`
- `library_sync_cli.py` / `fill_ipe_columns_from_library.py` — imports: `library_sync` — default libraries: `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv` — operate on `*_ipe_flows_from_parameters.csv`
- `library_sync.py` — imports: `csv`, `re`, `pathlib` — reads/updates mapping files: `component_library_ecoinvent_uuid_map.csv`, `component_library_ecoinvent_uuid_provider_map.csv`, writes: `created_flows_uuid_map.csv`, `created_process_uuid_map.csv`
- `product_system_builder.py` — imports: `olca_ipc`, `olca_schema`, `parameter_library` — reads parameters via `parameter_library.get_param`
- `process_builder.py` — imports: `olca_schema`, `csv_reader` — reads `*_ipe_flows_from_parameters.csv` (via `csv_reader` helpers), writes openLCA entities via IPC
- `result_extraction.py` — imports: `pandas`, `json5`, `olca_ipc` — reads config from `global_parameters.json` and (optionally) `RESULTS/result_calculation_explained.py`; writes CSVs into `RESULTS/Deterministic results` (these outputs were removed from annex copy)
- `transport_workflow.py` — imports: `csv`, `pathlib` — reads: `LCI_TRANSPORT/code_transport.csv` and writes generated transport `*_ipe_flows_from_parameters.csv` files under `LCI_TRANSPORT`
- `finder.py` — imports: `olca_ipc`, `olca_schema` — helper to search openLCA for flows/processes
- `fill_ipe_columns_from_library.py` — wrapper CLI that calls `library_sync.run_fill_ipe_columns_from_library`

Notas de limpieza (recomendadas)
- Mantener: all `*.py` en `LCI/`, `global_parameters.json`, `component_library_ecoinvent_*.csv`, `transport_phase_legs_library.csv`, `created_*_uuid_map.csv` (si relevantes)
- Considerar eliminar o archivar fuera del annex: large/generated outputs (`RESULTS/`), plots (`*.png`), HTML exports, and any remaining `__pycache__`/`.pyc` (ya limpiados)
- Corregir: rutas absolutas hardcoded en `diagnosis.py` (apuntar a rutas relativas o parámetros)

Siguientes pasos propuestos
1. Generar un `requirements.txt` minimal desde el entorno (opcional).  
2. Detectar y parametrizar rutas absolutas (ej. `diagnosis.py`).  
3. Añadir docstrings / comentarios en los puntos de entrada (`main.py`, `create_product_systems.py`, `library_sync.py`) y producir pequeños tests o dry-run flags para ver qué archivos son necesarios.

Si quieres, genero ahora un `requirements.txt` aproximado y/o convierto las rutas absolutas detectadas en referencias a `global_parameters.json` o argumentos de línea de comandos.
