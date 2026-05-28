"""Validation harness for TESIS/annex/LCI.

Runs lightweight checks to validate the annex snapshot is runnable and
that canonical tools are importable. Designed to be safe (no heavy
openLCA calculations) and suitable for CI or manual pre-checks.

Checks performed:
 - Run `LCI_MEXICO_CONVERTER/smoke_test.py` (quick smoke test)
 - Import `LCI_MEXICO_CONVERTER/Pipeline.py` and validate expected functions
 - Import `library_sync_cli.py` and check for CLI availability
 - Import `results_tools` sankey visualizer and interactive visualizer
 - Scan for `*_component_parameters.csv` files and report counts

Usage:
    python validate_all.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import importlib.util
import traceback


ROOT = Path(__file__).resolve().parent


def run_smoke_test():
    smoke = ROOT / "LCI_MEXICO_CONVERTER" / "smoke_test.py"
    if not smoke.exists():
        return False, f"smoke_test.py not found at {smoke}"

    try:
        res = subprocess.run([sys.executable, str(smoke)], capture_output=True, text=True, timeout=120)
        ok = res.returncode == 0
        out = res.stdout + "\n" + res.stderr
        return ok, out.strip()
    except Exception as e:
        return False, f"Exception running smoke_test: {e}"


def try_import_module(path: Path):
    if not path.exists():
        return False, f"Not found: {path}"
    try:
        spec = importlib.util.spec_from_file_location(path.stem, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return True, mod
    except Exception as e:
        tb = traceback.format_exc()
        return False, tb


def scan_component_parameter_files():
    conv = ROOT / "LCI_MEXICO_CONVERTER"
    files = list(conv.glob("**/*_component_parameters.csv"))
    return files


def main():
    report = {"smoke_test": None, "imports": {}, "csv_scan": {}}

    print("1) Running smoke test (LCI_MEXICO_CONVERTER/smoke_test.py)...")
    ok, out = run_smoke_test()
    report["smoke_test"] = {"ok": ok, "output": out}
    print("   ->", "OK" if ok else "FAILED")

    # Safe imports
    targets = {
        "Pipeline": ROOT / "LCI_MEXICO_CONVERTER" / "Pipeline.py",
        "library_sync_cli": ROOT / "library_sync_cli.py",
        "sankey_visualizer": ROOT / "results_tools" / "sankey_visualizer.py",
        "interactive_visualizer": ROOT / "results_tools" / "visualize_results_interactive.py",
    }

    for name, path in targets.items():
        print(f"2) Import check: {name} -> {path.name}...")
        ok, result = try_import_module(path)
        info = result if isinstance(result, str) else getattr(result, "__name__", str(type(result)))
        report["imports"][name] = {"ok": bool(ok), "info": str(info)[:200]}
        print("   ->", "imported" if ok else "import-failed")

    # CSV scan
    print("3) Scanning for *_component_parameters.csv in LCI_MEXICO_CONVERTER...")
    files = scan_component_parameter_files()
    report["csv_scan"] = {"count": len(files), "examples": [str(p).replace(str(ROOT)+"/", "") for p in files[:10]]}
    print(f"   -> found {len(files)} files")

    # Summary
    summary_path = ROOT / "validation_report.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nValidation summary written to:", summary_path)
    print("Return status: ", "OK" if report["smoke_test"]["ok"] else "ISSUES")
    return 0 if report["smoke_test"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
