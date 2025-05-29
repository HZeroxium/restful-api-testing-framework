"""API response viewer component for the API Explorer."""

import streamlit as st


def render_api_response():
    """Render the API response if available."""
    if not st.session_state.get("last_response"):
        return

    response = st.session_state.last_response
    st.markdown("### Response")

    # Response status
    status_code = None
    if hasattr(response.response, "status_code"):
        status_code = response.response.status_code
    elif isinstance(response.response, dict) and "status_code" in response.response:
        status_code = response.response["status_code"]
    else:
        status_code = 500
        st.warning("Could not determine status code from response")

    status_color = "green" if 200 <= status_code < 300 else "red"
    st.markdown(
        f"**Status Code:** <span style='color:{status_color};'>{status_code}</span>",
        unsafe_allow_html=True,
    )

    # Response time
    st.markdown(f"**Response Time:** {response.elapsed:.3f} seconds")

    # Response headers
    with st.expander("Response Headers"):
        headers = {}
        if hasattr(response.response, "headers"):
            headers = response.response.headers
        elif isinstance(response.response, dict) and "headers" in response.response:
            headers = response.response["headers"]

        if headers:
            for header, value in headers.items():
                st.markdown(f"**{header}:** {value}")
        else:
            st.info("No headers found in response")

    # Response body
    st.markdown("**Response Body:**")
    body = None
    if hasattr(response.response, "body"):
        body = response.response.body
    elif isinstance(response.response, dict) and "body" in response.response:
        body = response.response["body"]

    if body is not None:
        if isinstance(body, dict) or isinstance(body, list):
            st.json(body)
        else:
            st.text(body)
    else:
        st.info("No body found in response")
