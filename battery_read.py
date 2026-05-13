import pandas as pd
import re # regular expression




#define warning limits in dictionary
DEFAULT_THRESHOLDS ={
    "lead_acid" : {
        "cell_voltage":{
            "low_critical": 2.10,
            "low_warning": 2.17,
            "high_warning": 2.20,
            "high_critical": 2.30
        },
        "specific_gravity":{
            "low_critical": 1.190,
            "low_warning": 1.210
        },
        "internal_resistance":{
            "high_warning":0.75,
            "high_critical":0.95
        }
    }
}

#keywords to deal with comments
COMMENT_KEYWORDS = {
    "critical": [
        "swelling",
        "crack",
        "leak",
        "fire",
        "smoke"
    ],

    "warning": [
        "corrosion",
        "warm",
        "hot",
        "odor",
        "low electrolyte",
        "replace"
    ]
}

#Open excel file
try:
    df = pd.read_excel('raw_substation_battery_test_export.xlsx')
    print("File opened successfully!")
except FileNotFoundError:
    print("Error: The file does not exist.")
except Exception as e:
    print(f"Error: Could not open file. {e}")

#standerdize columns
def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize spreadsheet column names into snake_case"""
    out = df.copy() #create copy
     # Replace existing column names with cleaned versions
    out.columns=[
         # Replace multiple underscores with a single underscore
        re.sub(r"_+","_",
               # Replace non-alphanumeric characters with underscores
            # Example:
            # "Cell Voltage (V)" -> "cell_voltage_v_"
            re.sub(r"[^0-9a-zA-Z]+","_",
                     # Convert column name to string
                # Remove leading/trailing spaces
                # Convert to lowercase
                   str(c).strip().lower()
            )
            # Remove underscores from beginning/end of string
        ).strip("_")
         # Loop through every column name in the DataFrame
        for c in out.columns
    ]
     # Return cleaned DataFrame
    return out

#check all columns are there
def required_columns(df: pd.DataFrame, required: set[str], sheet_name: str) -> list[str]:
    '''check for missing rows'''
    missing = sorted(required - set(df.columns))
    if missing:
        print(f"{sheet_name} is missing required columns: {', '.join(missing)}")
    return missing

#function to check numeric values against DEFAULT_THRESHOLDS
def check_cell(row: pd.Series,thresholds:dict)-> str:
    #define rows
    voltage = row.get("cell_voltage_v")
    resistance= row.get("internal_resistance_mohm")
    sg = row.get("specific_gravity")

    #define lead-acid dictionary
    lead_acid = thresholds["lead_acid"]
    #fail conditions, compare values to threshold dictionary
    fail = (
        (pd.notna(voltage) and voltage < lead_acid["cell_voltage"]['low_critical'])
        or (pd.notna(sg) and sg < lead_acid["specific_gravity"]["low_critical"])
    or (pd.notna(resistance) and resistance > lead_acid["internal_resistance"]["high_critical"])
    )
    #warning conditions, compare values to threshold dictionary
    warning = (
        (pd.notna(voltage) and voltage < lead_acid["cell_voltage"]['low_warning'])
        or (pd.notna(sg) and sg < lead_acid["specific_gravity"]["low_warning"])
    or (pd.notna(resistance) and resistance > lead_acid["internal_resistance"]["high_warning"])
    )
    if fail:
        return "Fail"
    if warning:
        return "Warning"
    return "Pass"

#function to check comments for flag words
def check_comment(row:pd.Series, keywords:dict)->str:
    '''Check comment cell in row and evaluates'''
    #import comment and convert to lowercase
    comment = row.get("technician_comments","").lower()

    #define dictionary critial/warning
    critical = keywords["critical"]
    warning = keywords["warning"]
    
    #check comments for Failure and warnings, return pass if pass
    for keyword in critical:
        if keyword in comment:
            return "Fail"
    for keyword in warning:
        if keyword in comment:
            return "Warning"
    return "Pass"

#create a new colum and fill each row with results of check_cell output
df["cell_status"] = df.apply(
    lambda row: check_cell(row, DEFAULT_THRESHOLDS), #for a give row, check_cell,
    axis=1 #work across rows
)

#create a new column and fill each row with results of check_comment output
df["comment_status"] = df.apply(
    lambda row: check_comment(row, COMMENT_KEYWORDS),
    axis=1
)

def combine_status(row):
    '''function to check both function results and return a pass, fail, warning metric'''
    if "Fail" in [row["cell_status"], row["comment_status"]]:
        return "Fail"
    if "Warning" in [row["cell_status"], row["comment_status"]]:
        return "Warning"
    return "Pass"

#create a review row
df["review_status"] = df.apply(combine_status, axis=1)


print(df[[
    "substation",
    "battery_bank",
    "cell_number",
    "cell_voltage_v",
    "internal_resistance_mohm",
    "specific_gravity",
    "technician_comments",
    "cell_status",
    "review_status"
]].head(20))