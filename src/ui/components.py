# ui/components.py

"""Reusable UI components for the API Testing Platform."""

import streamlit as st
import json


def render_method_badge(method):
    """Render an HTML badge for HTTP methods.

    Args:
        method: The HTTP method (GET, POST, etc.)

    Returns:
        HTML string for the method badge
    """
    method = method.lower()
    return f"""<span class="method-badge {method}-badge">{method.upper()}</span>"""


def render_status_badge(status):
    """Render an HTML badge for test status.

    Args:
        status: The test status (pass, fail, etc.)

    Returns:
        HTML string for the status badge
    """
    status_lower = status.lower()
    return (
        f"""<span class="status-badge status-{status_lower}">{status.upper()}</span>"""
    )


def render_tag(tag):
    """Render an HTML tag.

    Args:
        tag: The tag text

    Returns:
        HTML string for the tag
    """
    return f"""<span class="tag">{tag}</span>"""


def show_endpoint_card(endpoint):
    """Render an API endpoint card.

    Args:
        endpoint: The endpoint object containing method, path, name, etc.
    """
    # Add method badge and endpoint path
    st.markdown(
        f"""
        <div class="endpoint-card">
            {render_method_badge(endpoint.method)}
            <span class="endpoint-path">{endpoint.path}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Display endpoint name and description
    if hasattr(endpoint, "name") and endpoint.name:
        st.markdown(f"**Name**: {endpoint.name}")

    if hasattr(endpoint, "description") and endpoint.description:
        st.markdown(f"**Description**: {endpoint.description}")

    # Display authentication requirements
    if hasattr(endpoint, "auth_required") and endpoint.auth_required:
        auth_type = (
            endpoint.auth_type.value
            if hasattr(endpoint, "auth_type") and endpoint.auth_type
            else "Unknown"
        )
        st.markdown(f"**Auth**: {auth_type}")

    # Display tags if available
    if hasattr(endpoint, "tags") and endpoint.tags:
        tags_html = " ".join([render_tag(tag) for tag in endpoint.tags])
        st.markdown(
            f"""<div class="tag-container">{tags_html}</div>""", unsafe_allow_html=True
        )


def show_metrics_summary(
    total_tests, total_passed, total_failed, total_errors, success_rate
):
    """Show metrics summary in a card.

    Args:
        total_tests: Total number of tests
        total_passed: Number of passed tests
        total_failed: Number of failed tests
        total_errors: Number of tests with errors
        success_rate: Success rate percentage
    """
    st.markdown(
        """<div class="summary-card">
        <h3 style="margin-top: 0;">Test Summary</h3>
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #28a745;">{}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #dc3545;">{}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: #fd7e14;">{}</div>
                <div class="metric-label">Errors</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: {}">{:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
    </div>""".format(
            total_tests,
            total_passed,
            total_failed,
            total_errors,
            (
                "#28a745"
                if success_rate >= 80
                else "#fd7e14" if success_rate >= 50 else "#dc3545"
            ),
            success_rate,
        ),
        unsafe_allow_html=True,
    )


def show_test_result_card(endpoint_method, endpoint_path, summary, status_class):
    """Show a test result card.

    Args:
        endpoint_method: HTTP method of the endpoint
        endpoint_path: Path of the endpoint
        summary: Test summary statistics (either dict or object with attributes)
        status_class: CSS class for styling based on status
    """
    # Handle both dictionary and object cases
    if isinstance(summary, dict):
        passed = summary.get("passed", 0)
        total_tests = summary.get("total_tests", 0)
    else:
        # It's a Pydantic model or another object with attributes
        passed = getattr(summary, "passed", 0)
        total_tests = getattr(summary, "total_tests", 0)

    st.markdown(
        f"""
    <div class="test-result-card {status_class}">
        <h4>
            {render_method_badge(endpoint_method)}
            {endpoint_path} 
            <span style="float:right;">
                {passed} / {total_tests} tests passed
            </span>
        </h4>
    </div>
    """,
        unsafe_allow_html=True,
    )


def show_validation_result(validation):
    """Show a validation result.

    Args:
        validation: Validation result object (can be dict or Pydantic model)
    """
    # Check if validation is a dictionary or a Pydantic model
    if isinstance(validation, dict):
        status = validation["status"].lower()
        script_name = validation["script_name"]
        message = validation.get("message", "")
    else:
        # It's a Pydantic model object
        status = validation.status.lower()
        script_name = validation.script_name
        message = validation.message if validation.message else ""

    status_class = {
        "pass": "validation-pass",
        "fail": "validation-fail",
        "error": "validation-error",
    }.get(status, "")

    st.markdown(
        f"""
    <div class="validation-item {status_class}">
        {render_status_badge(status.upper())}
        <strong>{script_name}</strong>
        {': ' + message if message else ''}
    </div>
    """,
        unsafe_allow_html=True,
    )


def show_welcome_screen():
    """Show welcome screen when no API is loaded."""
    st.info("👈 Please select an OpenAPI specification file from the sidebar to start.")

    # Show some sample instructions
    with st.expander("How to use this tool"):
        st.markdown(
            """
        ### Getting Started
        
        1. Select an OpenAPI specification file from the sidebar dropdown
        2. Click "Load API" to parse the specification
        3. Use the tabs to interact with the API:
            - **Explorer**: Test individual endpoints with custom parameters
            - **Testing**: Run automated tests on selected endpoints
            - **Collections**: Create and manage reusable test collections
        
        ### Available Demo Specs
        
        - **Toolshop API**: A sample e-commerce API for testing
        - **JSON Placeholder API**: A simple API with common REST endpoints
        """
        )


def pretty_json(obj):
    """Format JSON object for display.

    Args:
        obj: Object to format as JSON

    Returns:
        Formatted JSON string
    """
    json_str = json.dumps(obj, indent=2, sort_keys=True, default=str)
    return f"""<pre class="json-viewer">{json_str}</pre>"""
