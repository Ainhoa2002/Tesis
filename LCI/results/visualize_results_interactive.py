"""
INTERACTIVE LCA RESULTS VISUALIZATION WITH MULTI-SYSTEM COMPARISON
====================================================================

This script provides an interactive terminal interface for comparing
LCA results across multiple product systems and environmental impacts.

WORKFLOW:
1. User selects environmental impacts to analyze (or "all")
2. User selects product systems to compare
3. User selects which graph types to generate
4. Script generates interactive visualizations

GRAPH TYPES:
1. RELATIVE IMPACT: 100% stacked bars per EI (max system = 100%, others scaled)
2. NORMALIZED COMPARISON: Bar chart showing normalized values per EI
3. ABSOLUTE IMPACT COMPARISON: One graph per EI comparing raw values across systems

REQUIREMENTS:
- pandas, matplotlib installed
- *_impacts.csv files in same directory as this script
- Columns: Impact category, Amount (Raw), Unit, Amount (Normalized), Normalized Unit
"""

import os
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_graph_to_files(filename, fig, output_dir=".", export_folder=None):
    """
    Save graph to both local and export directories.
    
    Parameters:
        filename: Name of the PNG file
        fig: matplotlib figure object
        output_dir: Local output directory
        export_folder: Export folder path (optional)
    
    Returns:
        Tuple of (local_path, export_path or None)
    """
    local_path = os.path.join(output_dir, filename)
    fig.savefig(local_path, dpi=300, bbox_inches='tight')
    
    export_path = None
    if export_folder:
        try:
            Path(export_folder).mkdir(parents=True, exist_ok=True)
            export_path = os.path.join(export_folder, filename)
            fig.savefig(export_path, dpi=300, bbox_inches='tight')
        except Exception as e:
            print(f"  [!] Warning: Could not save to export folder: {e}")
    
    return local_path, export_path


def discover_impact_csvs(results_dir="."):
    """
    Find all impact CSV files in results directory.
    
    Returns:
        list: Tuples of (system_name, csv_path, method_name)
              Example: ("connector_system", "/path/to/connector_system_EF v3.1_impacts.csv", "EF v3.1")
    """
    pattern = os.path.join(results_dir, "*_impacts.csv")
    csv_files = sorted(glob.glob(pattern))
    
    # Exclude *_impacts_normalized.csv and *_NORMALIZATION_RESULTS.csv
    csv_files = [f for f in csv_files if not f.endswith("_normalized.csv") and "NORMALIZATION_RESULTS" not in f]
    
    systems = []
    for csv_path in csv_files:
        filename = os.path.basename(csv_path)
        # Format: {system}_{method}_impacts.csv
        parts = filename.replace("_impacts.csv", "").rsplit("_", 1)
        if len(parts) == 2:
            system_name = parts[0]
            method_name = parts[1]
            systems.append((system_name, csv_path, method_name))
    
    return systems


def load_impacts_data(csv_paths):
    """
    Load and consolidate impact data from multiple CSV files.
    
    Parameters:
        csv_paths: List of CSV file paths
    
    Returns:
        dict: {system_name: DataFrame}
    """
    systems_data = {}
    
    for system_name, csv_path, method_name in csv_paths:
        try:
            df = pd.read_csv(csv_path)
            systems_data[system_name] = df
            print(f"  [OK] Loaded {system_name}: {len(df)} impact categories")
        except Exception as e:
            print(f"  [ERR] Failed to load {csv_path}: {e}")
    
    return systems_data


def get_unique_impacts(systems_data):
    """
    Get all unique impact categories across all systems.
    
    Returns:
        list: Sorted list of impact category names
    """
    impacts = set()
    for df in systems_data.values():
        impacts.update(df["Impact category"].unique())
    
    return sorted(list(impacts))


def interactive_select_impacts(all_impacts):
    """
    Interactive CLI to select environmental impacts.
    
    Returns:
        list: Selected impact category names
    """
    print("\n" + "=" * 70)
    print("SELECT ENVIRONMENTAL IMPACTS")
    print("=" * 70)
    print("\nAvailable impacts:")
    for i, impact in enumerate(all_impacts, 1):
        print(f"  {i:2d}. {impact}")
    
    print("\nOptions:")
    print("  [a] Analyze ALL impacts")
    print("  [c] Choose specific impacts")
    
    while True:
        choice = input("\nEnter your choice [a/c]: ").strip().lower()
        if choice == 'a':
            return all_impacts
        elif choice == 'c':
            selected = []
            print("\nEnter impact numbers (comma-separated, e.g., 1,3,5):")
            try:
                indices = [int(x.strip()) - 1 for x in input("> ").split(",")]
                for idx in indices:
                    if 0 <= idx < len(all_impacts):
                        selected.append(all_impacts[idx])
                
                if selected:
                    print(f"\n[OK] Selected {len(selected)} impacts:")
                    for imp in selected:
                        print(f"    - {imp}")
                    return selected
                else:
                    print("[ERR] No valid impacts selected. Try again.")
            except (ValueError, IndexError):
                print("[ERR] Invalid input. Please enter valid numbers.")
        else:
            print("[ERR] Invalid choice. Enter 'a' or 'c'.")


def interactive_select_systems(available_systems):
    """
    Interactive CLI to select product systems to compare.
    
    Returns:
        list: Selected system names
    """
    print("\n" + "=" * 70)
    print("SELECT PRODUCT SYSTEMS TO COMPARE")
    print("=" * 70)
    print("\nAvailable systems:")
    for i, system in enumerate(available_systems, 1):
        print(f"  {i}. {system}")
    
    print("\nOptions:")
    print("  [a] Compare ALL systems")
    print("  [c] Choose specific systems")
    
    while True:
        choice = input("\nEnter your choice [a/c]: ").strip().lower()
        if choice == 'a':
            return available_systems
        elif choice == 'c':
            selected = []
            print("\nEnter system numbers (comma-separated, e.g., 1,2):")
            try:
                indices = [int(x.strip()) - 1 for x in input("> ").split(",")]
                for idx in indices:
                    if 0 <= idx < len(available_systems):
                        selected.append(available_systems[idx])
                
                if selected:
                    print(f"\n[OK] Selected {len(selected)} systems:")
                    for sys in selected:
                        print(f"    - {sys}")
                    return selected
                else:
                    print("[ERR] No valid systems selected. Try again.")
            except (ValueError, IndexError):
                print("[ERR] Invalid input. Please enter valid numbers.")
        else:
            print("[ERR] Invalid choice. Enter 'a' or 'c'.")


def interactive_select_graph_types():
    """
    Interactive CLI to select which graph types to generate.
    
    Returns:
        list: Selected graph types
    """
    print("\n" + "=" * 70)
    print("SELECT GRAPH TYPES TO GENERATE")
    print("=" * 70)
    
    graph_types = [
        ("Relative Impact", "100% stacked bar per EI (max system = 100%, others scaled)"),
        ("Normalized Comparison", "Bar chart showing normalized values per EI"),
        ("Absolute Impact Comparison", "One graph per EI comparing raw values across systems"),
    ]
    
    print("\nAvailable graph types:")
    for i, (name, desc) in enumerate(graph_types, 1):
        print(f"  {i}. {name}")
        print(f"     {desc}")
    
    print("\nOptions:")
    print("  [a] Generate ALL graph types")
    print("  [c] Choose specific types")
    
    while True:
        choice = input("\nEnter your choice [a/c]: ").strip().lower()
        if choice == 'a':
            return [name for name, _ in graph_types]
        elif choice == 'c':
            selected = []
            print("\nEnter graph type numbers (comma-separated, e.g., 1,2):")
            try:
                indices = [int(x.strip()) - 1 for x in input("> ").split(",")]
                for idx in indices:
                    if 0 <= idx < len(graph_types):
                        selected.append(graph_types[idx][0])
                
                if selected:
                    print(f"\n[OK] Selected {len(selected)} graph types:")
                    for gt in selected:
                        print(f"    - {gt}")
                    return selected
                else:
                    print("[ERR] No valid graph types selected. Try again.")
            except (ValueError, IndexError):
                print("[ERR] Invalid input. Please enter valid numbers.")
        else:
            print("[ERR] Invalid choice. Enter 'a' or 'c'.")


def interactive_select_export_options():
    """
    Interactive CLI to select export options for graphs.
    
    Returns:
        dict: Contains 'export' (bool) and 'export_folder' (str or None)
    """
    print("\n" + "=" * 70)
    print("EXPORT OPTIONS")
    print("=" * 70)
    
    default_export_folder = r"C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems"
    
    print(f"\nDefault export folder:")
    print(f"  {default_export_folder}")
    
    # Ask if user wants to export
    print("\nDo you want to export graphs to external folder?")
    print("  [y] Yes (default)")
    print("  [n] No")
    
    export = True
    while True:
        choice = input("\nEnter your choice [y/n]: ").strip().lower()
        if choice in ['y', '']:
            export = True
            break
        elif choice == 'n':
            export = False
            break
        else:
            print("[ERR] Invalid choice. Enter 'y' or 'n'.")
    
    if not export:
        return {'export': False, 'export_folder': None}
    
    # Ask for export folder
    print("\nEnter export folder path or press Enter for default:")
    user_folder = input("> ").strip()
    
    export_folder = user_folder if user_folder else default_export_folder
    
    print(f"\n[OK] Export enabled")
    print(f"  Folder: {export_folder}")
    
    return {'export': True, 'export_folder': export_folder}


# ============================================================================
# GRAPH GENERATION FUNCTIONS
# ============================================================================

def plot_relative_impact(systems_data, selected_systems, selected_impacts, output_dir=".", export_folder=None):
    """
    RELATIVE IMPACT: One combined graph with all selected EIs.
    
    For each environmental impact:
    - Find the system with maximum raw value
    - Set that system to 100%
    - Scale all other systems proportionally
    
    All impacts shown in one grouped bar chart.
    Generates one PNG file: RELATIVE_IMPACT_COMBINED.png
    """
    print("\n[>] Generating RELATIVE IMPACT graph...")
    
    if not selected_impacts or not selected_systems:
        print("  [!] No impacts or systems selected, skipping.")
        return
    
    # Collect relative values for all impacts across all systems
    relative_data = {}
    
    for impact in selected_impacts:
        # Collect raw values for this impact
        values = {}
        for system in selected_systems:
            df = systems_data[system]
            impact_row = df[df["Impact category"] == impact]
            
            if not impact_row.empty:
                raw_value = impact_row["Amount (Raw)"].values[0]
                values[system] = float(raw_value) if pd.notna(raw_value) else 0.0
            else:
                values[system] = 0.0
        
        # Find max value for this impact
        max_value = max(values.values()) if values else 1.0
        
        if max_value == 0:
            # Skip impacts with all zero values
            continue
        
        # Calculate relative percentages
        relative_data[impact] = {sys: (val / max_value) * 100 for sys, val in values.items()}
    
    if not relative_data:
        print("  [!] All selected impacts have zero values, skipping.")
        return
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(16, 8))
    
    impacts_list = list(relative_data.keys())
    systems_list = selected_systems
    
    # Set up bar positions
    x = np.arange(len(impacts_list))
    width = 0.8 / len(systems_list)
    
    # Define colors for each system
    colors = plt.cm.Set3(np.linspace(0, 1, len(systems_list)))
    
    # Plot bars for each system
    for i, system in enumerate(systems_list):
        values = [relative_data[impact].get(system, 0) for impact in impacts_list]
        offset = (i - len(systems_list)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=system, color=colors[i], 
                     edgecolor='black', linewidth=1)
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            if val > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f"{val:.0f}%", ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Format plot
    ax.set_xlabel("Environmental Impact Categories", fontsize=12, fontweight='bold')
    ax.set_ylabel("Relative Impact (%)", fontsize=12, fontweight='bold')
    ax.set_title(f"Relative Impact Comparison: {len(selected_impacts)} Environmental Impacts\n(% of maximum system value per impact)", 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([imp[:30] + "..." if len(imp) > 30 else imp for imp in impacts_list], 
                       rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper left', fontsize=10, title='Product Systems', title_fontsize=11)
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Save figure to both directories
    local_path, export_path = save_graph_to_files("RELATIVE_IMPACT_COMBINED.png", fig, output_dir, export_folder)
    plt.close()
    
    print(f"  [OK] All {len(selected_impacts)} impacts -> {local_path}")
    if export_path:
        print(f"    [OK] Exported to: {export_path}")


def plot_normalized_comparison(systems_data, selected_systems, selected_impacts, output_dir=".", export_folder=None):
    """
    NORMALIZED COMPARISON: One combined graph with all selected EIs.
    
    For each environmental impact:
    - Extract normalized values from "Amount (Normalized)" column
    - Create grouped bar chart showing normalized values for all systems and impacts
    
    Generates one PNG file: NORMALIZED_COMPARISON_COMBINED.png
    """
    print("\n[>] Generating NORMALIZED COMPARISON graph...")
    
    if not selected_impacts or not selected_systems:
        print("  [!] No impacts or systems selected, skipping.")
        return
    
    # Collect normalized values for all impacts
    normalized_data = {}
    has_any_normalized = False
    
    for impact in selected_impacts:
        values = {}
        for system in selected_systems:
            df = systems_data[system]
            impact_row = df[df["Impact category"] == impact]
            
            if not impact_row.empty:
                if "Amount (Normalized)" in df.columns:
                    norm_value = impact_row["Amount (Normalized)"].values[0]
                    if pd.notna(norm_value) and norm_value != 0:
                        values[system] = float(norm_value)
                        has_any_normalized = True
                    else:
                        values[system] = 0.0
                else:
                    values[system] = 0.0
            else:
                values[system] = 0.0
        
        # Only include impacts with at least one non-zero normalized value
        if any(v > 0 for v in values.values()):
            normalized_data[impact] = values
    
    if not has_any_normalized or not normalized_data:
        print("  [!] No normalized values available for selected impacts, skipping.")
        return
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(16, 8))
    
    impacts_list = list(normalized_data.keys())
    systems_list = selected_systems
    
    # Set up bar positions
    x = np.arange(len(impacts_list))
    width = 0.8 / len(systems_list)
    
    # Define colors for each system
    colors = plt.cm.Set2(np.linspace(0, 1, len(systems_list)))
    
    # Plot bars for each system
    for i, system in enumerate(systems_list):
        values = [normalized_data[impact].get(system, 0) for impact in impacts_list]
        offset = (i - len(systems_list)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=system, color=colors[i], 
                     edgecolor='black', linewidth=1)
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            if val > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f"{val:.3e}", ha='center', va='bottom', fontsize=8)
    
    # Format plot
    ax.set_xlabel("Environmental Impact Categories", fontsize=12, fontweight='bold')
    ax.set_ylabel("Normalized Impact Value", fontsize=12, fontweight='bold')
    ax.set_title(f"Normalized Comparison: {len(impacts_list)} Environmental Impacts\n(Normalized reference values across systems)", 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([imp[:30] + "..." if len(imp) > 30 else imp for imp in impacts_list], 
                       rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper left', fontsize=10, title='Product Systems', title_fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Save figure to both directories
    local_path, export_path = save_graph_to_files("NORMALIZED_COMPARISON_COMBINED.png", fig, output_dir, export_folder)
    plt.close()
    
    print(f"  [OK] All {len(impacts_list)} impacts -> {local_path}")
    if export_path:
        print(f"    [OK] Exported to: {export_path}")


def plot_absolute_impact_comparison(systems_data, selected_systems, selected_impacts, output_dir=".", export_folder=None):
    """
    ABSOLUTE IMPACT COMPARISON: One graph per selected EI.
    
    For each environmental impact:
    - Create a grouped bar chart comparing absolute raw values
    - All systems shown with different colors
    - Y-axis: System names, X-axis: Absolute impact value with unit
    
    Generates one PNG per impact category.
    """
    print("\n[>] Generating ABSOLUTE IMPACT COMPARISON graphs...")
    
    for impact in selected_impacts:
        # Collect absolute values for this impact
        values = {}
        unit = None
        
        for system in selected_systems:
            df = systems_data[system]
            impact_row = df[df["Impact category"] == impact]
            
            if not impact_row.empty:
                raw_value = impact_row["Amount (Raw)"].values[0]
                if unit is None and "Unit" in df.columns:
                    unit = impact_row["Unit"].values[0]
                
                values[system] = float(raw_value) if pd.notna(raw_value) else 0.0
            else:
                values[system] = 0.0
        
        if all(v == 0 for v in values.values()):
            continue
        
        # Create vertical bar chart for this impact
        fig, ax = plt.subplots(figsize=(12, 7))
        
        systems_list = list(values.keys())
        abs_vals = [values[sys] for sys in systems_list]
        
        # Define colors for each system
        colors = plt.cm.Set3(np.linspace(0, 1, len(systems_list)))
        
        bars = ax.bar(systems_list, abs_vals, color=colors, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for bar, val in zip(bars, abs_vals):
            if val > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f"{val:.3e}", ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        unit_label = f" ({unit})" if unit else ""
        ax.set_ylabel(f"Absolute Impact Value{unit_label}", fontsize=12, fontweight='bold')
        ax.set_xlabel("Product Systems", fontsize=12, fontweight='bold')
        ax.set_title(f"Absolute Impact Comparison: {impact}\n(Raw impact values across systems)", 
                    fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # Save figure to both directories
        safe_impact = impact.replace(":", "").replace("/", "_").replace(" ", "_")
        filename = f"ABSOLUTE_COMPARISON_{safe_impact}.png"
        local_path, export_path = save_graph_to_files(filename, fig, output_dir, export_folder)
        plt.close()
        
        print(f"  [OK] {impact} -> {local_path}")
        if export_path:
            print(f"    [OK] Exported to: {export_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Interactive main workflow.
    """
    print("\n" + "=" * 70)
    print("INTERACTIVE LCA RESULTS VISUALIZATION")
    print("=" * 70)
    
    # Step 1: Discover available CSVs
    print("\n[>] Scanning for impact CSV files...")
    results_dir = os.path.dirname(os.path.abspath(__file__)) or "."
    csv_systems = discover_impact_csvs(results_dir)
    
    if not csv_systems:
        print("[ERR] No impact CSV files found in this directory.")
        print(f"  Expected format: *_impacts.csv")
        print(f"  Directory: {results_dir}")
        return
    
    print(f"[OK] Found {len(csv_systems)} product system(s):")
    for system_name, _, method_name in csv_systems:
        print(f"    - {system_name} ({method_name})")
    
    # Step 2: Load data
    print("\n[>] Loading impact data...")
    systems_data = load_impacts_data(csv_systems)
    
    if not systems_data:
        print("[ERR] Failed to load any impact data.")
        return
    
    available_systems = list(systems_data.keys())
    all_impacts = get_unique_impacts(systems_data)
    
    print(f"[OK] Loaded data for {len(available_systems)} system(s)")
    print(f"[OK] Found {len(all_impacts)} unique impact categories")
    
    # Step 3: User selections
    selected_impacts = interactive_select_impacts(all_impacts)
    selected_systems = interactive_select_systems(available_systems)
    selected_graph_types = interactive_select_graph_types()
    export_options = interactive_select_export_options()
    
    # Step 4: Generate graphs
    print("\n" + "=" * 70)
    print("GENERATING VISUALIZATIONS")
    print("=" * 70)
    
    output_dir = results_dir
    export_folder = export_options['export_folder'] if export_options['export'] else None
    
    for graph_type in selected_graph_types:
        if graph_type == "Relative Impact":
            plot_relative_impact(systems_data, selected_systems, selected_impacts, output_dir, export_folder)
        elif graph_type == "Normalized Comparison":
            plot_normalized_comparison(systems_data, selected_systems, selected_impacts, output_dir, export_folder)
        elif graph_type == "Absolute Impact Comparison":
            plot_absolute_impact_comparison(systems_data, selected_systems, selected_impacts, output_dir, export_folder)
    
    print("\n" + "=" * 70)
    print("[OK] VISUALIZATION COMPLETE")
    print("=" * 70)
    print(f"\nGraphs saved to: {output_dir}")
    print(f"Selected impacts: {len(selected_impacts)}")
    print(f"Compared systems: {len(selected_systems)}")
    print(f"Graph types generated: {len(selected_graph_types)}")


if __name__ == "__main__":
    main()

