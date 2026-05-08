"""
LCA RESULT CALCULATION & EXTRACTION SCRIPT WITH PARAMETER DOCUMENTATION
========================================================================

This script extracts and calculates Life Cycle Assessment (LCA) results from
openLCA product systems using the IPC (Inter-Process Communication) interface.

WORKFLOW:
1. Connect to openLCA server (running on port 8080)
2. For each product system in PRODUCT_SYSTEMS:
   - Calculate impacts using LCIA methodology
   - Extract total environmental flows (inventory)
   - Analyze process contributions (upstream analysis)
   - Generate process dependency graphs (Sankey diagrams)
3. Save results to CSV and JSON files

REQUIREMENTS:
- openLCA server running on localhost:8080
- olca_ipc, pandas packages installed
- All parameters defined at the beginning of this script

AUTHOR: LCI System
"""

import os
import json
import re
from pathlib import Path

import pandas as pd
import olca_ipc as ipc
import olca_schema as o
import threading
import traceback


# ============================================================================
# CONFIGURATION PARAMETERS - EDIT THESE VARIABLES
# ============================================================================
# Set all parameters here. No need to edit global_parameters.json


# ============================================================================
# PRODUCT SYSTEMS & LCIA METHOD
# ============================================================================

# Product systems to analyze (must exist in openLCA)
# Type: List of strings
# Example: ["Buck Converter Assembly", "Li-ion Battery Module"]
PRODUCT_SYSTEMS = [
    "connector_system",
    "magnet",
    "MEXICO",   # ← Edit: Add your system names here
]

# Life Cycle Impact Assessment method name
# Type: String
# Common values: "EF v3.1", "ReCiPe 2016", "TRACI 2.1"
# Note: Must be imported in openLCA
LCIA_METHOD = "EF v3.1"


# ============================================================================
# IMPACT CATEGORY FILTER
# ============================================================================

# Impact categories to extract
# Type: List of strings or None
# None = extract ALL available categories
# Example: ["Climate Change", "Water Depletion", "Resource Depletion"]
IMPACT_CATEGORIES = None


# ============================================================================
# CONTRIBUTION ANALYSIS
# ============================================================================

# Number of top contributing processes to report per impact
# Type: Integer (typically 3-10)
# Example: 5 = show top 5 processes causing each impact category
TOP_N_CONTRIBUTORS = 5


# ============================================================================
# NORMALIZATION SETTINGS
# ============================================================================

# Enable normalized results (divide by reference values)
# Type: Boolean
# True = include normalized impacts in output
# False = skip normalization
NORMALIZATION_ENABLED = True

# Which Normalization/Weighting set to use
# Type: String or None
# None = use default from LCIA method
# Example: "EF v3.1 Europe" for regional set
NORMALIZATION_NW_SET = "EF v3.1 (Global Reference 2010)" 



# ============================================================================
# DATA QUALITY EXTRACTION
# ============================================================================

# Extract pedigree matrix scores for each process
# Type: Boolean
# True = retrieve quality scores from openLCA
INCLUDE_PROCESS_DQ = False

# Extract quality scores for individual flows
# Type: Boolean
# True = per-flow quality assessment
INCLUDE_EXCHANGE_DQ = False

# Save comprehensive data quality report to JSON
# Type: Boolean
# True = create *_data_quality.json
EXPORT_DQ_SYSTEM_INFO = False


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
# Default: C:\\Users\\alorzaga\\cernbox\\WINDOWS\\Desktop\\TESIS\\LCIA_Power systems
EXPORT_RESULT_FOLDER = r"C:\Users\alorzaga\cernbox\WINDOWS\Desktop\TESIS\LCIA_Power systems"


# ============================================================================
# SANKEY DIAGRAM SETTINGS
# ============================================================================

# Sankey diagram mode
# Type: Integer (0, 1, or 2)
# 0 = Disabled
# 1 = Flow-based (shows material/energy flows)
# 2 = Impact-based (shows impact contributions)
SANKEY_MODE = 1

# Max nodes in flow-based Sankey diagram (used when SANKEY_MODE == 1)
# Type: Integer (typically 5-20)
SANKEY_TOP_FLOWS = 10

# Max nodes in impact-based Sankey diagram (used when SANKEY_MODE == 2)
# Type: Integer (typically 3-10)
SANKEY_TOP_IMPACTS = 5

# Maximum upstream levels to show in Sankey
# Type: Integer or None
# Note: Currently NOT SUPPORTED by olca_schema (ignored)
SANKEY_MAX_DEPTH = 3


# ============================================================================
# OPENLCA CONNECTION
# ============================================================================

# Port where openLCA IPC server is running
# Type: Integer
# Default: 8080 (standard openLCA port)
OPENLCA_PORT = 8080

# Timeout (seconds) for potentially blocking IPC calls to openLCA
# Increase if you expect long calculations; keep moderate to avoid hangs
IPC_TIMEOUT = 60


# ============================================================================
# OUTPUT DIRECTORIES (auto-set)
# ============================================================================
# Results will be saved to: LCI/results/
output_dir = str(Path(__file__).resolve().parent)
export_output_dir = EXPORT_RESULT_FOLDER if EXPORT_RESULT else None
client = None
method_ref = None


# ============================================================================
# 3. HELPER FUNCTIONS
# ============================================================================

def find_entity(client, model_type, name):
    """
    Find an entity (Product System, Impact Method, etc.) by name in openLCA.
    
    Parameters:
        client: olca_ipc.Client connected to openLCA server
        model_type: Entity type (e.g., o.ProductSystem, o.ImpactMethod)
        name: Exact name of the entity to find
    
    Returns:
        Reference object if found
    
    Raises:
        ValueError: If entity not found in database
    """
    ref = client.find(model_type, name=name)
    if ref is None:
        raise ValueError(f"{model_type.__name__} '{name}' not found in openLCA")
    return ref


def filter_impacts_by_names(impacts, allowed_names):
    """
    Filter impact results to only include specified categories.
    
    Parameters:
        impacts: List of impact result objects from openLCA calculation
        allowed_names: List of impact category names to keep (None = keep all)
    
    Returns:
        Filtered list of impacts
    """
    if not allowed_names:
        return impacts  # Keep all if no filter specified
    return [i for i in impacts if i.impact_category.name in allowed_names]


def safe_filename(value):
    """
    Convert any string to a filesystem-safe filename.
    
    Removes or replaces characters that are invalid in Windows/Linux filenames:
    - Special chars: < > : " / \\ | ? *
    - Control characters (\x00-\x1f)
    - Leading/trailing spaces and dots
    
    Parameters:
        value: String to sanitize
    
    Returns:
        Safe filename string
    
    Example:
        "Climate Change / GWP" → "Climate Change _ GWP"
    """
    text = str(value)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(" .")
    return text or "unnamed"


def save_to_results(filename, content_saver):
    """
    Save content to both output directories (local and export folder).
    
    Parameters:
        filename: Name of the file to save
        content_saver: Function that takes a file path and saves content there
                      (e.g., lambda path: df.to_csv(path, index=False))
    
    Returns:
        Tuple of (local_path, export_path or None)
    """
    # Save to local directory
    local_path = os.path.join(output_dir, filename)
    content_saver(local_path)
    
    # Save to export directory if enabled
    export_path = None
    if export_output_dir:
        try:
            Path(export_output_dir).mkdir(parents=True, exist_ok=True)
            export_path = os.path.join(export_output_dir, filename)
            content_saver(export_path)
        except Exception as e:
            print(f"⚠ Warning: Could not save to export folder: {e}")
    
    return local_path, export_path


def normalize_key(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def run_with_timeout(fn, timeout=IPC_TIMEOUT):
    """Run callable `fn` in a thread and return its value or raise on timeout/exception.

    Args:
        fn: zero-argument callable to execute
        timeout: seconds to wait before timing out

    Returns:
        The return value of `fn`.

    Raises:
        TimeoutError: if execution exceeded `timeout` seconds
        Exception: re-raises any exception raised by `fn`
    """
    result = {}
    exc = {}

    def target():
        try:
            result['value'] = fn()
        except Exception as e:
            exc['error'] = e

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    if 'error' in exc:
        # Attach traceback for easier debugging
        tb = traceback.format_exception(type(exc['error']), exc['error'], exc['error'].__traceback__)
        raise Exception(f"IPC call failed: {exc['error']}\n{''.join(tb)}")
    return result.get('value')


# ============================================================================
# NORMALIZATION HELPER FUNCTIONS
# ============================================================================

def get_normalization_reference_factors(client, method_ref, nw_set_name=None):
    """
    Extract normalization reference values from LCIA method's NwSet.
    
    WHAT IS NORMALIZATION?
    ├─ Takes LCA results and divides by reference values
    ├─ Example: Climate Change = 1000 kg CO2-eq ÷ 8500 kg CO2-eq/person
    │          = 0.118 person-equivalents
    └─ Makes different impact categories comparable
    
    NORMALIZATION WORKFLOW:
    1. Find NwSet (Normalization & Weighting Set) in the LCIA method
    2. Extract normalization_factor for each impact category
    3. Divide raw results by these factors
    
    Parameters:
        client: olca_ipc.Client connected to openLCA
        method_ref: Reference to the LCIA method
        nw_set_name: Specific NwSet to use (None = use default)
    
    Returns:
        dict: Maps impact category ID → normalization factor
        
    Example output:
        {
            "Climate Change": 8500,  # kg CO2-eq per person per year
            "Water Depletion": 2500,  # m³ per person per year
        }
    """
    if not NORMALIZATION_ENABLED:
        return {}
    
    try:
        # Get full method object (not just reference)
        impact_method = client.get(o.ImpactMethod, method_ref.id)
        
        if not impact_method.nw_sets:
            print("  ⚠ No Normalization/Weighting sets found in method")
            return {}
        
        # Select which NwSet to use
        if nw_set_name:
            # Find specific NwSet by name
            nw_set = next(
                (nw for nw in impact_method.nw_sets if nw.name == nw_set_name),
                None
            )
            if not nw_set:
                print(f"  ⚠ NwSet '{nw_set_name}' not found. Available:")
                for nw in impact_method.nw_sets:
                    print(f"    - {nw.name}")
                return {}
        else:
            # Use first available NwSet (default)
            nw_set = impact_method.nw_sets[0]
        
        print(f"  → Using Normalization Set: {nw_set.name}")
        
        # Extract normalization factors
        norm_factors = {}
        for factor in nw_set.factors:
            cat_name = factor.impact_category.name
            norm_factors[cat_name] = factor.normalisation_factor
            print(f"    {cat_name}: {factor.normalisation_factor}")
        
        return norm_factors
    
    except Exception as e:
        print(f"  ✗ Error extracting normalization factors: {e}")
        return {}


# ============================================================================
# DATA QUALITY HELPER FUNCTIONS
# ============================================================================

def extract_process_dq_info(client, process_id):
    """
    Extract data quality information from a process.
    
    YOUR DATA QUALITY SCORES: Retrieves the DQ pedigree matrix scores 
    that you've already set in openLCA for this process.
    
    PEDIGREE MATRIX FORMAT: "(score1;score2;score3;score4;score5)"
    - Each score 1-5: 1=best (measured), 5=worst (estimated)
    - Represents reliability of different aspects of the data
    
    This function retrieves EXISTING scores you've entered in openLCA.
    
    Parameters:
        client: olca_ipc.Client connected to openLCA
        process_id: UUID of process
    
    Returns:
        dict: DQ entry and uncertainty info you've already set
    """
    if not INCLUDE_PROCESS_DQ:
        return None
    
    try:
        process = client.get(o.Process, process_id)
        
        dq_data = {
            "process_name": process.name,
            "process_id": process_id,
            "process_dq_entry": process.dq_entry,  # YOUR SCORES: e.g., "(3;2;4;n.a.;2)"
            "dq_system": None,
            "indicators": []
        }
        
        # Get DQ System definition (what your scores mean)
        if process.dq_system:
            dq_system = client.get(o.DQSystem, process.dq_system.id)
            dq_data["dq_system"] = dq_system.name
            dq_data["has_uncertainties"] = dq_system.has_uncertainties
            
            # Document each DQ indicator (meaning of each score position)
            for indicator in dq_system.indicators:
                ind_data = {
                    "name": indicator.name,
                    "position": indicator.position,
                    "scores": []
                }
                # Show what each score value means
                for score in indicator.scores:
                    ind_data["scores"].append({
                        "value": score.position,
                        "label": score.label,
                        "description": score.description,
                        "uncertainty": score.uncertainty
                    })
                dq_data["indicators"].append(ind_data)
        
        return dq_data
    
    except Exception as e:
        print(f"    ✗ Error extracting process DQ: {e}")
        return None


def extract_exchange_dq_info(client, process_id):
    """
    Extract data quality scores for each flow input/output.
    
    YOUR EXCHANGE DQ SCORES: Retrieves the per-flow DQ scores 
    you've set for each input and output in openLCA.
    
    More granular than process-level: each flow has its own quality assessment.
    
    Parameters:
        client: olca_ipc.Client connected to openLCA
        process_id: UUID of process
    
    Returns:
        list[dict]: DQ entries for each flow (YOUR SCORES)
    """
    if not INCLUDE_EXCHANGE_DQ:
        return []
    
    try:
        process = client.get(o.Process, process_id)
        exchange_dq = []
        
        for exchange in process.exchanges:
            ex_data = {
                "flow_name": exchange.flow.name if exchange.flow else "Unknown",
                "amount": exchange.amount,
                "unit": exchange.unit.name if exchange.unit else "unknown",
                "is_input": exchange.is_input,
                "dq_entry": exchange.dq_entry,  # YOUR SCORES: e.g., "(1;3;2;5;1)"
                "uncertainty": None
            }
            
            # Include uncertainty data if you've set it
            if exchange.uncertainty:
                ex_data["uncertainty"] = {
                    "distribution_type": exchange.uncertainty.distribution_type.value 
                                        if hasattr(exchange.uncertainty, 'distribution_type') else None,
                    "mean": exchange.uncertainty.mean,
                    "sd": exchange.uncertainty.sd,
                    "min": exchange.uncertainty.minimum_value,
                    "max": exchange.uncertainty.maximum_value,
                }
            
            exchange_dq.append(ex_data)
        
        return exchange_dq
    
    except Exception as e:
        print(f"    ✗ Error extracting exchange DQ: {e}")
        return []


# ============================================================================
# 4. SERVER CONNECTION & INITIALIZATION
# ============================================================================

# Connection and LCIA method setup are initialized inside `main()` so the module can be imported safely.


# ============================================================================
# 5. MAIN CALCULATION FUNCTION
# ============================================================================

def process_system(system_name):
    """
    Calculate and extract LCA results for a single product system.
    
    This function:
    1. Finds the product system in openLCA
    2. Sets up calculation with specified LCIA method
    3. Runs the LCA calculation
    4. Extracts and saves:
       - Total impacts (environmental indicators)
       - Total inventory flows (emissions and resource extraction)
       - Contribution analysis (which processes cause the impacts)
       - Sankey diagram (visualization of upstream dependencies)
    
    Parameters:
        system_name: Exact name of product system in openLCA (must exist)
    
    Output Files Created:
        {system}_{method}_impacts.csv
            Columns: Impact category | Amount | Unit
            Content: Total environmental impact per category
        
        {system}_{method}_inventory.csv
            Columns: Flow | Amount | Unit | Is input
            Content: All environmental flows (emissions, resource use)
        
        {system}_{method}_{category}_upstream.csv
            Columns: Process | Contribution | Unit
            Content: Top N processes causing impact in this category
            Files: One per impact category (only if impacts > 0)
        
        {system}_{method}_sankey.json
            Content: Process network graph (if SANKEY_MODE != 0)
    """
    
    print(f"\n{'=' * 70}")
    print(f"PROCESSING: {system_name}")
    print(f"Method: {method_ref.name}")
    print("=" * 70)

    # Step 1: Find the product system
    ps = find_entity(client, o.ProductSystem, system_name)
    print(f"✓ Found product system: {ps.id}")

    # Step 2: Create calculation setup
    # CalculationSetup specifies:
    #   - target: which product system to calculate
    #   - impact_method: which LCIA method to use for characterization
    #   - nw_set: which Normalization/Weighting set to use (if normalization enabled)
    setup = o.CalculationSetup(target=ps, impact_method=method_ref)
    
    # Add NW set to setup if normalization is enabled
    if NORMALIZATION_ENABLED and NORMALIZATION_NW_SET:
        try:
            # Find the NW set by name in the LCIA method
            nw_sets = method_ref.nw_sets if hasattr(method_ref, 'nw_sets') else []
            if not nw_sets:
                # Get full method object to access NW sets
                full_method = client.get(o.ImpactMethod, method_ref.id)
                nw_sets = full_method.nw_sets if full_method and full_method.nw_sets else []
            
            if nw_sets:
                # Find NW set by name
                selected_nw = next(
                    (nw for nw in nw_sets if nw.name == NORMALIZATION_NW_SET),
                    None
                )
                if selected_nw:
                    setup.nw_set = selected_nw
                    print(f"  → Normalization enabled: {selected_nw.name}")
                else:
                    print(f"  ⚠ NW set '{NORMALIZATION_NW_SET}' not found in method")
            else:
                print(f"  ⚠ No NW sets available in method for normalization")
        except Exception as e:
            print(f"  ⚠ Could not set NW set: {e}")

    # Step 3: Run LCA calculation on openLCA server (with timeout protection)
    try:
        result = run_with_timeout(lambda: client.calculate(setup), timeout=IPC_TIMEOUT)
        # Wait until calculation finishes (also timeboxed)
        if hasattr(result, 'wait_until_ready'):
            run_with_timeout(lambda: result.wait_until_ready(), timeout=IPC_TIMEOUT)
        print("✓ LCA calculation completed.")
    except TimeoutError as te:
        print(f"✗ Calculation timed out: {te}")
        return
    except Exception as e:
        print(f"✗ Calculation failed: {e}")
        return

    # ========================================================================
    # 5A. EXTRACT TOTAL IMPACTS
    # ========================================================================
    # Total impacts = environmental indicators aggregated across entire supply chain
    # Each impact is calculated by:
    #   1. Summing all elementary flows at product system boundary
    #   2. Multiplying by characterization factors from LCIA method
    # Example: CO2(kg) + CH4(kg)*28 + N2O(kg)*265 → kg CO2-eq (Climate Change)
    
    # Get raw impacts (timeboxed)
    try:
        all_impacts = run_with_timeout(lambda: result.get_total_impacts(), timeout=IPC_TIMEOUT)
    except TimeoutError:
        print("✗ Getting total impacts timed out; skipping this system.")
        result.dispose()
        return
    except Exception as e:
        print(f"✗ Error getting total impacts: {e}")
        result.dispose()
        return
    
    # Get normalized impacts (if enabled)
    all_normalized_impacts = None
    normalization_factors = {}
    if NORMALIZATION_ENABLED:
        try:
            all_normalized_impacts = result.get_normalized_impacts()
            if all_normalized_impacts:
                print(f"✓ Normalized impacts calculated ({len(all_normalized_impacts)} categories).")
            else:
                print(f"⚠ Normalized impacts returned empty. Ensure NW set is properly defined in CalculationSetup.")
                all_normalized_impacts = None
        except Exception as e:
            print(f"  ⚠ Could not get normalized impacts: {e}")
    
    if all_impacts:
        # Apply impact category filter (if specified in config)
        impacts = filter_impacts_by_names(all_impacts, IMPACT_CATEGORIES)
        normalized_lookup = {}
        if all_normalized_impacts:
            for index, normalized_impact in enumerate(all_normalized_impacts):
                category = getattr(normalized_impact, "impact_category", None)
                if category is None:
                    continue
                normalized_lookup[normalize_key(category.name)] = normalized_impact
                normalized_lookup.setdefault(category.id, normalized_impact)
                normalized_lookup.setdefault(index, normalized_impact)
        
        # Prepare DataFrame with both raw and normalized values
        impacts_data = []
        for index, i in enumerate(impacts):
            row = {
                "Impact category": i.impact_category.name,
                "Amount (Raw)": i.amount,
                "Unit": i.impact_category.ref_unit,
                "Amount (Normalized)": None,
                "Normalized Unit": None,
            }
            
            # Add normalized value if available
            if all_normalized_impacts:
                norm_impact = (
                    normalized_lookup.get(i.impact_category.id)
                    or normalized_lookup.get(normalize_key(i.impact_category.name))
                    or normalized_lookup.get(index)
                )
                if norm_impact:
                    row["Amount (Normalized)"] = norm_impact.amount
                    # Normalized unit typically uses reference unit per reference object
                    # (e.g., kg CO2-eq per person-equivalent for climate change)
                    row["Normalized Unit"] = f"{i.impact_category.ref_unit}/ref"
            
            impacts_data.append(row)
        
        df_impacts = pd.DataFrame(impacts_data)
        
        # Save impacts to CSV
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        
        imp_filename = f"{safe_system}_{safe_method}_impacts.csv"
        local_imp_path, export_imp_path = save_to_results(imp_filename, lambda p: df_impacts.to_csv(p, index=False))
        print(f"✓ Saved impacts: {len(df_impacts)} categories → {local_imp_path}")
        if export_imp_path:
            print(f"  ✓ Exported to: {export_imp_path}")
        
        if all_normalized_impacts and "Amount (Normalized)" in df_impacts.columns:
            norm_filename = f"{safe_system}_{safe_method}_impacts_normalized.csv"
            norm_df = df_impacts[["Impact category", "Amount (Normalized)", "Normalized Unit"]]
            local_norm_path, export_norm_path = save_to_results(norm_filename, lambda p: norm_df.to_csv(p, index=False))
            print(f"✓ Saved normalized impacts → {local_norm_path}")
            if export_norm_path:
                print(f"  ✓ Exported to: {export_norm_path}")
    else:
        print("⚠ No impacts found.")
        impacts = []

    # ========================================================================
    # 5B. EXTRACT TOTAL INVENTORY FLOWS
    # ========================================================================
    # Total flows = all elementary flows (emissions + resource extraction)
    # aggregated across entire product system
    # Classified as:
    #   - is_input = True: Resources consumed (e.g., copper ore, water)
    #   - is_input = False: Emissions released (e.g., CO2 to air)
    
    flows = result.get_total_flows()
    if flows:
        # Convert to DataFrame for CSV export
        df_flows = pd.DataFrame(
            [
                {
                    "Flow": (
                        f.envi_flow.flow.name
                        if getattr(f, "envi_flow", None) and getattr(f.envi_flow, "flow", None)
                        else ""
                    ),
                    "Amount": f.amount,
                    "Unit": (
                        f.envi_flow.flow.ref_unit
                        if getattr(f, "envi_flow", None)
                        and getattr(f.envi_flow, "flow", None)
                        and getattr(f.envi_flow.flow, "ref_unit", None)
                        else ""
                    ),
                    "Is input": (
                        f.envi_flow.is_input
                        if getattr(f, "envi_flow", None) and hasattr(f.envi_flow, "is_input")
                        else None
                    ),
                }
                for f in flows
            ]
        )
        
        # Save inventory to CSV
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        flo_filename = f"{safe_system}_{safe_method}_inventory.csv"
        local_flo_path, export_flo_path = save_to_results(flo_filename, lambda p: df_flows.to_csv(p, index=False))
        print(f"✓ Saved inventory: {len(df_flows)} flows → {local_flo_path}")
        if export_flo_path:
            print(f"  ✓ Exported to: {export_flo_path}")
    else:
        print("⚠ No inventory flows found.")

    # ========================================================================
    # 5C. EXTRACT CONTRIBUTION ANALYSIS (UPSTREAM ANALYSIS)
    # ========================================================================
    # Contribution analysis shows which processes are responsible for impacts
    # For each impact category:
    #   1. Get all contributing processes
    #   2. Rank by contribution magnitude (absolute value)
    #   3. Keep top N specified in config (TOP_N_CONTRIBUTORS)
    #
    # This reveals which parts of the supply chain drive environmental impacts
    
    # Get impacts again if not already available (in case impacts is empty)
    if not impacts:
        all_impacts = result.get_total_impacts()
        impacts = filter_impacts_by_names(all_impacts, IMPACT_CATEGORIES)
        if not impacts:
            print("⚠ No impacts found - cannot analyze contributions.")
    
    if impacts:
        print(f"  → Analyzing contributions for {len(impacts)} impact categories")
        for impact in impacts:
            cat = impact.impact_category
            print(f"    Analyzing: {cat.name}")
            
            try:
                # Get contribution of each process to this impact category (timeboxed)
                try:
                    contributions = run_with_timeout(
                        lambda: result.get_impact_contributions_of(impact_category=cat),
                        timeout=IPC_TIMEOUT,
                    )
                except TimeoutError:
                    print(f"    ✗ Contribution extraction for {cat.name} timed out; skipping category.")
                    continue

                print(f"      Found {len(contributions)} contributing processes")
                
                # Filter out processes with zero contribution
                non_zero_contributions = [c for c in contributions if c.amount != 0.0]
                print(f"      Non-zero contributions: {len(non_zero_contributions)}")
                
                if not non_zero_contributions:
                    print(f"    ⚠ No non-zero contributions found for {cat.name}.")
                    continue

                # Convert to DataFrame for ranking and CSV export
                df_contrib = pd.DataFrame(
                    [
                        {
                            "Process": item.tech_flow.provider.name if item.tech_flow.provider else "Unknown",
                            "Contribution": item.amount,
                            "Unit": cat.ref_unit,
                        }
                        for item in non_zero_contributions
                    ]
                )
                
                # Sort by absolute contribution value (descending) and keep top N
                df_contrib = df_contrib.sort_values(
                    "Contribution", ascending=False, key=lambda s: s.abs()
                ).head(TOP_N_CONTRIBUTORS)
                
                # Save contributions to CSV
                safe_system = safe_filename(system_name)
                safe_method = safe_filename(method_ref.name)
                safe_category = safe_filename(cat.name)
                contrib_filename = f"{safe_system}_{safe_method}_{safe_category}_upstream.csv"
                local_contrib_path, export_contrib_path = save_to_results(
                    contrib_filename,
                    lambda p: df_contrib.to_csv(p, index=False)
                )
                print(f"    ✓ Saved top {len(df_contrib)} contributors → {local_contrib_path}")
                if export_contrib_path:
                    print(f"      ✓ Exported to: {export_contrib_path}")
            
            except Exception as e:
                print(f"    ✗ Error analyzing contributions for {cat.name}: {e}")

    # ========================================================================
    # 5D. EXTRACT DATA QUALITY INFORMATION
    # ========================================================================
    # YOUR DATA QUALITY SCORES: This section retrieves all DQ scores
    # that you've already entered in openLCA for processes and flows
    #
    # PEDIGREE MATRIX FORMAT: "(score1;score2;score3;score4;score5)"
    # - 1 = Best/Measured (most reliable)
    # - 5 = Worst/Guessed (least reliable)
    # - n.a. = Not applicable for this indicator
    #
    # This reports on ALL contributing processes in the system,
    # showing which parts have good data and where quality is lower.
    
    if INCLUDE_PROCESS_DQ or INCLUDE_EXCHANGE_DQ:
        print(f"  → Extracting data quality scores (from all contributing processes)")
        
        # Get all contributing processes (not just a sample)
        if impacts:
            all_dq_data = {
                "system": system_name,
                "lcia_method": method_ref.name,
                "processes": [],
                "summary": {
                    "total_processes": 0,
                    "processes_with_dq": 0,
                    "average_dq_entry": None,
                    "quality_distribution": {}
                }
            }
            
            # Extract from all contributing processes per impact category
            for impact in impacts:
                cat = impact.impact_category
                try:
                    contributions = run_with_timeout(
                        lambda: result.get_impact_contributions_of(impact_category=cat),
                        timeout=IPC_TIMEOUT,
                    )
                except TimeoutError:
                    print(f"    ✗ Contribution listing for {cat.name} timed out; skipping these contributions.")
                    continue
                
                # Process each contributing flow
                for contribution in contributions:
                    if contribution.amount == 0:
                        continue
                    
                    try:
                        provider = contribution.tech_flow.provider
                        if not provider:
                            continue
                        
                        # Skip if already extracted (avoid duplicates)
                        existing_process = next(
                            (p for p in all_dq_data["processes"] if p["process_id"] == provider.id),
                            None
                        )
                        if existing_process:
                            continue
                        
                        # Extract DQ for this process
                        process_dq = extract_process_dq_info(client, provider.id)
                        if process_dq:
                            process_dq["impact_contribution"] = {
                                "category": cat.name,
                                "contribution": contribution.amount,
                                "unit": cat.ref_unit
                            }
                            all_dq_data["processes"].append(process_dq)
                    
                    except Exception as e:
                        continue
            
            # Generate summary statistics
            all_dq_data["summary"]["total_processes"] = len(all_dq_data["processes"])
            all_dq_data["summary"]["processes_with_dq"] = sum(
                1 for p in all_dq_data["processes"] if p["process_dq_entry"]
            )
            
            # Categorize by quality (based on average score)
            quality_scores = []
            for process in all_dq_data["processes"]:
                dq_entry = process.get("process_dq_entry", "")
                if dq_entry and dq_entry != "n.a.":
                    try:
                        scores = [int(s) for s in dq_entry.strip("()").split(";") if s.isdigit()]
                        if scores:
                            avg_score = sum(scores) / len(scores)
                            quality_scores.append(avg_score)
                    except:
                        pass
            
            if quality_scores:
                all_dq_data["summary"]["average_dq_entry"] = f"Average Quality Score: {sum(quality_scores)/len(quality_scores):.2f}"
                
                # Count how many processes fall into each quality tier
                for score in quality_scores:
                    tier = "High (1-2)" if score <= 2 else "Medium (2-3)" if score <= 3 else "Low (3-5)"
                    all_dq_data["summary"]["quality_distribution"][tier] = \
                        all_dq_data["summary"]["quality_distribution"].get(tier, 0) + 1
            
            # Save comprehensive DQ report
            if all_dq_data["processes"] and EXPORT_DQ_SYSTEM_INFO:
                safe_system = safe_filename(system_name)
                safe_method = safe_filename(method_ref.name)
                dq_filename = f"{safe_system}_{safe_method}_data_quality.json"
                
                def save_dq_json(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(all_dq_data, f, indent=2, default=str)
                
                local_dq_path, export_dq_path = save_to_results(dq_filename, save_dq_json)
                
                print(f"    ✓ Extracted DQ scores from {all_dq_data['summary']['total_processes']} processes")
                print(f"      → Processes with DQ data: {all_dq_data['summary']['processes_with_dq']}")
                if all_dq_data["summary"]["average_dq_entry"]:
                    print(f"      → {all_dq_data['summary']['average_dq_entry']}")
                if all_dq_data["summary"]["quality_distribution"]:
                    print(f"      → Quality breakdown: {all_dq_data['summary']['quality_distribution']}")
                print(f"    ✓ Saved data quality report → {local_dq_path}")
                if export_dq_path:
                    print(f"      ✓ Exported to: {export_dq_path}")
            elif all_dq_data["processes"]:
                print(f"    ✓ Extracted DQ from {len(all_dq_data['processes'])} contributing processes")

    # ========================================================================
    # 5E. GENERATE SANKEY DIAGRAM (PROCESS DEPENDENCY GRAPH)
    # ========================================================================
    # Sankey diagram visualizes how processes are connected in the supply chain
    # 
    # Components:
    #   - NODES: Individual processes (suppliers)
    #     * index: unique identifier for this node
    #     * provider: process name
    #     * direct_result: impact caused directly by this process
    #     * total_result: impact including all upstream (cumulative)
    #
    #   - EDGES: Connections between processes (material/energy flows)
    #     * node_index: receiving process
    #     * provider_index: supplying process
    #     * upstream_share: % of receiving process's impact from this supplier
    #
    # Modes (SANKEY_MODE):
    #   - 0: Disabled
    #   - 1: Flow-based (shows environmental flows between processes)
    #   - 2: Impact-based (shows impact contributions between processes)
    
    if SANKEY_MODE != 0 and impacts:
        cat = impacts[0].impact_category
        print(f"  → Creating Sankey diagram for: {cat.name}")
        
        # Determine max nodes based on mode
        max_nodes = SANKEY_TOP_FLOWS if SANKEY_MODE == 1 else SANKEY_TOP_IMPACTS
        
        if SANKEY_MAX_DEPTH is not None:
            print("  ⚠ Note: sankey_max_depth is configured but not yet supported by olca_schema.")

        # Request Sankey graph from openLCA calculation
        sankey_req = o.SankeyRequest(
            impact_category=cat,
            max_nodes=max_nodes,
        )
        try:
            sankey_graph = run_with_timeout(lambda: result.get_sankey_graph(sankey_req), timeout=IPC_TIMEOUT)
        except TimeoutError:
            print(f"    ✗ Sankey generation timed out for {cat.name}; skipping Sankey.")
            sankey_graph = None
        except Exception as e:
            print(f"    ✗ Sankey generation failed: {e}")
            sankey_graph = None
        
        if sankey_graph:
            # Convert to JSON-serializable format
            sankey_data = {
                "impact_category": cat.name,
                "mode": SANKEY_MODE,  # Document which mode was used
                "max_nodes": max_nodes,
                "nodes": [
                    {
                        "index": n.index,
                        "provider": (
                            n.tech_flow.provider.name
                            if getattr(n, "tech_flow", None) and getattr(n.tech_flow, "provider", None)
                            else "Unknown"
                        ),
                        "direct_result": n.direct_result,  # Impact from this process only
                        "total_result": n.total_result,    # Including all upstream
                    }
                    for n in sankey_graph.nodes
                ],
                "edges": [
                    {
                        "node_index": e.node_index,         # Receiving process
                        "provider_index": e.provider_index, # Supplying process
                        "upstream_share": e.upstream_share, # % contribution from supplier
                    }
                    for e in sankey_graph.edges
                ],
            }
            
            # Save Sankey data to JSON
            safe_system = safe_filename(system_name)
            safe_method = safe_filename(method_ref.name)
            sankey_filename = f"{safe_system}_{safe_method}_sankey.json"
            
            def save_sankey_json(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(sankey_data, f, indent=2)
            
            local_sankey_path, export_sankey_path = save_to_results(sankey_filename, save_sankey_json)
            
            print(f"    ✓ Saved Sankey graph ({len(sankey_graph.nodes)} nodes, "
                  f"{len(sankey_graph.edges)} edges) → {local_sankey_path}")
            if export_sankey_path:
                print(f"      ✓ Exported to: {export_sankey_path}")
        else:
            print("    ⚠ Sankey graph not available; skipped saving.")

    # ========================================================================
    # 5F. GENERATE TREE DIAGRAM (UPSTREAM PROCESS HIERARCHY)
    # ========================================================================
    # Tree diagram shows hierarchical upstream processes
    # Unlike Sankey (which aggregates), tree shows each process instance
    # at its specific position in the supply chain
    #
    # UpstreamNode contains:
    # - tech_flow: process + product/waste flow
    # - result: total result (upstream + direct)
    # - direct_contribution: direct contribution only
    # - required_amount: amount needed at this supply chain point
    
    if impacts:
        cat = impacts[0].impact_category
        print(f"  → Creating process tree for: {cat.name}")
        
        try:
            # Get upstream tree for the impact category (timeboxed)
            upstream_tree = run_with_timeout(
                lambda: result.get_upstream_tree(impact_category=cat),
                timeout=IPC_TIMEOUT,
            )
            
            if upstream_tree:
                # Convert tree to JSON-serializable format
                tree_data = {
                    "impact_category": cat.name,
                    "unit": cat.ref_unit,
                    "nodes": []
                }
                
                def build_tree_structure(node, depth=0):
                    """Recursively build tree structure from UpstreamNode"""
                    node_dict = {
                        "depth": depth,
                        "process": (
                            node.tech_flow.provider.name 
                            if node.tech_flow and node.tech_flow.provider 
                            else "Unknown"
                        ),
                        "flow": (
                            node.tech_flow.flow.name 
                            if node.tech_flow and node.tech_flow.flow 
                            else "Unknown"
                        ),
                        "required_amount": node.required_amount,
                        "direct_contribution": node.direct_contribution,
                        "total_result": node.result,
                        "children": []
                    }
                    
                    # Add child nodes if they exist
                    if hasattr(node, 'child_nodes') and node.child_nodes:
                        for child in node.child_nodes:
                            node_dict["children"].append(build_tree_structure(child, depth + 1))
                    
                    return node_dict
                
                # Build tree structure from root
                if upstream_tree:
                    root_tree = build_tree_structure(upstream_tree)
                    tree_data["nodes"] = [root_tree]
                
                # Save tree to JSON
                safe_system = safe_filename(system_name)
                safe_method = safe_filename(method_ref.name)
                tree_filename = f"{safe_system}_{safe_method}_process_tree.json"
                
                def save_tree_json(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(tree_data, f, indent=2, default=str)
                
                local_tree_path, export_tree_path = save_to_results(tree_filename, save_tree_json)
                
                print(f"    ✓ Saved process tree → {local_tree_path}")
                if export_tree_path:
                    print(f"      ✓ Exported to: {export_tree_path}")
        except Exception as e:
            print(f"    ⚠ Could not generate tree diagram: {e}")

    # Clean up: Free memory from calculation result
    result.dispose()
    print(f"✓ Finished processing {system_name}\n")


# ============================================================================
# 6. MAIN EXECUTION
# ============================================================================

def main():
    """
    Orchestrate result extraction for all configured product systems.
    """
    global client, method_ref, output_dir

    output_dir = str(Path(__file__).resolve().parent)
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("LCA RESULT CALCULATION SCRIPT")
    print("=" * 70)
    print(f"Product systems: {PRODUCT_SYSTEMS}")
    print(f"LCIA method: {LCIA_METHOD}")
    print(f"Impact categories: {IMPACT_CATEGORIES if IMPACT_CATEGORIES else 'ALL'}")
    print(f"Top N contributors: {TOP_N_CONTRIBUTORS}")
    print(f"Normalization enabled: {NORMALIZATION_ENABLED}")
    print(f"Data quality extraction: {INCLUDE_PROCESS_DQ or INCLUDE_EXCHANGE_DQ}")
    print(f"Output directory: {output_dir}")
    print("=" * 70 + "\n")

    client = ipc.Client(8080)

    method_ref = client.find(o.ImpactMethod, name=LCIA_METHOD)
    if not method_ref:
        raise ValueError(f"Impact method '{LCIA_METHOD}' not found")
    print(f"Using impact method: {method_ref.name} (ID: {method_ref.id})")

    print("\n" + "=" * 70)
    print("LCA RESULT EXTRACTION STARTING")
    print("=" * 70 + "\n")
    
    if not PRODUCT_SYSTEMS:
        print("⚠ No product systems configured in global_parameters.json")
        print("  Add system names to: result_extraction → product_systems_result_analysis")
        return

    for sys_name in PRODUCT_SYSTEMS:
        try:
            process_system(sys_name)
        except Exception as e:
            print(f"✗ Error processing '{sys_name}': {e}\n")
    
    print("=" * 70)
    print("LCA RESULT EXTRACTION COMPLETED")
    print("=" * 70 + "\n")
    print("Output files saved to: LCI/results/")


if __name__ == "__main__":
    main()
