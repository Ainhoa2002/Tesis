Thesis subsection: Python tool, workflow, characteristics, and limitations

Overview

This project includes a reproducible Python-based toolkit used to generate, validate, and import Life Cycle Inventory (LCI) data into openLCA. The toolkit is intended as an annex to the thesis and provides the source code and canonical CSV inputs required to reproduce the data preparation and import pipeline. The code is organized as an orchestrated pipeline plus a small library that handles UUID/provider mappings, created-object tracking, and optional openLCA IPC interactions.

Core function

The toolkit performs three main roles: (1) generate per-system CSVs (parameter-driven "ipe" flows and component results), (2) fill `UUID` and `UUID_provider` columns from a shared provider library and from created-object libraries produced during import, and (3) create or update openLCA processes via available IPC (optional). These steps can be run independently or in coordinated multi-pass mode to support iterative creation of system objects and consistent provider mapping.

Workflow and reproducibility

- Generation: Converters produce canonical CSVs following a stable naming pattern (e.g., `*_ipe_flows_from_parameters.csv` and `*_component_results.csv`). These CSVs are preserved in the annex to provide the data inputs used in thesis figures and analyses.
- Library sync: `library_sync.py` implements deterministic filling of `UUID`/`UUID_provider` using a global map, a provider map, and created-object maps. Missing providers are recorded and can be optionally resolved against an openLCA instance.
- Import: `main.py` orchestrates the pipeline and provides flags to limit work to specific systems or prefixes so reviewers can run a scoped, fast import instead of the full dataset.
- Validation: `validate_all.py` runs lightweight smoke tests and import-safety checks; it reports results to `validation_report.json` so reviewers can confirm the annex integrity without connecting to openLCA.

Characteristics and design choices

- Import-safety: All scripts are guarded with `if __name__ == "__main__":` and defer optional heavy imports to runtime. This makes the annex safe for static import by automated tools and allows reviewers to inspect code without executing side-effects.
- Minimal preserved inputs: CSV inputs are included, but outputs and database snapshots are not, keeping the annex lightweight while enabling exact reproduction of data-generation steps.
- Optional IPC: Interactions with openLCA are optional and isolated; the code can run in a minimal environment without openLCA. When IPC is available, the toolkit can resolve missing providers and upsert created objects.
- Traceable provenance: Each canonical annex folder contains `validation_report.json`, `ARCHIVE_INVENTORY.txt`, and a short provenance header in `README.md` with the commit hash used for validation.

Limitations

- External dependencies: Some visualizers and IPC functions depend on optional packages (e.g., `olca_ipc`, `plotly`). Reviewers who need visual outputs must install the optional requirements documented in the annex README.
- Determinism depends on external service state: When using openLCA IPC for provider resolution or upsert, results can vary across openLCA instances with different libraries or prior imports. For reproducible benchmarking, run the pipeline in non-IPC mode or snapshot the target openLCA library state.
- Performance/scalability: The toolkit is designed for correctness and reproducibility rather than maximal speed. Large imports may take significant wall time; `main.py` includes filters to limit scope for reviewer convenience.

Suggested thesis language (short)

Include a short paragraph in the methods section describing the annex: where the canonical CSV inputs are stored, the purpose of the library-sync and import pipeline, the validation steps (`validate_all.py`), and the provenance files included for reproducibility. Note the optional nature of openLCA IPC and highlight the import-safety design for reviewer inspection.

Recommended citation point

Reference the annex folder as `TESIS/annex/LCI/` (commit recorded in `README.md`) and include a brief instruction for reviewers to run `validate_all.py` to confirm annex integrity before attempting IPC-enabled imports.