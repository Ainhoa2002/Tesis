# Sankey Diagram Visualization Summary
## LCI System - Power Electronics LCA Project

---

## 1. EXISTING VISUALIZATION PACKAGES & SETUP

### Installed Visualization Packages
- **Plotly** (`plotly.graph_objects`) — PRIMARY visualization library
  - Used extensively in all PLCA notebooks
  - Supports interactive Sankey diagrams
  - Modern HTML-based visualization with export capabilities
  
- **Matplotlib** (`matplotlib.pyplot`) — Secondary library
  - Used in PLCA notebooks for basic plots
  - Good for static charts

### Visualization Examples Found
- **zPLCA notebooks** (4 notebooks with active Plotly usage):
  - `PLCA_model_Buck_Converter_Ecodesign_scenarios_v2.ipynb` — Most comprehensive visualization
  - `PLCA_model_Buck_Converter_Sensitivity_analysis.ipynb`
  - `PLCA_model_Buck_Converter_Detail_design_result_v2.ipynb`
  - `Parametric LCA meta-model for Power Electronics.ipynb`

- **IPC_Connect_with_Python notebooks**:
  - `oplen_lca_connection.ipynb` — Connection examples to openLCA

---

## 2. EXISTING SANKEY INFRASTRUCTURE

### Already Configured in System
The system **already has Sankey configuration parameters** in:
- **File**: [LCI/global_parameters.json](LCI/global_parameters.json)
- **File**: [LCI/RESULTS/result_calculation_explained.py](LCI/RESULTS/result_calculation_explained.py) (lines 139-160)

### Sankey Configuration Parameters
```python
SANKEY_MODE = 1              # 0=disabled, 1=flow-based, 2=impact-based
SANKEY_TOP_FLOWS = 10        # Max nodes in flow-based diagram
SANKEY_TOP_IMPACTS = 5       # Max nodes in impact-based diagram  
SANKEY_MAX_DEPTH = 3         # Maximum upstream levels (NOT YET SUPPORTED)
```

### Modes Explained
- **Mode 0**: Sankey generation disabled
- **Mode 1**: Flow-based Sankey (shows material/energy flows through processes)
- **Mode 2**: Impact-based Sankey (shows impact category contributions)

---

## 3. EXISTING SANKEY IMPLEMENTATION IN OPENLCA

### Current Sankey Generation (Lines 1000-1050 of result_calculation_explained.py)
The system uses **openLCA's native Sankey API**:

```python
# Request Sankey graph from openLCA calculation
sankey_req = o.SankeyRequest(
    impact_category=cat,
    max_nodes=max_nodes,
)

sankey_graph = result.get_sankey_graph(sankey_req)

# Output: sankey_data dictionary with:
# - nodes: [index, provider_name, direct_result, total_result]
# - edges: [node_index, provider_index, upstream_share]
```

### Output Format
- **File**: `{system}_{method}_sankey.json`
- **Content**: JSON structure with process nodes and flow edges
- **Structure**:
  ```json
  {
    "impact_category": "Climate Change",
    "mode": 1,
    "max_nodes": 10,
    "nodes": [
      {
        "index": 0,
        "provider": "Process name",
        "direct_result": 100.5,      // Impact from this process only
        "total_result": 500.0         // Including all upstream
      }
    ],
    "edges": [
      {
        "node_index": 1,              // Receiving process
        "provider_index": 0,          // Supplying process
        "upstream_share": 0.85        // % contribution from supplier
      }
    ]
  }
  ```

---

## 4. DATA FORMATS AVAILABLE FOR SANKEY CONSTRUCTION

### Primary Data Sources

#### A. Flow-based Data (CSV format)
**Files**: `*_ipe_flows_from_parameters.csv`  
**Located**: LCI_CONNECTION/, LCI_MAGNET/, LCI_MEXICO_CONVERTER/, etc.

**Structure**:
```
Flow,UUID,Unit,Amount,Direction,UUID_provider,Transport_phase_codes
"copper, cathode",fbb039f7-f9cc-46d2-b631-313ddb125c1a,kg,0.0839627,Input,9e4d4bb4-2aed-3ef2-9caa-46439cf1c523,
"extrusion, plastic pipes",cdb7b939-f508-49ed-80f3-b39f6137fe1c,kg,0.0368856,Input,9c50ed69-94ad-322b-989f-839b77e10648,
```

**Key Columns**:
- `Flow` — Material/energy name
- `Amount` — Quantity flowing
- `Direction` — Input or Output
- `UUID_provider` — Source provider in openLCA
- `Unit` — kg, item, MJ, etc.

#### B. Process Contribution Data (Generated from openLCA)
**Files**: `{system}_{method}_{category}_upstream.csv`

**Structure**:
```
Process,Contribution,Unit
"Raw material extraction and manufacturing phase",850.5,kg CO2-eq
"Transport phase",125.3,kg CO2-eq
"Use phase",2450.1,kg CO2-eq
```

#### C. Impact Results (Generated from openLCA)
**Files**: `{system}_{method}_impacts.csv`

**Structure**:
```
Impact category,Amount (Raw),Unit,Amount (Normalized),Normalized Unit
"Climate Change",3500.0,kg CO2-eq,0.412,kg CO2-eq/ref
"Water Depletion",150.0,m³,0.0015,m³/ref
```

#### D. Inventory Flows (Generated from openLCA)
**Files**: `{system}_{method}_inventory.csv`

**Structure**:
```
Flow,Amount,Unit,Is input
"CO2",3500.0,kg,False
"Copper ore",125.0,kg,True
"Electricity",2500.0,MJ,True
```

---

## 5. RECOMMENDED SANKEY VISUALIZATION APPROACHES

### Option 1: Use OpenLCA's Native Sankey (RECOMMENDED - Already Partially Implemented)
**Pros**:
- Already configured in system
- Generates JSON output automatically
- Respects openLCA's calculation dependencies
- Supports both flow-based and impact-based modes

**Requirements**:
1. Visualization layer to render the JSON
2. Plotly-based renderer (or D3.js alternative)
3. Already have JSON structure, just need HTML rendering

**Implementation**:
```python
# Already generates: {system}_{method}_sankey.json
# Next step: Create Python function to render JSON → Interactive Plotly Sankey

import plotly.graph_objects as go
import json

def render_sankey_from_json(json_file_path):
    with open(json_file_path) as f:
        sankey_data = json.load(f)
    
    # Extract nodes and edges
    nodes = [n["provider"] for n in sankey_data["nodes"]]
    edges_source = [e["provider_index"] for e in sankey_data["edges"]]
    edges_target = [e["node_index"] for e in sankey_data["edges"]]
    values = [e["upstream_share"] for e in sankey_data["edges"]]
    
    # Create Plotly Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(label=nodes),
        link=dict(source=edges_source, target=edges_target, value=values)
    )])
    
    return fig
```

### Option 2: Construct from CSV Flow Data
**Pros**:
- More flexible, custom aggregation possible
- Can combine multiple data sources
- Good for exploratory analysis

**Cons**:
- Requires manual graph construction
- May not capture all dependency nuances from openLCA

**Data Path**:
```
Flow CSV → Group by provider/recipient → Create Sankey edges → Plotly render
```

### Option 3: Hybrid Approach
**Use openLCA's Sankey structure + Plotly rendering**:
1. openLCA generates flow data structure (already done)
2. Python reads JSON
3. Plotly renders interactive Sankey
4. Export as HTML for reports

---

## 6. KEY FINDINGS: STRUCTURE OF DATA

### Process Dependency Chain
```
Raw Materials (Input Flows)
    ↓
Manufacturing Processes (with UUIDs)
    ↓
Assembly/Transport (optional phases)
    ↓
Use Phase (if applicable)
    ↓
End of Life
    ↓
Final Impact Categories (kg CO2-eq, m³ water, etc.)
```

### Data Availability for Sankey
✓ Process names and UUIDs (from openLCA)  
✓ Flow amounts and directions (from CSV)  
✓ Impact contributions per process (from openLCA calculation)  
✓ Material flow quantities (from CSV)  
✗ Max depth filtering (SANKEY_MAX_DEPTH not yet supported by olca_schema)

---

## 7. EXAMPLE DATA STRUCTURES

### Sankey Node Example
```python
{
    "index": 0,
    "provider": "Copper extraction",
    "direct_result": 50.2,      # This process's direct impact
    "total_result": 450.8       # Including all upstream impacts
}
```

### Sankey Edge Example
```python
{
    "node_index": 2,            # Process receiving input
    "provider_index": 0,        # Process providing input
    "upstream_share": 0.78      # 78% of node_2's input comes from node_0
}
```

### Flow Data Example
```python
{
    "Flow": "copper, cathode",
    "UUID": "fbb039f7-f9cc-46d2-b631-313ddb125c1a",
    "Amount": 0.0839627,
    "Unit": "kg",
    "Direction": "Input",
    "UUID_provider": "9e4d4bb4-2aed-3ef2-9caa-46439cf1c523"
}
```

---

## 8. VISUALIZATION LIBRARIES COMPARISON

| Library | Plotly | D3.js | Graphviz |
|---------|--------|-------|----------|
| Language | Python/JS | JavaScript | Python wrapper |
| Sankey Support | ✓ Native | ✓ Custom | Limited |
| Interactive | ✓ Yes | ✓ Yes | ✗ No |
| Export HTML | ✓ Yes | ✓ Yes | ✓ Yes |
| Integration | ✓ Easy | ⚠ Requires JS | ⚠ System dependency |
| **Recommended** | **✓ YES** | - | - |

---

## 9. NEXT STEPS FOR SANKEY IMPLEMENTATION

### Phase 1: Visualization Layer
```
1. Create sankey_visualizer.py module
2. Read {system}_{method}_sankey.json files
3. Convert to Plotly Sankey format
4. Render interactive HTML
5. Add color coding by impact/flow type
```

### Phase 2: Integration
```
1. Hook into result_extraction.py output
2. Generate Sankey visualizations automatically
3. Export to RESULTS/ folder
4. Add to HTML report templates
```

### Phase 3: Enhancements
```
1. Filter by impact category
2. Toggle between flow-based and impact-based
3. Aggregation levels (top N processes)
4. Depth limiting (when olca_schema supports)
```

---

## 10. CONFIGURATION RECOMMENDATIONS

### For Flow-based Sankey (SANKEY_MODE = 1)
```json
"sankey": {
  "sankey_mode": 1,
  "sankey_top_flows": 12,        // Material flows to show
  "sankey_top_impacts": 5,
  "sankey_max_depth": 3          // May not work - leave as note
}
```

### For Impact-based Sankey (SANKEY_MODE = 2)
```json
"sankey": {
  "sankey_mode": 2,
  "sankey_top_flows": 10,
  "sankey_top_impacts": 8,       // Impact categories to show
  "sankey_max_depth": 3
}
```

---

## 11. SUMMARY TABLE

| Aspect | Status | Location | Format |
|--------|--------|----------|--------|
| Sankey Parameters | ✓ Configured | global_parameters.json | JSON |
| Sankey Generation | ✓ Implemented | result_calculation_explained.py | JSON output |
| Flow Data | ✓ Available | LCI/*/\*_ipe_flows_from_parameters.csv | CSV |
| Process Data | ✓ Available | openLCA DB | via IPC |
| Impact Results | ✓ Available | RESULTS/\*_impacts.csv | CSV |
| Plotly Setup | ✓ Installed | zPLCA notebooks | Working examples |
| **Visualization Rendering** | **✗ TODO** | (New module needed) | HTML/Interactive |
| Export/Reports | ⚠ Partial | RESULTS/ folder | CSV/JSON |

---

## 12. GOTCHAS & NOTES

### Known Limitations
- `SANKEY_MAX_DEPTH` parameter is NOT YET SUPPORTED by olca_schema (documented in code)
- Sankey generation may timeout on very large product systems (60s IPC timeout configured)
- Provider linking conflicts can cause incomplete Sankey generation

### Critical Configuration
- Port 8080 must be available for openLCA IPC connection
- Timeout: 60 seconds for IPC calls (adjustable in code)
- Mode 2 (impact-based) requires LCIA method with impact categories

### Performance Notes
- `SANKEY_TOP_FLOWS` = 10-12 recommended for readability
- `SANKEY_TOP_IMPACTS` = 5-8 recommended (too many becomes cluttered)
- Larger top_N values slow down rendering and IPC calls

---

## 13. RECOMMENDED SANKEY DIAGRAM CONSTRUCTION PATTERN

```python
# 1. Use existing openLCA Sankey as data source
sankey_json = load_json("{system}_{method}_sankey.json")

# 2. Transform to Plotly format
nodes = [n["provider"] for n in sankey_json["nodes"]]
node_colors = assign_colors_by_impact(nodes)

source_indices = [e["provider_index"] for e in sankey_json["edges"]]
target_indices = [e["node_index"] for e in sankey_json["edges"]]
values = [e["upstream_share"] * 100 for e in sankey_json["edges"]]

# 3. Create interactive Sankey
fig = go.Figure(data=[go.Sankey(
    node=dict(
        label=nodes,
        color=node_colors,
        line=dict(color="black", width=0.5)
    ),
    link=dict(
        source=source_indices,
        target=target_indices,
        value=values,
        color="rgba(0,0,0,0.2)"  # Semi-transparent flows
    )
)])

# 4. Add title and export
fig.update_layout(
    title=f"{system} - {sankey_json['impact_category']} Supply Chain",
    height=600,
    font=dict(size=11)
)
fig.write_html(f"{system}_sankey.html")
```

---

## 14. FILE LOCATION REFERENCE

### Configuration Files
- [LCI/global_parameters.json](LCI/global_parameters.json) — Sankey parameters
- [LCI/RESULTS/result_calculation_explained.py](LCI/RESULTS/result_calculation_explained.py) — Sankey generation logic

### Data Source Files
- `LCI_CONNECTION/connector_system_ipe_flows_from_parameters.csv` — Flow data
- `LCI_MEXICO_CONVERTER/SECTION_*_ipe_flows_from_parameters.csv` — Section flows
- `LCI_TRANSPORT/transport_ipe_flows_from_parameters.csv` — Transport flows

### Output Location
- `LCI/RESULTS/` — Generated Sankey JSON and impact results
- `LCI/results/` — Same directory (auto-created)

### Visualization Examples
- [zPLCA/PLCA_model_Buck_Converter_Ecodesign_scenarios_v2.ipynb](zPLCA/PLCA_model_Buck_Converter_Ecodesign_scenarios_v2.ipynb) — Plotly examples
- [IPC_Connect_with_Python/oplen_lca_connection.ipynb](IPC_Connect_with_Python/oplen_lca_connection.ipynb) — openLCA connection

---

## Conclusion

**The project already has solid groundwork for Sankey visualization:**
✓ Sankey data generation (openLCA)  
✓ Configuration parameters set  
✓ CSV flow data available  
✓ Plotly library installed  

**Missing component:**
✗ Visualization rendering layer (convert JSON → interactive HTML)

**Recommended action:**
Create `sankey_visualizer.py` module to transform openLCA's generated JSON into Plotly-based interactive Sankey diagrams for reports and exploration.
