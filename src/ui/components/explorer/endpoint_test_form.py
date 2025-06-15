import streamlit as st
import json
import time
import asyncio

from typing import Dict, Any
from ui.components.common.validation import show_validation_result
from ui.components.common.cards import show_response_object


async def execute_api_request(tool, call_input):
    """Execute an API request and return the response.

    Args:
        tool: API caller tool to use
        call_input: Input parameters for the API call

    Returns:
        API response object
    """
    try:
        start_time = time.time()
        response = await tool.execute(call_input)
        end_time = time.time()

        # Add elapsed time to response
        response.elapsed_time = end_time - start_time

        return response
    except Exception as e:
        st.error(f"Error executing API request: {str(e)}")
        return None


def render_endpoint_test_form():
    """Render a form for testing an API endpoint."""
    if "selected_endpoint" not in st.session_state:
        st.info("Please select an endpoint to test")
        return

    endpoint = st.session_state.selected_endpoint
    tool_key = f"{endpoint.method.lower()}_{endpoint.path}"

    if tool_key not in st.session_state.endpoint_tools:
        st.error(
            f"No API caller available for {endpoint.method.upper()} {endpoint.path}"
        )
        return

    tool = st.session_state.endpoint_tools[tool_key]

    st.markdown(f"### Test {endpoint.method.upper()} {endpoint.path}")

    # Create a form for inputting request parameters
    with st.form(key=f"test_form_{tool_key}"):
        # Define request parameters
        parameters = {}
        headers = {}
        body = None

        # Query parameters
        if hasattr(endpoint, "parameters") and endpoint.parameters:
            st.markdown("#### Query Parameters")

            for param in endpoint.parameters:
                if param.in_field == "query":
                    param_key = f"param_{param.name}"

                    if param.type == "boolean":
                        parameters[param.name] = st.checkbox(
                            f"{param.name} ({param.type}){' (required)' if param.required else ''}",
                            key=param_key,
                        )
                    elif param.type == "array":
                        # Handle array parameters
                        array_value = st.text_input(
                            f"{param.name} ({param.type}){' (required)' if param.required else ''} - comma separated values",
                            key=param_key,
                        )
                        if array_value:
                            parameters[param.name] = array_value.split(",")
                    else:
                        # Default to text input for other types
                        param_value = st.text_input(
                            f"{param.name} ({param.type}){' (required)' if param.required else ''}",
                            key=param_key,
                        )
                        if param_value:
                            parameters[param.name] = param_value

        # Headers
        st.markdown("#### Headers")
        content_type = st.selectbox(
            "Content-Type",
            [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain",
            ],
            key="header_content_type",
        )
        headers["Content-Type"] = content_type

        # Authentication
        if hasattr(endpoint, "auth_required") and endpoint.auth_required:
            st.markdown("#### Authentication")
            auth_token = st.text_input(
                "Authentication Token", type="password", key="auth_token"
            )
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

        # Request body
        if endpoint.method.lower() in ["post", "put", "patch"]:
            st.markdown("#### Request Body")

            if hasattr(endpoint, "request_schema") and endpoint.request_schema:
                body_json = st.text_area(
                    "Body (JSON)",
                    value=(
                        json.dumps(endpoint.request_schema, indent=2)
                        if endpoint.request_schema
                        else "{}"
                    ),
                    height=200,
                    key="request_body",
                )

                try:
                    body = json.loads(body_json)
                except json.JSONDecodeError:
                    st.error("Invalid JSON in request body")
                    body = {}

        # Submit button
        submit_button = st.form_submit_button("Send Request")

        if submit_button:
            # Prepare API call input
            call_input = {}

            if parameters:
                call_input["params"] = {k: v for k, v in parameters.items() if v}

            if headers:
                call_input["headers"] = headers

            if body:
                call_input["json"] = body

            # Execute API call
            with st.spinner(f"Executing {endpoint.method.upper()} {endpoint.path}..."):
                response = asyncio.run(execute_api_request(tool, call_input))

                if response:
                    # Store response in session state
                    st.session_state.last_response = response

                    # Redirect to show the response
                    st.experimental_rerun()

    # Display the response if available
    if "last_response" in st.session_state and st.session_state.last_response:
        response = st.session_state.last_response

        # Create a formatted response object for display
        formatted_response = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.body,
        }

        # Display response
        show_response_object(formatted_response)

        # Show elapsed time
        if hasattr(response, "elapsed_time"):
            st.info(f"Request completed in {response.elapsed_time:.3f} seconds")

        # Clear response button
        if st.button("Clear Response"):
            st.session_state.last_response = None
            st.experimental_rerun()
