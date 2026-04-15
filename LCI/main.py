"""LCI import workflow orchestrator.

This script coordinates workflow phases only. Creation of openLCA entities lives
in process_builder.py, UUID/provider library operations live in library_sync.py,
and transport preprocessing lives in transport_workflow.py.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import olca_ipc as ipc

from library_sync import (
    run_created_uuid_fill_if_available,
    run_final_system_uuid_fill_if_available,
    run_final_transport_uuid_fill_if_available,
    run_uuid_fill_if_available,
    update_created_libraries,
)
from process_builder import ProcessImportReport, process_csv
from process_builder import create_product_systems_for_processes
from transport_workflow import prepare_transport_unit_processes

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class ImportWorkflowState:
    total_files: int = 0
    created_processes: int = 0
    updated_processes: int = 0
    created_flows: int = 0
    created_flow_rows: list[dict[str, str]] = field(default_factory=list)
    created_process_rows: list[dict[str, str]] = field(default_factory=list)
    systems_with_csv: list[Path] = field(default_factory=list)
    system_csv_map: dict[str, list[Path]] = field(default_factory=dict)
    reports: list[ProcessImportReport] = field(default_factory=list)


def _parse_product_system_names(value: str) -> list[str]:
    items = []
    for part in str(value or "").split(","):
        name = part.strip()
        if name:
            items.append(name)
    return items


def _resolve_product_system_targets(state: ImportWorkflowState, selection_mode: str, explicit_names: str) -> list[str]:
    mode = str(selection_mode or "none").strip().lower()
    if mode == "none":
        return []

    if mode == "names":
        return _parse_product_system_names(explicit_names)

    if mode == "imported":
        names = []
        seen = set()
        for report in state.reports:
            if report.skipped:
                continue
            key = report.process_name.strip().lower()
            if key == "" or key in seen:
                continue
            seen.add(key)
            names.append(report.process_name)
        return names

    return []


# Each first-level folder under LCI is treated as one system source.
def iter_system_folders(base_dir: Path):
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        yield child


# To create openLCA folder; eliminates the LCI_ of the name
def resolve_category_name(folder_name: str) -> str:
    # openLCA category drops the technical LCI_ prefix when present.
    if folder_name.startswith("LCI_") and len(folder_name) > 4:
        return folder_name[4:]
    return folder_name


# Search correct folders in the system folder, it gives back a list with the files.
def iter_system_csvs(system_folder: Path):
    # Support both layouts:
    # 1) <system>/LCI/*.csv
    # 2) <system>/*.csv
    lci_subfolder = system_folder / "LCI"
    search_dir = lci_subfolder if lci_subfolder.is_dir() else system_folder
    return sorted(search_dir.glob("*_ipe_flows_from_parameters.csv"))


def run_system_pipeline_if_available(system_folder: Path, dry_run: bool = False):
    """Regenerate generated CSVs for a system before importing them into openLCA."""
    pipeline_script = system_folder / "Pipeline.py"
    if not pipeline_script.exists():
        return

    cmd = [sys.executable, str(pipeline_script)]
    run_kwargs = {"check": True}

    if system_folder.name == "LCI_MEXICO_CONVERTER":
        # Select all subsystems and decline optional summary prompts.
        cmd.append("all")
        run_kwargs["input"] = "n\nn\n"
        run_kwargs["text"] = True
    elif system_folder.name == "LCI_MAGNET":
        # Keep the outer import flow in charge of UUID filling.
        cmd.append("--skip-fill")

    if dry_run:
        print(f"  [DRY-RUN] Would run pipeline: {' '.join(cmd)}")
        return

    print(f"  Running pipeline for {system_folder.name}...")
    subprocess.run(cmd, **run_kwargs)
    print(f"  Pipeline completed for {system_folder.name}.")


def ensure_ipc_server_available(host: str = "localhost", port: int = 8080, timeout_seconds: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _register_report(state: ImportWorkflowState, report: ProcessImportReport, collect_library_rows: bool) -> bool:
    """Store a file report and update counters; returns True if import was persisted."""
    state.reports.append(report)
    if report.skipped:
        return False

    if report.process_created:
        state.created_processes += 1
    else:
        state.updated_processes += 1

    if collect_library_rows:
        state.created_flows += len(report.created_output_flows)
        state.created_flow_rows.extend(report.output_flows_for_library)
        state.created_process_rows.extend(report.process_provider_rows)

    return True


def _phase_first_fill_and_import(
    *,
    base_dir: Path,
    systems: list[Path],
    state: ImportWorkflowState,
    client,
    dry_run: bool,
) -> None:
    """Phase 1: pipeline refresh + first UUID fill + first process import."""
    for system_folder in systems:
        category_name = resolve_category_name(system_folder.name)

        try:
            run_system_pipeline_if_available(system_folder, dry_run=dry_run)
        except Exception as exc:
            print(f"  [Warning] Pipeline refresh failed in {system_folder.name}: {exc}")

        csv_files = iter_system_csvs(system_folder)
        if not csv_files:
            print(f"Skipping {system_folder.name}: no *_ipe_flows_from_parameters.csv files found.")
            continue

        state.systems_with_csv.append(system_folder)
        state.system_csv_map[str(system_folder)] = list(csv_files)

        print(f"\nSystem: {system_folder.name} -> openLCA category: {category_name}")
        try:
            run_uuid_fill_if_available(base_dir, system_folder, dry_run=dry_run)
        except Exception as exc:
            print(f"  [Warning] UUID fill failed in {system_folder.name}: {exc}")

        for csv_file in csv_files:
            state.total_files += 1
            if dry_run:
                print(f"  [DRY-RUN] {csv_file.name}")
                continue

            report = process_csv(client, str(csv_file), category_name)
            _register_report(state, report, collect_library_rows=True)


def _phase_second_fill_and_reimport(base_dir: Path, client, state: ImportWorkflowState) -> int:
    """Phase 2: second UUID fill from created libraries and full re-import."""
    for system_folder in state.systems_with_csv:
        try:
            run_created_uuid_fill_if_available(base_dir, system_folder, dry_run=False)
        except Exception as exc:
            print(f"  [Warning] Second UUID fill failed in {system_folder.name}: {exc}")

    second_round_reimports = 0
    for system_folder in state.systems_with_csv:
        category_name = resolve_category_name(system_folder.name)
        for csv_file in state.system_csv_map.get(str(system_folder), []):
            report = process_csv(client, str(csv_file), category_name)
            imported = _register_report(state, report, collect_library_rows=False)
            if imported:
                second_round_reimports += 1

    return second_round_reimports


def _phase_third_fill_and_aggregate_reimport(base_dir: Path, client, state: ImportWorkflowState) -> None:
    """Phase 3: third targeted fill and aggregate re-import for system/transport."""
    system_folder = base_dir / "LCI_SYSTEM"
    try:
        run_final_system_uuid_fill_if_available(base_dir, system_folder, dry_run=False)
    except Exception as exc:
        print(f"  [Warning] Third UUID fill failed for {system_folder.name}: {exc}")

    transport_folder = base_dir / "LCI_TRANSPORT"
    transport_third_fill_ok = False
    try:
        transport_third_fill_ok = run_final_transport_uuid_fill_if_available(base_dir, transport_folder, dry_run=False)
    except Exception as exc:
        print(f"  [Warning] Third UUID fill failed for {transport_folder.name}: {exc}")

    system_target_file = system_folder / "system_ipe_flows_from_parameters.csv"
    if system_target_file.exists():
        try:
            report = process_csv(client, str(system_target_file), resolve_category_name(system_folder.name))
            _register_report(state, report, collect_library_rows=False)
            print("  Third-round system file re-imported into openLCA.")
        except Exception as exc:
            print(f"  [Warning] Could not re-import third-round system file: {exc}")

    if transport_third_fill_ok:
        transport_target_file = transport_folder / "transport_ipe_flows_from_parameters.csv"
        if transport_target_file.exists():
            try:
                report = process_csv(client, str(transport_target_file), resolve_category_name(transport_folder.name))
                _register_report(state, report, collect_library_rows=False)
                print("  Third-round transport file re-imported into openLCA.")
            except Exception as exc:
                print(f"  [Warning] Could not re-import third-round transport file: {exc}")


def _print_report_summary(reports: list[ProcessImportReport]) -> None:
    """Print centralized warning/error totals per imported CSV report."""
    warnings_total = sum(len(r.warnings) for r in reports)
    errors_total = sum(len(r.errors) for r in reports)
    files_with_errors = [r for r in reports if r.errors]

    print(
        "Import report summary. "
        f"Files reported: {len(reports)}. "
        f"Warnings: {warnings_total}. Errors: {errors_total}."
    )

    if files_with_errors:
        print("Files with errors:")
        for report in files_with_errors:
            print(f"  - {Path(report.csv_path).name}: {len(report.errors)} error(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Import all system CSVs under LCI and store processes in matching openLCA categories."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be imported and target categories, without connecting to openLCA.",
    )
    parser.add_argument(
        "--product-systems",
        choices=["none", "imported", "names"],
        default="none",
        help=(
            "Create or update product systems after process import: "
            "none (default), imported (all imported process names), names (comma list in --product-system-names)."
        ),
    )
    parser.add_argument(
        "--product-system-names",
        default="",
        help="Comma-separated process names to use with --product-systems names.",
    )
    args = parser.parse_args()

    state = ImportWorkflowState()

    # Phase 0: transport preprocessing before import.
    try:
        prepare_transport_unit_processes(BASE_DIR, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[Warning] Transport unit-process preparation failed: {exc}")

    systems = list(iter_system_folders(BASE_DIR))
    if not systems:
        print(f"No system folders found in {BASE_DIR}")
        return

    client = None
    if not args.dry_run:
        if not ensure_ipc_server_available(host="localhost", port=8080):
            print(
                "openLCA IPC server is not reachable on localhost:8080. "
                "Start openLCA and enable the IPC server, or run with --dry-run."
            )
            return

        client = ipc.Client(8080)
        print("Connected to openLCA IPC server")

    # Phase 1: first fill + first import
    _phase_first_fill_and_import(
        base_dir=BASE_DIR,
        systems=systems,
        state=state,
        client=client,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"\nDry run complete. Files detected: {state.total_files}")
        return

    # Phase 2: created-library upsert from first import results.
    lib_stats = update_created_libraries(
        BASE_DIR,
        flow_rows=state.created_flow_rows,
        process_rows=state.created_process_rows,
    )

    print(
        f"\nStep 2 complete. Processes created: {state.created_processes}. "
        f"Processes updated: {state.updated_processes}. "
        f"Output flows created: {state.created_flows}."
    )
    print(
        "Created libraries updated. "
        f"Flows added/updated/skipped_existing: "
        f"{lib_stats.flow_added}/{lib_stats.flow_updated}/{lib_stats.flow_skipped_existing}. "
        f"Process providers added/updated/skipped_existing: "
        f"{lib_stats.process_added}/{lib_stats.process_updated}/{lib_stats.process_skipped_existing}."
    )

    # Phase 3: second fill + reimport
    second_round_reimports = _phase_second_fill_and_reimport(BASE_DIR, client, state)
    print(
        "Second-round provider updates applied to openLCA. "
        f"Processes re-imported: {second_round_reimports}."
    )

    # Phase 4: third fill + aggregate reimport
    _phase_third_fill_and_aggregate_reimport(BASE_DIR, client, state)

    # Phase 5: optional product system creation/update from selected processes.
    ps_targets = _resolve_product_system_targets(
        state,
        selection_mode=args.product_systems,
        explicit_names=args.product_system_names,
    )
    if ps_targets:
        print("Product system phase started...")
        ps_reports = create_product_systems_for_processes(client, ps_targets)
        ps_created = sum(1 for r in ps_reports if r.created)
        ps_updated = sum(1 for r in ps_reports if r.updated)
        ps_skipped = sum(1 for r in ps_reports if r.skipped)
        ps_errors = sum(len(r.errors) for r in ps_reports)
        print(
            "Product system phase complete. "
            f"Created: {ps_created}. Updated: {ps_updated}. "
            f"Skipped: {ps_skipped}. Errors: {ps_errors}."
        )
    elif args.product_systems != "none":
        print("Product system phase skipped: no valid process names were selected.")

    _print_report_summary(state.reports)
    print("\nAll done! Please refresh openLCA to see the new processes.")


if __name__ == "__main__":
    main()
