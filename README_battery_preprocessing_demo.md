# Battery Test Preprocessing Demo

This package contains synthetic Excel data and a starter Streamlit app for preprocessing substation backup DC battery test results.

## Files

- `synthetic_substation_dc_battery_tests.xlsx` — fake but realistic demo workbook.
- `battery_preprocessing_streamlit_app.py` — Streamlit dashboard and preprocessing script.
- `requirements.txt` — packages needed for the demo.

## Run

```bash
pip install -r requirements.txt
streamlit run battery_preprocessing_streamlit_app.py
```

Then upload the Excel workbook inside the Streamlit app.

## Demo workflow

1. Read Excel sheets with pandas.
2. Normalize column names.
3. Validate required fields.
4. Classify cell readings using demo thresholds.
5. Combine string-level and cell-level results.
6. Show KPIs, issue tables, and charts.
7. Export a cleaned summary CSV.

## Production upgrade ideas

- Replace demo thresholds with manufacturer-specific limits.
- Add parser templates for messy field spreadsheets.
- Add trend analysis by substation, battery string, and cell number.
- Add anomaly detection for cells drifting from their historical baseline.
- Store cleaned results in SQLite, SharePoint, or a maintenance database.