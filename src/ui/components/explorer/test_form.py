"""Test form components for the API Explorer."""

import json
import re
import asyncio
import streamlit as st
from utils.api_utils import execute_api_call


def render_endpoint_test_form():
    """Render the form for testing an endpoint if one is selected."""
    if (
        "selected_endpoint" not in st.session_state
        or not st.session_state.selected_endpoint
    ):
        return

    endpoint = st.session_state.selected_endpoint

    st.markdown(f"### Test Endpoint: {endpoint.method.upper()} {endpoint.path}")

    with st.form(key=f"test_form_{endpoint.method}_{endpoint.path}"):
        params_values = {}

        # Path parameters (if any)
        path_params = []
        for param in re.findall(r"\{([^}]+)\}", endpoint.path):
            path_params.append(param)

        if path_params:
            st.markdown("#### Path Parameters")
            for param in path_params:
                params_values[param] = st.text_input(
                    f"{param} (required)", key=f"path_{param}"
                )

        # Query parameters (if GET/DELETE)
        if endpoint.method.upper() in [
            "GET",
            "DELETE",
        ] and endpoint.input_schema.get("properties"):
            st.markdown("#### Query Parameters")

            for param_name, param_info in endpoint.input_schema.get(
                "properties", {}
            ).items():
                # Skip parameters that are already included as path params
                if param_name in path_params:
                    continue

                # Get parameter details
                param_type = param_info.get("type", "STRING").upper()
                is_required = param_name in endpoint.input_schema.get("required", [])
                description = param_info.get("description", "")

                # Display appropriate input field based on type
                if param_type == "INTEGER":
                    params_values[param_name] = st.number_input(
                        f"{param_name} ({'required' if is_required else 'optional'})",
                        help=description,
                        step=1,
                    )
                elif param_type == "NUMBER":
                    params_values[param_name] = st.number_input(
                        f"{param_name} ({'required' if is_required else 'optional'})",
                        help=description,
                    )
                elif param_type == "BOOLEAN":
                    params_values[param_name] = st.checkbox(
                        f"{param_name} ({'required' if is_required else 'optional'})",
                        help=description,
                    )
                else:  # STRING or default
                    params_values[param_name] = st.text_input(
                        f"{param_name} ({'required' if is_required else 'optional'})",
                        help=description,
                        key=f"query_{param_name}",
                    )

        # Headers
        headers = render_headers_section(endpoint)

        # Request body (if POST/PUT/PATCH)
        body_params = {}
        if endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
            body_params = render_request_body_section(endpoint, path_params)

        # Combine all parameters for the API call
        all_params = {}
        all_params.update(params_values)
        all_params.update(headers)

        if endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
            all_params.update(body_params)

        submitted = st.form_submit_button("Send Request")
        if submitted:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                response = loop.run_until_complete(
                    execute_api_call(endpoint, all_params)
                )
                st.session_state.last_response = response
            except Exception as e:
                st.error(f"Error executing API call: {str(e)}")


def render_headers_section(endpoint):
    """Render the headers section in the endpoint test form.

    Args:
        endpoint: The endpoint being tested

    Returns:
        Dictionary of header parameters
    """
    headers = {}

    with st.expander("Headers"):
        st.markdown("Add custom headers if needed:")
        num_headers = st.number_input(
            "Number of headers", min_value=0, max_value=10, value=0
        )

        for i in range(num_headers):
            col1, col2 = st.columns(2)
            with col1:
                header_name = st.text_input(
                    f"Header Name #{i+1}", key=f"header_name_{i}"
                )
            with col2:
                header_value = st.text_input(
                    f"Header Value #{i+1}", key=f"header_value_{i}"
                )

            if header_name:
                headers[f"header_{header_name}"] = header_value

        # Add authentication header if needed
        if endpoint.auth_required:
            st.markdown("**Authentication Required**")
            auth_type = endpoint.auth_type.value if endpoint.auth_type else "bearer"

            if auth_type == "bearer":
                token = st.text_input("Bearer Token")
                if token:
                    headers["header_Authorization"] = f"Bearer {token}"
            elif auth_type == "api_key":
                api_key = st.text_input("API Key")
                api_key_header = st.text_input("API Key Header Name", value="X-API-Key")
                if api_key and api_key_header:
                    headers[f"header_{api_key_header}"] = api_key

    return headers


def render_request_body_section(endpoint, path_params):
    """Render the request body section in the endpoint test form.

    Args:
        endpoint: The endpoint being tested
        path_params: List of path parameters to exclude

    Returns:
        Dictionary of body parameters
    """
    st.markdown("#### Request Body")

    # Option to use form fields or raw JSON
    body_input_type = st.radio(
        "Input Type",
        options=["Form Fields", "Raw JSON"],
        horizontal=True,
    )

    body_params = {}

    if body_input_type == "Form Fields" and endpoint.input_schema.get("properties"):
        for param_name, param_info in endpoint.input_schema.get(
            "properties", {}
        ).items():
            # Skip parameters that are already included as path params
            if param_name in path_params:
                continue

            # Get parameter details
            param_type = param_info.get("type", "STRING").upper()
            is_required = param_name in endpoint.input_schema.get("required", [])
            description = param_info.get("description", "")

            # Display appropriate input field based on type
            if param_type == "INTEGER":
                body_params[param_name] = st.number_input(
                    f"{param_name} ({'required' if is_required else 'optional'})",
                    help=description,
                    step=1,
                    key=f"body_int_{param_name}",
                )
            elif param_type == "NUMBER":
                body_params[param_name] = st.number_input(
                    f"{param_name} ({'required' if is_required else 'optional'})",
                    help=description,
                    key=f"body_num_{param_name}",
                )
            elif param_type == "BOOLEAN":
                body_params[param_name] = st.checkbox(
                    f"{param_name} ({'required' if is_required else 'optional'})",
                    help=description,
                    key=f"body_bool_{param_name}",
                )
            else:  # STRING or default
                body_params[param_name] = st.text_input(
                    f"{param_name} ({'required' if is_required else 'optional'})",
                    help=description,
                    key=f"body_str_{param_name}",
                )
    else:  # Raw JSON
        default_json = "{}"
        if endpoint.input_schema.get("example"):
            default_json = json.dumps(endpoint.input_schema["example"], indent=2)

        json_body = st.text_area("JSON Body", value=default_json, height=200)

        try:
            body_params = json.loads(json_body)
        except json.JSONDecodeError:
            st.error("Invalid JSON format")
            body_params = {}

    return body_params
