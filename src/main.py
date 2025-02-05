import streamlit as st

st.set_page_config(
    page_title="Nida, understand your calls",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
        @media (prefers-color-scheme: light) {
            :root {
            /* -- Base Colors for Light Mode -- */
            --color-bg-primary: #ffffff;          /* e.g., detailed headers, explanation box */
            --color-bg-secondary: #f8f8f8;        /* e.g., parameter-card, transcript container */
            --color-bg-tertiary: #fafafa;         /* a third tier if needed */
            --color-border: #dddddd;
            --color-text-primary: #000000;
            --color-text-secondary: #333333;
            --color-link: #0066cc;
            --color-link-hover: #004999;
            
            /* -- Special Themed Elements -- */
            --color-match-bg: #d1fae5;
            --color-match-text: #065f46;
            --color-match-border: #10b981;

            --color-mismatch-bg: #fee2e2;
            --color-mismatch-text: #b91c1c;
            --color-mismatch-border: #f87171;

            --color-focus: #3b82f6; /* used for highlighting or active states */
            
            /* -- Scrollbar Colors (Light) -- */
            --scrollbar-track: #f0f0f0;
            --scrollbar-thumb: #cccccc;
            --scrollbar-thumb-hover: #bbbbbb;
        }
    }

    @media (prefers-color-scheme: dark) {
      :root {
          /* -- Base Colors for Dark Mode -- */
          --color-bg-primary: #1e1e1e;
          --color-bg-secondary: #2d2d2d;
          --color-bg-tertiary: #333333;
          --color-border: #404040;
          --color-text-primary: #ffffff;
          --color-text-secondary: #e5e5e5;
          --color-link: #3b82f6;
          --color-link-hover: #60a5fa;

          /* -- Special Themed Elements -- */
          --color-match-bg: #1a422b;
          --color-match-text: #4ade80;
          --color-match-border: #4ade80;

          --color-mismatch-bg: #422a2a;
          --color-mismatch-text: #f87171;
          --color-mismatch-border: #f87171;

          --color-focus: #3b82f6; /* same as above, if you want it uniform */

          /* -- Scrollbar Colors (Dark) -- */
          --scrollbar-track: #1e1e1e;
          --scrollbar-thumb: #404040;
          --scrollbar-thumb-hover: #4a4a4a;
      }
    }

    /* ===== Main App Structure ===== */
    [data-testid="stAppViewContainer"] {
        background-color: var(--primary-bg) !important;
        color: var(--primary-text) !important;
        transition: background-color 0.3s ease, color 0.3s ease;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--hover-effect);
    }

    [data-testid="stSidebar"] {
        background-color: var(--secondary-bg) !important;
        color: var(--primary-text) !important;
        border-right: 1px solid var(--hover-effect);
        box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
    }

    /* ===== Typography ===== */
    .title-text {
        font-size: 2.4em;
        font-weight: 700;
        margin-bottom: 0.4em;
        color: var(--accent-1);
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
        letter-spacing: -0.5px;
    }

    .subtitle-text {
        font-size: 1.2em;
        color: var(--secondary-text);
        margin-bottom: 1.2em;
        line-height: 1.4;
    }

    /* ===== Interactive Elements ===== */
    button {
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }

    /* ===== Scrollbar Styling ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--primary-bg);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--secondary-text);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-1);
    }

     /* Buttons */
    .stButton > button {
        background-color: var(--color-bg-secondary) !important;
        color: var(--color-text-primary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.5rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: var(--color-focus) !important;
        border-color: var(--color-focus) !important;
    }

    /* Select Boxes */
    .stSelectbox [data-baseweb="select"] {
        background-color: var(--color-bg-secondary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.5rem !important;
        color: var(--color-text-primary) !important;
    }

    /* Text Areas */
    .stTextArea textarea {
        background-color: var(--color-bg-primary) !important;
        color: var(--color-text-primary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.5rem !important;
    }

    /* Alerts and Info Boxes */
    .stAlert {
        background-color: var(--color-bg-secondary) !important;
        color: var(--color-text-primary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.5rem !important;
    }

    /* Code Blocks */
    .stCodeBlock {
        background-color: var(--color-bg-primary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.5rem !important;
        color: var(--color-text-primary) !important;
    }

    /* Metrics (these class names may vary depending on Streamlit versions) */
    .css-1r6slb0 {
        background-color: var(--color-bg-secondary) !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 0.75rem !important;
        padding: 1rem !important;
    }
    .css-1r6slb0 label {
        color: var(--color-text-secondary) !important;
    }
    .css-1r6slb0 .css-1wivap2 {
        color: var(--color-text-primary) !important;
    }

    /* Header Text */
    h1, h2, h3, h4, h5, h6 {
        color: var(--color-text-primary) !important;
    }

    /* General Text */
    p, span, div {
        color: var(--color-text-secondary);
    }

    /* Links */
    a {
        color: var(--color-link) !important;
        text-decoration: none;
    }
    a:hover {
        color: var(--color-link-hover) !important;
        text-decoration: underline;
    }

     /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--color-bg-primary);
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--color-bg-secondary);
        border-radius: 0.5rem;
        border: 1px solid var(--color-border);
        color: var(--color-text-primary);
        padding: 0.5rem 1rem;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--color-bg-tertiary);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--color-focus);
        border-color: var(--color-focus);
    }

    </style>
    """,
    unsafe_allow_html=True
)

pg = st.navigation([
    st.Page("1_calls.py", title="Calls Management", icon="📞"),
    st.Page("2_personas.py", title="Personas and GenAI", icon="👥"),
    st.Page("3_summary.py", title="Summary", icon="📈"),
    st.Page("4_details.py", title="Details", icon="📊"),
    st.Page("5_chat.py", title="Chat With your Calls", icon="💬"),
    st.Page("6_configuration.py", title="Configuration", icon="⚙️"),
    st.Page("7_advanced.py", title="Advanced", icon="📈"),
    st.Page("8_diagnostics.py", title="Diagnostics", icon="🔍"),
])
pg.run()
