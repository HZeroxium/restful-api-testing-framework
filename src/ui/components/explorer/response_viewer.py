"""API response viewer component for the API Explorer."""

import streamlit as st
from typing import Any, Dict


def render_api_response():
    """Render the API response if available."""
    if not st.session_state.get("last_response"):
        return

    response = st.session_state.last_response
    st.markdown("### Response")

    # Response status
    status_code = extract_status_code(response)
    status_color = "green" if 200 <= status_code < 300 else "red"
    st.markdown(
        f"**Status Code:** <span style='color:{status_color};'>{status_code}</span>",
        unsafe_allow_html=True,
    )

    # Response time
    elapsed = getattr(response, "elapsed", 0)
    st.markdown(f"**Response Time:** {elapsed:.3f} seconds")

    # Response headers
    with st.expander("Response Headers"):
        headers = extract_headers(response)
        if headers:
            for header, value in headers.items():
                st.markdown(f"**{header}:** {value}")
        else:
            st.info("No headers found in response")

    # Response body
    st.markdown("**Response Body:**")
    body = extract_body(response)

    if body is not None:
        if isinstance(body, dict) or isinstance(body, list):
            st.json(body)
        else:
            st.text(body)
    else:
        st.info("No body found in response")


def extract_status_code(response: Any) -> int:
    """Extract status code from various response structures.

    Args:
        response: Response object with various possible structures

    Returns:
        HTTP status code
    """
    # Try different ways to get status code
    if hasattr(response, "response"):
        if hasattr(response.response, "status_code"):
            return response.response.status_code
        elif isinstance(response.response, dict) and "status_code" in response.response:
            return response.response["status_code"]

    # If response is itself a dict
    if isinstance(response, dict) and "status_code" in response:
        return response["status_code"]

    # Direct attribute access as fallback
    if hasattr(response, "status_code"):
        return response.status_code

    # Default status code if nothing found
    return 500


def extract_headers(response: Any) -> Dict[str, str]:
    """Extract headers from various response structures.

    Args:
        response: Response object with various possible structures

    Returns:
        Dictionary of HTTP headers
    """
    headers = {}

    # Try different ways to get headers
    if hasattr(response, "response"):
        if hasattr(response.response, "headers"):
            headers = response.response.headers
        elif isinstance(response.response, dict) and "headers" in response.response:
            headers = response.response["headers"]

    # If response is itself a dict
    if isinstance(response, dict) and "headers" in response:
        headers = response["headers"]

    # Direct attribute access as fallback
    if hasattr(response, "headers"):
        headers = response.headers

    return headers


def extract_body(response: Any) -> Any:
    """Extract body from various response structures.

    Args:
        response: Response object with various possible structures

    Returns:
        Response body content
    """
    body = None

    # Try different ways to get body
    if hasattr(response, "response"):
        if hasattr(response.response, "body"):
            body = response.response.body
        elif isinstance(response.response, dict) and "body" in response.response:
            body = response.response["body"]

    # If response is itself a dict
    if isinstance(response, dict) and "body" in response:
        body = response["body"]

    # Direct attribute access as fallback
    if hasattr(response, "body"):
        body = response.body

    return body
