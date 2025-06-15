"""Collection-based testing interface for the API Testing Platform."""

import asyncio
import streamlit as st
import pandas as pd

from core.services.test_collection_service import TestCollectionService
from core.services.test_execution_service import TestExecutionService
from ui.components.common.metrics import show_metrics_summary
from ui.components.common.cards import show_test_result_card
from ui.components.tester.test_results import (
    render_test_results_chart,
    render_test_case_results_from_report,
)
from ui.collections import get_summary_value


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
                    key=f"tester_run_collection_{selected_collection_id}",
                ):
                    st.session_state.collection_to_run = selected_collection
                    st.rerun()

            with col2:
                if st.button(
                    "View in Collections Tab",
                    key=f"tester_view_collection_{selected_collection_id}",
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
                    st.dataframe(
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
