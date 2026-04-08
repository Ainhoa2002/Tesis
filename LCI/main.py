import argparse
import csv
from pathlib import Path
import socket
import subprocess
import sys
import olca_ipc as ipc
from process_builder import process_csv

BASE_DIR = Path(__file__).resolve().parent

# Each first-level folder under LCI is treated as one system source.
def iter_system_folders(base_dir: Path):
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        yield child

#To create openLCA foler; eliminates the LCI_ of the name
def resolve_category_name(folder_name: str) -> str:
    # openLCA category drops the technical LCI_ prefix when present.
    if folder_name.startswith("LCI_") and len(folder_name) > 4:
        return folder_name[4:]
    return folder_name

#Search correct folders in the system folder, it gives back a list with the fields.
def iter_system_csvs(system_folder: Path):
    # Support both layouts:
    # 1) <system>/LCI/*.csv
    # 2) <system>/*.csv
    lci_subfolder = system_folder / "LCI"
    if lci_subfolder.is_dir():
        search_dir = lci_subfolder
    else:
        search_dir = system_folder
    return sorted(search_dir.glob("*_ipe_flows_from_parameters.csv"))


def run_uuid_fill_if_available(system_folder: Path, dry_run: bool = False):
    """Run UUID enrichment using global libraries for one system folder."""
    fill_script = BASE_DIR / "fill_ipe_columns_from_library.py"
    uuid_library = BASE_DIR / "component_library_ecoinvent_uuid_map.csv"
    provider_library = BASE_DIR / "component_library_ecoinvent_uuid_provider_map.csv"

    if not fill_script.exists():
        print(f"  [Warning] UUID fill script not found: {fill_script}")
        return
    if not uuid_library.exists() or not provider_library.exists():
        print(
            "  [Warning] Global UUID libraries not found. "
            "Expected both component_library_ecoinvent_uuid_map.csv and "
            "component_library_ecoinvent_uuid_provider_map.csv in LCI/."
        )
        return

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

    if dry_run:
        cmd.append("--dry-run")
        print(f"  [DRY-RUN] Would run UUID fill: {' '.join(cmd)}")
        return

    print(f"  Running UUID fill in {system_folder.name}...")
    subprocess.run(cmd, check=True)
    print("  UUID fill completed.")


def ensure_ipc_server_available(host: str = "localhost", port: int = 8080, timeout_seconds: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _normalize_key(value: str) -> str:
    return "".join(str(value or "").lower().split())


def _upsert_created_flows_library(path: Path, rows):
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
    for row in rows:
        flow = str(row.get("Flow", "") or "").strip()
        uid = str(row.get("UUID", "") or "").strip()
        if not flow or not uid:
            continue
        key = _normalize_key(flow)
        mapped = {"Ecoinvent_flow": flow, "UUID": uid}
        if key in index:
            if existing_rows[index[key]].get("UUID", "") != uid:
                existing_rows[index[key]] = mapped
                updated += 1
        else:
            existing_rows.append(mapped)
            index[key] = len(existing_rows) - 1
            added += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)

    return added, updated


def _upsert_created_process_library(path: Path, rows):
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
            old = existing_rows[index[key]]
            if old.get("UUID_provider", "") != proc_uuid or old.get("Ecoinvent_process", "") != proc_name:
                existing_rows[index[key]] = mapped
                updated += 1
        else:
            existing_rows.append(mapped)
            index[key] = len(existing_rows) - 1
            added += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)

    return added, updated


def main():
    parser = argparse.ArgumentParser(
        description="Import all system CSVs under LCI and store processes in matching openLCA categories."
    )
    # Si se usa el script asi: python main.py --dry-run, no se crean los archivos en openLCA
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be imported and target categories, without connecting to openLCA.",
    )
    args = parser.parse_args()
    #Find the folders
    systems = list(iter_system_folders(BASE_DIR))
    if not systems:
        print(f"No system folders found in {BASE_DIR}")
        return
    #Connect to IPC
    client = None
    if not args.dry_run:
        if not ensure_ipc_server_available(host="localhost", port=8080):
            print(
                "openLCA IPC server is not reachable on localhost:8080. "
                "Start openLCA and enable the IPC server, or run with --dry-run."
            )
            return

        # Real import mode writes processes into openLCA via IPC.
        client = ipc.Client(8080)
        print("Connected to openLCA IPC server")
    
    ####PROCESS EACH FOLDER AND FILES:####
    total_files = 0
    created_processes = 0
    updated_processes = 0
    created_flows = 0
    created_flow_rows = []
    created_process_rows = []
    for system_folder in systems:
        # Folder name determines the destination process category in openLCA.
        category_name = resolve_category_name(system_folder.name)
        #Search correct folders in the system folder, it gives back a list with the fields.
        csv_files = iter_system_csvs(system_folder)
        if not csv_files:
            print(f"Skipping {system_folder.name}: no *_ipe_flows_from_parameters.csv files found.")
            continue
        print(f"\nSystem: {system_folder.name} -> openLCA category: {category_name}")
        try:
            run_uuid_fill_if_available(system_folder, dry_run=args.dry_run)
        except Exception as exc:
            print(f"  [Warning] UUID fill failed in {system_folder.name}: {exc}")
        #Acumulates the number of files
        for csv_file in csv_files:
            total_files += 1
            if args.dry_run:
                # Dry-run prints planned actions without touching openLCA.
                print(f"  [DRY-RUN] {csv_file.name}")
                continue
            result = process_csv(client, str(csv_file), category_name)
            if not result:
                continue
            if result.get("process_created"):
                created_processes += 1
            else:
                updated_processes += 1
            created_flows += len(result.get("created_output_flows", []))
            created_flow_rows.extend(result.get("created_output_flows", []))

            process_uuid = str(result.get("process_uuid", "") or "").strip()
            process_name = str(result.get("process_name", "") or "").strip()
            for flow_ref in result.get("output_flow_references", []):
                created_process_rows.append(
                    {
                        "Ecoinvent_flow_reference": flow_ref,
                        "Ecoinvent_process": process_name,
                        "UUID_provider": process_uuid,
                    }
                )

    if args.dry_run:
        print(f"\nDry run complete. Files detected: {total_files}")
    else:
        created_flows_library = BASE_DIR / "created_flows_uuid_map.csv"
        created_process_library = BASE_DIR / "created_process_uuid_map.csv"
        flow_added, flow_updated = _upsert_created_flows_library(created_flows_library, created_flow_rows)
        process_added, process_updated = _upsert_created_process_library(created_process_library, created_process_rows)

        print(
            f"\nStep 2 complete. Processes created: {created_processes}. "
            f"Processes updated: {updated_processes}. "
            f"Output flows created: {created_flows}."
        )
        print(
            f"Created libraries updated. "
            f"Flows added/updated: {flow_added}/{flow_updated}. "
            f"Process providers added/updated: {process_added}/{process_updated}."
        )
        print("\nAll done! Please refresh openLCA to see the new processes.")

if __name__ == "__main__":
    main()