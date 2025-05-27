# ui/explorer.py

"""API Explorer tab component for the API Testing Platform."""

import asyncio
import json
import re
import streamlit as st
from utils.api_utils import execute_api_call
from ui.components import show_endpoint_card


def render_explorer_tab():
    """Render the API Explorer tab."""
    st.markdown("## API Explorer")
    st.markdown("Select an endpoint to test and provide parameters or request body.")

    if not st.session_state.endpoints:
        st.info("No endpoints available. Please load an API specification first.")
        return

    # Group endpoints by tags or paths for better organization
    endpoints_by_path = {}
    for endpoint in st.session_state.endpoints:
        path_base = (
            endpoint.path.split("/")[1]
            if len(endpoint.path.split("/")) > 1
            else "other"
        )
        if path_base not in endpoints_by_path:
            endpoints_by_path[path_base] = []
        endpoints_by_path[path_base].append(endpoint)

    # Create expandable sections for each group
    for path_group, group_endpoints in endpoints_by_path.items():
        with st.expander(
            f"{path_group.capitalize()} ({len(group_endpoints)} endpoints)"
        ):
            for endpoint in group_endpoints:
                # Create a card for each endpoint
                show_endpoint_card(endpoint)

                # Action buttons
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button(
                        "Test Endpoint",
                        key=f"test_{endpoint.method}_{endpoint.path}",
                    ):
                        st.session_state.selected_endpoint = endpoint

                with col2:
                    if st.button(
                        "View Details",
                        key=f"details_{endpoint.method}_{endpoint.path}",
                    ):
                        st.session_state.view_endpoint_details = endpoint

    # Show endpoint details if requested
    render_endpoint_details()

    # Show form for testing endpoint if selected
    render_endpoint_test_form()

    # Show test results if available
    render_test_results()


def render_endpoint_details():
    """Render the endpoint details section if an endpoint is selected for viewing."""
    if (
        "view_endpoint_details" in st.session_state
        and st.session_state.view_endpoint_details
    ):
        endpoint = st.session_state.view_endpoint_details
        st.markdown("### Endpoint Details")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Path**: {endpoint.path}")
            st.markdown(f"**Method**: {endpoint.method.upper()}")
            st.markdown(f"**Name**: {endpoint.name}")

        with col2:
            st.markdown(
                f"**Auth Required**: {'Yes' if endpoint.auth_required else 'No'}"
            )
            if endpoint.auth_required and endpoint.auth_type:
                st.markdown(f"**Auth Type**: {endpoint.auth_type.value}")
            st.markdown(
                f"**Tags**: {', '.join(endpoint.tags) if endpoint.tags else 'None'}"
            )

        # Show input schema
        if endpoint.input_schema and "properties" in endpoint.input_schema:
            with st.expander("Input Schema", expanded=True):
                st.json(endpoint.input_schema)

        # Show output schema
        if endpoint.output_schema:
            with st.expander("Output Schema"):
                st.json(endpoint.output_schema)


def render_endpoint_test_form():
    """Render the form for testing an endpoint if one is selected."""
    if "selected_endpoint" in st.session_state and st.session_state.selected_endpoint:
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
                    is_required = param_name in endpoint.input_schema.get(
                        "required", []
                    )
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

        # Display response if available
        render_api_response()


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


def render_api_response():
    """Render the API response if available."""
    if st.session_state.get("last_response"):
        response = st.session_state.last_response
        st.markdown("### Response")

        # Response status
        # Get status code from the response, handling both object and dict access
        if hasattr(response.response, "status_code"):
            status_code = response.response.status_code
        else:
            status_code = response.response.get("status_code", 500)

        status_color = "green" if 200 <= status_code < 300 else "red"
        st.markdown(
            f"**Status Code:** <span style='color:{status_color};'>{status_code}</span>",
            unsafe_allow_html=True,
        )

        # Response time
        st.markdown(f"**Response Time:** {response.elapsed:.3f} seconds")

        # Response headers
        with st.expander("Response Headers"):
            for header, value in response.response.headers.items():
                st.markdown(f"**{header}:** {value}")

        # Response body
        st.markdown("**Response Body:**")
        if isinstance(response.response.body, dict) or isinstance(
            response.response.body, list
        ):
            st.json(response.response.body)
        else:
            st.text(response.response.body)


def render_test_results():
    """Render the test results if available."""
    if "last_test_result" in st.session_state:
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
