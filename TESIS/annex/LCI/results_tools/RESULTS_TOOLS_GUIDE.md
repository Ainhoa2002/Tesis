# Results tools — Guide

This single guide summarizes the result extraction and visualization tools included in the annex, how to use their export/configuration options, and where to find the canonical scripts.

Purpose
-------
- Describe the purpose and usage of the scripts that extract results, calculate impacts, normalize values, export data, and generate visualizations (including Sankey diagrams).

Where the canonical scripts live
-------------------------------
- Extraction & calculation: `TESIS/annex/LCI/results_tools/result_calculation_explained.py`
- Interactive visualization: `TESIS/annex/LCI/results_tools/visualize_results_interactive.py`
- Static plotting / impact comparisons: `TESIS/annex/LCI/results_tools/visualize_impact_results.py`
- Sankey generation & exports: `TESIS/annex/LCI/results_tools/sankey_visualizer.py`
- Sankey selector/CLI: `TESIS/annex/LCI/results_tools/sankey_interactive_selector.py`
- Batch Sankey generator: `TESIS/annex/LCI/results_tools/generate_all_sankey_diagrams.py`

Quick usage
-----------
1. Run extraction (dry-run to validate):

```powershell
python TESIS\annex\LCI\results_tools\result_calculation_explained.py --dry-run
```

2. Generate interactive comparison graphs:

```powershell
python TESIS\annex\LCI\results_tools\visualize_results_interactive.py
```

3. Generate Sankey HTML (single or batch):

```powershell
python TESIS\annex\LCI\results_tools\sankey_visualizer.py --input path/to/_sankey.json --output sankey.html
python TESIS\annex\LCI\results_tools\generate_all_sankey_diagrams.py
```

Export & configuration summary
------------------------------
- Export behavior is controlled inside `result_calculation_explained.py` and interactive visualization script.
- Key flags / variables:
  - `EXPORT_RESULT` (bool) — if True, results are copied to `EXPORT_RESULT_FOLDER` as well as local `LCI/RESULTS`.
  - `EXPORT_RESULT_FOLDER` (path) — default export location used in the original runs.
  - Visualization scripts prompt interactively to export graphs; accept default or supply a custom folder.

Normalization and Data Quality (DQ)
----------------------------------
- Normalization: optional; when enabled the impacts CSV files include `Amount (Normalized)` and `Normalized Unit` columns. Enable via `global_parameters.json` under `result_extraction.normalization.enabled`.
- Data Quality: optional extraction of process/exchange DQ (pedigree) into `*_data_quality.json`. Enable via `global_parameters.json` under `result_extraction.data_quality`.

Sankey notes
-----------
- Sankeys support two modes: flow-based and impact-based (configurable). They can be exported as interactive HTML (recommended) and optionally as PNG (requires `kaleido`).
- The notebook `sankey_visualization_guide.ipynb` contained examples and export snippets; the essential export code is included in `sankey_visualizer.py` and described above.

What I removed and why
----------------------
- The following archived docs were consolidated into this file and removed from the archive to avoid duplication:
  - `TESIS/annex/LCI/archived_results_and_tools/LCI/results/EXPORT_CONFIGURATION.md`
  - `TESIS/annex/LCI/archived_results_and_tools/LCI/results/NORMALIZATION_AND_DQ_GUIDE.md`
  - `TESIS/annex/LCI/archived_results_and_tools/LCI/results/VISUALIZATION_GUIDE.md`
  - `TESIS/annex/LCI/archived_results_and_tools/LCI/results/sankey_visualization_guide.ipynb`

Troubleshooting
---------------
- Missing normalized columns: re-run `result_calculation_explained.py` with normalization enabled.
- Export permission errors: verify `EXPORT_RESULT_FOLDER` path and write permissions.
- Sankey PNG export failures: install `kaleido` (`pip install kaleido`).

If you want a longer guide (preserving the full original text or notebook), I can keep these as archived references instead of removing them.

---
Generated/updated by automation on request. For details or to revert the consolidation, ask me to restore any file.
