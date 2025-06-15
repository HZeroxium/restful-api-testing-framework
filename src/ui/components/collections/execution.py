"""Component for displaying test execution history."""

import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px

from .utils import load_execution_history
from ui.utils import get_summary_value
from ui.components.common.metrics import show_metrics_summary
from ui.components.common.cards import show_test_result_card
from ui.components.common.validation import show_validation_result
from ui.components.common.badges import render_status_badge


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
    st.dataframe(
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
            _render_execution_details(selected_execution)


def _render_execution_details(selected_execution):
    """Render detailed information for a selected execution.

    Args:
        selected_execution: The execution to display details for
    """
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
            expanderId = f"history_{selected_execution.id}_{report.endpoint_method}_{hash(report.endpoint_path)}"
            _render_test_case_results(report.test_case_results, expanderId)


def _render_test_case_results(test_case_results, expanderId):
    """Render test case results for an execution report.

    Args:
        test_case_results: List of test case results to display
        expanderId: Unique ID for the expander
    """
    for test_case in test_case_results:
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

        # Display validation results without expanders
        if hasattr(test_case, "validation_results") and test_case.validation_results:
            st.markdown("##### Validations:")
            # Group validations by status for better organization
            tabs = st.tabs(["All", "Failed", "Passed", "Errors"])

            with tabs[0]:  # All validations
                for validation in test_case.validation_results:
                    show_validation_result(validation)

            with tabs[1]:  # Failed validations
                failed_validations = [
                    v
                    for v in test_case.validation_results
                    if hasattr(v, "status") and v.status.lower() == "fail"
                ]
                if failed_validations:
                    for validation in failed_validations:
                        show_validation_result(validation)
                else:
                    st.info("No failed validations")

            with tabs[2]:  # Passed validations
                passed_validations = [
                    v
                    for v in test_case.validation_results
                    if hasattr(v, "status") and v.status.lower() == "pass"
                ]
                if passed_validations:
                    for validation in passed_validations:
                        show_validation_result(validation)
                else:
                    st.info("No passed validations")

            with tabs[3]:  # Error validations
                error_validations = [
                    v
                    for v in test_case.validation_results
                    if hasattr(v, "status") and v.status.lower() == "error"
                ]
                if error_validations:
                    for validation in error_validations:
                        show_validation_result(validation)
                else:
                    st.info("No validation errors")

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
