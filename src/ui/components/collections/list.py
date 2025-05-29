"""Component for listing and viewing collection details."""

import asyncio
import streamlit as st
import pandas as pd

from .utils import load_collections, collection_service
from ui.components.common.badges import render_method_badge


def render_collections_list():
    """Render the list of collections and detail views."""
    st.markdown("### All Test Collections")

    # Load collections
    if st.button("Refresh Collections"):
        st.session_state.collections = asyncio.run(load_collections())

    if "collections" not in st.session_state:
        st.session_state.collections = asyncio.run(load_collections())

    collections = st.session_state.collections

    if not collections:
        st.info("No test collections found. Create a new collection to get started.")
        return

    # Display collections in a searchable table
    collection_data = []
    for collection in collections:
        endpoint_count = sum(len(suite.test_cases) for suite in collection.test_suites)
        collection_data.append(
            {
                "ID": collection.id,
                "Name": collection.name,
                "API": (
                    f"{collection.api_name} v{collection.api_version}"
                    if collection.api_name
                    else "-"
                ),
                "Endpoints": len(collection.test_suites),
                "Test Cases": endpoint_count,
                "Last Updated": collection.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    df = pd.DataFrame(collection_data)

    # Add search and filtering
    search_term = st.text_input("🔍 Search collections", "")
    if search_term:
        df = df[
            df["Name"].str.contains(search_term, case=False)
            | df["API"].str.contains(search_term, case=False)
        ]

    # Display table with selectable rows
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "ID": None,  # Hide ID column
        },
        hide_index=True,
    )

    # Collection details and actions
    st.markdown("### Collection Details")

    # Choose a collection to view details
    collection_options = {c.id: c.name for c in collections}
    selected_collection_id = st.selectbox(
        "Select a collection",
        options=list(collection_options.keys()),
        format_func=lambda x: collection_options[x],
    )

    if selected_collection_id:
        selected_collection = next(
            (c for c in collections if c.id == selected_collection_id), None
        )

        if selected_collection:
            _render_collection_details(selected_collection)


def _render_collection_details(selected_collection):
    """Render detailed information for a selected collection.

    Args:
        selected_collection: The collection to display details for
    """
    # Display collection details
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown(f"**Name:** {selected_collection.name}")
    with col2:
        st.markdown(
            f"**API:** {selected_collection.api_name or '-'} v{selected_collection.api_version or '-'}"
        )
    with col3:
        st.markdown(
            f"**Created:** {selected_collection.created_at.strftime('%Y-%m-%d')}"
        )

    if selected_collection.description:
        st.markdown(f"**Description:** {selected_collection.description}")

    # Display test suites
    st.markdown("#### Test Suites")
    for i, suite in enumerate(selected_collection.test_suites):
        endpoint = suite.endpoint_info
        method = endpoint.method.upper()
        path = endpoint.path

        st.markdown(
            f"""
            <div class="endpoint-card {method.lower()}-method">
                {render_method_badge(method)}
                <strong>{path}</strong> ({len(suite.test_cases)} test cases)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show endpoint constraints if needed
        endpoint_key = f"{endpoint.method}_{endpoint.path}"
        if (
            "endpoint_constraints" in st.session_state
            and endpoint_key in st.session_state.endpoint_constraints
        ):
            with st.expander("View Endpoint Constraints"):
                constraints = st.session_state.endpoint_constraints[endpoint_key]

                from ui.components.common.constraints import show_constraints_section

                # Show request-response constraints
                show_constraints_section(
                    constraints["request_response"],
                    "Request-Response Constraints",
                )

                # Show response property constraints
                show_constraints_section(
                    constraints["response_property"],
                    "Response Property Constraints",
                )

        # Show test cases in an expander
        with st.expander(f"View Test Cases for {method} {path}"):
            _render_test_cases(suite.test_cases)

    # Actions for the collection
    _render_collection_actions(selected_collection)


def _render_test_cases(test_cases):
    """Render test cases list for a test suite.

    Args:
        test_cases: List of test cases to display
    """
    for j, test_case in enumerate(test_cases):
        st.markdown(f"##### {test_case.name}")
        st.markdown(f"- **Description:** {test_case.description}")
        # Display with better formatting
        status_color = "green" if 200 <= test_case.expected_status_code < 300 else "red"
        st.markdown(
            f"- **Expected Status:** <span style='color:{status_color};'>{test_case.expected_status_code}</span>",
            unsafe_allow_html=True,
        )

        # Show validation scripts in a dropdown
        if hasattr(test_case, "validation_scripts") and test_case.validation_scripts:
            with st.expander(
                f"View Validation Scripts ({len(test_case.validation_scripts)})"
            ):
                for script in test_case.validation_scripts:
                    from ui.components.common.validation import (
                        show_validation_script_details,
                    )

                    show_validation_script_details(script)


def _render_collection_actions(selected_collection):
    """Render action buttons for a collection.

    Args:
        selected_collection: The collection to render actions for
    """
    st.markdown("#### Actions")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button(
            "Run Tests",
            key=f"list_run_collection_{selected_collection.id}",
        ):
            st.session_state.collection_to_run = selected_collection
            st.rerun()  # To update the UI

    with col2:
        if st.button(
            "Edit Collection",
            key=f"list_edit_collection_{selected_collection.id}",
        ):
            st.session_state.collection_to_edit = selected_collection
            st.session_state.active_tab = "collections_edit"
            st.rerun()  # To update the UI

    with col3:
        if st.button(
            "Delete Collection",
            key=f"list_delete_collection_{selected_collection.id}",
        ):
            if asyncio.run(
                collection_service.delete_collection(selected_collection.id)
            ):
                st.success(
                    f"Collection '{selected_collection.name}' deleted successfully!"
                )
                # Refresh collections
                st.session_state.collections = asyncio.run(load_collections())
                st.rerun()  # To update the UI
            else:
                st.error("Failed to delete collection.")
