"""Ad-hoc testing interface for the API Testing Platform."""

import asyncio
import streamlit as st
from datetime import datetime
from typing import List

from utils.api_utils import run_tests_for_endpoints
from ui.components.common.metrics import show_metrics_summary
from ui.components.tester.test_results import render_test_results
from core.services.test_collection_service import TestCollectionService
from schemas.test_collection import TestCollectionModel


def render_adhoc_testing():
    """Render the ad-hoc testing interface for testing selected endpoints."""
    st.markdown("### Ad-hoc Endpoint Testing")
    st.markdown("Select endpoints to test and run automated tests.")

    if not st.session_state.endpoints:
        st.info("No endpoints available. Please load an API specification first.")
        return

    # Create a multiselect for choosing endpoints
    endpoint_options = []
    for endpoint in st.session_state.endpoints:
        endpoint_options.append(
            (endpoint, f"{endpoint.method.upper()} {endpoint.path}")
        )

    selected_indices = st.multiselect(
        "Select Endpoints to Test",
        options=range(len(endpoint_options)),
        format_func=lambda i: endpoint_options[i][1],
    )

    selected_endpoints = [st.session_state.endpoints[i] for i in selected_indices]

    # Add test customization options
    st.markdown("### Test Settings")
    col1, col2 = st.columns([1, 1])

    with col1:
        test_case_count = st.number_input(
            "Test Cases per Endpoint",
            min_value=1,
            max_value=5,
            value=2,
            help="Number of test cases to generate for each selected endpoint",
        )

    with col2:
        include_invalid_data = st.checkbox(
            "Include Invalid Test Data",
            value=True,
            help="Generate test cases that should trigger error responses",
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        run_button = st.button("Run Tests", key="run_tests_button")

    if run_button and selected_endpoints:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with st.spinner("Running tests..."):
                # Pass the test customization parameters to the run_tests_for_endpoints function
                test_results = loop.run_until_complete(
                    run_tests_for_endpoints(
                        selected_endpoints,
                        test_case_count=test_case_count,
                        include_invalid_data=include_invalid_data,
                    )
                )
                st.session_state.test_results = test_results
                st.success(f"Tests completed for {len(test_results)} endpoints!")
        except Exception as e:
            st.error(f"Error running tests: {str(e)}")

    # Display test results if available
    if st.session_state.test_results:
        render_test_results()

        # Add option to save as collection
        st.markdown("### Save as Test Collection")
        with st.expander("Save these test results as a collection"):
            save_results_as_collection()


def save_results_as_collection():
    """Save the current test results as a test collection."""
    # Initialize collection service
    collection_service = TestCollectionService()

    with st.form("save_collection_form"):
        name = st.text_input(
            "Collection Name",
            f"Test Collection {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
        description = st.text_area(
            "Description", "Collection created from ad-hoc test results"
        )
        tags_input = st.text_input("Tags (comma-separated)", "ad-hoc,generated")
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        submitted = st.form_submit_button("Save as Collection")

        if submitted:
            if not name:
                st.error("Please enter a collection name.")
                return

            try:
                from schemas.tools.test_suite_generator import (
                    TestSuite,
                    TestCase,
                    ValidationScript,
                )
                from schemas.tools.test_collection_generator import TestCollection

                test_suites = []

                for result in st.session_state.test_results:
                    # Find the endpoint that was tested
                    endpoint = next(
                        (
                            ep
                            for ep in st.session_state.endpoints
                            if ep.method.upper() == result["endpoint_method"].upper()
                            and ep.path == result["endpoint_path"]
                        ),
                        None,
                    )

                    if endpoint:
                        # Create test cases from results
                        test_cases = []
                        for i, test_case_result in enumerate(
                            result["test_case_results"]
                        ):
                            # Create validation scripts
                            validation_scripts = []
                            for j, validation in enumerate(
                                test_case_result.get("validation_results", [])
                            ):
                                script = ValidationScript(
                                    id=f"script_{i}_{j}",
                                    name=validation.get("script_name", "Validation"),
                                    script_type="status_code",
                                    validation_code="""
def validate_status_code(request, response):
    \"\"\"Validate response status code\"\"\"
    try:
        # Handle both dictionary and object access
        if isinstance(response, dict):
            return response.get("status_code") == expected_status_code
        else:
            return getattr(response, "status_code", None) == expected_status_code
    except Exception as e:
        return False
""",
                                    description="Validates response status code",
                                )
                                validation_scripts.append(script)

                            # Extract request data
                            request_data = test_case_result.get("request", {})
                            response_data = test_case_result.get("response", {})

                            # Extract test data if available
                            test_data = test_case_result.get("test_data", {})

                            # Create test case with test data preserved
                            test_case = TestCase(
                                id=f"test_case_{i}",
                                name=f"Test case {i+1}",
                                description=f"Test case generated from results",
                                expected_status_code=test_data.get(
                                    "expected_status_code",
                                    response_data.get("status_code", 200),
                                ),
                                request_params=test_data.get(
                                    "request_params", request_data.get("params", {})
                                ),
                                request_headers=test_data.get(
                                    "request_headers", request_data.get("headers", {})
                                ),
                                request_body=test_data.get(
                                    "request_body", request_data.get("body", {})
                                ),
                                expected_response_schema=test_data.get(
                                    "expected_response_schema", {}
                                ),
                                expected_response_contains=test_data.get(
                                    "expected_response_contains", []
                                ),
                                validation_scripts=validation_scripts,
                            )
                            test_cases.append(test_case)

                        # Create test suite
                        test_suite = TestSuite(
                            endpoint_info=endpoint, test_cases=test_cases
                        )
                        test_suites.append(test_suite)

                # Create collection
                collection = TestCollectionModel(
                    name=name,
                    description=description,
                    test_suites=test_suites,
                    api_name=st.session_state.api_info.get("title", "Unknown API"),
                    api_version=st.session_state.api_info.get("version", "1.0.0"),
                    tags=tags,
                )

                # Save collection
                saved_collection = asyncio.run(
                    collection_service.create_collection(collection)
                )

                # Update session state
                if "collections" in st.session_state:
                    st.session_state.collections = asyncio.run(
                        collection_service.get_all_collections()
                    )

                st.success(
                    f"Collection '{saved_collection.name}' created successfully!"
                )

            except Exception as e:
                st.error(f"Error creating collection: {str(e)}")
