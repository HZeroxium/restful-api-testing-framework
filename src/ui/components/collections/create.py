"""Component for creating new test collections."""

import asyncio
import streamlit as st

from .utils import load_collections, collection_service
from schemas.test_collection import TestCollectionModel


def render_collection_creation():
    """Render the form for creating a new test collection."""
    st.markdown("### Create New Test Collection")

    # Initialize selection state if not exists
    if "selected_endpoints" not in st.session_state:
        st.session_state.selected_endpoints = []

    # Check if API loaded
    if not st.session_state.endpoints:
        st.warning("Please load an API specification first to create a collection.")
        return

    # Collection form
    with st.form("create_collection_form"):
        col1, col2 = st.columns([2, 1])

        with col1:
            name = st.text_input("Collection Name", "")

        with col2:
            test_case_count = st.number_input(
                "Tests per Endpoint", min_value=1, max_value=5, value=2
            )

        description = st.text_area("Description", "")

        # Tags
        tags_input = st.text_input("Tags (comma-separated)", "")
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        # Endpoint selection
        st.markdown("### Select Endpoints")

        # Group endpoints by tags or paths for better organization
        endpoints_by_path = _group_endpoints_by_path()

        # Create expandable sections for each group
        selected_endpoints = []

        for path_group, group_endpoints in endpoints_by_path.items():
            with st.expander(
                f"{path_group.capitalize()} ({len(group_endpoints)} endpoints)"
            ):
                # Use vertical arrangement to make selection clearer
                st.write("Select endpoints to include in the collection:")

                # Use a more efficient selection mechanism
                all_endpoints_in_group = [
                    f"{endpoint.method.upper()} {endpoint.path}"
                    for endpoint in group_endpoints
                ]

                # Create checkboxes with improved layout
                cols = st.columns(2)
                for i, endpoint in enumerate(group_endpoints):
                    with cols[i % 2]:
                        endpoint_key = f"{endpoint.method.upper()}_{endpoint.path}"
                        selected = st.checkbox(
                            f"{endpoint.method.upper()} {endpoint.path}",
                            key=f"create_endpoint_{endpoint_key}",
                        )
                        if selected:
                            selected_endpoints.append(endpoint)

        # Include invalid test data
        include_invalid = st.checkbox("Include Invalid Test Data", value=True)

        submitted = st.form_submit_button("Create Collection")

        if submitted:
            # Validate inputs
            if not name:
                st.error("Please enter a collection name.")
                return

            if not selected_endpoints:
                st.error("Please select at least one endpoint.")
                return

            # Create test suites (we'll do this asynchronously)
            if "api_info" in st.session_state and st.session_state.api_info:
                # Store creation request in session state
                st.session_state.create_collection_request = {
                    "name": name,
                    "description": description,
                    "endpoints": selected_endpoints,
                    "test_case_count": test_case_count,
                    "include_invalid": include_invalid,
                    "tags": tags,
                    "api_name": st.session_state.api_info["title"],
                    "api_version": st.session_state.api_info["version"],
                }

                # Flag to trigger async creation
                st.session_state.trigger_collection_creation = True
                st.rerun()

    # Handle async collection creation if triggered
    if st.session_state.get("trigger_collection_creation", False):
        _handle_collection_creation()


def _group_endpoints_by_path():
    """Group endpoints by their base path for better organization.

    Returns:
        Dictionary with path groups as keys and lists of endpoints as values
    """
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
    return endpoints_by_path


def _handle_collection_creation():
    """Handle the asynchronous creation of a test collection."""
    create_request = st.session_state.create_collection_request

    with st.spinner("Creating test collection..."):
        # Process this asynchronously
        from tools.core.test_collection_generator import TestCollectionGeneratorTool
        from schemas.tools.test_collection_generator import (
            TestCollectionGeneratorInput,
        )

        # Create a test collection generator tool
        tool = TestCollectionGeneratorTool(verbose=False)

        # Create input
        input_data = TestCollectionGeneratorInput(
            api_name=create_request["api_name"],
            api_version=create_request["api_version"],
            endpoints=create_request["endpoints"],
            test_case_count=create_request["test_case_count"],
            include_invalid_data=create_request["include_invalid"],
        )

        try:
            # Execute the tool
            result = asyncio.run(tool.execute(input_data))

            # Create the collection model
            collection = TestCollectionModel(
                name=create_request["name"],
                description=create_request["description"],
                test_suites=result.test_collection.test_suites,
                api_name=create_request["api_name"],
                api_version=create_request["api_version"],
                tags=create_request["tags"],
            )

            # Save to repository
            saved_collection = asyncio.run(
                collection_service.create_collection(collection)
            )

            # Update session state
            if "collections" in st.session_state:
                st.session_state.collections = asyncio.run(load_collections())

            # Show success message
            st.success(f"Collection '{saved_collection.name}' created successfully!")

        except Exception as e:
            st.error(f"Error creating collection: {str(e)}")

        finally:
            # Clear the trigger
            st.session_state.trigger_collection_creation = False
            st.session_state.create_collection_request = None
