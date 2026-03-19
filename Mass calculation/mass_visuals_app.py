"""
Working with Streamlit to visualize mass results across subsystems and components. "
This app:
1.reads all *_component_mass_results.csv files
2.allows filtering by subsystem and component
3.provides various visualizations like bar charts and treemaps"
Streamlit is a library for building interactive web apps in Python,
Used for data visualization and exploration.


HOW TO USE IT:
- In the termianal: .\Mass calculation\mass_visuals_app.py
                - Make sure you have Streamlit installed: .\\.venv\\Scripts\\python.exe -m pip install streamlit plotly pandas numpy
- The app will open in your web browser, showing mass results from all subsystems.
- In the web parameters can be changed for visualization
    - You can change parameters in the web app to update visualizations.
    - You can edit the code while the app is running; save changes to auto-reload.
- Press Ctrl + C in the terminal to stop the app.

"""""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
RESULT_SUFFIX = "_component_mass_results.csv"


def _to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


@st.cache_data(show_spinner=False)
def load_all_results(base_dir: Path) -> pd.DataFrame:
    files = sorted(base_dir.glob(f"*{RESULT_SUFFIX}"))
    frames = []

    for p in files:
        subsystem = p.name[: -len(RESULT_SUFFIX)]
        df = pd.read_csv(p, engine="python", on_bad_lines="skip")
        df.columns = [str(c).strip() for c in df.columns]
        df["Subsystem"] = subsystem
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    for c in ["Section", "Subsection", "Category", "Part_Number", "Designators", "Ecoinvent_unit"]:
        if c not in df.columns:
            df[c] = "Unknown"
        df[c] = df[c].astype(str).str.strip().replace({"": "Unknown", "nan": "Unknown", "None": "Unknown"})

    if "Total_quantity" not in df.columns:
        df["Total_quantity"] = np.nan
    df["Total_quantity"] = _to_num(df["Total_quantity"])

    # Mass rows only (kg)
    unit = df["Ecoinvent_unit"].str.lower()
    df["is_mass_row"] = unit.eq("kg")
    df["mass_kg"] = np.where(df["is_mass_row"], df["Total_quantity"], np.nan)

    # Label for components
    df["Component"] = df["Part_Number"]
    df.loc[df["Component"].isin(["Unknown", "", "nan"]), "Component"] = df["Designators"]

    return df


def main() -> None:
    st.set_page_config(page_title="Mass visuals", layout="wide")
    st.title("Mass visuals (all subsystems, all components)")

    df = load_all_results(BASE_DIR)
    if df.empty:
        st.error(f"No files found: *{RESULT_SUFFIX} in {BASE_DIR}")
        st.stop()

    st.sidebar.header("Filters")
    subsystem_list = sorted(df["Subsystem"].unique().tolist())
    selected_subsystems = st.sidebar.multiselect("Subsystems", subsystem_list, default=subsystem_list)

    view = df[df["Subsystem"].isin(selected_subsystems)].copy()

    only_mass = st.sidebar.checkbox("Use only mass rows (Ecoinvent_unit = kg)", value=True)
    if only_mass:
        view = view[view["is_mass_row"]].copy()

    comp_list = sorted(view["Component"].dropna().unique().tolist())
    selected_components = st.sidebar.multiselect("Components", comp_list, default=comp_list)
    if selected_components:
        view = view[view["Component"].isin(selected_components)].copy()

    k1, k2, k3 = st.columns(3)
    k1.metric("Rows", f"{len(view):,}")
    k2.metric("Subsystems", f"{view['Subsystem'].nunique():,}")
    k3.metric("Total mass (kg)", f"{view['mass_kg'].sum(skipna=True):.6f}")

    # 1) Horizontal bar (top components)
    st.subheader("1) Top components by mass")
    top_n = st.slider("Top N", 5, 100, 25, 5)
    b1 = (
        view.groupby("Component", as_index=False)["mass_kg"]
        .sum()
        .sort_values("mass_kg", ascending=False)
        .head(top_n)
        .sort_values("mass_kg", ascending=True)
    )
    fig1 = px.bar(b1, x="mass_kg", y="Component", orientation="h", labels={"mass_kg": "Mass (kg)"})
    st.plotly_chart(fig1, width="stretch")

    # 2) Treemap
    st.subheader("2) Treemap")
    fig2 = px.treemap(
        view,
        path=["Subsystem", "Section", "Subsection", "Component"],  # <- Category eliminada
        values="mass_kg",
    )
    st.plotly_chart(fig2, width="stretch")

    # 3) One bar per subsystem, subdivided
    st.subheader("3) Subsystem bars (stacked)")
    split_mode = st.radio(
        "Subdivision",
        ["Option 1: Components", "Option 2: Sections"],
        horizontal=True,
    )
    split_col = "Component" if split_mode.startswith("Option 1") else "Section"

    b3 = view.groupby(["Subsystem", split_col], as_index=False)["mass_kg"].sum()
    order = (
        view.groupby("Subsystem", as_index=False)["mass_kg"]
        .sum()
        .sort_values("mass_kg", ascending=False)["Subsystem"]
        .tolist()
    )

    fig3 = px.bar(
        b3,
        x="Subsystem",
        y="mass_kg",
        color=split_col,
        barmode="stack",
        category_orders={"Subsystem": order},
        labels={"mass_kg": "Mass (kg)"},
    )
    st.plotly_chart(fig3, width="stretch")

    st.subheader("Data preview")
    cols = [
        c for c in [
            "Subsystem",
            "Designators",
            "Section",
            "Subsection",
            "Part_Number",
            "Ecoinvent_unit",
            "Total_quantity",
            "mass_kg",
        ]
        if c in view.columns
    ]
    st.dataframe(view[cols].sort_values(["Subsystem", "mass_kg"], ascending=[True, False]), width="stretch")


if __name__ == "__main__":
    main()