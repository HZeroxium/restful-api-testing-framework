"""Sidebar component for the API Testing Platform."""

import os
import asyncio
import streamlit as st
from utils.api_utils import load_openapi_spec


def render_sidebar():
    """Render the sidebar with API specification selection and info."""
    with st.sidebar:
        st.markdown("### API Specification")

        # Get list of available spec files
        spec_dir = os.path.join("data")
        spec_files = []

        if os.path.exists(spec_dir):
            for root, dirs, files in os.walk(spec_dir):
                for file in files:
                    if file.endswith((".yaml", ".json")):
                        spec_files.append(os.path.join(root, file))

        spec_path = st.selectbox(
            "Select an OpenAPI specification",
            options=spec_files,
            format_func=lambda x: x.replace("data/", ""),
        )

        if spec_path and st.button("Load API", key="load_api_button"):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                api_info, endpoints, factory = loop.run_until_complete(
                    load_openapi_spec(spec_path)
                )
                st.session_state.api_info = api_info
                st.session_state.endpoints = endpoints
                st.session_state.factory = factory
                st.success("API loaded successfully!")
            except Exception as e:
                st.error(f"Failed to load API: {str(e)}")

        # Show API information if available
        if "api_info" in st.session_state and st.session_state.api_info:
            st.markdown("### API Information")
            st.markdown(f"**Name:** {st.session_state.api_info['title']}")
            st.markdown(f"**Version:** {st.session_state.api_info['version']}")
            if st.session_state.api_info["description"]:
                with st.expander("Description"):
                    st.markdown(st.session_state.api_info["description"])

            if st.session_state.api_info["servers"]:
                st.markdown(f"**Server:** {st.session_state.api_info['servers'][0]}")
