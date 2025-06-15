# src/api_test_gui.py

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
from ui.collections import render_collections_tab, render_edit_collection
from ui.components.common import show_welcome_screen


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
    if "collections" not in st.session_state:
        st.session_state.collections = []
    if "executions" not in st.session_state:
        st.session_state.executions = []
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = None
    # Initialize flags for collection operations
    if "collection_to_run" not in st.session_state:
        st.session_state.collection_to_run = None
    if "collection_to_edit" not in st.session_state:
        st.session_state.collection_to_edit = None
    if "trigger_collection_creation" not in st.session_state:
        st.session_state.trigger_collection_creation = False
    if "create_collection_request" not in st.session_state:
        st.session_state.create_collection_request = None


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

    # Check if we need to show the collection edit form
    if st.session_state.active_tab == "collections_edit":
        render_edit_collection()
        return

    # Check if we need to run tests for a collection
    if st.session_state.collection_to_run:
        from ui.collections import run_collection_tests
        import asyncio
        from core.services.test_execution_service import TestExecutionService

        collection = st.session_state.collection_to_run

        with st.spinner(f"Running tests for collection '{collection.name}'..."):
            try:
                # Run the tests
                results = asyncio.run(run_collection_tests(collection))

                # Save the execution
                execution_service = TestExecutionService()
                execution = asyncio.run(
                    execution_service.create_execution(
                        collection_id=collection.id,
                        collection_name=collection.name,
                        reports=results,
                    )
                )

                # Update execution history
                st.session_state.executions = asyncio.run(
                    execution_service.get_all_executions()
                )

                # Store in test results for immediate viewing
                st.session_state.test_results = results

                # Clear the collection to run
                st.session_state.collection_to_run = None

                # Show success message
                st.success(f"Tests completed for collection '{collection.name}'!")

                # Switch to test results tab
                st.session_state.active_tab = "testing"
                st.rerun()

            except Exception as e:
                st.error(f"Error running tests: {str(e)}")
                st.session_state.collection_to_run = None

    # Main content - Tabs for different functionality
    tab1, tab2, tab3 = st.tabs(["🔍 API Explorer", "🧪 API Testing", "📚 Collections"])

    # Tab 1: API Explorer - Test individual endpoints
    with tab1:
        render_explorer_tab()

    # Tab 2: API Testing - Run batch tests
    with tab2:
        render_tester_tab()

    # Tab 3: Collections - Manage test collections
    with tab3:
        render_collections_tab()


if __name__ == "__main__":
    main()
