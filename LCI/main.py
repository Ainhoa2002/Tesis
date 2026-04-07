import argparse
from pathlib import Path
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
    """Run UUID enrichment for systems that ship a fill script and UUID library."""
    fill_script = system_folder / "fill_ipe_columns_from_library.py"
    uuid_library = system_folder / "component_library_ecoinvent_uuid_map.csv"
    provider_library = system_folder / "component_library_ecoinvent_uuid_provider_map.csv"

    if not fill_script.exists() or not uuid_library.exists():
        return

    cmd = [
        sys.executable,
        str(fill_script),
        "--library",
        str(uuid_library),
        "--root",
        str(system_folder),
    ]
    if provider_library.exists():
        cmd.extend(["--provider-library", str(provider_library)])

    if dry_run:
        print(f"  [DRY-RUN] Would run UUID fill: {' '.join(cmd)}")
        return

    print(f"  Running UUID fill in {system_folder.name}...")
    subprocess.run(cmd, check=True)
    print("  UUID fill completed.")


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
        # Real import mode writes processes into openLCA via IPC.
        client = ipc.Client(8080)   # or ipc.IpC(8080) if needed
        print("Connected to openLCA IPC server")
    
    ####PROCESS EACH FOLDER AND FILES:####
    total_files = 0
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
            process_csv(client, str(csv_file), category_name)

    if args.dry_run:
        print(f"\nDry run complete. Files detected: {total_files}")
    else:
        print("\nAll done! Please refresh openLCA to see the new processes.")

if __name__ == "__main__":
    main()