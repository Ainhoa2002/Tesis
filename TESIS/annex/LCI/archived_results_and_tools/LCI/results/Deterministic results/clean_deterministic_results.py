"""Cleanup helper for deterministic result outputs.

By default this script preserves CSV files and deletes only derived artifacts
such as JSON, HTML, image, and spreadsheet exports. Use --include-csv to also
remove CSV files.
"""

from __future__ import annotations

import argparse
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parent


GENERATED_SUFFIXES = {
    ".json",
    ".png",
    ".html",
    ".xlsx",
}


def clean_deterministic_results(folder: Path | None = None, include_csv: bool = False) -> int:
    """Delete generated files from the deterministic results folder.

    Returns the number of files removed.
    """
    target_dir = Path(folder) if folder is not None else RESULTS_DIR
    removed = 0

    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        if path == Path(__file__).resolve():
            continue
        suffix = path.suffix.lower()
        if suffix == ".csv" and not include_csv:
            continue
        if suffix not in GENERATED_SUFFIXES and suffix != ".csv":
            continue
        path.unlink()
        removed += 1

    # Remove empty subdirectories after deleting files.
    for path in sorted((p for p in target_dir.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if path == target_dir:
            continue
        try:
            path.rmdir()
        except OSError:
            pass

    return removed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean deterministic result artifacts.")
    parser.add_argument(
        "--include-csv",
        action="store_true",
        help="Also delete CSV files (disabled by default).",
    )
    args = parser.parse_args()

    removed_count = clean_deterministic_results(include_csv=args.include_csv)
    mode = "including CSV" if args.include_csv else "preserving CSV"
    print(f"Removed {removed_count} generated file(s) from {RESULTS_DIR} ({mode})")
