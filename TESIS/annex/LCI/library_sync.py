"""Library synchronization helpers for UUID/provider mapping.

This module centralizes:
- UUID and UUID_provider filling
- created-object library upserts
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
import logging

@dataclass
class CreatedLibrariesUpdateStats:
    flow_added: int
    flow_updated: int
    flow_skipped_existing: int
    process_added: int
    process_updated: int
    process_skipped_existing: int


def _normalize_key(value: str) -> str:
    return "".join(str(value or "").lower().split())


def _normalize_fill_key(value: str) -> str:
    text = str(value or "").replace('"', "").replace("'", "")
    return "".join(text.split()).lower()


def _iter_target_files(root_dir: Path, suffix: str = "_ipe_flows_from_parameters.csv"):
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if name.endswith(suffix):
                yield Path(dirpath) / name


def _read_csv_rows(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [name for name in list(reader.fieldnames or []) if name]
        rows = list(reader)
    return fieldnames, rows


def _build_mapping(rows: list[dict[str, str]], key_candidates: list[str], value_col: str, mapping_name: str):
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
        key = _normalize_fill_key(row.get(key_col, ""))
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
        raise ValueError(f"{mapping_name} library has ambiguous mappings: {preview}")

    return mapping


def _load_uuid_map(path: Path):
    _, rows = _read_csv_rows(path)
    if not rows:
        return {}
    return _build_mapping(
        rows,
        key_candidates=["Ecoinvent_flow", "Flow"],
        value_col="UUID",
        mapping_name="UUID",
    )


def _load_provider_map(path: Path):
    _, rows = _read_csv_rows(path)
    if not rows:
        return {}

    key_candidates = ["Ecoinvent_flow_reference", "Ecoinvent_flow", "Flow"]
    uuid_pattern = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
    )

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
            f"UUID_provider library missing key column. Expected one of: {', '.join(key_candidates)}"
        )

    mapping = {}
    for row in rows:
        key = _normalize_fill_key(row.get(key_col, ""))
        value = str(row.get("UUID_provider", "") or "").strip()
        if key == "" or value == "" or not uuid_pattern.match(value):
            continue
        mapping.setdefault(key, value)

    return mapping


def _collect_missing_provider_flows(targets: list[Path], provider_map: dict[str, str]):
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

            key = _normalize_fill_key(flow)
            if provider_map.get(key, "") != "":
                continue

            if key not in seen:
                seen.add(key)
                missing.append(flow)
    return missing


def _preferred_process_score(name_lower: str, flow_lower: str) -> int:
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


def _resolve_missing_providers_from_openlca(flows: list[str]):
    if not flows:
        return []

    try:
        import olca_ipc as ipc
        import olca_schema as o
    except Exception as exc:
        logging.warning("openLCA packages not available for provider auto-sync: %s", exc)
        return []

    try:
        client = ipc.Client(8080)
        descriptors = list(client.get_descriptors(o.Process))
    except Exception as exc:
        logging.warning("could not connect to openLCA IPC for provider auto-sync: %s", exc)
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
            logging.warning("no provider candidate found in openLCA for '%s'", flow)
            continue

        ranked.sort(key=lambda t: (t[0], t[1]))
        _, process_name, process_uuid = ranked[0]
        logging.info("Auto-mapped provider for '%s': %s -> %s", flow, process_name, process_uuid)
        resolved.append(
            {
                "Ecoinvent_flow_reference": flow,
                "Ecoinvent_process": process_name,
                "UUID_provider": process_uuid,
            }
        )

    return resolved


def _append_provider_mappings(provider_library_path: Path, new_rows: list[dict[str, str]], dry_run: bool = False):
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
        _normalize_fill_key(r.get("Ecoinvent_flow_reference", ""))
        for r in existing_rows
        if str(r.get("UUID_provider", "") or "").strip() != ""
    }

    appended = 0
    for row in new_rows:
        key = _normalize_fill_key(row.get("Ecoinvent_flow_reference", ""))
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


def _fill_single_file(
    path: Path,
    uuid_map: dict[str, str],
    provider_map: dict[str, str],
    overwrite_uuid: bool = False,
    overwrite_provider: bool = False,
    dry_run: bool = False,
):
    fieldnames, rows = _read_csv_rows(path)
    if not fieldnames:
        return {
            "file": str(path),
            "updated": False,
            "rows": 0,
            "uuid": 0,
            "provider": 0,
            "missing": 0,
            "missing_provider": 0,
        }

    if "Flow" not in fieldnames:
        logging.warning("%s has no 'Flow' column. Skipping.", path)
        return {
            "file": str(path),
            "updated": False,
            "rows": len(rows),
            "uuid": 0,
            "provider": 0,
            "missing": 0,
            "missing_provider": 0,
        }

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

        key = _normalize_fill_key(row.get("Flow", ""))
        if key == "":
            continue

        current_uuid = str(row.get("UUID", "") or "").strip()
        mapped_uuid = uuid_map.get(key, "")
        mapped_provider = provider_map.get(key, "")

        if mapped_uuid == "" and current_uuid == "":
            missing += 1
            logging.warning("no UUID mapping found for '%s' in %s", row.get("Flow", ""), path.name)

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
            logging.warning("no UUID_provider mapping found for '%s' in %s", row.get("Flow", ""), path.name)

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


def run_fill_ipe_columns_from_library(
    *,
    library_path: Path,
    provider_library_path: Path,
    root_dir: Path | None = None,
    target_file: Path | None = None,
    overwrite_uuid: bool = False,
    overwrite_provider: bool = False,
    sync_provider_library: bool = True,
    dry_run: bool = False,
) -> dict[str, int]:
    """Fill UUID and UUID_provider fields in one file or all IPE files under root."""
    uuid_library = Path(library_path).resolve()
    provider_library = Path(provider_library_path).resolve()
    if not uuid_library.exists():
        raise FileNotFoundError(f"UUID library not found: {uuid_library}")
    if not provider_library.exists():
        raise FileNotFoundError(f"Provider library not found: {provider_library}")

    uuid_map = _load_uuid_map(uuid_library)
    try:
        provider_map = _load_provider_map(provider_library)
    except ValueError as exc:
        logging.warning("provider library could not be loaded cleanly: %s", exc)
        provider_map = {}

    if target_file is not None:
        targets = [Path(target_file).resolve()]
    else:
        if root_dir is None:
            raise ValueError("Either target_file or root_dir must be provided")
        targets = list(_iter_target_files(Path(root_dir).resolve()))

    if sync_provider_library:
        missing_flows = _collect_missing_provider_flows(targets, provider_map)
        if missing_flows:
            discovered = _resolve_missing_providers_from_openlca(missing_flows)
            added = _append_provider_mappings(provider_library, discovered, dry_run=dry_run)
            if added > 0:
                logging.info("Auto-sync: added %s provider mapping(s) to %s", added, provider_library.name)
                provider_map = _load_provider_map(provider_library)
            elif discovered:
                logging.info("Auto-sync: provider candidates found but no new mappings were added.")

    processed = 0
    changed = 0
    total_uuid = 0
    total_provider = 0
    total_missing = 0
    total_missing_provider = 0

    for target in targets:
        if not target.exists():
            logging.warning("target file does not exist: %s", target)
            continue
        result = _fill_single_file(
            target,
            uuid_map,
            provider_map,
            overwrite_uuid=overwrite_uuid,
            overwrite_provider=overwrite_provider,
            dry_run=dry_run,
        )
        processed += 1
        changed += 1 if result["updated"] else 0
        total_uuid += result["uuid"]
        total_provider += result["provider"]
        total_missing += result["missing"]
        total_missing_provider += result["missing_provider"]
        status = "updated" if result["updated"] else "unchanged"
        logging.info(
            "%s: %s | uuid=%s | provider=%s | missing_uuid_map=%s | missing_provider_map=%s",
            status,
            result["file"],
            result["uuid"],
            result["provider"],
            result["missing"],
            result["missing_provider"],
        )

    logging.info(
        "Processed %s file(s). Changed: %s. UUID filled: %s. UUID_provider filled: %s. Unmapped input rows: %s. Unmapped provider rows: %s.",
        processed,
        changed,
        total_uuid,
        total_provider,
        total_missing,
        total_missing_provider,
    )
    return {
        "processed": processed,
        "changed": changed,
        "uuid_filled": total_uuid,
        "provider_filled": total_provider,
        "missing_uuid": total_missing,
        "missing_provider": total_missing_provider,
    }


def run_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run first UUID enrichment pass using global libraries."""
    uuid_library = base_dir / "component_library_ecoinvent_uuid_map.csv"
    provider_library = base_dir / "component_library_ecoinvent_uuid_provider_map.csv"

    if not uuid_library.exists() or not provider_library.exists():
        logging.warning(
            "Global UUID libraries not found. Expected both component_library_ecoinvent_uuid_map.csv and component_library_ecoinvent_uuid_provider_map.csv in LCI/"
        )
        return False

    logging.info("Running UUID fill in %s...", system_folder.name)
    run_fill_ipe_columns_from_library(
        library_path=uuid_library,
        provider_library_path=provider_library,
        root_dir=system_folder,
        dry_run=dry_run,
    )
    logging.info("UUID fill in %s completed.", system_folder.name)
    return True


def run_created_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run second UUID enrichment pass using created-object libraries."""
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"

    if not uuid_library.exists() or not provider_library.exists():
        logging.warning(
            "Created UUID libraries not found. Expected both created_flows_uuid_map.csv and created_process_uuid_map.csv in LCI/."
        )
        return False

    logging.info("Running second UUID fill in %s...", system_folder.name)
    run_fill_ipe_columns_from_library(
        library_path=uuid_library,
        provider_library_path=provider_library,
        root_dir=system_folder,
        overwrite_uuid=True,
        overwrite_provider=True,
        sync_provider_library=False,
        dry_run=dry_run,
    )
    logging.info("Second UUID fill in %s completed.", system_folder.name)
    return True


def run_final_system_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run third UUID fill pass focused on LCI_SYSTEM aggregate file."""
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"
    target_file = system_folder / "system_ipe_flows_from_parameters.csv"

    if not target_file.exists():
        logging.warning("System target file not found: %s", target_file)
        return False
    if not uuid_library.exists() or not provider_library.exists():
        logging.warning(
            "Created UUID libraries not found for system final fill. Expected both created_flows_uuid_map.csv and created_process_uuid_map.csv in LCI/."
        )
        return False

    logging.info("Running third UUID fill for system file in %s...", system_folder.name)
    run_fill_ipe_columns_from_library(
        library_path=uuid_library,
        provider_library_path=provider_library,
        target_file=target_file,
        overwrite_uuid=True,
        overwrite_provider=True,
        sync_provider_library=False,
        dry_run=dry_run,
    )
    logging.info("Third UUID fill for system file in %s completed.", system_folder.name)
    return True


def run_final_transport_uuid_fill_if_available(base_dir: Path, transport_folder: Path, dry_run: bool = False) -> bool:
    """Run third UUID fill pass focused on LCI_TRANSPORT aggregate file."""
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"
    target_file = transport_folder / "transport_ipe_flows_from_parameters.csv"

    if not target_file.exists():
        logging.warning("Transport target file not found: %s", target_file)
        return False
    if not uuid_library.exists() or not provider_library.exists():
        logging.warning(
            "Created UUID libraries not found for transport final fill. Expected both created_flows_uuid_map.csv and created_process_uuid_map.csv in LCI/."
        )
        return False

    logging.info("Running third UUID fill for transport file in %s...", transport_folder.name)
    run_fill_ipe_columns_from_library(
        library_path=uuid_library,
        provider_library_path=provider_library,
        target_file=target_file,
        overwrite_uuid=True,
        overwrite_provider=True,
        sync_provider_library=False,
        dry_run=dry_run,
    )
    logging.info("Third UUID fill for transport file in %s completed.", transport_folder.name)
    return True


def upsert_created_flows_library(path: Path, rows: list[dict[str, str]]):
    """Upsert flow UUID mappings keyed by normalized flow name."""
    fieldnames = ["Ecoinvent_flow", "UUID"]
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

    index = {}
    for i, row in enumerate(existing_rows):
        key = _normalize_key(row.get("Ecoinvent_flow", ""))
        if key:
            index[key] = i

    added = 0
    updated = 0
    skipped_existing = 0
    for row in rows:
        flow = str(row.get("Flow", "") or "").strip()
        uid = str(row.get("UUID", "") or "").strip()
        if not flow or not uid:
            continue

        key = _normalize_key(flow)
        mapped = {"Ecoinvent_flow": flow, "UUID": uid}
        if key in index:
            i = index[key]
            existing = existing_rows[i]
            existing_uid = str(existing.get("UUID", "") or "").strip()
            existing_flow = str(existing.get("Ecoinvent_flow", "") or "").strip()
            if existing_uid != uid or existing_flow != flow:
                existing_rows[i] = mapped
                updated += 1
            else:
                skipped_existing += 1
        else:
            existing_rows.append(mapped)
            index[key] = len(existing_rows) - 1
            added += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)

    return added, updated, skipped_existing


def upsert_created_process_library(path: Path, rows: list[dict[str, str]]):
    """Upsert provider UUID mappings keyed by normalized flow reference."""
    fieldnames = ["Ecoinvent_flow_reference", "Ecoinvent_process", "UUID_provider"]
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

    index = {}
    for i, row in enumerate(existing_rows):
        key = _normalize_key(row.get("Ecoinvent_flow_reference", ""))
        if key:
            index[key] = i

    added = 0
    updated = 0
    skipped_existing = 0
    for row in rows:
        flow_ref = str(row.get("Ecoinvent_flow_reference", "") or "").strip()
        proc_name = str(row.get("Ecoinvent_process", "") or "").strip()
        proc_uuid = str(row.get("UUID_provider", "") or "").strip()
        if not flow_ref or not proc_uuid:
            continue

        key = _normalize_key(flow_ref)
        mapped = {
            "Ecoinvent_flow_reference": flow_ref,
            "Ecoinvent_process": proc_name,
            "UUID_provider": proc_uuid,
        }
        if key in index:
            i = index[key]
            existing = existing_rows[i]
            existing_name = str(existing.get("Ecoinvent_process", "") or "").strip()
            existing_uuid = str(existing.get("UUID_provider", "") or "").strip()
            if existing_name != proc_name or existing_uuid != proc_uuid:
                existing_rows[i] = mapped
                updated += 1
            else:
                skipped_existing += 1
        else:
            existing_rows.append(mapped)
            index[key] = len(existing_rows) - 1
            added += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)

    return added, updated, skipped_existing


def update_created_libraries(
    base_dir: Path,
    flow_rows: list[dict[str, str]],
    process_rows: list[dict[str, str]],
) -> CreatedLibrariesUpdateStats:
    """Update both created-object libraries and return merged statistics."""
    created_flows_library = base_dir / "created_flows_uuid_map.csv"
    created_process_library = base_dir / "created_process_uuid_map.csv"

    flow_added, flow_updated, flow_skipped_existing = upsert_created_flows_library(
        created_flows_library,
        flow_rows,
    )
    process_added, process_updated, process_skipped_existing = upsert_created_process_library(
        created_process_library,
        process_rows,
    )

    return CreatedLibrariesUpdateStats(
        flow_added=flow_added,
        flow_updated=flow_updated,
        flow_skipped_existing=flow_skipped_existing,
        process_added=process_added,
        process_updated=process_updated,
        process_skipped_existing=process_skipped_existing,
    )
