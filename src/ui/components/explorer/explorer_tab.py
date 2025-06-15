"""Explorer tab component for the API Testing Platform."""

import streamlit as st
from ui.components.explorer.endpoint_listing import render_endpoint_listing
from ui.components.explorer.endpoint_details import render_endpoint_details
from ui.components.explorer.test_form import render_endpoint_test_form
from ui.components.explorer.response_viewer import render_api_response
from ui.components.explorer.test_results import render_explorer_test_results


def render_explorer_tab():
    """Render the API Explorer tab."""
    st.markdown("## API Explorer")
    st.markdown("Select an endpoint to test and provide parameters or request body.")

    if not st.session_state.endpoints:
        st.info("No endpoints available. Please load an API specification first.")
        return

    # Render the endpoint listing component
    render_endpoint_listing()

    # Show endpoint details if requested
    render_endpoint_details()

    # Show form for testing endpoint if selected
    render_endpoint_test_form()

    # Show API response if available
    render_api_response()

    # Show test results if available
    render_explorer_test_results()
