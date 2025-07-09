"""Endpoint details component for the API Explorer."""

import asyncio
import streamlit as st
from ui.components.common.constraints import show_constraints_section
from tools.llm.static_constraint_miner import StaticConstraintMinerTool
from schemas.tools.constraint_miner import StaticConstraintMinerInput


def render_endpoint_details():
    """Render the endpoint details section if an endpoint is selected for viewing."""
    if (
        "view_endpoint_details" not in st.session_state
        or not st.session_state.view_endpoint_details
    ):
        return

    endpoint = st.session_state.view_endpoint_details
    st.markdown("### Endpoint Details")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Path**: {endpoint.path}")
        st.markdown(f"**Method**: {endpoint.method.upper()}")
        st.markdown(f"**Name**: {endpoint.name}")

    with col2:
        st.markdown(f"**Auth Required**: {'Yes' if endpoint.auth_required else 'No'}")
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

    # Show constraints if available
    if st.button("Analyze API Constraints"):
        with st.spinner("Analyzing API constraints..."):
            # Get constraints for this endpoint
            try:
                # Create constraint miner tool
                constraint_miner = StaticConstraintMinerTool(verbose=False)

                # Create input for constraint miner
                miner_input = StaticConstraintMinerInput(
                    endpoint_info=endpoint,
                    include_examples=True,
                    include_schema_constraints=True,
                    include_correlation_constraints=True,
                )

                # Execute the constraint miner
                miner_output = asyncio.run(constraint_miner.execute(miner_input))

                # Store constraints in session state for this endpoint
                endpoint_key = f"{endpoint.method}_{endpoint.path}"
                if "endpoint_constraints" not in st.session_state:
                    st.session_state.endpoint_constraints = {}

                st.session_state.endpoint_constraints[endpoint_key] = {
                    "request_response": miner_output.request_response_constraints,
                    "response_property": miner_output.response_property_constraints,
                }

                st.success(f"Found {miner_output.total_constraints} constraints!")
            except Exception as e:
                st.error(f"Error analyzing constraints: {str(e)}")

    # Display constraints if they've been analyzed
    endpoint_key = f"{endpoint.method}_{endpoint.path}"
    if (
        "endpoint_constraints" in st.session_state
        and endpoint_key in st.session_state.endpoint_constraints
    ):
        constraints = st.session_state.endpoint_constraints[endpoint_key]

        # Show request-response constraints
        show_constraints_section(
            constraints["request_response"], "Request-Response Constraints"
        )

        # Show response property constraints
        show_constraints_section(
            constraints["response_property"], "Response Property Constraints"
        )
