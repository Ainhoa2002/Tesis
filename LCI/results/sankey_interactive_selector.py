#!/usr/bin/env python3
"""
Interactive Sankey Diagram Generator
Allows selection of Environmental Impact (EI) and Product System
"""

# USO / INSTRUCCIONES
# - Activa el entorno virtual del proyecto:
#     & .venv\Scripts\Activate.ps1    (PowerShell)
#     source .venv/bin/activate        (bash)
# - Instala dependencias si es necesario:
#     pip install plotly
# - Ejemplos de ejecución:
#     python LCI/RESULTS/sankey_interactive_selector.py --system-name "connecting_cable_EoL" --phase-name "Acidification"
#     python LCI/RESULTS/sankey_interactive_selector.py --system-index 208 --phase-index 1
#     python LCI/RESULTS/sankey_interactive_selector.py --system-name "connecting_cable_EoL" --auto-phase --open
# - Notas:
#   * Busca recursivamente archivos '*_sankey.json' bajo `LCI/RESULTS`.
#   * Exporta el HTML a `LCI/RESULTS/sankey_html_exports` (o a la carpeta cernbox si existe).
#   * Usa `--open` para abrir el HTML automáticamente en el navegador por defecto.


import json
import plotly.graph_objects as go
from pathlib import Path
from collections import defaultdict
import sys
import argparse

# ============================================================================
# CONFIGURATION
# ============================================================================

RESULTS_DIR = Path(__file__).parent
PREFERRED_EXPORT = Path("C:/Users/alorzaga/cernbox/WINDOWS/Desktop/TESIS/LCIA_Power systems/Data quality and monte carlo/.sankey_html_exports")
if PREFERRED_EXPORT.exists():
    EXPORT_DIR = PREFERRED_EXPORT
else:
    EXPORT_DIR = RESULTS_DIR / "sankey_html_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PARSE SANKEY FILES
# ============================================================================

def extract_file_info(filename):
    """Extract Environmental Impact and Product System from filename."""
    # Format: {Product_System}_{Phase}_EF v3.1_sankey.json
    # Example: "Converter (all phases)_EF v3.1_sankey.json"
    # Example: "converter_EoL_EF v3.1_sankey.json"
    
    name = filename.replace("_sankey.json", "").replace("_EF v3.1", "")
    
    # Split by last underscore to separate phase/description
    parts = name.rsplit("_", 1)
    if len(parts) == 2:
        system, phase = parts
        return system, phase
    else:
        return name, "all phases"

sankey_files = sorted(RESULTS_DIR.glob("**/*_sankey.json"))

# Organize files by Product System
systems_dict = defaultdict(list)
for f in sankey_files:
    system, phase = extract_file_info(f.name)
    systems_dict[system].append((phase, f))

print("\n" + "="*70)
print("AVAILABLE PRODUCT SYSTEMS")
print("="*70)

systems_list = sorted(systems_dict.keys())
for i, system in enumerate(systems_list, 1):
    phases = [phase for phase, _ in systems_dict[system]]
    print(f"{i:2d}. {system}")
    for phase in phases:
        print(f"    - {phase}")

# If no sankey files were found, inform the user and exit gracefully
if not systems_list:
    print("\nNo sankey files found in:", RESULTS_DIR)
    print("Make sure files matching '*_sankey.json' exist in that folder.")
    sys.exit(1)

# ============================================================================
# USER INPUT
# ============================================================================

print("\n" + "="*70)
print("SELECT PRODUCT SYSTEM AND PHASE")
print("="*70)

# CLI arguments to allow non-interactive selection
parser = argparse.ArgumentParser(description="Generate Sankey HTML for a chosen system and impact")
parser.add_argument("--system-index", type=int, help="1-based product system index from the printed list")
parser.add_argument("--system-name", type=str, help="Product system name (exact match)")
parser.add_argument("--phase-index", type=int, help="1-based phase index for the selected system")
parser.add_argument("--phase-name", type=str, help="Phase name (exact match)")
parser.add_argument("--auto-phase", action="store_true", help="Automatically select the first phase for the chosen system")
parser.add_argument("--open", action="store_true", help="Open the generated HTML in the default browser")
args = parser.parse_args()

selected_system = None
selected_phase = None

try:
    # Select system by name or index (name preferred)
    if args.system_name:
        if args.system_name in systems_list:
            selected_system = args.system_name
        else:
            print(f"System name '{args.system_name}' not found.")
            sys.exit(1)
    elif args.system_index:
        si = args.system_index - 1
        if 0 <= si < len(systems_list):
            selected_system = systems_list[si]
        else:
            print("Invalid system index")
            sys.exit(1)
    else:
        # Interactive prompt
        system_idx = int(input(f"Select product system (1-{len(systems_list)}): ")) - 1
        if not 0 <= system_idx < len(systems_list):
            print("Invalid selection")
            sys.exit(1)
        selected_system = systems_list[system_idx]

    phases = [phase for phase, _ in systems_dict[selected_system]]

    # Select phase by name or index; if only one phase, pick it automatically
    if args.phase_name:
        if args.phase_name in phases:
            selected_phase = args.phase_name
        else:
            print(f"Phase name '{args.phase_name}' not found for system '{selected_system}'.")
            sys.exit(1)
    elif args.phase_index:
        pi = args.phase_index - 1
        if 0 <= pi < len(phases):
            selected_phase = phases[pi]
        else:
            print("Invalid phase index")
            sys.exit(1)
    elif len(phases) == 1 or args.auto_phase:
        selected_phase = phases[0]
    else:
        print(f"\nAvailable phases for '{selected_system}':")
        for i, phase in enumerate(phases, 1):
            print(f"  {i}. {phase}")
        phase_idx = int(input(f"Select phase (1-{len(phases)}): ")) - 1
        if not 0 <= phase_idx < len(phases):
            print("Invalid selection")
            sys.exit(1)
        selected_phase = phases[phase_idx]

    # Get the file matching selection
    sankey_file = None
    for phase, f in systems_dict[selected_system]:
        if phase == selected_phase:
            sankey_file = f
            break

    if not sankey_file:
        print("File not found")
        sys.exit(1)

except (ValueError, KeyError, IndexError) as e:
    print(f"Error: {e}")
    sys.exit(1)

# ============================================================================
# LOAD AND CREATE SANKEY
# ============================================================================

print(f"\n📊 Loading: {sankey_file.name}")

with open(sankey_file, "r", encoding="utf-8") as f:
    sankey_data = json.load(f)

nodes = sankey_data.get("nodes", [])
edges = sankey_data.get("edges", [])
impact_category = sankey_data.get("impact_category", "Unknown")
mode = sankey_data.get("mode", 1)

if not nodes or not edges:
    print("No data to visualize")
    sys.exit(1)

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
        source=edge_sources,
        target=edge_targets,
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
        text=f"<b>LCA Sankey Diagram: {impact_category}</b><br><sub>System: {selected_system} | Phase: {selected_phase} | {mode_description}</sub>",
        x=0.5,
        xanchor="center",
        font=dict(size=14, color="#2c3e50")
    ),
    font=dict(
        size=11,
        family="Arial, sans-serif",
        color="#2c3e50"
    ),
    height=700,
    width=1400,
    plot_bgcolor="white",
    paper_bgcolor="#f8f9fa",
    margin=dict(l=20, r=20, t=120, b=20),
    annotations=[
        dict(
            text=f"<i>Nodes: {len(nodes)} | Edges: {len(edge_sources)}</i>",
            xref="paper", yref="paper",
            x=0.5, y=-0.05,
            showarrow=False,
            font=dict(size=10, color="gray")
        )
    ]
)

# ========== EXPORT TO HTML ==========
safe_impact = impact_category.replace("/", "_").replace(" ", "_")
safe_system = selected_system.replace("/", "_").replace(" ", "_").replace("&", "and")
safe_phase = selected_phase.replace("/", "_").replace(" ", "_")
html_filename = f"{safe_system}_{safe_phase}_{safe_impact}_sankey.html"
html_path = EXPORT_DIR / html_filename

fig.write_html(str(html_path), include_plotlyjs=True, full_html=True)

print(f"\n✓ Sankey diagram created successfully!")
print(f"  • Filename: {html_filename}")
print(f"  • Nodes: {len(nodes)}")
print(f"  • Edges: {len(edge_sources)}")
print(f"  • Impact: {impact_category}")
print(f"  • Saved to: {html_path}")

# ========== OPEN IN BROWSER (OPTIONAL) ==========
import webbrowser
open_browser = input(f"\nOpen in browser? (y/n): ").lower()
if open_browser == 'y':
    webbrowser.open(str(html_path))
    print("Opening in browser...")
