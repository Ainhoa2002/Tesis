"""
Role: Command-line interface for library synchronization operations.

Brief: Provides a CLI wrapper to run `library_sync` actions such as updating
component UUID mappings and syncing with the parameter library.
"""

import argparse
from pathlib import Path

from library_sync import run_fill_ipe_columns_from_library


# Purpose: Main.
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

    target_file = Path(args.target_file).resolve() if args.target_file else None
    root_dir = None if target_file is not None else Path(args.root).resolve()

    try:
        run_fill_ipe_columns_from_library(
            library_path=Path(args.library).resolve(),
            provider_library_path=Path(args.provider_library).resolve(),
            root_dir=root_dir,
            target_file=target_file,
            overwrite_uuid=args.overwrite_uuid,
            overwrite_provider=args.overwrite_provider,
            sync_provider_library=not args.no_sync_provider_library,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        logging.exception("Error running library sync CLI: %s", exc)


if __name__ == "__main__":
    main()
