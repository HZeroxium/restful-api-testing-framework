# ui/collections.py

"""UI component for managing test collections."""

import asyncio
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from core.services.test_collection_service import TestCollectionService
from core.services.test_execution_service import TestExecutionService
from schemas.test_collection import TestCollectionModel
from ui.components import (
    show_metrics_summary,
    show_test_result_card,
    show_validation_result,
    render_status_badge,
    render_method_badge,
)

# Initialize services
collection_service = TestCollectionService()
execution_service = TestExecutionService()


# Add this new helper function to safely access summary data
def get_summary_value(summary, key, default=0):
    """Safely get a value from summary object whether it's a dict or a Pydantic model.

    Args:
        summary: The summary object (can be a dict or a Pydantic model)
        key: The key/attribute to access
        default: Default value if key doesn't exist

    Returns:
        The value of the key/attribute or the default
    """
    if hasattr(summary, key):
        return getattr(summary, key)
    elif isinstance(summary, dict) and key in summary:
        return summary[key]
    return default


def render_collections_tab():
    """Render the Test Collections management tab."""
    st.markdown("## Test Collections")

    # Tabs for different operations
    collection_tabs = st.tabs(
        ["📋 All Collections", "➕ Create Collection", "📊 Execution History"]
    )

    # Tab 1: List all collections
    with collection_tabs[0]:
        render_collections_list()

    # Tab 2: Create new collection
    with collection_tabs[1]:
        render_collection_creation()

    # Tab 3: Execution history
    with collection_tabs[2]:
        render_execution_history()


async def load_collections():
    """Load all collections."""
    return await collection_service.get_all_collections()


async def load_execution_history():
    """Load all execution history."""
    return await execution_service.get_all_executions()


def render_collections_list():
    """Render the list of collections."""
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
    selected_indices = st.dataframe(
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

                # Show test cases in an expander
                with st.expander(f"View Test Cases for {method} {path}"):
                    for j, test_case in enumerate(suite.test_cases):
                        st.markdown(f"##### {test_case.name}")
                        st.markdown(f"- **Description:** {test_case.description}")
                        # Display with better formatting
                        status_color = (
                            "green"
                            if 200 <= test_case.expected_status_code < 300
                            else "red"
                        )
                        st.markdown(
                            f"- **Expected Status:** <span style='color:{status_color};'>{test_case.expected_status_code}</span>",
                            unsafe_allow_html=True,
                        )

            # Actions for the collection
            st.markdown("#### Actions")
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                if st.button(
                    "Run Tests",
                    key=f"list_run_collection_{selected_collection_id}",
                ):
                    st.session_state.collection_to_run = selected_collection
                    st.rerun()  # To update the UI

            with col2:
                if st.button(
                    "Edit Collection",
                    key=f"list_edit_collection_{selected_collection_id}",
                ):
                    st.session_state.collection_to_edit = selected_collection
                    st.session_state.active_tab = "collections_edit"
                    st.rerun()  # To update the UI

            with col3:
                if st.button(
                    "Delete Collection",
                    key=f"list_delete_collection_{selected_collection_id}",
                ):
                    if asyncio.run(
                        collection_service.delete_collection(selected_collection_id)
                    ):
                        st.success(
                            f"Collection '{selected_collection.name}' deleted successfully!"
                        )
                        # Refresh collections
                        st.session_state.collections = asyncio.run(load_collections())
                        st.rerun()  # To update the UI
                    else:
                        st.error("Failed to delete collection.")


def render_collection_creation():
    """Render the form for creating a new collection."""
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
        selected_endpoints = []

        for path_group, group_endpoints in endpoints_by_path.items():
            with st.expander(
                f"{path_group.capitalize()} ({len(group_endpoints)} endpoints)"
            ):
                for endpoint in group_endpoints:
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
        create_request = st.session_state.create_collection_request

        with st.spinner("Creating test collection..."):
            # Process this asynchronously
            from tools.test_collection_generator import TestCollectionGeneratorTool
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
                st.success(
                    f"Collection '{saved_collection.name}' created successfully!"
                )

            except Exception as e:
                st.error(f"Error creating collection: {str(e)}")

            finally:
                # Clear the trigger
                st.session_state.trigger_collection_creation = False
                st.session_state.create_collection_request = None


def render_edit_collection():
    """Render the form for editing an existing collection."""
    if "collection_to_edit" not in st.session_state:
        st.error("No collection selected for editing.")
        return

    collection = st.session_state.collection_to_edit
    st.markdown(f"### Edit Collection: {collection.name}")

    with st.form("edit_collection_form"):
        name = st.text_input("Collection Name", collection.name)
        description = st.text_area("Description", collection.description or "")

        # Tags
        current_tags = ", ".join(collection.tags) if collection.tags else ""
        tags_input = st.text_input("Tags (comma-separated)", current_tags)
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Validate inputs
            if not name:
                st.error("Please enter a collection name.")
                return

            # Update collection
            collection.name = name
            collection.description = description
            collection.tags = tags
            collection.updated_at = datetime.now()

            try:
                # Save to repository
                updated = asyncio.run(
                    collection_service.update_collection(collection.id, collection)
                )

                # Update session state
                if "collections" in st.session_state:
                    st.session_state.collections = asyncio.run(load_collections())

                # Show success message
                st.success(f"Collection '{updated.name}' updated successfully!")

                # Clear editing state
                st.session_state.collection_to_edit = None
                st.session_state.active_tab = "collections"
                st.rerun()

            except Exception as e:
                st.error(f"Error updating collection: {str(e)}")


def render_execution_history():
    """Render the execution history view."""
    st.markdown("### Test Execution History")

    # Load execution history
    if st.button("Refresh History"):
        st.session_state.executions = asyncio.run(load_execution_history())

    if "executions" not in st.session_state:
        st.session_state.executions = asyncio.run(load_execution_history())

    executions = st.session_state.executions

    if not executions:
        st.info("No test execution history found. Run some tests to see results here.")
        return

    # Display executions in a searchable table
    execution_data = []
    for execution in executions:
        execution_data.append(
            {
                "ID": execution.id,
                "Collection": execution.collection_name or "Unknown",
                "Executed": execution.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Total Tests": get_summary_value(execution.summary, "total_tests"),
                "Passed": get_summary_value(execution.summary, "passed"),
                "Failed": get_summary_value(execution.summary, "failed"),
                "Errors": get_summary_value(execution.summary, "errors"),
                "Success Rate": f"{get_summary_value(execution.summary, 'success_rate'):.1f}%",
            }
        )

    df = pd.DataFrame(execution_data)

    # Add search and filtering
    search_term = st.text_input("🔍 Search execution history", "")
    if search_term:
        df = df[df["Collection"].str.contains(search_term, case=False)]

    # Display table with selectable rows
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "ID": None,  # Hide ID column
        },
        hide_index=True,
    )

    # Execution details and actions
    st.markdown("### Execution Details")

    # Choose an execution to view details
    execution_options = {
        ex.id: f"{ex.collection_name} ({ex.timestamp.strftime('%Y-%m-%d %H:%M')})"
        for ex in executions
    }

    selected_execution_id = st.selectbox(
        "Select an execution",
        options=list(execution_options.keys()),
        format_func=lambda x: execution_options[x],
    )

    if selected_execution_id:
        selected_execution = next(
            (ex for ex in executions if ex.id == selected_execution_id), None
        )

        if selected_execution:
            # Display execution summary
            st.markdown(f"#### Execution Summary: {selected_execution.collection_name}")
            st.markdown(
                f"Executed on: {selected_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Display metrics
            summary = selected_execution.summary
            show_metrics_summary(
                get_summary_value(summary, "total_tests"),
                get_summary_value(summary, "passed"),
                get_summary_value(summary, "failed"),
                get_summary_value(summary, "errors"),
                get_summary_value(summary, "success_rate"),
            )

            # Visualize results if we have data
            if len(selected_execution.reports) > 0:
                render_execution_results_chart(selected_execution)

            # Display detailed results for each endpoint test
            st.markdown("#### Detailed Results")

            for report in selected_execution.reports:
                endpoint_method = report.endpoint_method.upper()
                endpoint_path = report.endpoint_path

                # Determine the status color
                if (
                    get_summary_value(report.summary, "failed") > 0
                    or get_summary_value(report.summary, "errors") > 0
                ):
                    status_class = (
                        "fail-card"
                        if get_summary_value(report.summary, "failed") > 0
                        else "error-card"
                    )
                else:
                    status_class = "pass-card"

                show_test_result_card(
                    endpoint_method, endpoint_path, report.summary, status_class
                )

                with st.expander(f"View Details ({endpoint_method} {endpoint_path})"):
                    # Use a unique key for each expander in execution history
                    expanderId = f"history_{selected_execution_id}_{report.endpoint_method}_{hash(report.endpoint_path)}"

                    # Display each test case result
                    for test_case in report.test_case_results:
                        st.markdown(f"##### Test Case: {test_case.test_case_name}")

                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col1:
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
                        if (
                            hasattr(test_case, "validation_results")
                            and test_case.validation_results
                        ):
                            st.markdown("##### Validations:")
                            for validation in test_case.validation_results:
                                show_validation_result(validation)

                        # Display request/response details
                        req_resp_tab1, req_resp_tab2 = st.tabs(["Request", "Response"])

                        with req_resp_tab1:
                            if hasattr(test_case, "request") and test_case.request:
                                st.json(test_case.request)

                        with req_resp_tab2:
                            if hasattr(test_case, "response") and test_case.response:
                                if "status_code" in test_case.response:
                                    status_code = test_case.response["status_code"]
                                    st.markdown(f"**Status Code:** {status_code}")

                                if "body" in test_case.response:
                                    st.markdown("**Body:**")
                                    st.json(test_case.response["body"])


def render_execution_results_chart(execution):
    """Render a chart showing execution results.

    Args:
        execution: The test execution to visualize
    """
    # Create data for the chart
    chart_data = []

    for report in execution.reports:
        endpoint_name = f"{report.endpoint_method.upper()} {report.endpoint_path}"
        chart_data.append(
            {
                "Endpoint": (
                    endpoint_name
                    if len(endpoint_name) < 30
                    else endpoint_name[:27] + "..."
                ),
                "Passed": get_summary_value(report.summary, "passed"),
                "Failed": get_summary_value(report.summary, "failed"),
                "Errors": get_summary_value(report.summary, "errors"),
                "Skipped": get_summary_value(report.summary, "skipped"),
            }
        )

    if chart_data:
        df = pd.DataFrame(chart_data)

        # Create a stacked bar chart for test results
        fig = px.bar(
            df,
            x="Endpoint",
            y=["Passed", "Failed", "Errors", "Skipped"],
            title="Test Results by Endpoint",
            color_discrete_map={
                "Passed": "#28a745",
                "Failed": "#dc3545",
                "Errors": "#fd7e14",
                "Skipped": "#6c757d",
            },
            height=400,
        )
        fig.update_layout(
            xaxis_title="Endpoint",
            yaxis_title="Number of Tests",
            legend_title="Status",
            barmode="stack",
        )
        # Generate a unique key based on the execution ID
        unique_key = f"execution_chart_{execution.id}"
        st.plotly_chart(fig, use_container_width=True, key=unique_key)


async def run_collection_tests(collection):
    """Run tests for a collection.

    Args:
        collection: The collection to run tests for

    Returns:
        List of test reports
    """
    from utils.api_utils import run_tests_for_endpoints

    # Extract endpoints from test suites
    endpoints = [suite.endpoint_info for suite in collection.test_suites]

    # Run tests
    reports = await run_tests_for_endpoints(endpoints)

    # Calculate overall summary
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0

    for report in reports:
        if isinstance(report, dict) and "summary" in report:
            total_tests += report["summary"].get("total_tests", 0)
            total_passed += report["summary"].get("passed", 0)
            total_failed += report["summary"].get("failed", 0)
            total_errors += report["summary"].get("errors", 0)
            total_skipped += report["summary"].get("skipped", 0)
        elif hasattr(report, "summary"):
            total_tests += getattr(report.summary, "total_tests", 0)
            total_passed += getattr(report.summary, "passed", 0)
            total_failed += getattr(report.summary, "failed", 0)
            total_errors += getattr(report.summary, "errors", 0)
            total_skipped += getattr(report.summary, "skipped", 0)

    # Add overall summary to each report if needed
    for report in reports:
        if not hasattr(report, "overall_summary"):
            report["overall_summary"] = {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "errors": total_errors,
                "skipped": total_skipped,
                "success_rate": (
                    (total_passed / total_tests) * 100 if total_tests > 0 else 0
                ),
            }

    return reports
