import sys
import uuid
import pandas as pd
import json
import streamlit as st

# Adjust path as needed to import your modules
from services import azure_storage
from services import azure_oai

# -------------------------------------------------------- #
# Custom CSS for a cleaner look
# -------------------------------------------------------- #
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

# -------------------------------------------------------- #
# SIDEBAR
# -------------------------------------------------------- #
with st.sidebar:
    st.title("ℹ️ About This App")
    st.info(
        "Welcome! This application helps you **upload**, **manage**, **transcribe**, "
        "and **analyze** audio files using Azure Storage and LLM-based analysis."
    )
 
# ------------------------ 1. Upload Prompt File ------------------------ #
st.header("1. 📝 Upload Persona File")
prompt_file = st.file_uploader("Select a Persona File (TXT)", type=["txt"])

upload_col, _ = st.columns([1, 3])
with upload_col:
    if st.button("Upload Persona", help="Click to upload your Persona"):
        if prompt_file:
            result = azure_storage.upload_prompt_to_blob(prompt_file)
            st.success(result)
        else:
            st.error("No Persona file selected.")

st.markdown("---")

# ------------------------ 2. Manage Existing Prompts ------------------------ #
st.header("2. ⚙️ Manage Existing Personas")
prompt_blobs = azure_storage.list_prompts()

if not prompt_blobs:
    st.warning("No Persona found. Upload one first!")
    st.stop()

selected_prompt_name = st.selectbox("Select a Persona to view or edit:", prompt_blobs)
if not selected_prompt_name:
    st.info("Select a Persona to manage from the dropdown above.")
    st.stop()
else:
    config = azure_storage.read_prompt_config(selected_prompt_name)
    if config:
        st.session_state["kpis"] = config  
    else:
        st.session_state["kpis"] = {}

# --- Load content and config for selected prompt ---
prompt_content = azure_storage.read_prompt(selected_prompt_name)
updated_content = st.text_area(
    "Persona Definition and goals",
    prompt_content,
    height=300,
    help="This represents the persona's goals, characteristics, and other details. Defined as an LLMs prompt",
)

if st.button("Update Persona"):
    if updated_content.strip():
        azure_storage.update_prompt(selected_prompt_name, updated_content)
        st.success("Persona updated successfully.")
    else:
        st.error("Cannot update with empty content.")

st.subheader("2.b. Optional: Display values")
#add some help here to explain that those KPIs should align with the JSON defined in the personas to be extracted
st.markdown("By default we will use the keys in the JSON from the LLM output. If you want to have friendly names in the next steps, please define them here.")

# --- UI for adding a new KPI ---
with st.expander("Add or Update a KPI Parameter", expanded=False):
    kpi_name = st.text_input("KPI Name", value="", max_chars=100)
    kpi_desc = st.text_input("KPI Description", value="", max_chars=200)
    add_kpi_col, _ = st.columns([1, 3])
    with add_kpi_col:
        if st.button("Add KPI"):
            if not kpi_name.strip():
                st.error("KPI name cannot be empty.")
            else:
                st.session_state["kpis"][kpi_name] = kpi_desc
                azure_storage.upload_prompt_config(selected_prompt_name, st.session_state["kpis"])
                st.success(f"KPI '{kpi_name}' added/updated.")


# --- Display current KPIs ---
if st.session_state["kpis"]:
    st.write("**Current KPIs/Parameters**:")
    # A simple table with remove buttons
    for key, val in list(st.session_state["kpis"].items()):
        remove_col, text_col = st.columns([0.1, 0.9])
        with remove_col:
            if st.button("❌", key=f"remove_{key}", help=f"Remove {key}"):
                st.session_state["kpis"].pop(key, None)
                azure_storage.upload_prompt_config(selected_prompt_name, st.session_state["kpis"])
        with text_col:
            st.write(f"**{key}**: {val}")
else:
    st.info("No KPIs defined yet. Add at least one above.")