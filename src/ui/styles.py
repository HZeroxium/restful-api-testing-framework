"""CSS styles for the API Testing Platform UI."""

# Main CSS style definition for the entire application
MAIN_STYLE = """
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e6f0ff;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4c78e0 !important;
        color: white !important;
    }
    .endpoint-card {
        padding: 12px;
        border-radius: 5px;
        margin-bottom: 10px;
        background-color: white;
        border-left: 5px solid #4c78e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .get-method { border-left: 5px solid #61affe; }
    .post-method { border-left: 5px solid #49cc90; }
    .put-method { border-left: 5px solid #fca130; }
    .delete-method { border-left: 5px solid #f93e3e; }
    .patch-method { border-left: 5px solid #50e3c2; }
    
    .method-badge {
        padding: 4px 8px;
        border-radius: 3px;
        color: white;
        font-weight: bold;
        display: inline-block;
        font-size: 12px;
    }
    .get-badge { background-color: #61affe; }
    .post-badge { background-color: #49cc90; }
    .put-badge { background-color: #fca130; }
    .delete-badge { background-color: #f93e3e; }
    .patch-badge { background-color: #50e3c2; }
    
    .test-result-card {
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        background-color: white;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1);
    }
    .pass-card { border-left: 5px solid #49cc90; }
    .fail-card { border-left: 5px solid #f93e3e; }
    .error-card { border-left: 5px solid #ff9800; }
    
    .validation-item {
        padding: 10px;
        border-radius: 3px;
        margin-top: 8px;
    }
    .validation-pass { background-color: #e6ffec; }
    .validation-fail { background-color: #ffebe9; }
    .validation-error { background-color: #fff8e6; }
    
    .status-badge {
        padding: 3px 6px;
        border-radius: 3px;
        color: white;
        font-weight: bold;
        font-size: 11px;
    }
    .status-pass { background-color: #28a745; }
    .status-fail { background-color: #dc3545; }
    .status-error { background-color: #fd7e14; }
    .status-skipped { background-color: #6c757d; }
    
    .summary-card {
        background-color: white;
        border-radius: 5px;
        padding: 20px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    .json-viewer {
        background-color: #1e1e1e;
        border-radius: 5px;
        padding: 15px;
        color: #dcdcdc;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
        margin-top: 10px;
    }
    
    /* Custom metric styles */
    .metric-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 10px;
    }
    .metric-card {
        flex: 1;
        min-width: 120px;
        background-color: white;
        padding: 12px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 12px;
        color: #666;
        text-transform: uppercase;
    }
</style>
"""


def apply_styles():
    """Apply the CSS styles to the Streamlit app."""
    import streamlit as st

    st.markdown(MAIN_STYLE, unsafe_allow_html=True)
