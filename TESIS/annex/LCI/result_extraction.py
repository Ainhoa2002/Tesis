"""
Role: Extract calculated results (impacts, inventories) from raw output files.

Brief: Reads calculation outputs and converts them into CSV/JSON summary
formats for analysis and visualization. Designed to be downstream of
calculation routines.
"""

import os
import json
import re
from pathlib import Path
import logging

import json5
import pandas as pd
try:
    import olca_ipc as ipc
    import olca_schema as o
except Exception as exc:
    logging.warning("olca_ipc/olca_schema not available: %s", exc)
    ipc = None
    o = None


"""
Parameter loading strategy:
1. Prefer parameters defined at the top of `RESULTS/result_calculation_explained.py` (authoritative for ad-hoc runs).
2. If that file or variables are not available, fall back to `global_parameters.json` (legacy/default).
"""

OVERRIDE_VARS = {}
try:
    # Safely parse top-level literal assignments from the explained script using AST
    import ast

    rc_path = Path(__file__).resolve().parent / "RESULTS" / "result_calculation_explained.py"
    if rc_path.exists():
        text = rc_path.read_text(encoding="utf-8")
        mod = ast.parse(text)
        # Minimal safe set: only basic run-control parameters (no normalization or DQ flags)
        wanted = {
            "PRODUCT_SYSTEMS",
            "LCIA_METHOD",
            "IMPACT_CATEGORIES",
            "TOP_N_CONTRIBUTORS",
            "SANKEY_MODE",
            "SANKEY_TOP_FLOWS",
            "SANKEY_TOP_IMPACTS",
            "SANKEY_MAX_DEPTH",
        }
        for node in mod.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in wanted:
                        try:
                            value = ast.literal_eval(node.value)
                        except Exception as exc:
                            # Non-literal expressions (computed at runtime) are skipped
                            continue
                        OVERRIDE_VARS[target.id] = value
except Exception as exc:
    logging.debug("Could not parse overrides from explained script: %s", exc)
    OVERRIDE_VARS = {}


CONFIG_FILE = Path(__file__).resolve().parent / "global_parameters.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    data = json5.load(f)
    config = data.get("parameters", {}).get("result_extraction", {})

# Use overrides when present, otherwise read from config
PRODUCT_SYSTEMS = OVERRIDE_VARS.get("PRODUCT_SYSTEMS", config.get("product_systems_result_analysis", []))
LCIA_METHOD = OVERRIDE_VARS.get("LCIA_METHOD", config.get("lcia_methodology"))
RAW_IMPACT_CATEGORIES = OVERRIDE_VARS.get("IMPACT_CATEGORIES", config.get("impact_categories", None))
TOP_N_CONTRIBUTORS = OVERRIDE_VARS.get("TOP_N_CONTRIBUTORS", config.get("number_top_contributors", 5))
SANKEY_MODE = OVERRIDE_VARS.get("SANKEY_MODE", config.get("sankey", {}).get("sankey_mode"))
SANKEY_TOP_FLOWS = OVERRIDE_VARS.get("SANKEY_TOP_FLOWS", config.get("sankey", {}).get("sankey_top_flows"))
SANKEY_TOP_IMPACTS = OVERRIDE_VARS.get("SANKEY_TOP_IMPACTS", config.get("sankey", {}).get("sankey_top_impacts"))
SANKEY_MAX_DEPTH = OVERRIDE_VARS.get("SANKEY_MAX_DEPTH", config.get("sankey", {}).get("sankey_max_depth"))
NORMALIZATION_ENABLED = OVERRIDE_VARS.get("NORMALIZATION_ENABLED", config.get("normalization", {}).get("enabled", False))
NORMALIZATION_NW_SET = OVERRIDE_VARS.get("NORMALIZATION_NW_SET", config.get("normalization", {}).get("nw_set_name", None))



# Purpose: Find entity.
def find_entity(client, model_type, name):
    ref = client.find(model_type, name=name)
    if ref is None:
        raise ValueError(f"{model_type.__name__} '{name}' not found")
    return ref


# Purpose: Filter impacts by names.
def filter_impacts_by_names(impacts, allowed_names):
    if not allowed_names:
        return impacts
    return [i for i in impacts if i.impact_category.name in allowed_names]


# Purpose: Normalize impact categories.
def normalize_impact_categories(value):
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned or None
    text = str(value).strip()
    return [text] if text else None


IMPACT_CATEGORIES = normalize_impact_categories(RAW_IMPACT_CATEGORIES)


output_dir = str(Path(__file__).resolve().parent / "RESULTS" / "Deterministic results")
os.makedirs(output_dir, exist_ok=True)

if ipc is None or o is None:
    logging.error("olca_ipc or olca_schema not available. Result extraction requires openLCA. Exiting.")
    raise SystemExit(1)

try:
    client = ipc.Client(8080)
except Exception as exc:
    logging.exception("Could not connect to openLCA IPC: %s", exc)
    raise SystemExit(1)

method_ref = client.find(o.ImpactMethod, name=LCIA_METHOD)
if not method_ref:
    logging.error("Impact method '%s' not found", LCIA_METHOD)
    raise SystemExit(1)
logging.info("Using impact method: %s (ID: %s)", method_ref.name, method_ref.id)


# Purpose: Safe filename.
def safe_filename(value):
    text = str(value)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(" .")
    return text or "unnamed"



# Purpose: Process system.
def process_system(system_name):
    logging.info("%s", "\n" + ("=" * 60))
    logging.info("Processing: %s | Method: %s", system_name, method_ref.name)
    logging.info("%s", "=" * 60)

    ps = find_entity(client, o.ProductSystem, system_name)
    setup = o.CalculationSetup(target=ps, impact_method=method_ref)
    result = client.calculate(setup)
    result.wait_until_ready()
    logging.info("Calculation completed.")

    all_impacts = result.get_total_impacts()
    # Optionally request normalized impacts (if the calculation/setup supports it)
    all_normalized_impacts = None
    if NORMALIZATION_ENABLED:
        try:
            all_normalized_impacts = result.get_normalized_impacts()
            logging.info("Normalized impacts retrieved.")
        except Exception as e:
            logging.warning("Could not get normalized impacts: %s", e)

    if all_impacts:
        impacts = filter_impacts_by_names(all_impacts, IMPACT_CATEGORIES)
        impacts_data = []
        for i in impacts:
            row = {
                "Impact category": i.impact_category.name,
                "Amount (Raw)": i.amount,
                "Unit": i.impact_category.ref_unit,
            }
            if all_normalized_impacts:
                norm_impact = next(
                    (n for n in all_normalized_impacts if n.impact_category.id == i.impact_category.id),
                    None,
                )
                if norm_impact:
                    row["Amount (Normalized)"] = norm_impact.amount
                    row["Normalized Unit"] = f"{i.impact_category.ref_unit}/ref"
            impacts_data.append(row)

        df_impacts = pd.DataFrame(impacts_data)
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        imp_path = os.path.join(output_dir, f"{safe_system}_{safe_method}_impacts.csv")
        df_impacts.to_csv(imp_path, index=False)
        logging.info("Saved impacts: %s categories -> %s", len(df_impacts), imp_path)
    else:
        logging.info("No impacts found.")
        impacts = []

    flows = result.get_total_flows()
    if flows:
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
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        flo_path = os.path.join(output_dir, f"{safe_system}_{safe_method}_inventory.csv")
        df_flows.to_csv(flo_path, index=False)
        logging.info("Saved inventory: %s flows -> %s", len(df_flows), flo_path)
    else:
        logging.info("No inventory flows found.")

    if impacts:
        for impact in impacts:
            cat = impact.impact_category
            logging.info("Analysing contributions for category: %s", cat.name)
            contributions = result.get_impact_contributions_of(impact_category=cat)
            non_zero_contributions = [c for c in contributions if c.amount != 0.0]
            if not non_zero_contributions:
                logging.info("No non-zero contributions found for %s.", cat.name)
                continue

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
            df_contrib = df_contrib.sort_values(
                "Contribution", ascending=False, key=lambda s: s.abs()
            ).head(TOP_N_CONTRIBUTORS)
            safe_system = safe_filename(system_name)
            safe_method = safe_filename(method_ref.name)
            safe_category = safe_filename(cat.name)
            contrib_path = os.path.join(
                output_dir, f"{safe_system}_{safe_method}_{safe_category}_upstream.csv"
            )
            df_contrib.to_csv(contrib_path, index=False)
            logging.info("Saved top %s contributions -> %s", TOP_N_CONTRIBUTORS, contrib_path)

    if SANKEY_MODE != 0 and impacts:
        cat = impacts[0].impact_category
        logging.info("Creating Sankey diagram for category: %s", cat.name)
        max_nodes = SANKEY_TOP_FLOWS if SANKEY_MODE == 1 else SANKEY_TOP_IMPACTS

        if SANKEY_MAX_DEPTH is not None:
            logging.info("Note: sankey_max_depth is configured but not supported by current olca_schema; ignoring it.")

        sankey_req = o.SankeyRequest(
            impact_category=cat,
            max_nodes=max_nodes,
        )
        sankey_graph = result.get_sankey_graph(sankey_req)
        sankey_data = {
            "impact_category": cat.name,
            "nodes": [
                {
                    "index": n.index,
                    "provider": (
                        n.tech_flow.provider.name
                        if getattr(n, "tech_flow", None) and getattr(n.tech_flow, "provider", None)
                        else "Unknown"
                    ),
                    "direct_result": n.direct_result,
                    "total_result": n.total_result,
                }
                for n in sankey_graph.nodes
            ],
            "edges": [
                {
                    "node_index": e.node_index,
                    "provider_index": e.provider_index,
                    "upstream_share": e.upstream_share,
                }
                for e in sankey_graph.edges
            ],
        }
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        sankey_path = os.path.join(output_dir, f"{safe_system}_{safe_method}_sankey.json")
        with open(sankey_path, "w", encoding="utf-8") as f:
            json.dump(sankey_data, f, indent=2)
        logging.info(
            "Saved Sankey data (%s nodes, %s edges) -> %s",
            len(sankey_graph.nodes),
            len(sankey_graph.edges),
            sankey_path,
        )

    result.dispose()
    logging.info("Finished %s\n", system_name)



# Purpose: Main.
def main():
    for sys_name in PRODUCT_SYSTEMS:
        try:
            process_system(sys_name)
        except Exception as exc:
            logging.exception("Error processing %s: %s", sys_name, exc)
    logging.info("All extractions completed.")


if __name__ == "__main__":
    main()
