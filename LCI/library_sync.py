"""Library synchronization helpers for UUID and provider mappings.

This module centralizes everything related to UUID and UUID_provider filling,
plus created-object library upserts. It intentionally contains no openLCA
object creation logic.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


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


def _run_fill_command(cmd: list[str], dry_run: bool, dry_run_label: str, run_label: str) -> bool:
    if dry_run:
        dry_cmd = list(cmd)
        dry_cmd.append("--dry-run")
        print(f"  [DRY-RUN] Would run {dry_run_label}: {' '.join(dry_cmd)}")
        return True

    print(f"  Running {run_label}...")
    subprocess.run(cmd, check=True)
    print(f"  {run_label.capitalize()} completed.")
    return True


def run_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run first UUID enrichment pass using global libraries."""
    fill_script = base_dir / "fill_ipe_columns_from_library.py"
    uuid_library = base_dir / "component_library_ecoinvent_uuid_map.csv"
    provider_library = base_dir / "component_library_ecoinvent_uuid_provider_map.csv"

    if not fill_script.exists():
        print(f"  [Warning] UUID fill script not found: {fill_script}")
        return False
    if not uuid_library.exists() or not provider_library.exists():
        print(
            "  [Warning] Global UUID libraries not found. "
            "Expected both component_library_ecoinvent_uuid_map.csv and "
            "component_library_ecoinvent_uuid_provider_map.csv in LCI/."
        )
        return False

    cmd = [
        sys.executable,
        str(fill_script),
        "--library",
        str(uuid_library),
        "--provider-library",
        str(provider_library),
        "--root",
        str(system_folder),
    ]
    return _run_fill_command(
        cmd,
        dry_run=dry_run,
        dry_run_label="UUID fill",
        run_label=f"UUID fill in {system_folder.name}",
    )


def run_created_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run second UUID enrichment pass using created-object libraries."""
    fill_script = base_dir / "fill_ipe_columns_from_library.py"
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"

    if not fill_script.exists():
        print(f"  [Warning] UUID fill script not found: {fill_script}")
        return False
    if not uuid_library.exists() or not provider_library.exists():
        print(
            "  [Warning] Created UUID libraries not found. "
            "Expected both created_flows_uuid_map.csv and "
            "created_process_uuid_map.csv in LCI/."
        )
        return False

    cmd = [
        sys.executable,
        str(fill_script),
        "--library",
        str(uuid_library),
        "--provider-library",
        str(provider_library),
        "--root",
        str(system_folder),
        "--overwrite-uuid",
        "--no-sync-provider-library",
        "--overwrite-provider",
    ]
    return _run_fill_command(
        cmd,
        dry_run=dry_run,
        dry_run_label="created UUID fill",
        run_label=f"second UUID fill in {system_folder.name}",
    )


def run_final_system_uuid_fill_if_available(base_dir: Path, system_folder: Path, dry_run: bool = False) -> bool:
    """Run third UUID fill pass focused on LCI_SYSTEM aggregate file."""
    fill_script = base_dir / "fill_ipe_columns_from_library.py"
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"
    target_file = system_folder / "system_ipe_flows_from_parameters.csv"

    if not fill_script.exists():
        print(f"  [Warning] UUID fill script not found: {fill_script}")
        return False
    if not target_file.exists():
        print(f"  [Warning] System target file not found: {target_file}")
        return False
    if not uuid_library.exists() or not provider_library.exists():
        print(
            "  [Warning] Created UUID libraries not found for system final fill. "
            "Expected both created_flows_uuid_map.csv and created_process_uuid_map.csv in LCI/."
        )
        return False

    cmd = [
        sys.executable,
        str(fill_script),
        "--library",
        str(uuid_library),
        "--provider-library",
        str(provider_library),
        "--target-file",
        str(target_file),
        "--overwrite-uuid",
        "--overwrite-provider",
        "--no-sync-provider-library",
    ]
    return _run_fill_command(
        cmd,
        dry_run=dry_run,
        dry_run_label="final system fill",
        run_label=f"third UUID fill for system file in {system_folder.name}",
    )


def run_final_transport_uuid_fill_if_available(base_dir: Path, transport_folder: Path, dry_run: bool = False) -> bool:
    """Run third UUID fill pass focused on LCI_TRANSPORT aggregate file."""
    fill_script = base_dir / "fill_ipe_columns_from_library.py"
    uuid_library = base_dir / "created_flows_uuid_map.csv"
    provider_library = base_dir / "created_process_uuid_map.csv"
    target_file = transport_folder / "transport_ipe_flows_from_parameters.csv"

    if not fill_script.exists():
        print(f"  [Warning] UUID fill script not found: {fill_script}")
        return False
    if not target_file.exists():
        print(f"  [Warning] Transport target file not found: {target_file}")
        return False
    if not uuid_library.exists() or not provider_library.exists():
        print(
            "  [Warning] Created UUID libraries not found for transport final fill. "
            "Expected both created_flows_uuid_map.csv and created_process_uuid_map.csv in LCI/."
        )
        return False

    cmd = [
        sys.executable,
        str(fill_script),
        "--library",
        str(uuid_library),
        "--provider-library",
        str(provider_library),
        "--target-file",
        str(target_file),
        "--overwrite-uuid",
        "--overwrite-provider",
        "--no-sync-provider-library",
    ]
    return _run_fill_command(
        cmd,
        dry_run=dry_run,
        dry_run_label="final transport fill",
        run_label=f"third UUID fill for transport file in {transport_folder.name}",
    )


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
