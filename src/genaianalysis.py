import sys
import uuid
import pandas as pd
import json
import streamlit as st

# Adjust path as needed to import your modules
from services import azure_storage
from services import azure_oai
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
def analyze_blob(blob_name):
    # Read transcription
    transcribed_text = azure_storage.read_transcription(blob_name)
    # Call the LLM with the prompt and transcription text
    analysis_result = azure_oai.call_llm(prompt_content, transcribed_text)
    # Upload the analysis result back to storage
    azure_storage.upload_llm_analysis_to_blob(
        blob_name, 
        chosen_analysis_prompt, 
        analysis_result
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
    st.markdown("---")
    st.subheader("🔍 Quick Navigation")
    st.write(
        "1. **LLM Analysis**\n"
        "2. **Evaluation**"
    )

# -------------------------------------------------------- #
# MAIN APP TABS
# -------------------------------------------------------- #
tabs = st.tabs(["LLM Analysis", "Advanced"])

# ===================== TAB 1: LLM Analysis ===================== #
with tabs[0]:
    st.title("1. 🤖 LLM Analysis")
    st.markdown("Analyze all transcribed files using a selected persona.")

    analysis_prompts = azure_storage.list_prompts()
    if not analysis_prompts:
        st.warning("No Personas available for analysis.")
        st.stop()

    chosen_analysis_prompt = st.selectbox("Select a Persona for Analysis", analysis_prompts)

    if st.button("Analyze with LLM"):
        transcription_blobs = azure_storage.list_transcriptions()
        if not transcription_blobs:
            st.warning("No transcribed files available for analysis.")
        else:
            prompt_content = azure_storage.read_prompt(chosen_analysis_prompt)
            with st.spinner("Running analysis on transcriptions..."):
            # Create a thread pool with a maximum of 5 threads
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit each blob's analysis task to the executor
                    future_to_blob = {
                        executor.submit(analyze_blob, blob_name): blob_name
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

# ===================== TAB 3: Evaluation ===================== #
with tabs[1]:
    st.title("2. 📊 Advanced")
    st.markdown("Upload an evaluation (CSV/XLSX) containing the KPIs defined for a given prompt.")

    prompt_files = azure_storage.list_prompts()
    if not prompt_files:
        st.warning("No persona files found in the container.")
        st.stop()

    selected_eval_prompt = st.selectbox("Select a Persona", prompt_files)
    if not selected_eval_prompt:
        st.info("Select a persona from the dropdown above to continue.")
        st.stop()

    # Attempt to download the config from the same container
    config_data = azure_storage.read_prompt_config(selected_eval_prompt)
    if config_data is None:
        st.error(f"Could not find a config file for prompt '{selected_eval_prompt}'. Please define KPIs first.")
        st.stop()

    # The config looks like {"Parameter1": "Description...", "Parameter2": "..."}
    # We'll treat the keys of that dict as required columns, plus "Call ID"
    required_columns = list(config_data.keys()) + ["Call ID"]
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

# -------------------------------------------------------- #
# FOOTER
# -------------------------------------------------------- #
st.write("")
st.markdown("<hr style='border: 1px solid #ddd;' />", unsafe_allow_html=True)
st.caption("© 2025 Contoso - Built with Azure AI Services")
