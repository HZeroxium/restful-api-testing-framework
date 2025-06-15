"""Test results visualization components for the API Testing Platform."""

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from typing import List, Dict, Any

from ui.components.common.metrics import show_metrics_summary
from ui.components.common.cards import show_test_result_card
from ui.components.common.validation import (
    show_validation_result,
    show_validation_script_details,
)


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
    unique_key = f"test_results_chart_{hash(str(test_summary_data))}_{time.time()}"
    st.plotly_chart(fig, use_container_width=True, key=unique_key)


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
            from ui.components.common.badges import render_status_badge

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

            # Group validations by status
            passed_validations = []
            failed_validations = []
            error_validations = []

            for validation in test_case["validation_results"]:
                status = (
                    validation.get("status", "").lower()
                    if isinstance(validation, dict)
                    else validation.status.lower()
                )

                if status == "pass":
                    passed_validations.append(validation)
                elif status == "fail":
                    failed_validations.append(validation)
                else:
                    error_validations.append(validation)

            # Show failed validations first (they're most important)
            if failed_validations:
                st.markdown("**Failed Validations:**")
                for validation in failed_validations:
                    show_validation_result(validation)
                    # Pass use_expander=False since we're already inside a container
                    show_validation_script_details(validation, use_expander=False)

            # Show error validations next
            if error_validations:
                st.markdown("**Error Validations:**")
                for validation in error_validations:
                    show_validation_result(validation)
                    # Pass use_expander=False since we're already inside a container
                    show_validation_script_details(validation, use_expander=False)

            # Show passed validations - using a cleaner, compact design
            if passed_validations:
                st.markdown(f"**Passed Validations ({len(passed_validations)})**")
                # Create a container with a light gray background to visually group the passed validations
                passed_container = st.container()
                with passed_container:
                    # Add a subtle visual separator
                    st.markdown(
                        """<hr style="margin: 5px 0; height: 1px; border: none; background-color: #f0f0f0;">""",
                        unsafe_allow_html=True,
                    )

                    # Show the passed validations
                    for validation in passed_validations:
                        show_validation_result(validation)
                        # Always use use_expander=False for passed validations
                        show_validation_script_details(validation, use_expander=False)

                        # Add a subtle divider between validations
                        st.markdown(
                            """<hr style="margin: 5px 0; height: 1px; border: none; background-color: #f0f0f0;">""",
                            unsafe_allow_html=True,
                        )

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


def render_test_case_results_from_report(test_case_results):
    """Render test case results from a TestReport object.

    Args:
        test_case_results: List of TestCaseResult objects from a report
    """
    for test_case in test_case_results:
        st.markdown(f"#### Test Case: {test_case.test_case_name}")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            from ui.components.common.badges import render_status_badge

            st.markdown(
                f"**Status:** {render_status_badge(test_case.status)}",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**Time:** {test_case.elapsed_time:.3f}s")
        with col3:
            if hasattr(test_case, "message") and test_case.message:
                st.markdown(f"**Message:** {test_case.message}")

        # Display validation results with enhanced script details
        if hasattr(test_case, "validation_results") and test_case.validation_results:
            st.markdown("##### Validations:")

            # Group validations by status
            passed_validations = []
            failed_validations = []
            error_validations = []

            for validation in test_case.validation_results:
                status = (
                    validation.status.lower()
                    if hasattr(validation, "status")
                    else validation.get("status", "").lower()
                )

                if status == "pass":
                    passed_validations.append(validation)
                elif status == "fail":
                    failed_validations.append(validation)
                else:
                    error_validations.append(validation)

            # Show failed validations first
            if failed_validations:
                st.markdown("**Failed Validations:**")
                for validation in failed_validations:
                    show_validation_result(validation)
                    show_validation_script_details(validation)

            # Show error validations
            if error_validations:
                st.markdown("**Error Validations:**")
                for validation in error_validations:
                    show_validation_result(validation)
                    show_validation_script_details(validation)

            # Show passed validations in an expander
            if passed_validations:
                st.markdown(f"**Passed Validations ({len(passed_validations)})**")
                # Create a container with a light gray background to visually group the passed validations
                passed_container = st.container()
                with passed_container:
                    # Add a subtle visual separator
                    st.markdown(
                        """<hr style="margin: 5px 0; height: 1px; border: none; background-color: #f0f0f0;">""",
                        unsafe_allow_html=True,
                    )

                    # Show the passed validations
                    for validation in passed_validations:
                        show_validation_result(validation)
                        show_validation_script_details(validation, use_expander=False)

                        # Add a subtle divider between validations
                        st.markdown(
                            """<hr style="margin: 5px 0; height: 1px; border: none; background-color: #f0f0f0;">""",
                            unsafe_allow_html=True,
                        )

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
