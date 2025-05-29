"""Test results component for the API Explorer."""

import streamlit as st


def render_explorer_test_results():
    """Render the test results if available."""
    if "last_test_result" not in st.session_state:
        return

    result = st.session_state.last_test_result

    st.markdown("### Test Results")

    # Display test data if available
    if "test_data" in result:
        with st.expander("Test Data", expanded=True):
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Expected Status Code:**")
                st.write(result["test_data"]["expected_status_code"])

                if result["test_data"].get("request_params"):
                    st.markdown("**Request Parameters:**")
                    st.json(result["test_data"]["request_params"])

                if result["test_data"].get("request_headers"):
                    st.markdown("**Request Headers:**")
                    st.json(result["test_data"]["request_headers"])

            with cols[1]:
                if result["test_data"].get("request_body"):
                    st.markdown("**Request Body:**")
                    st.json(result["test_data"]["request_body"])

                if result["test_data"].get("expected_response_schema"):
                    st.markdown("**Expected Response Schema:**")
                    st.json(result["test_data"]["expected_response_schema"])

                if result["test_data"].get("expected_response_contains"):
                    st.markdown("**Expected Response Contains:**")
                    st.write(result["test_data"]["expected_response_contains"])

    # Display result summary
    with st.expander("Result Summary", expanded=True):
        st.markdown("**Status:**")
        st.write(result["status"])

        if result["status"] == "failed":
            st.markdown("**Error Message:**")
            st.write(result["error_message"])

        st.markdown("**Response Status Code:**")
        st.write(result["response_status_code"])

        st.markdown("**Response Body:**")
        st.json(result["response_body"])

    # Display raw request/response if available
    if "raw_request" in result and "raw_response" in result:
        with st.expander("Raw Request/Response", expanded=False):
            st.markdown("**Raw Request:**")
            st.code(result["raw_request"], language="http")

            st.markdown("**Raw Response:**")
            st.code(result["raw_response"], language="http")
