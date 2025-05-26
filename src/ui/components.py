"""Reusable UI components for the API Testing Platform."""

import streamlit as st


def render_method_badge(method):
    """Render an HTTP method badge with appropriate styling.

    Args:
        method: The HTTP method (GET, POST, etc.)

    Returns:
        HTML string for the badge
    """
    method = method.lower()
    return f"""<span class="method-badge {method}-badge">{method.upper()}</span>"""


def render_status_badge(status):
    """Render a test status badge with appropriate styling.

    Args:
        status: The test status (pass, fail, error, etc.)

    Returns:
        HTML string for the badge
    """
    status_lower = status.lower()
    return (
        f"""<span class="status-badge status-{status_lower}">{status.upper()}</span>"""
    )


def show_endpoint_card(endpoint):
    """Display an API endpoint card with proper styling.

    Args:
        endpoint: EndpointInfo object
    """
    method_class = endpoint.method.lower() + "-method"
    st.markdown(
        f"""
        <div class="endpoint-card {method_class}">
            {render_method_badge(endpoint.method)}
            <strong>{endpoint.path}</strong>
            <p style="margin: 5px 0; color: #666; font-size: 14px;">{endpoint.description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_validation_result(validation):
    """Display a validation result with appropriate styling.

    Args:
        validation: ValidationResult object
    """
    status_class = {
        "pass": "validation-pass",
        "fail": "validation-fail",
        "error": "validation-error",
    }.get(validation["status"].lower(), "")

    st.markdown(
        f"""
        <div class="validation-item {status_class}">
            {render_status_badge(validation['status'])}
            <strong>{validation['script_name']}</strong>
            {': ' + validation['message'] if 'message' in validation else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_test_result_card(endpoint_method, endpoint_path, summary, status_class):
    """Display a test result card with appropriate styling.

    Args:
        endpoint_method: HTTP method of the endpoint
        endpoint_path: Path of the endpoint
        summary: Test summary data
        status_class: CSS class for styling (pass-card, fail-card, etc.)
    """
    st.markdown(
        f"""
        <div class="test-result-card {status_class}">
            <h4>
                {render_method_badge(endpoint_method)}
                {endpoint_path} 
                <span style="float:right;">
                    {summary["passed"]} / {summary["total_tests"]} tests passed
                </span>
            </h4>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_metrics_summary(
    total_tests, total_passed, total_failed, total_errors, success_rate
):
    """Display metrics summary with custom styling.

    Args:
        total_tests: Total number of tests
        total_passed: Number of passed tests
        total_failed: Number of failed tests
        total_errors: Number of tests with errors
        success_rate: Success rate percentage
    """
    color = (
        "#28a745"
        if success_rate >= 80
        else "#fd7e14" if success_rate >= 50 else "#dc3545"
    )

    st.markdown(
        f"""
        <div class="summary-card">
            <h3 style="margin-top: 0;">Test Summary</h3>
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-value">{total_tests}</div>
                    <div class="metric-label">Total Tests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #28a745;">{total_passed}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #dc3545;">{total_failed}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #fd7e14;">{total_errors}</div>
                    <div class="metric-label">Errors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: {color}">{success_rate:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_welcome_screen():
    """Display the welcome screen when no API is loaded."""
    st.info("👈 Please select an OpenAPI specification file from the sidebar to start.")

    with st.expander("How to use this tool"):
        st.markdown(
            """
        ### Getting Started
        
        1. Select an OpenAPI specification file from the sidebar dropdown
        2. Click "Load API" to parse the specification
        3. Use the tabs to interact with the API:
            - **Explorer**: Test individual endpoints with custom parameters
            - **Testing**: Run automated tests on selected endpoints
        
        ### Available Demo Specs
        
        - **Toolshop API**: A sample e-commerce API for testing
        - **JSON Placeholder API**: A simple API with common REST endpoints
        """
        )
