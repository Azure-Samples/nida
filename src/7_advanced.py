import pandas as pd
import json
import streamlit as st
import os
from sklearn.metrics import accuracy_score, precision_score, f1_score
from collections import defaultdict

# Adjust path as needed to import your modules
from services import azure_storage

st.markdown(
    """
    <style>
    /* Make the main container a bit narrower */
    .main > div {
        max-width: 800px;
    }
    /* Add subtle styling to text areas */
    .stTextArea textarea {
        border: 1px solid #ddd;
        border-radius: 6px;
    }
    /* Center-align the success/info/warning messages */
    .element-container {
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

############################
# 1. Helper Functions
############################
def flatten_json(nested_json, parent_key='', sep='.'):
    """
    Recursively flattens a nested JSON/dict.
    E.g. {"Key1": {"SubKey1": "val1", "SubKey2": "val2"}, "Key2": true}
    becomes {"Key1.SubKey1": "val1", "Key1.SubKey2": "val2", "Key2": true}
    """
    items = []
    for k, v in nested_json.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def aggregate_data(json_list):
    """
    Flatten each JSON and collect values in a dict of lists:
        {
          "Key1.SubKey1": [val1, val2, ...],
          "Key2": [val3, val4, ...],
          ...
        }
    """
    aggregated = defaultdict(list)
    for j in json_list:
        flat_j = flatten_json(j)
        for key, val in flat_j.items():
            aggregated[key].append(val)
    return aggregated

def convert_value(x):

    # Return booleans unchanged.
    if isinstance(x, bool):
        return x

    # Leave integers unchanged.
    if isinstance(x, int):
        return x

    # Process floats: only 1.0 and 0.0 are recognized.
    if isinstance(x, float):
        if x == 1.0:
            return True
        elif x == 0.0:
            return False
        else:
            return None

    # Process strings.
    if isinstance(x, str):
        s = x.strip().lower()
        mapping = {"yes": True, "true": True, "no": False, "false": False}
        if s in mapping:
            return mapping[s]
        # Also allow strings that are numeric representations.
        try:
            num = int(s)
            if num == 1:
                return True
            elif num == 0:
                return False
        except ValueError:
            return None
        return None

    # For other types, attempt to convert to a string and process.
    try:
        s = str(x).strip().lower()
    except Exception:
        return None
    if s in ("yes", "true"):
        return True
    elif s in ("no", "false"):
        return False
    return None

def get_eval_data(selected_prompt_name):
    llm_analysis = azure_storage.list_llmanalysis(selected_prompt_name)
# Parse the JSON input
    all_jsons = []
    if llm_analysis:
        for file in llm_analysis:
            try:
                data = azure_storage.read_llm_analysis(selected_prompt_name, file)
                ground_truth = azure_storage.read_eval(selected_prompt_name, file)
                all_jsons.append(data)
                for key, value in ground_truth.items():
                    if key.lower() == "call id":
                        continue
                    data[f"{key}.gt"] = value
                all_jsons.append(data)
            except Exception as e:
                st.error(f"Error reading {file}: {e}")
    return all_jsons

############################
# 1. UI
############################

st.header("1. ⚙️ Scoring Parameters")
#add some help here to explain that those KPIs should align with the JSON defined in the personas to be extracted
st.markdown("Define the KPIs/Parameters that will be extracted from the evaluation files.")

if "kpis" not in st.session_state:
    st.session_state["kpis"] = []

prompt_files = azure_storage.list_prompts()
if not prompt_files:
    st.warning("No persona files found in the container.")
    st.stop()

selected_eval_prompt = st.selectbox("Select a Persona", prompt_files)
if not selected_eval_prompt:
    st.info("Select a persona from the dropdown above to continue.")
    st.stop()
else:
    existing_config = azure_storage.read_prompt_config(selected_eval_prompt)
    if existing_config:
        st.session_state["kpis"] = existing_config
    else:
        st.session_state["kpis"] = []
    
# --- UI for adding a new KPI ---
with st.expander("Add or Update a KPI Parameter", expanded=False):
    kpi_name = st.text_input("KPI Name", value="", max_chars=100)
    add_kpi_col, _ = st.columns([1, 3])
    with add_kpi_col:
        if st.button("Add ground truth KPI", help="Click to add/update a KPI parameter."):
            if not kpi_name.strip():
                st.error("KPI name cannot be empty.")
            else:
                st.session_state["kpis"].append(kpi_name)
                azure_storage.upload_prompt_config(selected_eval_prompt, st.session_state["kpis"])
                st.success(f"KPI '{kpi_name}' added/updated.")


# --- Display current KPIs ---
if st.session_state["kpis"] and len(st.session_state["kpis"]) > 0:
    st.write("**Current KPIs/Parameters**:")
    # A simple table with remove buttons
    for value in list(st.session_state["kpis"]):
        remove_col, text_col = st.columns([0.1, 0.9])
        with remove_col:
            if st.button("❌", key=f"remove_{value}", help=f"Remove {value}"):
                st.session_state["kpis"].remove(value)
                azure_storage.upload_prompt_config(selected_eval_prompt, st.session_state["kpis"])
        with text_col:
            st.write(value)
else:
    st.info("No KPIs defined yet. Add at least one above.")
    st.stop()

st.markdown("---")

st.title("2. 📊 Ground truth")
st.markdown("Upload an evaluation (CSV/XLSX) containing the KPIs defined for a given prompt.")

# Attempt to download the config from the same container
config_data = azure_storage.read_prompt_config(selected_eval_prompt)
if config_data is None:
    st.error(f"Could not find a config file for prompt '{selected_eval_prompt}'. Please define KPIs first.")
    st.stop()

# The config looks like {"Parameter1": "Description...", "Parameter2": "..."}
# We'll treat the keys of that dict as required columns, plus "Call ID"
required_columns = list(config_data) + ["Call ID"]
st.write(f"**Required columns** for this evaluation file: {required_columns}")

uploaded_eval_file = st.file_uploader(
    f"Upload your evaluation file for '{selected_eval_prompt}' (CSV/XLSX)",
    type=["csv", "xlsx"]
)

if uploaded_eval_file is not None:
    # Read file into DataFrame
    try:
        if uploaded_eval_file.name.endswith(".csv"):
            df_eval = pd.read_csv(uploaded_eval_file)
        else:
            df_eval = pd.read_excel(uploaded_eval_file, sheet_name='Parameters')
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    # Check required columns
    missing_cols = [col for col in required_columns if col not in df_eval.columns]
    if missing_cols:
        st.error(f"Missing required columns in your file: {missing_cols}")
        st.stop()

    # Upload each row as JSON
    success_count = 0
    for idx, row in df_eval.iterrows():
        row_dict = row.to_dict()
        call_id = str(row_dict["Call ID"]).strip()

        if not call_id or call_id.lower() == "not found":
            st.warning(f"Skipping row {idx}: invalid Call ID.")
            continue

        blob_name = f"{call_id}.json"
        row_json = json.dumps(row_dict, indent=2)

        try:
            azure_storage.upload_eval_to_blob(blob_name, selected_eval_prompt, row_json)
            success_count += 1
        except Exception as e:
            st.error(f"Failed to upload row index {idx} (Call ID: {call_id}). Error: {e}")

    if success_count:
        st.success(f"Successfully uploaded {success_count} evaluation file(s) to storage.")

st.markdown("---")

st.title("3. 📈 Evaluation Results")
st.markdown("Evaluate the AI predictions against the ground truth data.")

eval_data = get_eval_data(selected_eval_prompt)

# Aggregate all JSON data
if len(eval_data) == 0:
    st.warning("⚠️  No Persona or calls have been analyzed yet.")
    st.stop()

aggregated = aggregate_data(eval_data)

# This handles columns of different lengths by converting values to Pandas Series.
df = pd.DataFrame({k: pd.Series(v) for k, v in aggregated.items()})

st.markdown(df.head())
# Define the parameters to evaluate.
parameters = azure_storage.read_prompt_config(selected_eval_prompt) or []

# Create a column layout: one column per parameter.
cols = st.columns(len(parameters))

for i, param in enumerate(parameters):
    # According to your CSV format:
    #   Ground truth is in the column "<Parameter>"
    #   AI prediction is in the column "<Parameter> - Score"
    pred_col = f"{param}.score"
    truth_col = f"{param}.gt"
    
    with cols[i]:
        st.write(f"### {param}")
        if pred_col not in df.columns or truth_col not in df.columns:
            st.error(f"Columns for {param} not found.")
            continue
        
        # Convert the values using your conversion function.
        y_true = df[truth_col].apply(convert_value)
        y_pred = df[pred_col].apply(convert_value)

        # Drop rows where conversion failed.
        valid_mask = y_true.notnull() & y_pred.notnull()
        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        if len(y_true) == 0:
            st.warning(f"No valid data for {param}")
        else:
            # Compute accuracy (works regardless of averaging).
            acc = accuracy_score(y_true, y_pred)

           # Decide on the averaging method:
            # If the first elements in both series are booleans, assume binary classification.
            # Otherwise (e.g. if integers are used), assume it's not binary.
            if isinstance(y_true.iloc[0], bool) and isinstance(y_pred.iloc[0], bool):
                # Binary classification.
                prec = precision_score(y_true, y_pred, average='binary', pos_label=True, zero_division=0)
                f1 = f1_score(y_true, y_pred, average='binary', pos_label=True, zero_division=0)
            else:
                # Assume multi-class (non-binary) when integers are used.
                prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)

            # Display the metrics.
            st.metric("Accuracy", f"{acc:.2f}")
            st.metric("Precision", f"{prec:.2f}")
            st.metric("F1 Score", f"{f1:.2f}")
