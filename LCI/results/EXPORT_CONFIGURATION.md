# Export Configuration Guide

## Overview
Both the result extraction and visualization scripts now support exporting results to an external folder in addition to saving locally.

---

## 1. RESULT EXTRACTION EXPORT (result_calculation_explained.py)

### Configuration Parameters

Located at the top of the script (lines 105-120):

```python
# ============================================================================
# RESULT EXPORT SETTINGS
# ============================================================================

# Enable exporting results to external folder
# Type: Boolean
# True = save results to EXPORT_RESULT_FOLDER
# False = save only to current LCI/RESULTS directory
EXPORT_RESULT = True

# Folder where results will be exported
# Type: String (absolute or relative path)
# Default: C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems
EXPORT_RESULT_FOLDER = r"C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems"
```

### Output Files Saved

When `EXPORT_RESULT = True`, the following files are saved to BOTH directories:

**Local Directory** (always):
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_impacts.csv`
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_impacts_normalized.csv`
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_inventory.csv`
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_{impact}_upstream.csv` (per impact)
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_data_quality.json` (if enabled)
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_sankey.json` (if enabled)
- `c:\Users\alorzaga\Git\tesis\LCI\RESULTS\{system}_{method}_process_tree.json` (if enabled)

**Export Directory** (if EXPORT_RESULT = True):
- `C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems\{same files}`

### Usage

1. Edit `EXPORT_RESULT_FOLDER` to change the export destination
2. Set `EXPORT_RESULT = True` to enable export (default: enabled)
3. Run the script normally - it will automatically save to both directories

---

## 2. GRAPH VISUALIZATION EXPORT (visualize_results_interactive.py)

### Interactive Export Selection

When you run the script, after selecting impacts, systems, and graph types, you'll see:

```
======================================================================
EXPORT OPTIONS
======================================================================

Default export folder:
  C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems

Do you want to export graphs to external folder?
  [y] Yes (default)
  [n] No

Enter your choice [y/n]: 
```

### Workflow

1. **Default: Export YES** - Press Enter or type `y` to accept
2. **Custom folder** - Enter folder path, or press Enter for default
3. **No export** - Type `n` to save graphs only locally

### Output Files Generated

**Local Directory** (always):
- `RELATIVE_IMPACT_COMBINED.png`
- `NORMALIZED_COMPARISON_COMBINED.png`
- `ABSOLUTE_COMPARISON_{impact_name}.png` (one per impact)

**Export Directory** (if user selects YES):
- Same three file types to export folder

### Example Console Output

```
[OK] Exported to: C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems\RELATIVE_IMPACT_COMBINED.png
```

---

## 3. Configuration Summary

| Component | Parameter | Default | Type |
|-----------|-----------|---------|------|
| Result Extraction | EXPORT_RESULT | True | Boolean |
| Result Extraction | EXPORT_RESULT_FOLDER | Desktop\LCIA_Power systems | String (path) |
| Graph Visualization | Export prompt | Yes | Interactive |
| Graph Visualization | Export folder | Desktop\LCIA_Power systems | Interactive (with default) |

---

## 4. Troubleshooting

### Results not exporting?
- Check `EXPORT_RESULT = True` in result_calculation_explained.py
- Verify `EXPORT_RESULT_FOLDER` path exists or is writable
- Check console for warning messages about export folder access

### Graphs not exporting?
- Select "Yes" when prompted for export in visualization script
- Verify the export folder path is accessible
- Check console output for export confirmation messages

### Permission denied error?
- Ensure the export folder is writable
- Check that the path is correct
- Try running with administrator privileges if needed

---

## 5. File Organization

After running both scripts with export enabled:

```
Local (LCI/RESULTS/):
  - connector_system_EF v3.1_impacts.csv
  - RELATIVE_IMPACT_COMBINED.png
  - NORMALIZED_COMPARISON_COMBINED.png
  - ABSOLUTE_COMPARISON_*.png (25 files)

Export (Desktop/LCIA_Power systems/):
  - connector_system_EF v3.1_impacts.csv (copy)
  - RELATIVE_IMPACT_COMBINED.png (copy)
  - NORMALIZED_COMPARISON_COMBINED.png (copy)
  - ABSOLUTE_COMPARISON_*.png (copies of all 25)
```
