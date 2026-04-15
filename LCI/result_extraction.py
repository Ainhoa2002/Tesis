import os
import json
import re
from pathlib import Path

import json5
import pandas as pd
import olca_ipc as ipc
import olca_schema as o


CONFIG_FILE = Path(__file__).resolve().parent / "global_parameters.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    data = json5.load(f)
    config = data["parameters"]["result_extraction"]


PRODUCT_SYSTEMS = config["product_systems_result_analysis"]
LCIA_METHOD = config["lcia_methodology"]
RAW_IMPACT_CATEGORIES = config.get("impact_categories", None)
TOP_N_CONTRIBUTORS = config["number_top_contributors"]
SANKEY_MODE = config["sankey"]["sankey_mode"]
SANKEY_TOP_FLOWS = config["sankey"]["sankey_top_flows"]
SANKEY_TOP_IMPACTS = config["sankey"]["sankey_top_impacts"]
SANKEY_MAX_DEPTH = config["sankey"]["sankey_max_depth"]



def find_entity(client, model_type, name):
    ref = client.find(model_type, name=name)
    if ref is None:
        raise ValueError(f"{model_type.__name__} '{name}' not found")
    return ref


def filter_impacts_by_names(impacts, allowed_names):
    if not allowed_names:
        return impacts
    return [i for i in impacts if i.impact_category.name in allowed_names]


def normalize_impact_categories(value):
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned or None
    text = str(value).strip()
    return [text] if text else None


IMPACT_CATEGORIES = normalize_impact_categories(RAW_IMPACT_CATEGORIES)


client = ipc.Client(8080)
output_dir = str(Path(__file__).resolve().parent / "results")
os.makedirs(output_dir, exist_ok=True)

method_ref = client.find(o.ImpactMethod, name=LCIA_METHOD)
if not method_ref:
    raise ValueError(f"Impact method '{LCIA_METHOD}' not found")
print(f"Using impact method: {method_ref.name} (ID: {method_ref.id})")


def safe_filename(value):
    text = str(value)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(" .")
    return text or "unnamed"



def process_system(system_name):
    print(f"\n{'=' * 60}")
    print(f"Processing: {system_name} | Method: {method_ref.name}")
    print("=" * 60)

    ps = find_entity(client, o.ProductSystem, system_name)
    setup = o.CalculationSetup(target=ps, impact_method=method_ref)
    result = client.calculate(setup)
    result.wait_until_ready()
    print("Calculation completed.")

    all_impacts = result.get_total_impacts()
    if all_impacts:
        impacts = filter_impacts_by_names(all_impacts, IMPACT_CATEGORIES)
        df_impacts = pd.DataFrame(
            [
                {
                    "Impact category": i.impact_category.name,
                    "Amount": i.amount,
                    "Unit": i.impact_category.ref_unit,
                }
                for i in impacts
            ]
        )
        safe_system = safe_filename(system_name)
        safe_method = safe_filename(method_ref.name)
        imp_path = os.path.join(output_dir, f"{safe_system}_{safe_method}_impacts.csv")
        df_impacts.to_csv(imp_path, index=False)
        print(f"Saved impacts: {len(df_impacts)} categories -> {imp_path}")
    else:
        print("No impacts found.")
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
        print(f"Saved inventory: {len(df_flows)} flows -> {flo_path}")
    else:
        print("No inventory flows found.")

    if impacts:
        for impact in impacts:
            cat = impact.impact_category
            print(f"  Analysing contributions for category: {cat.name}")
            contributions = result.get_impact_contributions_of(impact_category=cat)
            non_zero_contributions = [c for c in contributions if c.amount != 0.0]
            if not non_zero_contributions:
                print(f"    No non-zero contributions found for {cat.name}.")
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
            print(f"    Saved top {TOP_N_CONTRIBUTORS} contributions -> {contrib_path}")

    if SANKEY_MODE != 0 and impacts:
        cat = impacts[0].impact_category
        print(f"  Creating Sankey diagram for category: {cat.name}")
        max_nodes = SANKEY_TOP_FLOWS if SANKEY_MODE == 1 else SANKEY_TOP_IMPACTS

        if SANKEY_MAX_DEPTH is not None:
            print("  Note: sankey_max_depth is configured but not supported by current olca_schema; ignoring it.")

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
        print(
            f"    Saved Sankey data ({len(sankey_graph.nodes)} nodes, {len(sankey_graph.edges)} edges) -> {sankey_path}"
        )

    result.dispose()
    print(f"Finished {system_name}\n")



def main():
    for sys_name in PRODUCT_SYSTEMS:
        try:
            process_system(sys_name)
        except Exception as e:
            print(f"Error processing {sys_name}: {e}")
    print("\nAll extractions completed.")


if __name__ == "__main__":
    main()
