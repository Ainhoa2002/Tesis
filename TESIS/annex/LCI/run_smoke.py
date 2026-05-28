"""
Role: Smoke test runner for quick validation of annex workflows.

Brief: Provides a lightweight smoke harness to run a minimal subset of the
pipeline and validate that scripts execute end-to-end in the annex environment.
"""

"""Run basic smoke checks for the LCI annex.

This script runs the main pipeline in dry-run mode and the Mexico converter smoke test.
"""
import subprocess
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Purpose: Run.
def run(cmd):
    logging.info("Running: %s", cmd)
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        logging.error("Command failed: %s (exit %s)", cmd, proc.returncode)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    python = sys.executable
    run(f"{python} -u {ROOT / 'main.py'} --dry-run")
    run(f"{python} -u {ROOT / 'LCI_MEXICO_CONVERTER' / 'smoke_test.py'}")
    logging.info("Smoke harness finished successfully.")
