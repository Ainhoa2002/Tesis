"""
Role: Static plotting utilities for impact results (charts and figures).

Brief: Contains helper functions to render static charts (matplotlib/plotly)
for impact and inventory results; used to create figures for reports or quick
visual inspections.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - plotting is optional at import time
    plt = None


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "Deterministic results"
if not RESULTS_DIR.exists():
    RESULTS_DIR = BASE_DIR

# Edit these values to control what gets plotted.
SYSTEM_NAMES = [
    "connector_system",
]
LCIA_METHOD = "EF v3.1"
IMPACTS_TO_PLOT = None  # e.g. ["Climate change", "Water use"] or None for all


# Purpose: Safe filename.
def safe_filename(value: object) -> str:
    text = str(value)
    for char in '<>:"/\\|?*':
        text = text.replace(char, "_")
    text = " ".join(text.split()).strip().rstrip(" .")
    return text or "unnamed"


# Purpose: Normalize key.
def normalize_key(value: object) -> str:
    return " ".join(str(value).strip().lower().split())


# Purpose: Load impacts.
def load_impacts(system_name: str, method_name: str) -> pd.DataFrame:
    impacts_path = RESULTS_DIR / f"{safe_filename(system_name)}_{safe_filename(method_name)}_impacts.csv"
    if not impacts_path.exists():
        raise FileNotFoundError(f"Missing impacts CSV: {impacts_path}")
    return pd.read_csv(impacts_path)


# Purpose: Filter impacts.
def filter_impacts(df: pd.DataFrame, impacts_to_plot: Iterable[str] | None) -> pd.DataFrame:
    if not impacts_to_plot:
        return df
    wanted = {normalize_key(name) for name in impacts_to_plot}
    mask = df["Impact category"].map(lambda value: normalize_key(value) in wanted)
    return df.loc[mask].copy()


# Purpose: Plot relative impacts.
def plot_relative_impacts(system_name: str, method_name: str, df: pd.DataFrame) -> Path | None:
    if plt is None or df.empty:
        return None

    values = pd.to_numeric(df["Amount (Raw)"], errors="coerce").fillna(0).abs()
    total = float(values.sum())
    if total <= 0:
        return None

    relative = values / total * 100.0
    plot_df = df.assign(_relative=relative).sort_values("_relative", ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(plot_df))))
    ax.barh(plot_df["Impact category"], plot_df["_relative"], color="#4C78A8")
    ax.set_xlabel("Relative share of raw impacts (%)")
    ax.set_title(f"Relative impacts — {system_name}")
    for idx, value in enumerate(plot_df["_relative"]):
        ax.text(value, idx, f" {value:.1f}%", va="center")
    fig.tight_layout()

    out_path = RESULTS_DIR / f"{safe_filename(system_name)}_{safe_filename(method_name)}_relative_impacts.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


# Purpose: Plot normalized impacts.
def plot_normalized_impacts(system_name: str, method_name: str, df: pd.DataFrame) -> Path | None:
    if plt is None or df.empty or "Amount (Normalized)" not in df.columns:
        return None

    values = pd.to_numeric(df["Amount (Normalized)"], errors="coerce")
    plot_df = df.assign(_normalized=values).dropna(subset=["_normalized"]).copy()
    if plot_df.empty:
        return None

    plot_df = plot_df.sort_values("_normalized", ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(plot_df))))
    ax.barh(plot_df["Impact category"], plot_df["_normalized"], color="#F58518")
    ax.set_xlabel("Normalized impact value")
    ax.set_title(f"Normalized impacts — {system_name}")
    for idx, value in enumerate(plot_df["_normalized"]):
        ax.text(value, idx, f" {value:.3g}", va="center")
    fig.tight_layout()

    out_path = RESULTS_DIR / f"{safe_filename(system_name)}_{safe_filename(method_name)}_normalized_impacts.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


# Purpose: Main.
def main() -> None:
    if plt is None:
        raise RuntimeError("matplotlib is not available in the current environment")

    for system_name in SYSTEM_NAMES:
        df = load_impacts(system_name, LCIA_METHOD)
        df = filter_impacts(df, IMPACTS_TO_PLOT)

        relative_path = plot_relative_impacts(system_name, LCIA_METHOD, df)
        normalized_path = plot_normalized_impacts(system_name, LCIA_METHOD, df)

        print(f"{system_name}: relative={relative_path if relative_path else 'skipped'}, normalized={normalized_path if normalized_path else 'skipped'}")


if __name__ == "__main__":
    main()
