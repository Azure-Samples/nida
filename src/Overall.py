import streamlit as st
import pandas as pd
import altair as alt
import glob
from datetime import datetime
from services import azure_storage, azure_evals

st.markdown("""
    <style>
    /* Main Container */
    .main {
        padding: 2rem;
        background-color: #121212;
        min-height: 100vh;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #2d2d2d;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #404040;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        margin-bottom: 1rem;
        color: #ffffff;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.3);
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: 1px solid #404040 !important;
        border-radius: 0.5rem !important;
        padding: 0.75rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
        transform: translateY(-1px);
    }

   
    .metric-label {
        color: #e5e5e5;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }

    .metric-trend-positive {
        color: #4ade80;
        font-size: 0.875rem;
    }

    .metric-trend-negative {
        color: #f87171;
        font-size: 0.875rem;
    }


    /* Charts and Graphs Container */
    .chart-container {
        background-color: #2d2d2d;
        border-radius: 0.75rem;
        padding: 1.5rem;
        border: 1px solid #404040;
        margin: 1rem 0;
    }

    /* Data Tables */
    .dataframe {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
    }

    .dataframe th {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        padding: 0.75rem !important;
        font-weight: 600 !important;
    }

    .dataframe td {
        background-color: #2d2d2d !important;
        color: #e5e5e5 !important;
        padding: 0.75rem !important;
    }

    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }

    .tooltip .tooltiptext {
        visibility: hidden;
        background-color: #1e1e1e;
        color: #ffffff;
        text-align: center;
        padding: 0.5rem;
        border-radius: 0.5rem;
        border: 1px solid #404040;
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

    /* Status Indicators */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .status-success {
        background-color: #1a422b;
        color: #4ade80;
        border: 1px solid #4ade80;
    }

    .status-warning {
        background-color: #422f1a;
        color: #fbbf24;
        border: 1px solid #fbbf24;
    }

    .status-error {
        background-color: #422a2a;
        color: #f87171;
        border: 1px solid #f87171;
    }

    /* Sidebar Customization */
    .css-1d391kg {  /* Sidebar */
        background-color: #1e1e1e;
    }

    .css-1d391kg .block-container {
        padding: 2rem 1rem;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #1e1e1e;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: #404040;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #4a4a4a;
    }
    </style>
""", unsafe_allow_html=True)


# --- Title and Intro ---
st.title("🎯 AI Performance Analytics Dashboard")
st.markdown("""
    <div style='background-color: #2d2d2d; padding: 1rem; border-radius: 0.5rem; margin-bottom: 2rem;'>
        <h4>Executive Summary</h4>
        This dashboard provides real-time insights into AI model performance against ground truth data, 
        highlighting key metrics and trends for strategic decision-making.
    </div>
""", unsafe_allow_html=True)



# 1. List all .txt prompt files in the PROMPTS_CONTAINER
all_prompt_files = azure_storage.list_prompts()

if not all_prompt_files:
    st.error("⚠️ No prompt .txt files found in Blob Storage.")
    st.stop()

selected_prompt_txt = st.sidebar.selectbox(
    "Select Prompt:",
    all_prompt_files
)

# 2. Load data for that prompt
df, parameters = azure_evals.load_and_prepare_data(selected_prompt_txt)

if df.empty:
    st.warning("No matching AI/Eval data found for this prompt.")
    st.stop()


metrics = azure_evals.calculate_metrics(df, parameters)

# -------------------------------------------------------------------------
# Executive Summary Section
# -------------------------------------------------------------------------
st.header("📊 Performance Overview")

col1, col2, col3 = st.columns(3)

# Overall accuracy: average of parameter accuracies
if metrics:
    overall_accuracy = sum(m["accuracy"] for m in metrics.values()) / len(metrics)
else:
    overall_accuracy = 0

with col1:
    st.metric(
        "Overall Accuracy",
        f"{overall_accuracy:.1f}%",
        delta_color="normal"
    )

with col2:
    if metrics:
        best_param = max(metrics.items(), key=lambda x: x[1]["accuracy"])[0]
        st.metric(
            "Best Performing Parameter",
            best_param,
            f"{metrics[best_param]['accuracy']:.1f}%"
        )
    else:
        st.metric("Best Performing Parameter", "N/A")

with col3:
    total_calls = len(df)
    st.metric("Total Analyzed Calls", f"{total_calls:,}")

# -------------------------------------------------------------------------
# Detailed Performance Metrics
# -------------------------------------------------------------------------
st.header("📈 Detailed Performance Metrics")

if metrics:
    param_comparison = pd.DataFrame({
        "Parameter": list(metrics.keys()),
        "Accuracy (%)": [m["accuracy"] for m in metrics.values()],
        "Precision (%)": [m["precision"] for m in metrics.values()],
    })
    
    chart = alt.Chart(param_comparison).transform_fold(
        ["Accuracy (%)", "Precision (%)"],
        as_=["Metric", "Value"]
    ).mark_bar().encode(
        x=alt.X("Parameter:N", title=None),
        y=alt.Y("Value:Q", title="Percentage"),
        color=alt.Color("Metric:N", scale=alt.Scale(scheme="set2")),
        column=alt.Column("Metric:N", title=None)
    ).properties(
        width=300
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    )
    
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No metrics computed because no parameters matched.")

# -------------------------------------------------------------------------
# Drill-Down Analysis
# -------------------------------------------------------------------------
st.header("🔍 Parameter Deep Dive")

if parameters:
    selected_param = st.selectbox("Select Parameter for Detailed Analysis:", parameters)
    
    # Confusion Matrix
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Confusion Matrix")
        # Build confusion matrix based on ground truth vs. AI
        param_gt = df[selected_param].fillna("").str.lower()
        param_ai = df[f"{selected_param} - Score"].fillna("").str.lower()
        
        confusion = pd.crosstab(param_gt, param_ai, margins=True)
        st.dataframe(confusion.style.highlight_max(axis=1))
    
    with col2:
        st.subheader("Key Insights")
        m = metrics.get(selected_param, {})
        accuracy = m.get("accuracy", 0)
        precision = m.get("precision", 0)
        st.markdown(f"""
            * **Accuracy**: {accuracy:.1f}%
            * **Precision**: {precision:.1f}%
            * **Total Calls**: {m.get("total", 0):,}
            * **Correct Predictions**: {m.get("matches", 0):,}
        """)
    
    # ---------------------------------------------------------------------
    # Error Analysis
    # ---------------------------------------------------------------------
    st.header("⚠️ Error Analysis")
    mismatches = df[param_gt != param_ai]  # or we can recalc
    
    if not mismatches.empty:
        st.markdown(f"**Showing {len(mismatches)} mismatched predictions for '{selected_param}':**")
        # We'll display the columns relevant to this parameter
        # e.g. Ground Truth (selected_param), AI Prediction, Explanation
        st.dataframe(
            mismatches[[
                "Call ID",
                selected_param,
                f"{selected_param} - Score",
                f"{selected_param} - Explanation"
            ]].rename(columns={
                selected_param: "Ground Truth",
                f"{selected_param} - Score": "AI Prediction",
                f"{selected_param} - Explanation": "AI Explanation"
            })
        )
    else:
        st.success("No mismatches found for this parameter! 🎉")
else:
    st.info("No parameters found in config.")

# -------------------------------------------------------------------------
# Recommendations
# -------------------------------------------------------------------------
st.header("💡 Recommendations")
if overall_accuracy < 90:
    st.warning("""
        * Consider reviewing AI model training data for potential biases
        * Implement additional validation steps for low-confidence predictions
        * Schedule regular model retraining with recent data
    """)
else:
    st.success("""
        * Current model performance meets or exceeds expectations
        * Continue monitoring for any performance degradation
        * Consider expanding to additional parameters
    """)

# -------------------------------------------------------------------------
# Export Options
# -------------------------------------------------------------------------
st.header("📥 Export Options")
col1, col2 = st.columns(2)

with col1:
    if st.button("Download Full Report (CSV)"):
        csv_str = df.to_csv(index=False)
        st.download_button(
            label="Click to Download",
            data=csv_str,
            file_name=f"ai_analysis_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col2:
    if st.button("Generate Executive Summary (PDF)"):
        st.info("Feature coming soon! 🚀")

# -------------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------------
st.markdown("""
    ---
    *Dashboard last updated: {}*
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))