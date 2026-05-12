#!/usr/bin/env python3
"""Interactive selector for Sankey JSON files.

Supports selecting one product system and one, many, or all impact categories.
"""

from pathlib import Path
from sankey_visualizer import load_sankey_json, create_sankey_figure

RESULTS_DIR = Path(__file__).parent
OUTPUT_DIR = RESULTS_DIR / "sankey_html_exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_meta(path):
    data = load_sankey_json(path)
    impact = data.get("impact_category", "Unknown")
    system = data.get("system_name")
    if not system:
        stem = path.stem.replace("_sankey", "")
        # Backward-compatible fallback for older files without system_name.
        # Example old name: converter_transport_EF v3.1_sankey
        # Keep everything before the LCIA method suffix when possible.
        method_marker = "_EF v3.1"
        if method_marker in stem:
            system = stem.split(method_marker)[0]
        else:
            system = stem
    return system, impact, path


def choose(options, title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    for i, txt in enumerate(options, 1):
        print(f"{i:2d}. {txt}")
    idx = int(input(f"\nSelect option (1-{len(options)}): ")) - 1
    if idx < 0 or idx >= len(options):
        raise ValueError("Invalid selection")
    return idx


def choose_many(options, title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    for i, txt in enumerate(options, 1):
        print(f"{i:2d}. {txt}")
    print("\nType one of:")
    print("  - a            (all impacts)")
    print("  - 3            (single impact)")
    print("  - 1,4,7        (multiple impacts)")

    raw = input("\nSelect impact(s): ").strip().lower()
    if raw == "a":
        return list(range(len(options)))

    indices = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        idx = int(token) - 1
        if idx < 0 or idx >= len(options):
            raise ValueError(f"Invalid impact selection: {token}")
        if idx not in indices:
            indices.append(idx)

    if not indices:
        raise ValueError("No impact selected")
    return indices


def main():
    files = sorted(RESULTS_DIR.glob("*_sankey.json"))
    if not files:
        print("No *_sankey.json files found.")
        return

    metas = [read_meta(f) for f in files]

    systems = sorted({m[0] for m in metas})
    system_idx = choose(systems, "SELECT PRODUCT SYSTEM")
    selected_system = systems[system_idx]

    impacts_for_system = sorted({m[1] for m in metas if m[0] == selected_system})
    impact_indices = choose_many(impacts_for_system, f"SELECT IMPACT(S) FOR: {selected_system}")
    selected_impacts = [impacts_for_system[i] for i in impact_indices]

    created = []
    for selected_impact in selected_impacts:
        candidates = [m for m in metas if m[0] == selected_system and m[1] == selected_impact]
        if not candidates:
            print(f"\n⚠ No matching Sankey file found for impact: {selected_impact}")
            continue

        _, _, selected_file = candidates[0]
        data = load_sankey_json(selected_file)
        fig = create_sankey_figure(data, title=f"{selected_system} - {selected_impact}")

        html_name = f"{selected_system}_EI_{selected_impact}_sankey_visualization.html"
        html_name = html_name.replace("/", "_").replace(":", "_")
        out_path = OUTPUT_DIR / html_name
        fig.write_html(str(out_path), include_plotlyjs=True, full_html=True)
        created.append(out_path)

    if not created:
        print("\n✗ No Sankey files were generated.")
        return

    print(f"\n✓ Generated {len(created)} Sankey file(s):")
    for p in created:
        print(f"  • {p}")


if __name__ == "__main__":
    main()
