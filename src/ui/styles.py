# ui/styles.py

"""CSS styles for the API Testing Platform."""

import streamlit as st


def apply_styles():
    """Apply CSS styles to the application."""
    st.markdown(
        """
        <style>
        /* Main app styles */
        .main {
            background-color: #f9f9f9;
        }
        
        /* Method badges */
        .method-badge {
            display: inline-block;
            padding: 3px 6px;
            border-radius: 4px;
            color: white;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            margin-right: 8px;
        }
        .get-badge { background-color: #28a745; }
        .post-badge { background-color: #007bff; }
        .put-badge { background-color: #fd7e14; }
        .delete-badge { background-color: #dc3545; }
        .patch-badge { background-color: #6f42c1; }
        .options-badge { background-color: #20c997; }
        .head-badge { background-color: #6c757d; }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 3px 6px;
            border-radius: 4px;
            color: white;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            margin-right: 8px;
        }
        .status-pass { background-color: #28a745; }
        .status-fail { background-color: #dc3545; }
        .status-error { background-color: #fd7e14; }
        .status-skipped { background-color: #6c757d; }
        
        /* API endpoint cards */
        .endpoint-card {
            display: flex;
            align-items: center;
            padding: 5px 0;
            margin-bottom: 5px;
        }
        .endpoint-path {
            font-family: monospace;
            font-size: 1rem;
        }

        /* Tags */
        .tag-container {
            margin: 5px 0;
        }
        .tag {
            display: inline-block;
            background-color: #e9ecef;
            border-radius: 20px;
            padding: 2px 8px;
            margin-right: 4px;
            font-size: 0.8rem;
            color: #495057;
        }
        
        /* Test result cards */
        .test-result-card {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #ccc;
        }
        .pass-card { border-left-color: #28a745; background-color: rgba(40, 167, 69, 0.1); }
        .fail-card { border-left-color: #dc3545; background-color: rgba(220, 53, 69, 0.1); }
        .error-card { border-left-color: #fd7e14; background-color: rgba(253, 126, 20, 0.1); }
        
        /* Validation results */
        .validation-item {
            margin: 5px 0;
            padding: 8px 10px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .validation-pass { background-color: rgba(40, 167, 69, 0.1); }
        .validation-fail { background-color: rgba(220, 53, 69, 0.1); }
        .validation-error { background-color: rgba(253, 126, 20, 0.1); }
        
        /* Constraint items */
        .constraint-item {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            position: relative;
        }
        .info-constraint { background-color: rgba(13, 110, 253, 0.1); border-left: 4px solid #0d6efd; }
        .warning-constraint { background-color: rgba(255, 193, 7, 0.1); border-left: 4px solid #ffc107; }
        .error-constraint { background-color: rgba(220, 53, 69, 0.1); border-left: 4px solid #dc3545; }
        
        .constraint-type {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 0.8rem;
            font-weight: 500;
            padding: 2px 6px;
            border-radius: 4px;
            background-color: rgba(0, 0, 0, 0.1);
        }
        
        .constraint-severity {
            font-size: 0.7rem;
            font-weight: 500;
            padding: 1px 5px;
            border-radius: 3px;
            margin-left: 8px;
            text-transform: uppercase;
            background-color: rgba(0, 0, 0, 0.1);
        }
        
        .constraint-description {
            margin-top: 5px;
        }
        
        /* Summary card */
        .summary-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        }
        
        .metric-row {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric-card {
            flex: 1;
            text-align: center;
            background-color: #f8f9fa;
            padding: 15px 10px;
            border-radius: 6px;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #6c757d;
        }
        
        /* JSON viewer */
        .json-viewer {
            background-color: #f8f9fa;
            border-radius: 4px;
            padding: 15px;
            font-family: monospace;
            white-space: pre-wrap;
            overflow-x: auto;
        }

        /* New styles for validation script display */
        .validation-code-section {
            margin: 5px 0;
            border: 1px solid #e9ecef;
            border-radius: 5px;
            background-color: #f8f9fa;
        }
        
        .validation-header {
            padding: 8px 10px;
            background-color: #f1f3f5;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 5px 5px 0 0;
        }
        
        .validation-title {
            font-weight: 500;
            font-size: 0.95rem;
        }
        
        .validation-type {
            font-size: 0.8rem;
            color: #6c757d;
            padding: 2px 6px;
            background-color: #e9ecef;
            border-radius: 4px;
        }
        
        .validation-content {
            padding: 10px;
        }

        .stButton > button {
            width: 100%;
        }        
        </style>
        """,
        unsafe_allow_html=True,
    )
