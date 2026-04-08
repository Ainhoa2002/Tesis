import argparse
import csv
import os
from pathlib import Path


def normalize_key(value):
    text = str(value or "").replace('"', "").replace("'", "")
    return "".join(text.split()).lower()


def iter_target_files(root_dir, suffix="_ipe_flows_from_parameters.csv"):
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if name.endswith(suffix):
                yield Path(dirpath) / name


def _read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [name for name in list(reader.fieldnames or []) if name]
        rows = list(reader)
    return fieldnames, rows


def _build_mapping(rows, key_candidates, value_col, mapping_name):
    key_col = None
    for candidate in key_candidates:
        if candidate in rows[0] if rows else []:
            key_col = candidate
            break

    if key_col is None and rows:
        first_keys = set(rows[0].keys())
        for candidate in key_candidates:
            if candidate in first_keys:
                key_col = candidate
                break

    if key_col is None:
        raise ValueError(
            f"{mapping_name} library missing key column. Expected one of: {', '.join(key_candidates)}"
        )

    mapping = {}
    conflicts = []
    for idx, row in enumerate(rows, start=2):
        key = normalize_key(row.get(key_col, ""))
        value = str(row.get(value_col, "") or "").strip()
        if key == "" or value == "":
            continue

        previous = mapping.get(key)
        if previous is None:
            mapping[key] = value
        elif previous != value:
            conflicts.append((idx, row.get(key_col, ""), previous, value))

    if conflicts:
        preview = "; ".join(
            [
                f"row {idx} key '{raw}' -> '{old}' vs '{new}'"
                for idx, raw, old, new in conflicts[:10]
            ]
        )
        raise ValueError(
            f"{mapping_name} library has ambiguous mappings: {preview}"
        )

    return mapping


def load_uuid_map(path):
    _, rows = _read_csv_rows(path)
    if not rows:
        return {}
    return _build_mapping(
        rows,
        key_candidates=["Ecoinvent_flow", "Flow"],
        value_col="UUID",
        mapping_name="UUID",
    )


def load_provider_map(path):
    _, rows = _read_csv_rows(path)
    if not rows:
        return {}
    return _build_mapping(
        rows,
        key_candidates=["Ecoinvent_flow_reference", "Ecoinvent_flow", "Flow"],
        value_col="UUID_provider",
        mapping_name="UUID_provider",
    )


def collect_missing_provider_flows(targets, provider_map):
    missing = []
    seen = set()
    for target in targets:
        if not target.exists():
            continue
        fieldnames, rows = _read_csv_rows(target)
        if "Flow" not in fieldnames:
            continue

        for row in rows:
            direction = str(row.get("Direction", "") or "").strip().lower()
            if direction == "output":
                continue

            flow = str(row.get("Flow", "") or "").strip()
            if flow == "":
                continue

            key = normalize_key(flow)
            if provider_map.get(key, "") != "":
                continue

            if key not in seen:
                seen.add(key)
                missing.append(flow)
    return missing


def _preferred_process_score(name_lower, flow_lower):
    # Prefer market datasets for the exact ecoinvent reference flow.
    exact_market = f"market for {flow_lower} | {flow_lower} | apos, u"
    exact_pipe = f"| {flow_lower} | apos, u"
    if exact_market in name_lower:
        return 0
    if name_lower.startswith("market for ") and exact_pipe in name_lower:
        return 1
    if exact_pipe in name_lower:
        return 2
    if flow_lower in name_lower:
        return 3
    return 99


def resolve_missing_providers_from_openlca(flows):
    if not flows:
        return []

    try:
        import olca_ipc as ipc
        import olca_schema as o
    except Exception as exc:
        print(f"Warning: openLCA packages not available for provider auto-sync: {exc}")
        return []

    try:
        client = ipc.Client(8080)
        descriptors = list(client.get_descriptors(o.Process))
    except Exception as exc:
        print(f"Warning: could not connect to openLCA IPC for provider auto-sync: {exc}")
        return []

    resolved = []
    for flow in flows:
        flow_lower = flow.lower().strip()
        ranked = []
        for d in descriptors:
            name = str(getattr(d, "name", "") or "")
            name_lower = name.lower()
            score = _preferred_process_score(name_lower, flow_lower)
            if score < 99:
                ranked.append((score, name, d.id))

        if not ranked:
            print(f"Warning: no provider candidate found in openLCA for '{flow}'")
            continue

        ranked.sort(key=lambda t: (t[0], t[1]))
        _, process_name, process_uuid = ranked[0]
        print(f"Auto-mapped provider for '{flow}': {process_name} -> {process_uuid}")
        resolved.append(
            {
                "Ecoinvent_flow_reference": flow,
                "Ecoinvent_process": process_name,
                "UUID_provider": process_uuid,
            }
        )

    return resolved


def append_provider_mappings(provider_library_path, new_rows, dry_run=False):
    if not new_rows:
        return 0

    fieldnames, existing_rows = _read_csv_rows(provider_library_path)
    if not fieldnames:
        fieldnames = ["Ecoinvent_flow_reference", "Ecoinvent_process", "UUID_provider"]

    if "Ecoinvent_flow_reference" not in fieldnames:
        fieldnames.append("Ecoinvent_flow_reference")
    if "Ecoinvent_process" not in fieldnames:
        fieldnames.append("Ecoinvent_process")
    if "UUID_provider" not in fieldnames:
        fieldnames.append("UUID_provider")

    existing_keys = {
        normalize_key(r.get("Ecoinvent_flow_reference", ""))
        for r in existing_rows
        if str(r.get("UUID_provider", "") or "").strip() != ""
    }

    appended = 0
    for row in new_rows:
        key = normalize_key(row.get("Ecoinvent_flow_reference", ""))
        if key == "" or key in existing_keys:
            continue
        existing_rows.append(row)
        existing_keys.add(key)
        appended += 1

    if appended > 0 and not dry_run:
        with open(provider_library_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(existing_rows)

    return appended


def fill_single_file(path, uuid_map, provider_map, overwrite_uuid=False, overwrite_provider=False, dry_run=False):
    fieldnames, rows = _read_csv_rows(path)
    if not fieldnames:
        return {"file": str(path), "updated": False, "rows": 0, "uuid": 0, "provider": 0, "missing": 0, "missing_provider": 0}

    if "Flow" not in fieldnames:
        print(f"Warning: {path} has no 'Flow' column. Skipping.")
        return {"file": str(path), "updated": False, "rows": len(rows), "uuid": 0, "provider": 0, "missing": 0, "missing_provider": 0}

    out_fieldnames = list(fieldnames)
    if "UUID" not in out_fieldnames:
        out_fieldnames.append("UUID")
    if "UUID_provider" not in out_fieldnames:
        out_fieldnames.append("UUID_provider")

    uuid_filled = 0
    provider_filled = 0
    missing = 0
    missing_provider = 0
    touched = False

    for row in rows:
        direction = str(row.get("Direction", "") or "").strip().lower()
        if direction == "output":
            continue

        key = normalize_key(row.get("Flow", ""))
        if key == "":
            continue

        current_uuid = str(row.get("UUID", "") or "").strip()
        mapped_uuid = uuid_map.get(key, "")
        mapped_provider = provider_map.get(key, "")

        # Only count missing UUID mapping when the target row also lacks UUID.
        if mapped_uuid == "" and current_uuid == "":
            missing += 1
            print(f"Warning: no UUID mapping found for '{row.get('Flow', '')}' in {path.name}")

        if mapped_uuid and (overwrite_uuid or current_uuid == ""):
            if current_uuid != mapped_uuid:
                row["UUID"] = mapped_uuid
                uuid_filled += 1
                touched = True

        current_provider = str(row.get("UUID_provider", "") or "").strip()
        if mapped_provider and (overwrite_provider or current_provider == ""):
            if current_provider != mapped_provider:
                row["UUID_provider"] = mapped_provider
                provider_filled += 1
                touched = True
        elif current_provider == "" and mapped_provider == "":
            missing_provider += 1
            print(f"Warning: no UUID_provider mapping found for '{row.get('Flow', '')}' in {path.name}")

    if touched and not dry_run:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    return {
        "file": str(path),
        "updated": touched,
        "rows": len(rows),
        "uuid": uuid_filled,
        "provider": provider_filled,
        "missing": missing,
        "missing_provider": missing_provider,
    }


def main():
    base_dir = Path(__file__).resolve().parent
    default_uuid_library = base_dir / "component_library_ecoinvent_uuid_map.csv"
    default_provider_library = base_dir / "component_library_ecoinvent_uuid_provider_map.csv"

    parser = argparse.ArgumentParser(
        description="Fill UUID and UUID_provider in *_ipe_flows_from_parameters.csv files."
    )
    parser.add_argument(
        "--library",
        default=str(default_uuid_library),
        help="Global UUID map CSV path (default: LCI/component_library_ecoinvent_uuid_map.csv)",
    )
    parser.add_argument(
        "--provider-library",
        default=str(default_provider_library),
        help="Global provider UUID map CSV path (default: LCI/component_library_ecoinvent_uuid_provider_map.csv)",
    )
    parser.add_argument(
        "--root",
        default=str(base_dir),
        help="Root directory to scan recursively (default: LCI/)",
    )
    parser.add_argument("--target-file", default="", help="Single target _ipe file to process")
    parser.add_argument("--overwrite-uuid", action="store_true", help="Overwrite existing UUID values")
    parser.add_argument("--overwrite-provider", action="store_true", help="Overwrite existing UUID_provider values")
    parser.add_argument(
        "--no-sync-provider-library",
        action="store_true",
        help="Disable automatic provider-library sync from openLCA for missing flows",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    args = parser.parse_args()

    uuid_library = Path(args.library).resolve()
    provider_library = Path(args.provider_library).resolve()
    if not uuid_library.exists():
        raise FileNotFoundError(f"UUID library not found: {uuid_library}")
    if not provider_library.exists():
        raise FileNotFoundError(f"Provider library not found: {provider_library}")

    uuid_map = load_uuid_map(uuid_library)
    provider_map = load_provider_map(provider_library)

    if args.target_file:
        targets = [Path(args.target_file).resolve()]
    else:
        targets = list(iter_target_files(Path(args.root).resolve()))

    if not args.no_sync_provider_library:
        missing_flows = collect_missing_provider_flows(targets, provider_map)
        if missing_flows:
            discovered = resolve_missing_providers_from_openlca(missing_flows)
            added = append_provider_mappings(provider_library, discovered, dry_run=args.dry_run)
            if added > 0:
                print(f"Auto-sync: added {added} provider mapping(s) to {provider_library.name}")
                provider_map = load_provider_map(provider_library)
            elif discovered:
                print("Auto-sync: provider candidates found but no new mappings were added.")

    processed = 0
    changed = 0
    total_uuid = 0
    total_provider = 0
    total_missing = 0
    total_missing_provider = 0

    for target in targets:
        if not target.exists():
            print(f"Warning: target file does not exist: {target}")
            continue
        result = fill_single_file(
            target,
            uuid_map,
            provider_map,
            overwrite_uuid=args.overwrite_uuid,
            overwrite_provider=args.overwrite_provider,
            dry_run=args.dry_run,
        )
        processed += 1
        changed += 1 if result["updated"] else 0
        total_uuid += result["uuid"]
        total_provider += result["provider"]
        total_missing += result["missing"]
        total_missing_provider += result["missing_provider"]
        status = "updated" if result["updated"] else "unchanged"
        print(
            f"{status}: {result['file']} | uuid={result['uuid']} | provider={result['provider']} | missing_uuid_map={result['missing']} | missing_provider_map={result['missing_provider']}"
        )

    print(
        f"\nProcessed {processed} file(s). Changed: {changed}. "
        f"UUID filled: {total_uuid}. UUID_provider filled: {total_provider}. "
        f"Unmapped input rows: {total_missing}. Unmapped provider rows: {total_missing_provider}."
    )


if __name__ == "__main__":
    main()
