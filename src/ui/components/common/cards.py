"""UI card components for the API Testing Platform."""

import streamlit as st
import json

from ui.components.common.badges import render_method_badge, render_tag
from ui.utils import get_summary_value


def show_test_result_card(endpoint_method, endpoint_path, summary, status_class):
    """Show a test result card.

    Args:
        endpoint_method: HTTP method of the endpoint
        endpoint_path: Path of the endpoint
        summary: Test summary statistics (either dict or object with attributes)
        status_class: CSS class for styling based on status
    """
    # Handle both dictionary and object cases
    passed = get_summary_value(summary, "passed", 0)
    total_tests = get_summary_value(summary, "total_tests", 0)

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


def show_response_object(response, title="Response"):
    """Show a response object with proper handling for different formats.

    Args:
        response: The response object (can be dict or object)
        title: Title for the section
    """
    st.markdown(f"### {title}")

    # Handle status code
    status_code = None
    if hasattr(response, "status_code"):
        status_code = response.status_code
    elif isinstance(response, dict) and "status_code" in response:
        status_code = response["status_code"]

    if status_code is not None:
        status_color = "green" if 200 <= status_code < 300 else "red"
        st.markdown(
            f"**Status Code:** <span style='color:{status_color};'>{status_code}</span>",
            unsafe_allow_html=True,
        )

    # Handle headers
    headers = None
    if hasattr(response, "headers"):
        headers = response.headers
    elif isinstance(response, dict) and "headers" in response:
        headers = response["headers"]

    if headers:
        with st.expander("Headers"):
            for header, value in headers.items():
                st.markdown(f"**{header}:** {value}")

    # Handle body
    body = None
    if hasattr(response, "body"):
        body = response.body
    elif isinstance(response, dict) and "body" in response:
        body = response["body"]

    if body is not None:
        st.markdown("**Body:**")
        if isinstance(body, dict) or isinstance(body, list):
            st.json(body)
        else:
            st.text(body)


def show_error_message(title, message, details=None):
    """Show an error message with optional details.

    Args:
        title: The error title
        message: The error message
        details: Optional details (can be shown in expander)
    """
    st.error(f"**{title}**\n\n{message}")
    if details:
        with st.expander("Error Details"):
            st.code(details)


def pretty_json(obj):
    """Format JSON object for display.

    Args:
        obj: Object to format as JSON

    Returns:
        Formatted JSON string
    """
    json_str = json.dumps(obj, indent=2, sort_keys=True, default=str)
    return f"""<pre class="json-viewer">{json_str}</pre>"""
