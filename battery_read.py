import pandas as pd
import re # regular expression
import streamlit as st

#streamlit calls for UI
st.set_page_config(page_title="Battery Test Preprocessing Demo", layout="wide")

st.title("Substation Backup DC Battery Test Preprocessing Demo")
st.caption("Synthetic demo: upload the Excel workbook, validate records, flag bad readings")


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
    df = pd.read_excel('Battery_preprocess/raw_substation_battery_test_export.xlsx')
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

def combine_status(row):
    '''function to check both function results and return a pass, fail, warning metric'''
    if "Fail" in [row["cell_status"], row["comment_status"]]:
        return "Fail"
    if "Warning" in [row["cell_status"], row["comment_status"]]:
        return "Warning"
    return "Pass"

def status_color(value):
    if value =="Fail":
        return "color: red"
    elif value == "Warning":
        return "color: orange"
    elif value == "Pass":
        return "color: green"
    return ""



#---------------UI Streamlit-----------------------
#creat a browser upload widget and store file once uploaded
uploaded = st.file_uploader("Upload battery test Excel workbook", type=["xlsx"])

#Open excel file
if uploaded is None:
    st.info("Upload an Excel file to begin.")
    st.stop()

try:
    df = pd.read_excel(uploaded)
    st.success("File opened successfully!")

except FileNotFoundError:
    st.error("Error: The file does not exist.")

except Exception as e:
    st.error(f"Error: Could not open file. {e}")
    st.stop()

#--------------call functions-----------------------
df = clean_cols(df)
#check for missing columns
REQUIRED_COLUMNS = {
    "substation",
    "battery_bank",
    "cell_number",
    "cell_voltage_v",
    "internal_resistance_mohm",
    "specific_gravity",
    "technician_comments"
}

missing = REQUIRED_COLUMNS - set(df.columns)

if missing:
    st.error(f"Missing required columns: {', '.join(missing)}")
    st.stop()

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

#create a review row
df["review_status"] = df.apply(combine_status, axis=1)

#apply function cell-by-cell
styled_df = df.style.map(
    status_color,
    subset=["cell_status", "review_status"]
)


#--------------Summary-----------------------
st.subheader("Battery Test Summary")

total_records = len(df)

fail_count = (df["review_status"]== "Fail").sum()
warning_count = (df["review_status"]== "Warning").sum()
pass_count = (df["review_status"]=="Pass").sum()

avg_voltage =df["cell_voltage_v"].mean()
min_voltage = df["cell_voltage_v"].min()
max_voltage = df["cell_voltage_v"].max()
voltage_spread = max_voltage - min_voltage

avg_resistance = df["internal_resistance_mohm"].mean()
max_resistance = df["internal_resistance_mohm"].max()

avg_sg = df["specific_gravity"].mean()
min_sg = df["specific_gravity"].min()

#---------display--------
c1, c2, c3, c4 = st.columns(4) #create 4 columns
c1.metric("Records Reviewed", total_records)
c2.metric("Pass", pass_count)
c3.metric("Warning", warning_count)
c4.metric("Failure", fail_count)

v1, v2, v3, v4 = st.columns(4) #create 4 more
v1.metric("Avg Cell Voltage", f"{avg_voltage:.3f} V") 
v2.metric("Min Cell Voltage", f"{min_voltage:.3f} V") 
v3.metric("Max Cell Voltage", f"{max_voltage:.3f} V") 
v4.metric("Voltage Spread", f"{voltage_spread:.3f} V") 

r1, r2, r3, r4 = st.columns(4) 
r1.metric("Avg Resistance", f"{avg_resistance:.3f} mΩ") 
r2.metric("Max Resistance", f"{max_resistance:.3f} mΩ") 
r3.metric("Avg Specific Gravity", f"{avg_sg:.3f}") 
r4.metric("Min Specific Gravity", f"{min_sg:.3f}") 

#-----------------Full excel table styled---------------
st.subheader("Full Excel File")
st.dataframe(styled_df)