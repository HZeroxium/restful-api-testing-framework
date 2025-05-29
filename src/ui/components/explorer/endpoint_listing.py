"""Endpoint listing component for the API Explorer."""

import streamlit as st
from ui.components.common import show_endpoint_card


def render_endpoint_listing():
    """Render the listing of available API endpoints."""
    if not st.session_state.endpoints:
        return

    # Group endpoints by tags or paths for better organization
    endpoints_by_path = {}
    for endpoint in st.session_state.endpoints:
        path_base = (
            endpoint.path.split("/")[1]
            if len(endpoint.path.split("/")) > 1
            else "other"
        )
        if path_base not in endpoints_by_path:
            endpoints_by_path[path_base] = []
        endpoints_by_path[path_base].append(endpoint)

    # Create expandable sections for each group
    for path_group, group_endpoints in endpoints_by_path.items():
        with st.expander(
            f"{path_group.capitalize()} ({len(group_endpoints)} endpoints)"
        ):
            for endpoint in group_endpoints:
                # Create a card for each endpoint
                show_endpoint_card(endpoint)

                # Action buttons
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button(
                        "Test Endpoint",
                        key=f"test_{endpoint.method}_{endpoint.path}",
                    ):
                        st.session_state.selected_endpoint = endpoint

                with col2:
                    if st.button(
                        "View Details",
                        key=f"details_{endpoint.method}_{endpoint.path}",
                    ):
                        st.session_state.view_endpoint_details = endpoint
