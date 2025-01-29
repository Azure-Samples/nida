import streamlit as st
import os
import json
from datetime import datetime
# Import your azure storage helpers
from services import azure_storage



# ---------- CSS/Styling ----------
st.markdown(
    """
    <style>
    /* Parameter Card Styles */
    .parameter-card {
        background: var(--color-bg-secondary);
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid var(--color-border);
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        color: var(--color-text-primary);
    }

    /* Metric Badge Styles */
    .metric-badge {
        display: inline-block;
        padding: 0.375rem 0.75rem;
        border-radius: 0.5rem;
        font-weight: 500;
        margin-right: 0.75rem;
        font-size: 0.875rem;
    }

    /* Match/Mismatch Indicators */
    .match {
        background-color: var(--color-match-bg);
        color: var(--color-match-text);
        border: 1px solid var(--color-match-border);
    }

    .mismatch {
        background-color: var(--color-mismatch-bg);
        color: var(--color-mismatch-text);
        border: 1px solid var(--color-mismatch-border);
    }

    /* Explanation Box */
    .explanation-box {
        background: var(--color-bg-primary);
        border-left: 4px solid var(--color-focus);
        padding: 1.25rem;
        margin: 0.75rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
        color: var(--color-text-primary);
    }

   
   
    </style>
    """,
    unsafe_allow_html=True
)

def display_ai_evaluation(ground_truth, param_key, display_name, ai_evaluation):
    st.markdown("#### LLM Results")
    # Always show the AI score
    if ground_truth:
        gt_score = ground_truth.get(param_key, None)
        if gt_score is not None:
            match = (str(ai_evaluation).strip().lower() == str(gt_score).strip().lower())
            match_class = "match" if match else "mismatch"
            st.markdown(
                f"""
                <div class="parameter-card">
                    <div class="metric-badge {match_class}">
                        {'✓ Match' if match else '✗ Mismatch'}
                    </div>
                    <br><br>
                    <strong>AI evaluation:</strong> {ai_evaluation}
                    <br><br>
                    <strong>Ground Truth:</strong> {gt_score}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info(f"No ground-truth for '{display_name}'")
    else:
        st.markdown(
            f"""
            <div class="parameter-card">
                {ai_evaluation}
            </div>
            """,
            unsafe_allow_html=True
        )

def parse_call_id_from_filename(filename: str) -> str:
    """
    Given a filename like 'call123.json', extract call123 as the ID 
    (or remove .json). Adjust logic if your naming differs.
    """
    return os.path.splitext(filename)[0]


# -------------------- PARAMETERS ANALYSIS --------------------
st.markdown("### 🎯 Call Analysis")

 # 1) List all prompts
prompt_list = azure_storage.list_prompts()  # e.g. ["marketing_prompt.txt", "sales_prompt_v2.txt", ...]
if not prompt_list:
    st.warning("⚠️ No Persona or calls have been analyzed yet.")
    st.stop()

selected_prompt = st.selectbox("Select A Persona", prompt_list, format_func=lambda x: x )

all_analysis_files = azure_storage.list_llmanalysis(selected_prompt)
analysis_files = [f for f in all_analysis_files if f.endswith(".json")]

if not analysis_files:
    st.warning("No Call Analysis found for this Persona.")
    st.stop()

# Convert each filename into a "call_id"
call_ids = [parse_call_id_from_filename(f) for f in analysis_files]
selected_call_id = st.selectbox("Select Call ID", call_ids)

# --- Main Content ---
analysis_filename = f"{selected_call_id}.json"  # e.g. "call123.json"
analysis_data = azure_storage.read_llm_analysis(selected_prompt, analysis_filename)

if not analysis_data:
    st.warning(f"No data found for Call ID {selected_call_id}")
    st.stop()

# fetch the KPIs from the prompt config (may be None or empty)
config_data = azure_storage.read_prompt_config(selected_prompt) or {}
# Example: { "Parameter 1": "Convincing power of sales", "Parameter 2": "Agent confident", ... }

eval_filename = f"{selected_call_id}.json"
ground_truth = azure_storage.read_eval(selected_prompt, eval_filename)

# --- Sidebar Controls ---
with st.sidebar:   
    # Quick stats
    st.markdown("### 📊 Quick Stats")
    st.markdown(f"Total Calls for this Persona: **{len(call_ids)}**")

    # Add timestamp
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# Decide which keys to use (config_data if available, else analysis_data).
if config_data:
    param_keys = sorted(config_data.keys(), key=lambda x: x.lower())
else:
    # Fallback if config_data is empty or None
    param_keys = sorted(analysis_data.keys(), key=lambda x: x.lower())

# Create tabs from either the config labels or raw keys
tabs = st.tabs([config_data.get(k, k) for k in param_keys])


for i, param_key in enumerate(param_keys):
    # The user-friendly name from the config, or fallback to the raw key
    display_name = config_data.get(param_key, param_key)

    with tabs[i]:
        # Retrieve the analysis result for the parameter
        result = analysis_data.get(param_key, "N/A")

        # Check if the result is a dictionary with score and explanation
        if isinstance(result, dict):
            ai_evaluation = result.get("Score", "N/A")
            ai_explanation = result.get("Explanation", "N/A")
        else:
            ai_evaluation = result
            ai_explanation = "N/A"  # or handle differently if needed

        # Compare with ground-truth (if it exists)
        if not ai_explanation or ai_explanation.strip().lower() == "n/a":
            display_ai_evaluation(ground_truth, param_key, display_name, ai_evaluation)
        else:
            col1, col2 = st.columns(2)
            with col1:
                display_ai_evaluation(ground_truth, param_key, display_name, ai_evaluation)
            with col2:
                st.markdown("#### LLM Explanation")
                if ai_explanation and ai_explanation.strip().lower() != "n/a":
                    st.markdown(
                        f"""
                        <div class="explanation-box">
                            {ai_explanation}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.info("No explanation provided.")


# -------------------- TRANSCRIPT SECTION --------------------
with st.expander("📝 Call Transcript"):
    transcript_text = azure_storage.read_transcription(selected_call_id + ".txt")
    if transcript_text:
        st.markdown(transcript_text)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning(f"No transcript found for Call ID '{selected_call_id}'.")