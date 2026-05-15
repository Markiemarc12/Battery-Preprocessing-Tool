# Battery Test Preprocessing Demo

This package contains synthetic Excel data and a starter Streamlit app for preprocessing substation backup DC battery test results.

## Engineering Concepts Demonstrated

- Deterministic engineering validation pipelines
- Threshold-based fault classification
- Voltage imbalance detection
- Review-state aggregation
- Engineering workflow automation
- Human-readable maintenance summaries
- Optional AI-assisted review generation

## Deterministic Validation Philosophy

- All pass/fail classifications are generated using deterministic engineering rules and configurable thresholds.

## System Architecture
```mermaid
flowchart LR
    A[Raw Excel Export] --> B[Pandas Loader]
    B --> C[Column Normalization]
    C --> D[Validation Engine]
    D --> E[Pass / Warning / Fail Classification]
    E --> F[Streamlit Dashboard]
    E --> G[Excel Export]
    E --> H[Optional AI Summary]
```

## Files

- [raw_substation_battery_test_export.xlsx](raw_substation_battery_test_export.xlsx) — example raw substation battery test export.

- `requirements.txt` — packages needed for the demo.

## Run

```bash
pip install -r requirements.txt
```

## Demo workflow

1. Read Excel sheets with pandas.
2. Normalize column names.
3. Validate required fields.
4. Classify cell readings using demo thresholds.
5. Combine string-level and cell-level results.

## App
### Landing Page
![Landing page](images/Stage0.png)
### Summary View
![Summary](images/Stage1.png)
### Bank Issues 
![Battery Bank Issues](images/Stage2.png)
### Full Excel Form
![Annotated Excel Form](images/Stage3.png)
### Optional AI Summary
![Optional AI Summary](images/Stage4.png)

- Gemni API is used here as a free demonstration of how Generative AI could be used to summerize results for engineer readibility. 
- AI does not make any decisions regarding maintenance or battery health status, it simply summerizes prior findings
- The prompt used here is: 
"""
You are assisting an electrical utility asset maintenance engineer reviewing backup substation DC battery test preprocessing results.

Rules:
- Do not make final maintenance decisions.
- Do not override the deterministic pass/warning/fail classifications.
- Summarize only the flagged records.
- Use cautious engineering language.
- Organize the summary by battery bank.

Flagged battery test records:
{ai_input}

Write a concise engineer-facing review summary.
"""



## Production upgrade ideas

- Replace demo thresholds with manufacturer-specific limits.
- Allow user to define threshold limits
- Allow user to download annotated excel file
- Add ability for historical data comparision and trend visualization
