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
    reasons = []
    status = "Pass"
    #define rows
    voltage = row.get("cell_voltage_v")
    resistance= row.get("internal_resistance_mohm")
    sg = row.get("specific_gravity")

    #define lead-acid dictionary
    lead_acid = thresholds["lead_acid"]
    #fail conditions, compare values to threshold dictionary
    if pd.notna(voltage):
        if voltage < lead_acid["cell_voltage"]['low_critical']:
            if status != "Fail":
                status = "Fail"
            reasons.append("Critically low voltage")
        elif voltage > lead_acid["cell_voltage"]['high_critical']:
            if status != "Fail":
                status = "Fail"
            reasons.append("Critically high voltage")
        elif voltage < lead_acid["cell_voltage"]['low_warning']:
            if status != "Fail":
                  status = "Warning"
            reasons.append("Low voltage")
        elif voltage > lead_acid["cell_voltage"]['high_warning']:
            if status != "Fail":
                status = "Warning"
            reasons.append("High  voltage")
    if pd.notna(sg):
        if sg < lead_acid["specific_gravity"]["low_critical"]:
            if status != "Fail":
                status = "Fail"
            reasons.append("Critically low specific gravity")
        elif sg < lead_acid["specific_gravity"]["low_warning"]:
            if status != "Fail":
                status = "Warning"
            reasons.append("low specific gravity")
    if pd.notna(resistance):
        if resistance > lead_acid["internal_resistance"]["high_critical"]:
          if status != "Fail":
            status = "Fail"
            reasons.append("Critically high resistance")
        elif resistance > lead_acid["internal_resistance"]["high_warning"]:
            if status != "Fail":
                status = "Warning"
            reasons.append("High resistance")
    return status, "; ".join(reasons)

#function to check comments for flag words
def check_comment(row:pd.Series, keywords:dict)->str:
    '''Check comment cell in row and evaluates'''
    reasons =[]
    status = "Pass"
    #import comment and convert to lowercase
    comment = row.get("technician_comments","").lower()

    #define dictionary critial/warning
    critical = keywords["critical"]
    warning = keywords["warning"]
    
    #check comments for Failure and warnings, return pass if pass
    for keyword in critical:
        if keyword in comment:
            reasons.append(f"Comment keyword: {keyword}")
            status = "Fail"
    for keyword in warning:
        if keyword in comment:
            reasons.append(f"Comment keyword: {keyword}")
            if status != "Fail":
                status = "Warning"
    return status, "; ".join(reasons)

#function get deviation for row
def row_voltage_deviation(row:pd.Series,avg):
    return abs(row["cell_voltage_v"]-avg)
#determine if imbalance
def imbalance_status(row:pd.Series):
    if row["voltage_deviation"] > 0.05:
        return "Fail"
    elif row["voltage_deviation"]> 0.03:
        return "Warning"
    

def combine_status(row):
    '''function to check both function results and return a pass, fail, warning metric'''
    if "Fail" in [row["cell_status"], row["comment_status"], row["imbalance_status"]]:
        return "Fail"
    if "Warning" in [row["cell_status"], row["comment_status"],row["imbalance_status"]]:
        return "Warning"
    return "Pass"

def status_color(value):
    if value =="Fail":
        return "background-color: red"
    elif value == "Warning":
        return "background-color: orange"
    elif value == "Pass":
        return "background-color: green"
    return ""

def highlight_row(row):
    if row["review_status"] == "Fail":
        return ["background-color: #ffcccc"]*len(row)
    elif row["review_status"] == "Warning":
        return ["background-color: #fff3cd"]*len(row)
    elif row["review_status"] == "Pass":
        return ["background-color: green"]*len(row)
    return [""]*len(row)

def get_review_reasons(row):
    #deal with missing syntax
    reasons =[]
    if row["cell_reasons"]:
        reasons.append(row['cell_reasons'])
    if row["comment_reasons"]:
        reasons.append(row['comment_reasons'])
    if row["imbalance_status"]=="Fail":
        reasons.append(f"Voltage imbalance: {row['voltage_deviation']:.3f} V from bank average")
    elif row["imbalance_status"]=="Warning":
         reasons.append(f"Voltage imbalance warning: {row['voltage_deviation']:.3f} V from bank average")
    return "; ".join(reasons)



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
df[["cell_status","cell_reasons"]] = df.apply(
    lambda row: check_cell(row, DEFAULT_THRESHOLDS), #for a give row, check_cell,
    axis=1, #work across rows
    result_type="expand"
)

#create a new column and fill each row with results of check_comment output
df[["comment_status","comment_reasons"]] = df.apply(
    lambda row: check_comment(row, COMMENT_KEYWORDS),
    axis=1,
    result_type="expand"
)
#create new voltage deviation ifo rows
df["voltage_deviation"] = 0.0
df["imbalance_status"] = "Pass"

#loop through each unique battery bank name calculate
for bank in df["battery_bank"].unique():
    #find rows associated with this bank
    bank_mask = df["battery_bank"] == bank
    #make temporary copy
    bank_df = df[bank_mask].copy()
    #calculate the avg cell votage for bank
    bank_avg = bank_df["cell_voltage_v"].mean()
    #calculate the voltage deviation for the bank
    bank_df["voltage_deviation"] = bank_df.apply(
        lambda row: row_voltage_deviation(row, bank_avg),
        axis=1
    )
    #write the deviation values back into the main df
    df.loc[bank_mask, "voltage_deviation"] = bank_df["voltage_deviation"]

df["imbalance_status"] = df.apply(imbalance_status,axis=1)

df["review_status"] = df.apply(combine_status, axis=1)

#create a review row
df["review_status"] = df.apply(combine_status, axis=1)
df["review_reasons"] = df.apply(get_review_reasons, axis=1)

#apply function cell-by-cell
styled_df = df.style.map(
    status_color,
    subset=["cell_status", "review_status"]
)



#--------------Summary-----------------------
st.header("Battery Test Summary")

total_records = len(df)

fail_count = (df["review_status"]== "Fail").sum()
warning_count = (df["review_status"]== "Warning").sum()
pass_count = (df["review_status"]=="Pass").sum()

#---------display summary--------
c1, c2, c3, c4 = st.columns(4) #create 4 columns
c1.metric("Records Reviewed", total_records)
c2.metric("Pass", pass_count)
c3.metric("Warning", warning_count)
c4.metric("Failure", fail_count)

#---------------battery bank summary------------------
st.subheader("Battery Bank Summary")
#create a new data frame
bank_summary = df.groupby("battery_bank").agg(
    cells_tested=("cell_number", "count"),
    avg_voltage=("cell_voltage_v", "mean"),
    min_voltage=("cell_voltage_v", "min"),
    max_voltage=("cell_voltage_v", "max"),
    avg_resistance=("internal_resistance_mohm", "mean"),
    max_resistance=("internal_resistance_mohm", "max"),
    avg_sg=("specific_gravity", "mean"),
    min_sg=("specific_gravity", "min"),
)
st.dataframe(bank_summary)

#-------------bank view--------------------------------
st.header("Battery Bank Issues")
st.markdown("""
### Review Key

🟥 Fail  
🟨 Warning
""")
#loop through banks in battery bank column
for bank in df["battery_bank"].unique():
    #create a new dataframe for each bank #
    bank_df = df[df["battery_bank"]== bank]

    #create another new dataframe filled with banks that failed test
    review_df = bank_df[
        bank_df["review_status"].isin(["Warning", "Fail"])
    ]
        
    #create dataframe of failures
    fail_df = bank_df[bank_df["review_status"]=="Fail"].sort_values("cell_number")
    #create dataframe of warnings
    warning_df = bank_df[bank_df["review_status"]=="Warning"].sort_values("cell_number")
    #create a styled dataframe 
    styled_review_df=review_df.style.apply(highlight_row, axis=1)

    st.subheader(bank)
    st.dataframe(styled_review_df, use_container_width=True)

    st.markdown("#### Failures")
    st.dataframe(fail_df[["cell_number", "review_reasons"]])

    st.markdown("#### Warnings")
    st.dataframe(warning_df[["cell_number", "review_reasons"]])


#-----------------Full excel table styled---------------
st.subheader("Full Excel File")
st.dataframe(styled_df)