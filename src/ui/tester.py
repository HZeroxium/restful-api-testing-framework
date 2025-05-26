"""API Testing tab component for the API Testing Platform."""

import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils.api_utils import run_tests_for_endpoints
from ui.components import (
    show_test_result_card,
    show_metrics_summary,
    show_validation_result,
)
from services.test_collection_service import TestCollectionService
from services.test_execution_service import TestExecutionService
from schemas.test_collection import TestCollectionModel
from ui.collections import get_summary_value


def render_tester_tab():
    """Render the API Testing tab."""
    st.markdown("## API Testing")

    # Create two tabs for testing: Ad-hoc Testing and Collection-based Testing
    test_tabs = st.tabs(["🧪 Ad-hoc Testing", "📚 Collection Tests"])

    with test_tabs[0]:
        render_adhoc_testing()

    with test_tabs[1]:
        render_collection_testing()


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

    col1, col2 = st.columns([1, 1])

    with col1:
        run_button = st.button("Run Tests", key="run_tests_button")

    if run_button and selected_endpoints:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with st.spinner("Running tests..."):
                test_results = loop.run_until_complete(
                    run_tests_for_endpoints(selected_endpoints)
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
                # Convert test results to test suites
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
                                    script="status_code == expected_status_code",
                                    description="Validates response status code",
                                )
                                validation_scripts.append(script)

                            # Extract request data
                            request_data = test_case_result.get("request", {})
                            response_data = test_case_result.get("response", {})

                            # Create test case
                            test_case = TestCase(
                                id=f"test_case_{i}",
                                name=f"Test case {i+1}",
                                description=f"Test case generated from results",
                                expected_status_code=response_data.get(
                                    "status_code", 200
                                ),
                                request_params=request_data.get("params", {}),
                                request_headers=request_data.get("headers", {}),
                                request_body=request_data.get("body", {}),
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


def render_collection_testing():
    """Render the interface for running tests from saved collections."""
    st.markdown("### Collection-based Testing")

    # Initialize services
    collection_service = TestCollectionService()
    execution_service = TestExecutionService()

    # Refresh button for collections
    if st.button("Refresh Collections", key="refresh_collections_button"):
        st.session_state.collections = asyncio.run(
            collection_service.get_all_collections()
        )

    # Load collections if not in session state
    if "collections" not in st.session_state:
        st.session_state.collections = asyncio.run(
            collection_service.get_all_collections()
        )

    collections = st.session_state.collections

    if not collections:
        st.info(
            "No test collections found. Create a new collection in the Collections tab or save test results as a collection."
        )
        return

    # Display collections in a dropdown
    collection_options = {c.id: c.name for c in collections}
    selected_collection_id = st.selectbox(
        "Select a collection to run",
        options=list(collection_options.keys()),
        format_func=lambda x: collection_options[x],
        key="collection_select",
    )

    if selected_collection_id:
        selected_collection = next(
            (c for c in collections if c.id == selected_collection_id), None
        )

        if selected_collection:
            # Display collection details
            st.markdown(f"**Collection:** {selected_collection.name}")
            if selected_collection.description:
                st.markdown(f"**Description:** {selected_collection.description}")

            st.markdown(f"**Endpoints:** {len(selected_collection.test_suites)}")

            test_case_count = sum(
                len(suite.test_cases) for suite in selected_collection.test_suites
            )
            st.markdown(f"**Test Cases:** {test_case_count}")

            # Action buttons
            col1, col2 = st.columns([1, 2])

            with col1:
                if st.button(
                    "Run Collection Tests",
                    key=f"tester_run_collection_{selected_collection_id}",  # Modified key with prefix
                ):
                    st.session_state.collection_to_run = selected_collection
                    st.rerun()

            with col2:
                if st.button(
                    "View in Collections Tab",
                    key=f"tester_view_collection_{selected_collection_id}",  # Modified key with prefix
                ):
                    st.session_state.active_tab = "collections"
                    st.rerun()

            # Display execution history for this collection
            st.markdown("### Execution History")

            # Refresh execution history
            if "executions" not in st.session_state:
                st.session_state.executions = asyncio.run(
                    execution_service.get_all_executions()
                )

            # Filter executions for this collection
            collection_executions = [
                ex
                for ex in st.session_state.executions
                if ex.collection_id == selected_collection_id
            ]

            if not collection_executions:
                st.info("No execution history found for this collection.")
            else:
                # Display executions in a table
                execution_data = []
                for execution in collection_executions:
                    execution_data.append(
                        {
                            "ID": execution.id,
                            "Executed": execution.timestamp.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "Total Tests": get_summary_value(
                                execution.summary, "total_tests"
                            ),
                            "Passed": get_summary_value(execution.summary, "passed"),
                            "Failed": get_summary_value(execution.summary, "failed"),
                            "Success Rate": f"{get_summary_value(execution.summary, 'success_rate'):.1f}%",
                        }
                    )

                if execution_data:
                    df = pd.DataFrame(execution_data)
                    selected_rows = st.dataframe(
                        df,
                        use_container_width=True,
                        column_config={"ID": None},  # Hide ID column
                        hide_index=True,
                    )

                    # Allow selecting an execution to view details
                    execution_options = {
                        execution.id: f"Execution on {execution.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        for execution in collection_executions
                    }

                    selected_execution_id = st.selectbox(
                        "Select an execution to view details",
                        options=list(execution_options.keys()),
                        format_func=lambda x: execution_options[x],
                        key="execution_select",
                    )

                    if selected_execution_id:
                        selected_execution = next(
                            (
                                execution
                                for execution in collection_executions
                                if execution.id == selected_execution_id
                            ),
                            None,
                        )

                        if selected_execution:
                            # Display execution summary
                            st.markdown(f"#### Execution Details")
                            st.markdown(
                                f"Executed on: {selected_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            )

                            # Display metrics
                            summary = selected_execution.summary
                            # Use the helper function to handle both dict and object cases
                            show_metrics_summary(
                                get_summary_value(summary, "total_tests"),
                                get_summary_value(summary, "passed"),
                                get_summary_value(summary, "failed"),
                                get_summary_value(summary, "errors"),
                                get_summary_value(summary, "success_rate"),
                            )

                            # If there are reports, display them
                            if selected_execution.reports:
                                # Convert reports to the format expected by render_test_results_chart
                                test_summary_data = []

                                for report in selected_execution.reports:
                                    endpoint_name = f"{report.endpoint_method.upper()} {report.endpoint_path}"
                                    test_summary_data.append(
                                        {
                                            "Endpoint": endpoint_name,
                                            "Passed": report.summary.passed,
                                            "Failed": report.summary.failed,
                                            "Errors": report.summary.errors,
                                        }
                                    )

                                if test_summary_data:
                                    render_test_results_chart(test_summary_data)

                                # Show detailed results for each endpoint
                                st.markdown("#### Test Results by Endpoint")

                                for report in selected_execution.reports:
                                    endpoint_method = report.endpoint_method.upper()
                                    endpoint_path = report.endpoint_path

                                    # Determine status class
                                    status_class = "pass-card"
                                    if report.summary.failed > 0:
                                        status_class = "fail-card"
                                    elif report.summary.errors > 0:
                                        status_class = "error-card"

                                    show_test_result_card(
                                        endpoint_method,
                                        endpoint_path,
                                        report.summary,
                                        status_class,
                                    )

                                    with st.expander(
                                        f"View Details ({endpoint_method} {endpoint_path})"
                                    ):
                                        render_test_case_results_from_report(
                                            report.test_case_results
                                        )


def render_test_case_results_from_report(test_case_results):
    """Render test case results from a TestReport object.

    Args:
        test_case_results: List of TestCaseResult objects from a report
    """
    for test_case in test_case_results:
        st.markdown(f"#### Test Case: {test_case.test_case_name}")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            from ui.components import render_status_badge

            st.markdown(
                f"**Status:** {render_status_badge(test_case.status)}",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**Time:** {test_case.elapsed_time:.3f}s")
        with col3:
            if hasattr(test_case, "message") and test_case.message:
                st.markdown(f"**Message:** {test_case.message}")

        # Display validation results
        if hasattr(test_case, "validation_results") and test_case.validation_results:
            st.markdown("##### Validations:")
            for validation in test_case.validation_results:
                show_validation_result(validation)

        # Display request/response details
        req_resp_tab1, req_resp_tab2 = st.tabs(["Request", "Response"])

        with req_resp_tab1:
            if hasattr(test_case, "request"):
                st.json(test_case.request)

        with req_resp_tab2:
            if hasattr(test_case, "response"):
                if "status_code" in test_case.response:
                    status_code = test_case.response["status_code"]
                    st.markdown(f"**Status Code:** {status_code}")

                if "body" in test_case.response:
                    st.markdown("**Body:**")
                    st.json(test_case.response["body"])


def render_test_results_chart(test_summary_data):
    """Render the test results chart.

    Args:
        test_summary_data: The test summary data for the chart
    """
    df = pd.DataFrame(test_summary_data)

    # Create a stacked bar chart for test results
    fig = px.bar(
        df,
        x="Endpoint",
        y=["Passed", "Failed", "Errors"],
        title="Test Results by Endpoint",
        color_discrete_map={
            "Passed": "#28a745",
            "Failed": "#dc3545",
            "Errors": "#fd7e14",
        },
        height=400,
    )
    fig.update_layout(
        xaxis_title="Endpoint",
        yaxis_title="Number of Tests",
        legend_title="Status",
        barmode="stack",
    )

    # Generate a unique key - add timestamp for true uniqueness
    import time

    unique_key = f"test_results_chart_{hash(str(test_summary_data))}_{time.time()}"
    st.plotly_chart(fig, use_container_width=True, key=unique_key)


def render_test_results():
    """Render the test results section."""
    st.markdown("## Test Results")

    # Aggregate test statistics
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0

    for result in st.session_state.test_results:
        total_tests += result["summary"]["total_tests"]
        total_passed += result["summary"]["passed"]
        total_failed += result["summary"]["failed"]
        total_errors += result["summary"]["errors"]

    success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0

    # Display test summary metrics
    show_metrics_summary(
        total_tests, total_passed, total_failed, total_errors, success_rate
    )

    # Create a DataFrame for visualization
    test_summary_data = []
    for result in st.session_state.test_results:
        endpoint_name = f"{result['endpoint_method'].upper()} {result['endpoint_path']}"
        test_summary_data.append(
            {
                "Endpoint": endpoint_name,
                "Passed": result["summary"]["passed"],
                "Failed": result["summary"]["failed"],
                "Errors": result["summary"]["errors"],
            }
        )

    # Create visualization chart if there's data
    if test_summary_data:
        render_test_results_chart(test_summary_data)

    # Display detailed results for each endpoint
    render_detailed_test_results()


def render_detailed_test_results():
    """Render the detailed test results for each endpoint."""
    for i, result in enumerate(st.session_state.test_results):
        endpoint_method = result["endpoint_method"].upper()
        endpoint_path = result["endpoint_path"]

        # Determine the status color
        if result["summary"]["failed"] > 0 or result["summary"]["errors"] > 0:
            status_class = (
                "fail-card" if result["summary"]["failed"] > 0 else "error-card"
            )
        else:
            status_class = "pass-card"

        show_test_result_card(
            endpoint_method, endpoint_path, result["summary"], status_class
        )

        with st.expander(f"View Details ({endpoint_method} {endpoint_path})"):
            # Display each test case result
            render_test_case_results(result["test_case_results"])


def render_test_case_results(test_case_results):
    """Render the results for each test case.

    Args:
        test_case_results: List of test case results
    """
    for test_case in test_case_results:
        st.markdown(f"#### Test Case: {test_case['test_case_name']}")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            from ui.components import render_status_badge

            st.markdown(
                f"**Status:** {render_status_badge(test_case['status'])}",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**Time:** {test_case['elapsed_time']:.3f}s")
        with col3:
            if "message" in test_case:
                st.markdown(f"**Message:** {test_case['message']}")

        # Display validation results
        if "validation_results" in test_case and test_case["validation_results"]:
            st.markdown("##### Validations:")
            for validation in test_case["validation_results"]:
                show_validation_result(validation)

        # Display request/response details
        req_resp_tab1, req_resp_tab2 = st.tabs(["Request", "Response"])

        with req_resp_tab1:
            if "request" in test_case:
                st.json(test_case["request"])

        with req_resp_tab2:
            if "response" in test_case:
                if "status_code" in test_case["response"]:
                    status_code = test_case["response"]["status_code"]
                    st.markdown(f"**Status Code:** {status_code}")

                if "body" in test_case["response"]:
                    st.markdown("**Body:**")
                    st.json(test_case["response"]["body"])
