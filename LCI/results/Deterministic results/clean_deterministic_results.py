"""Cleanup helper for deterministic result outputs.

This script removes generated result artifacts from the deterministic results
folder while keeping the cleanup script itself in place.
"""

from __future__ import annotations

from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parent


GENERATED_SUFFIXES = {
    ".csv",
    ".json",
    ".png",
    ".html",
    ".xlsx",
}


def clean_deterministic_results(folder: Path | None = None) -> int:
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
        if path.suffix.lower() not in GENERATED_SUFFIXES:
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
    removed_count = clean_deterministic_results()
    print(f"Removed {removed_count} generated file(s) from {RESULTS_DIR}")
