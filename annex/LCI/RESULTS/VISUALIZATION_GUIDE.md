# Interactive LCA Results Visualization Guide

## Overview
`visualize_results_interactive.py` provides a terminal-based interface for analyzing and comparing LCA results across multiple product systems.

## Features

### Three Interactive Selection Menus:

1. **Environmental Impacts Selection**
   - Option to analyze ALL impacts or select specific categories
   - Displays all 25+ available environmental impact categories
   - Enter impact numbers (comma-separated, e.g., 1,3,5)

2. **Product Systems Selection**  
   - Option to compare ALL systems or select specific ones
   - Lists all discovered systems with calculated results
   - Enter system numbers (comma-separated)

3. **Graph Types Selection**
   - Option to generate ALL graph types or select specific ones
   - Three graph types available (see below)

### Three Graph Types

#### 1. **Relative Impact** (ONE Combined Graph)
- **What it shows**: All selected environmental impacts in ONE graph showing relative percentages
- **Filename**: `RELATIVE_IMPACT_COMBINED.png`
- **Structure**: Grouped bar chart with:
  - X-axis: Environmental impact categories (all selected)
  - Y-axis: Relative impact percentage (0-110%)
  - Different colors: Different product systems
- **Calculation**: For each EI, max system = 100%, others scaled proportionally
- **Use case**: Compare how different impacts scale relative to each system
- **Example**: 
  - Climate Change impact: System A = 100%, System B = 65%, System C = 42%
  - Water Use impact: System A = 100%, System B = 78%, System C = 51%
  - All visible in one chart for easy comparison

#### 2. **Normalized Comparison** (ONE Combined Graph)
- **What it shows**: All selected environmental impacts in ONE graph using normalized reference values
- **Filename**: `NORMALIZED_COMPARISON_COMBINED.png`
- **Structure**: Grouped bar chart with:
  - X-axis: Environmental impact categories (all selected)
  - Y-axis: Normalized impact value
  - Different colors: Different product systems
- **Prerequisites**: CSV must contain `Amount (Normalized)` column
- **Requires**: Regenerate impacts CSV if normalized values are missing
- **Use case**: Compare systems using reference values (e.g., person-equivalents, regional averages)
- **Note**: Skipped if normalized values not available

#### 3. **Absolute Impact Comparison** (ONE Graph Per Selected EI)
- **What it shows**: ONE graph per environmental impact showing raw values
- **Filename Pattern**: `ABSOLUTE_COMPARISON_{impact_name}.png`
- **Structure**: For each EI:
  - X-axis: Product systems
  - Y-axis: Absolute impact value in original units
  - Different colors: Different product systems (for clarity)
- **Use case**: See the true numerical difference between systems per impact
- **Note**: Generates multiple PNG files (one per selected impact)

## Usage

### Basic Usage
```bash
cd LCI/RESULTS
c:/Users/alorzaga/Git/tesis/.venv/Scripts/python.exe visualize_results_interactive.py
```

### Interactive Workflow
```
1. Select environmental impacts: [a/c]
   - Enter 'a' for all
   - Enter 'c' to choose specific impacts

2. Select product systems: [a/c]
   - Enter 'a' for all
   - Enter 'c' to choose specific systems

3. Select graph types: [a/c]
   - Enter 'a' for all
   - Enter 'c' to choose specific types

4. Review generated graphs in the terminal output
```

### Example Session
```
SELECT ENVIRONMENTAL IMPACTS
[a] Analyze ALL impacts
[c] Choose specific impacts

Enter your choice [a/c]: c
Enter impact numbers (comma-separated, e.g., 1,3,5):
2,4,6  # Selects Climate change, Climate change: fossil, Ecotoxicity: freshwater

SELECT PRODUCT SYSTEMS TO COMPARE
[a] Compare ALL systems  
[c] Choose specific systems

Enter your choice [a/c]: a  # Compare all available systems

SELECT GRAPH TYPES TO GENERATE
[a] Generate ALL graph types
[c] Choose specific types

Enter your choice [a/c]: a  # Generate all three types
```

## Important: Enabling Normalized Comparison

If you see warnings like `⚠ {impact}: No normalized values available, skipping`, follow these steps:

### Step 1: Regenerate Impacts CSV
The impacts CSV must have normalized columns. Run the main calculation script:

```bash
c:/Users/alorzaga/Git/tesis/.venv/Scripts/python.exe result_calculation_explained.py
```

This will:
- Recalculate impacts for all product systems
- Add `Amount (Normalized)` and `Normalized Unit` columns
- Enable normalized comparison graphs

### Step 2: Verify CSV Structure
Check that your CSV has these columns:
```
Impact category | Amount (Raw) | Unit | Amount (Normalized) | Normalized Unit
```

### Step 3: Run Visualization Again
```bash
c:/Users/alorzaga/Git/tesis/.venv/Scripts/python.exe visualize_results_interactive.py
```

## Output Files

All graphs are saved as high-resolution PNG files (300 dpi) in the same directory as the script:

```
LCI/RESULTS/
├── RELATIVE_IMPACT_COMBINED.png                    (ONE file: all selected EIs)
├── NORMALIZED_COMPARISON_COMBINED.png              (ONE file: all selected EIs, if normalized values available)
├── ABSOLUTE_COMPARISON_Acidification.png           (ONE per selected EI)
├── ABSOLUTE_COMPARISON_Climate_change.png
├── ABSOLUTE_COMPARISON_Climate_change_biogenic.png
└── ... (one for each selected impact)
```

### File Count Summary

If you select all 25 impacts and all 3 graph types:
- **Relative Impact**: 1 file (all 25 impacts combined)
- **Normalized Comparison**: 1 file (all impacts with normalized values)
- **Absolute Impact Comparison**: Up to 25 files (one per impact)
- **Total**: ~27 PNG files maximum

## System Requirements

- Python 3.10+
- pandas
- matplotlib
- numpy

## Troubleshooting

### Q: No graphs are generated
**A**: Check that `*_impacts.csv` files exist in the same directory with the correct format.

### Q: Normalized graphs are skipped
**A**: See "Enabling Normalized Comparison" section above.

### Q: Only one system appears
**A**: Only systems with existing `{system_name}_{method}_impacts.csv` files are included.

### Q: Graph files are not created
**A**: Verify you have write permissions in the `LCI/RESULTS/` directory.

## Notes

- Graphs are created one per environmental impact (unless multiple impacts selected)
- For one system with multiple impacts selected: three graph types × N impacts = 3N PNG files
- Graph generation time depends on number of impacts and systems selected
- All graphs are stored in the same directory for easy access
