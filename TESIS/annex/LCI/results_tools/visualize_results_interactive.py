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
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_filename_part(text):
    """Make a text fragment safe for Windows filenames."""
    cleaned_text = text.replace("_", " ").strip()
    cleaned_text = cleaned_text.replace("/", "_").replace("\\", "_")
    cleaned_text = cleaned_text.replace(":", "").replace("*", "").replace("?", "")
    cleaned_text = cleaned_text.replace('"', "").replace("<", "").replace(">", "")
    cleaned_text = cleaned_text.replace("|", "_")
    cleaned_text = "_".join(cleaned_text.split())
    return cleaned_text


def build_graph_filename(prefix, selected_systems, impact=None):
    """Build an exported filename from the graph type, systems, and optional impact."""
    if len(selected_systems) > 6:
        system_part = "COMBINED"
    else:
        system_part = "_".join(clean_filename_part(system) for system in selected_systems)
    filename_parts = [clean_filename_part(prefix), system_part]
    if impact:
        filename_parts.append(clean_filename_part(impact))
    filename = "_".join(part for part in filename_parts if part)
    return f"{filename}.png"


def save_graph_to_files(filename, fig, output_dir=".", export_folder=None):
    """
    Save graph to the export directory when provided; otherwise save locally.
    
    Parameters:
        filename: Name of the PNG file
        fig: matplotlib figure object
        output_dir: Local output directory
        export_folder: Export folder path (optional)
    
    Returns:
        Tuple of (local_path, export_path or None)
    """
    local_path = None
    export_path = None
    if export_folder:
        try:
            Path(export_folder).mkdir(parents=True, exist_ok=True)
            export_path = os.path.join(export_folder, filename)
            fig.savefig(export_path, dpi=300, bbox_inches='tight')
        except Exception as e:
            print(f"  [!] Warning: Could not save to export folder: {e}")
    else:
        local_path = os.path.join(output_dir, filename)
        fig.savefig(local_path, dpi=300, bbox_inches='tight')
    
    return local_path, export_path


def cleanup_local_graph_files(output_dir):
    """Remove locally saved graph PNGs from the results folder."""
    patterns = [
        "RELATIVE_IMPACT*.png",
        "NORMALIZED_COMPARISON*.png",
        "ABSOLUTE_COMPARISON*.png",
    ]
    for pattern in patterns:
        for file_path in glob.glob(os.path.join(output_dir, pattern)):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"  [!] Warning: Could not remove local file {file_path}: {e}")


def save_tables_to_excel(base_filename, tables, export_folder):
    """Save one or more pandas DataFrames to an Excel file with multiple sheets.

    base_filename: filename without extension
    tables: dict of {sheet_name: DataFrame}
    export_folder: folder where to save
    Returns full path or None on error
    """
    try:
        Path(export_folder).mkdir(parents=True, exist_ok=True)
        excel_path = os.path.join(export_folder, f"{base_filename}.xlsx")
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for sheet, df in tables.items():
                safe_sheet = clean_filename_part(sheet)[:31] if sheet else 'Sheet'
                # ensure DataFrame exists
                if isinstance(df, (pd.DataFrame, pd.Series)):
                    df.to_excel(writer, sheet_name=safe_sheet)
        return excel_path
    except Exception as e:
        print(f"  [!] Warning: Could not save Excel file: {e}")
        return None


def append_tables_to_excel(excel_path, tables):
    """Append or create an Excel file with multiple sheets from dict of DataFrames."""
    try:
        Path(os.path.dirname(excel_path)).mkdir(parents=True, exist_ok=True)
        if os.path.exists(excel_path):
            # Append/replace sheets in existing workbook
            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                for sheet, df in tables.items():
                    safe_sheet = clean_filename_part(sheet)[:31] if sheet else 'Sheet'
                    if isinstance(df, (pd.DataFrame, pd.Series)):
                        df.to_excel(writer, sheet_name=safe_sheet)
        else:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for sheet, df in tables.items():
                    safe_sheet = clean_filename_part(sheet)[:31] if sheet else 'Sheet'
                    if isinstance(df, (pd.DataFrame, pd.Series)):
                        df.to_excel(writer, sheet_name=safe_sheet)
        return excel_path
    except Exception as e:
        print(f"  [!] Warning: Could not append/save Excel file: {e}")
        return None


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


def resolve_results_dir() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__)) or "."
    deterministic_dir = os.path.join(base_dir, "Deterministic results")
    if os.path.isdir(deterministic_dir):
        has_results = any(name.endswith("_impacts.csv") for name in os.listdir(deterministic_dir))
        if has_results:
            return deterministic_dir
    return base_dir


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
        ("Relative Impact (Horizontal)", "Horizontal grouped bars per EI; legend bottom-right"),
        ("Normalized Comparison (Horizontal)", "Horizontal grouped bars per EI; legend bottom-right"),
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
