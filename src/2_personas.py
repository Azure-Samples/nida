import sys
import uuid
import pandas as pd
import json
import streamlit as st
from datetime import datetime

# Adjust path as needed to import your modules
from services import azure_storage, azure_oai, azure_queue

from concurrent.futures import ThreadPoolExecutor, as_completed

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


# Function to process a single blob
def analyze_blob(persona_prompt, blob_name):
    # Read transcription
    transcribed_text = azure_storage.read_transcription(blob_name)
    # Call the LLM with the prompt and transcription text
    analysis_result = azure_oai.call_llm(prompt_content, transcribed_text)
    # Upload the analysis result back to storage
    azure_storage.upload_llm_analysis_to_blob(
        blob_name, 
        persona_prompt, 
        analysis_result
    )

    persona = persona_prompt.split(".")[0]
    azure_queue.send_message_to_queue(
        json.dumps({
            "blob_uri": azure_storage.get_uri(blob_name,persona ),
            "persona": persona,
            "date": datetime.now().isoformat()
        })
    )

    return f"Analysis completed for **{blob_name}**."

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

st.markdown("---")

st.title("3. 🤖 LLM Analysis")
st.markdown("Analyze all transcribed files using a selected persona.")


if st.button("Analyze with GenAI"):
    transcription_blobs = azure_storage.list_transcriptions()
    if not transcription_blobs:
        st.warning("No transcribed files available for analysis.")
    else:
        prompt_content = azure_storage.read_prompt(selected_prompt_name)
        with st.spinner("Running analysis on transcriptions..."):
        # Create a thread pool with a maximum of 5 threads
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit each blob's analysis task to the executor
                future_to_blob = {
                    executor.submit(analyze_blob, selected_prompt_name, blob_name): blob_name
                    for blob_name in transcription_blobs
                }
                # Process and display the results as each thread completes
                for future in as_completed(future_to_blob):
                    blob_name = future_to_blob[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        st.error(f"Analysis generated an exception for {blob_name}: {exc}")
                    else:
                        st.success(result)

