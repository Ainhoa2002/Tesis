"""
Role: Batch-generate Sankey diagrams for all available result sets.

Brief: Runs a non-interactive batch process to create Sankey diagrams for a
collection of result JSON files. Useful for creating an archive of diagrams.
"""

#!/usr/bin/env python3
"""
Generate Sankey diagrams for all available Sankey JSON files.
Creates interactive HTML visualizations and exports them to the designated folder.
"""

import json
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

RESULTS_DIR = Path(__file__).parent / "Deterministic results"
if not RESULTS_DIR.exists():
    RESULTS_DIR = Path(__file__).parent
EXPORT_DIR = RESULTS_DIR / "sankey_html_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FIND ALL SANKEY FILES
# ============================================================================

sankey_files = sorted(RESULTS_DIR.glob("*_sankey.json"))
print(f"Found {len(sankey_files)} Sankey file(s):")
for f in sankey_files:
    print(f"  • {f.name}")

# ============================================================================
# FUNCTION TO CREATE SANKEY DIAGRAM
# ============================================================================

def create_sankey_diagram(sankey_data):
    """Create a Plotly Sankey diagram from extracted sankey data."""
    
    # Extract data
    nodes = sankey_data.get("nodes", [])
    edges = sankey_data.get("edges", [])
    impact_category = sankey_data.get("impact_category", "Unknown")
    mode = sankey_data.get("mode", 1)
    
    if not nodes or not edges:
        print(f"  ⚠ Skipping {impact_category}: no nodes or edges data")
        return None
    
    # ========== NODE PARAMETERS ==========
    node_labels = [n["provider"] for n in nodes]
    node_total_results = [n["total_result"] for n in nodes]
    index_to_position = {n["index"]: position for position, n in enumerate(nodes)}
    index_to_node = {n["index"]: n for n in nodes}
    
    # ========== NODE COLORS ==========
    max_total = max(node_total_results) if node_total_results else 1
    normalized_values = [v / max_total for v in node_total_results]
    
    node_colors = []
    for norm_val in normalized_values:
        r = int(255 * norm_val)
        g = int(150 * (1 - norm_val))
        b = int(100 * (1 - norm_val))
        node_colors.append(f"rgb({r},{g},{b})")
    
    # ========== EDGE PARAMETERS ==========
    edge_sources = []
    edge_targets = []
    edge_values = []
    edge_percentages = []
    
    for edge in edges:
        source_index = edge["provider_index"]
        target_index = edge["node_index"]
        if source_index not in index_to_position or target_index not in index_to_position:
            continue
        edge_sources.append(index_to_position[source_index])
        edge_targets.append(index_to_position[target_index])
        target_node = index_to_node[target_index]
        edge_values.append(edge["upstream_share"] * target_node["total_result"])
        edge_percentages.append(edge["upstream_share"] * 100)
    
    if not edge_sources:
        print(f"  ⚠ Skipping {impact_category}: no valid edges")
        return None
    
    # ========== CREATE SANKEY FIGURE ==========
    fig = go.Figure(data=[go.Sankey(
        orientation="v",
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors,
            customdata=node_total_results,
            hovertemplate='<b>%{label}</b><br>Total Impact: %{customdata:.4f}<extra></extra>'
        ),
        link=dict(
            source=edge_targets,
            target=edge_sources,
            value=edge_values,
            color="rgba(200, 200, 200, 0.4)",
            customdata=edge_percentages,
            hovertemplate='<b>%{source.label}</b><br>Porcentaje: %{customdata:.1f}%<br>Contribución: %{value:.4f}<extra></extra>'
        )
    )])
    
    # ========== CUSTOMIZE LAYOUT ==========
    mode_description = {
        1: "Flow-based (Environmental flows)",
        2: "Impact-based (Impact contributions)"
    }.get(mode, f"Mode {mode}")
    
    fig.update_layout(
        title=dict(
            text=f"<b>LCA Sankey Diagram: {impact_category}</b><br><sub>{mode_description}</sub>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color="#2c3e50")
        ),
        font=dict(
            size=12,
            family="Arial, sans-serif",
            color="#2c3e50"
        ),
        height=700,
        width=1400,
        plot_bgcolor="white",
        paper_bgcolor="#f8f9fa",
        margin=dict(l=20, r=20, t=100, b=20),
        annotations=[
            dict(
                text=f"<i>Configuration: SANKEY_MODE={mode} | NODES={len(nodes)} | EDGES={len(edge_sources)}</i>",
                xref="paper", yref="paper",
                x=0.5, y=-0.05,
                showarrow=False,
                font=dict(size=10, color="gray")
            )
        ]
    )
    
    return fig, len(nodes), len(edge_sources)

# ============================================================================
# GENERATE DIAGRAMS FOR ALL FILES
# ============================================================================

print("\n" + "="*70)
print("GENERATING SANKEY DIAGRAMS")
print("="*70)

success_count = 0
error_count = 0

for sankey_file in sankey_files:
    try:
        with open(sankey_file, "r", encoding="utf-8") as f:
            sankey_data = json.load(f)
        
        impact_category = sankey_data.get("impact_category", "Unknown")
        print(f"\n📊 Processing file: {sankey_file.name}")
        print(f"   Impact: {impact_category}")
        
        result = create_sankey_diagram(sankey_data)
        if result is None:
            error_count += 1
            continue
        
        fig, num_nodes, num_edges = result
        
        # ========== EXPORT TO HTML ==========
        # Keep output name unique per source JSON to avoid overwriting files
        source_stem = sankey_file.stem.replace("_sankey", "")
        safe_source = source_stem.replace("/", "_").replace(" ", "_")
        html_filename = f"{safe_source}_sankey_visualization.html"
        html_path = EXPORT_DIR / html_filename
        
        fig.write_html(str(html_path), include_plotlyjs=True, full_html=True)
        
        print(f"  ✓ Created: {html_filename}")
        print(f"    • {num_nodes} nodes, {num_edges} edges")
        print(f"    • Saved to: {html_path}")
        
        success_count += 1
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        error_count += 1

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"✓ Successfully created: {success_count} diagram(s)")
if error_count > 0:
    print(f"✗ Failed: {error_count} diagram(s)")
print(f"\n📁 Export directory: {EXPORT_DIR}")
print(f"\nGenerated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
