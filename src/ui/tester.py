"""API Testing tab component for the API Testing Platform."""

import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api_utils import run_tests_for_endpoints
from ui.components import (
    show_test_result_card,
    show_metrics_summary,
    show_validation_result,
)


def render_tester_tab():
    """Render the API Testing tab."""
    st.markdown("## API Testing")
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

    if st.button("Run Tests", key="run_tests_button") and selected_endpoints:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
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
    st.plotly_chart(fig, use_container_width=True)


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
