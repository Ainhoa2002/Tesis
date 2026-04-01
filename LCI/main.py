import argparse
from pathlib import Path
import olca_ipc as ipc
from process_builder import process_csv

BASE_DIR = Path(__file__).resolve().parent


def iter_system_folders(base_dir: Path):
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        yield child


def resolve_category_name(folder_name: str) -> str:
    if folder_name.startswith("LCI_") and len(folder_name) > 4:
        return folder_name[4:]
    return folder_name


def iter_system_csvs(system_folder: Path):
    lci_subfolder = system_folder / "LCI"
    if lci_subfolder.is_dir():
        search_dir = lci_subfolder
    else:
        search_dir = system_folder
    return sorted(search_dir.glob("*_ipe_flows_from_parameters.csv"))


def main():
    parser = argparse.ArgumentParser(
        description="Import all system CSVs under LCI and store processes in matching openLCA categories."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be imported and target categories, without connecting to openLCA.",
    )
    args = parser.parse_args()

    systems = list(iter_system_folders(BASE_DIR))
    if not systems:
        print(f"No system folders found in {BASE_DIR}")
        return

    client = None
    if not args.dry_run:
        client = ipc.Client(8080)   # or ipc.IpC(8080) if needed
        print("Connected to openLCA IPC server")

    total_files = 0
    for system_folder in systems:
        category_name = resolve_category_name(system_folder.name)
        csv_files = iter_system_csvs(system_folder)
        if not csv_files:
            print(f"Skipping {system_folder.name}: no *_ipe_flows_from_parameters.csv files found.")
            continue

        print(f"\nSystem: {system_folder.name} -> openLCA category: {category_name}")
        for csv_file in csv_files:
            total_files += 1
            if args.dry_run:
                print(f"  [DRY-RUN] {csv_file.name}")
                continue
            process_csv(client, str(csv_file), category_name)

    if args.dry_run:
        print(f"\nDry run complete. Files detected: {total_files}")
    else:
        print("\nAll done! Please refresh openLCA to see the new processes.")

if __name__ == "__main__":
    main()