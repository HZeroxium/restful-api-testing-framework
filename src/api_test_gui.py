"""
API Testing Platform GUI Application.

This is the main entry point for the API Testing Platform GUI,
which allows testing and exploring REST APIs from OpenAPI specifications.
"""

import streamlit as st

# Import our UI components
from ui.styles import apply_styles
from ui.sidebar import render_sidebar
from ui.explorer import render_explorer_tab
from ui.tester import render_tester_tab
from ui.components import show_welcome_screen


# Initialize session state
def init_session_state():
    """Initialize the session state with default values."""
    if "api_info" not in st.session_state:
        st.session_state.api_info = None
    if "endpoints" not in st.session_state:
        st.session_state.endpoints = []
    if "factory" not in st.session_state:
        st.session_state.factory = None
    if "endpoint_tools" not in st.session_state:
        st.session_state.endpoint_tools = {}
    if "test_results" not in st.session_state:
        st.session_state.test_results = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None


def main():
    """Main function to run the Streamlit application."""
    # Set page configuration
    st.set_page_config(
        page_title="API Testing Platform",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply CSS styles
    apply_styles()

    # Initialize session state
    init_session_state()

    # Header
    st.markdown("# 🧪 API Testing Platform")

    # Sidebar
    render_sidebar()

    # If no API is loaded, show welcome screen
    if not st.session_state.api_info:
        show_welcome_screen()
        return

    # Main content - Tabs for different functionality
    tab1, tab2 = st.tabs(["🔍 API Explorer", "🧪 API Testing"])

    # Tab 1: API Explorer - Test individual endpoints
    with tab1:
        render_explorer_tab()

    # Tab 2: API Testing - Run batch tests
    with tab2:
        render_tester_tab()


if __name__ == "__main__":
    main()
