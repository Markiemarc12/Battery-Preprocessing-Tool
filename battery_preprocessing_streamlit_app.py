import re
from io import BytesIO

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except ImportError:
    px = None


st.set_page_config(page_title="Battery Test Preprocessing Demo", layout="wide")

st.title("Substation Backup DC Battery Test Preprocessing Demo")
st.caption("Synthetic demo: upload the Excel workbook, validate records, flag bad readings, and summarize trends.")


DEFAULT_THRESHOLDS = {
    "cell_voltage_fail": 2.10,
    "cell_voltage_watch": 2.17,
    "resistance_watch": 0.75,
    "resistance_fail": 0.95,
    "sg_watch": 1.205,
    "sg_fail": 1.190,
    "ripple_watch": 75.0,
    "ripple_fail": 100.0,
}


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize spreadsheet column names into snake_case."""
    out = df.copy()
    out.columns = [
        re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", str(c).strip().lower())).strip("_")
        for c in out.columns
    ]
    return out


def required_columns(df: pd.DataFrame, required: set[str], sheet_name: str) -> list[str]:
    missing = sorted(required - set(df.columns))
    if missing:
        st.error(f"{sheet_name} is missing required columns: {', '.join(missing)}")
    return missing


def classify_cell(row: pd.Series, thresholds: dict) -> str:
    voltage = row.get("cell_voltage_v")
    resistance = row.get("internal_resistance_mohm")
    sg = row.get("specific_gravity")

    fail = (
        pd.notna(voltage) and voltage < thresholds["cell_voltage_fail"]
    ) or (
        pd.notna(resistance) and resistance > thresholds["resistance_fail"]
    ) or (
        pd.notna(sg) and sg != "" and float(sg) < thresholds["sg_fail"]
    )

    watch = (
        pd.notna(voltage) and voltage < thresholds["cell_voltage_watch"]
    ) or (
        pd.notna(resistance) and resistance > thresholds["resistance_watch"]
    ) or (
        pd.notna(sg) and sg != "" and float(sg) < thresholds["sg_watch"]
    )

    if fail:
        return "Fail"
    if watch:
        return "Watch"
    return "Pass"


def classify_test(row: pd.Series, thresholds: dict) -> str:
    ripple = row.get("ac_ripple_mv")
    ground = str(row.get("dc_ground_status", "")).strip().lower()
    if ground == "alarm" or (pd.notna(ripple) and ripple > thresholds["ripple_fail"]):
        return "Fail"
    if pd.notna(ripple) and ripple > thresholds["ripple_watch"]:
        return "Watch"
    return row.get("overall_status", "Unknown")


uploaded = st.file_uploader("Upload battery test Excel workbook", type=["xlsx"])

with st.sidebar:
    st.header("Screening thresholds")
    thresholds = {
        "cell_voltage_fail": st.number_input("Cell voltage fail below (V)", value=DEFAULT_THRESHOLDS["cell_voltage_fail"], step=0.01),
        "cell_voltage_watch": st.number_input("Cell voltage watch below (V)", value=DEFAULT_THRESHOLDS["cell_voltage_watch"], step=0.01),
        "resistance_watch": st.number_input("Resistance watch above (mΩ)", value=DEFAULT_THRESHOLDS["resistance_watch"], step=0.01),
        "resistance_fail": st.number_input("Resistance fail above (mΩ)", value=DEFAULT_THRESHOLDS["resistance_fail"], step=0.01),
        "sg_watch": st.number_input("Specific gravity watch below", value=DEFAULT_THRESHOLDS["sg_watch"], step=0.001),
        "sg_fail": st.number_input("Specific gravity fail below", value=DEFAULT_THRESHOLDS["sg_fail"], step=0.001),
        "ripple_watch": st.number_input("AC ripple watch above (mV)", value=DEFAULT_THRESHOLDS["ripple_watch"], step=1.0),
        "ripple_fail": st.number_input("AC ripple fail above (mV)", value=DEFAULT_THRESHOLDS["ripple_fail"], step=1.0),
    }


if uploaded is None:
    st.info("Upload the synthetic workbook named `synthetic_substation_dc_battery_tests.xlsx` to start.")
    st.stop()

xls = pd.ExcelFile(uploaded)
tests = clean_columns(pd.read_excel(xls, "Test_Results"))
cells = clean_columns(pd.read_excel(xls, "Cell_Readings"))
assets = clean_columns(pd.read_excel(xls, "Asset_Register"))

missing_tests = required_columns(
    tests,
    {"test_id", "test_date", "substation_id", "substation_name", "region", "dc_system", "ac_ripple_mv", "dc_ground_status", "overall_status"},
    "Test_Results",
)
missing_cells = required_columns(
    cells,
    {"test_id", "test_date", "substation_id", "cell_number", "cell_voltage_v", "internal_resistance_mohm"},
    "Cell_Readings",
)

if missing_tests or missing_cells:
    st.stop()

tests["test_date"] = pd.to_datetime(tests["test_date"], errors="coerce")
cells["test_date"] = pd.to_datetime(cells["test_date"], errors="coerce")
cells["computed_cell_status"] = cells.apply(classify_cell, axis=1, thresholds=thresholds)
tests["computed_test_status"] = tests.apply(classify_test, axis=1, thresholds=thresholds)

cell_summary = (
    cells.groupby(["test_id", "substation_id"], as_index=False)
    .agg(
        cells_tested=("cell_number", "count"),
        min_cell_voltage=("cell_voltage_v", "min"),
        max_cell_resistance=("internal_resistance_mohm", "max"),
        failed_cells=("computed_cell_status", lambda s: (s == "Fail").sum()),
        watch_cells=("computed_cell_status", lambda s: (s == "Watch").sum()),
    )
)

test_summary = tests.merge(cell_summary, on=["test_id", "substation_id"], how="left")
test_summary["preprocess_flag"] = "Pass"
test_summary.loc[(test_summary["computed_test_status"] == "Watch") | (test_summary["watch_cells"].fillna(0) > 0), "preprocess_flag"] = "Watch"
test_summary.loc[(test_summary["computed_test_status"] == "Fail") | (test_summary["failed_cells"].fillna(0) > 0), "preprocess_flag"] = "Fail"

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Tests loaded", len(tests))
kpi2.metric("Cell readings", len(cells))
kpi3.metric("Failed tests", int((test_summary["preprocess_flag"] == "Fail").sum()))
kpi4.metric("Watch tests", int((test_summary["preprocess_flag"] == "Watch").sum()))

left, right = st.columns([1, 1])

with left:
    st.subheader("Status by substation")
    by_sub = (
        test_summary.pivot_table(index="substation_name", columns="preprocess_flag", values="test_id", aggfunc="count", fill_value=0)
        .reset_index()
    )
    st.dataframe(by_sub, use_container_width=True, hide_index=True)
    if px is not None:
        melted = by_sub.melt(id_vars="substation_name", var_name="Status", value_name="Tests")
        st.plotly_chart(px.bar(melted, x="substation_name", y="Tests", color="Status", barmode="group"), use_container_width=True)

with right:
    st.subheader("Worst cell readings")
    worst_cells = cells.sort_values(["computed_cell_status", "cell_voltage_v"], ascending=[True, True])
    st.dataframe(
        worst_cells[["test_id", "substation_id", "cell_number", "cell_voltage_v", "internal_resistance_mohm", "specific_gravity", "computed_cell_status"]].head(25),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Preprocessed test summary")
st.dataframe(
    test_summary[
        [
            "test_id",
            "test_date",
            "substation_id",
            "substation_name",
            "region",
            "dc_system",
            "ac_ripple_mv",
            "dc_ground_status",
            "min_cell_voltage",
            "max_cell_resistance",
            "failed_cells",
            "watch_cells",
            "preprocess_flag",
        ]
    ].sort_values(["preprocess_flag", "test_date"], ascending=[True, False]),
    use_container_width=True,
    hide_index=True,
)

csv_bytes = test_summary.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download cleaned summary CSV",
    data=csv_bytes,
    file_name="cleaned_battery_test_summary.csv",
    mime="text/csv",
)

st.caption("This demo uses simplified screening thresholds. For production use, replace these with OEM limits, utility standards, and battery model-specific acceptance criteria.")