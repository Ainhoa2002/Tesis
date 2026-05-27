# Thesis Annex Manifest

Included folder: `LCI/`

Core scripts and helpers to include:

- `LCI/_utils.py` — centralized CSV and normalization helpers
- `LCI/main.py` — entry point (supports `--dry-run`)
- `LCI/run_smoke.py` — smoke harness for validation
- `LCI/library_sync.py` and `LCI/library_sync_cli.py` — library UUID/provider filling
- `LCI/process_builder.py` — openLCA process/flow builders
- `LCI/transport_workflow.py` — transport CSV preparation
- `LCI/product_system_builder.py` and `LCI/create_product_systems.py`
- `LCI/fill_ipe_columns_from_library.py` — library-backed IPE filling
- `LCI/params.py` and `LCI/global_parameters.json`

Subsystems (examples):

- `LCI/LCI_MEXICO_CONVERTER/` — Mexico converter pipeline and `smoke_test.py`
- `LCI/LCI_MAGNET/` — magnet pipeline
- `LCI/LCI_TRANSPORT/` — transport helpers

Documentation and packaging notes:

- `README.md`, `LICENSE` are present at `TESIS/annex/`
- Preserved original generated outputs are archived under `LCI/archived_generated_orig/`
- Keep `--dry-run` behavior and IPC tolerance (openLCA) in distributed scripts

- Archived library CSVs moved to `LCI/archived_libraries/` (non-generated canonical maps)

If you want, I can now:

- create a zip of `TESIS/annex/LCI` with only the listed files
- add a short `README-ANNEX.md` describing how to run `main.py --dry-run`
