import pandas as pd
import json
import streamlit as st

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



st.header("1. ⚙️ Scoring Parameters")
#add some help here to explain that those KPIs should align with the JSON defined in the personas to be extracted
st.markdown("Define the KPIs/Parameters that will be extracted from the evaluation files.")

prompt_files = azure_storage.list_prompts()
if not prompt_files:
    st.warning("No persona files found in the container.")
    st.stop()

selected_eval_prompt = st.selectbox("Select a Persona", prompt_files)
if not selected_eval_prompt:
    st.info("Select a persona from the dropdown above to continue.")
    st.stop()

if "kpis" not in st.session_state:
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

