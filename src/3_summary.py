import streamlit as st
from datetime import datetime
from services import azure_storage, azure_oai
from collections import defaultdict
import numpy as np
import pandas as pd
import altair as alt
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

def is_numeric(val):
    return isinstance(val, (int, float))

def can_be_boolean(val):
    """
    Returns True if val is either a Python bool or a string "Yes"/"No" (case-insensitive).
    """
    if isinstance(val, bool):
        return True
    if isinstance(val, str) and val.strip().lower() in ["yes", "no"]:
        return True
    return False

def coerce_to_boolean(val):
    """
    Convert Python bool or "Yes"/"No" string to a Python bool.
    - "Yes" => True
    - "No"  => False
    """
    if isinstance(val, bool):
        return val
    elif isinstance(val, str):
        return (val.strip().lower() == "yes")
    # Fallback
    return False

def to_string(val):
    # Convert any non-string to string if needed
    return str(val)


##################################
# 2. Streamlit Page
##################################
st.markdown("""
    <style>

   /* CHARTS AND GRAPHS CONTAINER */
.chart-container {
    background-color: var(--color-bg-secondary);
    border-radius: 0.75rem;
    padding: 1.5rem;
    border: 1px solid var(--color-border);
    margin: 1rem 0;
    color: var(--color-text-primary);
}

/* DATA TABLES */
.dataframe {
    background-color: var(--color-bg-secondary) !important;
    color: var(--color-text-primary) !important;
}

.dataframe th {
    background-color: var(--color-bg-primary) !important;
    color: var(--color-text-primary) !important;
    padding: 0.75rem !important;
    font-weight: 600 !important;
}

.dataframe td {
    background-color: var(--color-bg-secondary) !important;
    color: var(--color-text-secondary) !important;
    padding: 0.75rem !important;
}

/* TOOLTIPS */
.tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
}

.tooltip .tooltiptext {
    visibility: hidden;
    background-color: var(--color-bg-primary);
    color: var(--color-text-primary);
    text-align: center;
    padding: 0.5rem;
    border-radius: 0.5rem;
    border: 1px solid var(--color-border);
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    opacity: 0;
    transition: opacity 0.2s;
}

    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }

    </style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_insights_cached(values):
    return azure_oai.get_insights(values)

def is_valid_analysis(data):
    """
    Returns True if the analysis data seems valid, False otherwise.
    Adjust the conditions based on your quality criteria.
    """
    # Example check: if the summary explicitly indicates no transcript was provided.
    summary = data.get("summary", "")
    if isinstance(summary, str) and "no transcript" in summary.lower():
        return False

    # Check sentiment: if Score is None, it might indicate invalid data.
    sentiment = data.get("sentiment", {})
    if sentiment.get("Score") is None:
        return False

    # Optionally, check if main_issues and resolution are both empty/null.
    if data.get("main_issues") is None and data.get("resolution") is None:
        return False

    return True
# --- Title and Intro ---
st.title("🎯 Summary of Call Analysis")

# 1. List all .txt prompt files in the PROMPTS_CONTAINER
all_prompt_files = azure_storage.list_prompts()

if not all_prompt_files:
    st.warning("⚠️ No personas .txt files found in Blob Storage.")
    st.stop()

selected_prompt_txt = st.selectbox("Select Persona:", all_prompt_files)
# 2. Load data for that prompt
llm_analysis = azure_storage.list_llmanalysis(selected_prompt_txt)
# Parse the JSON input
all_jsons = []
if llm_analysis:
    for file in llm_analysis:
        try:
            data = azure_storage.read_llm_analysis(selected_prompt_txt, file)
            all_jsons.append(data)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

# Aggregate all JSON data
if len(all_jsons) == 0:
    st.warning("⚠️  No Persona or calls have been analyzed yet.")
    st.stop()

aggregated = aggregate_data(all_jsons)

# Create tabs for each key
keys = list(aggregated.keys())
tabs = st.tabs(keys)

for i, key in enumerate(keys):
    values = aggregated[key]
    with tabs[i]:

        # Classification
        numeric_values = [v for v in values if is_numeric(v)]
        bool_candidates = [v for v in values if can_be_boolean(v)]

        # 1) All numeric?
        if len(numeric_values) == len(values):
               # Convert list to a NumPy array of ints
            arr = np.array(numeric_values, dtype=int)
            
            # Get unique values and their counts
            unique_vals, counts = np.unique(arr, return_counts=True)
            
            # Prepare a DataFrame
            chart_data = pd.DataFrame({
                "Value": unique_vals,
                "Count": counts
            })
            
            # Create an Altair bar chart with a different color for each bin
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Value:O', title=to_string(key)),
                y=alt.Y('Count:Q', title='Count'),
                # Using the 'Value' field to assign colors
                color=alt.Color('Value:N', scale=alt.Scale(scheme='category10'))
            ).properties(
                width=600,
                height=400
            )
            
            # Display the chart in Streamlit
            st.altair_chart(chart, use_container_width=True)
        elif len(bool_candidates) == len(values):
            actual_bool_values = [coerce_to_boolean(v) for v in values]
            true_count = sum(actual_bool_values)
            false_count = len(actual_bool_values) - true_count

            st.write(f"**True (Yes)**: {true_count}, **False (No)**: {false_count}")

            # Create a small DataFrame for the bar chart
            df_bool = pd.DataFrame({
                "Category": ["True", "False"],
                "Count": [true_count, false_count]
            })
            st.bar_chart(data=df_bool, x="Category", y="Count")

        # 3) Otherwise, treat as text
        else:
            insights = get_insights_cached(values)
            st.write(insights)
            st.write("---")

# -------------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------------
st.markdown("""
    ---
    *Dashboard last updated: {}*
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
