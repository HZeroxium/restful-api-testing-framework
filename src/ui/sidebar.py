# ui/sidebar.py

"""Sidebar component for the API Testing Platform."""

import os
import asyncio
import streamlit as st
from utils.api_utils import load_openapi_spec
import json


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

        if not spec_files:
            st.warning(
                "No API specification files found. Place OpenAPI files in the 'data' directory."
            )

            # Create example button if no specs found
            if st.button("Create Example Specification"):
                create_example_spec()
                st.success("Created example specification in data/example/")
                st.rerun()

        spec_path = st.selectbox(
            "Select an OpenAPI specification",
            options=spec_files,
            format_func=lambda x: x.replace("data/", ""),
        )

        if spec_path and st.button("Load API", key="load_api_button"):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Show a progress message while loading
                with st.spinner("Loading API specification..."):
                    api_info, endpoints, factory = loop.run_until_complete(
                        load_openapi_spec(spec_path)
                    )
                    st.session_state.api_info = api_info
                    st.session_state.endpoints = endpoints
                    st.session_state.factory = factory
                st.success(
                    f"API loaded successfully! Found {len(endpoints)} endpoints."
                )
            except Exception as e:
                st.error(f"Failed to load API: {str(e)}")

        # Show API information if available
        if "api_info" in st.session_state and st.session_state.api_info:
            st.markdown("### API Information")
            st.markdown(f"**Name:** {st.session_state.api_info['title']}")
            st.markdown(f"**Version:** {st.session_state.api_info['version']}")

            # Display server
            if st.session_state.api_info.get("servers"):
                st.markdown(f"**Server:** {st.session_state.api_info['servers'][0]}")

            # Show description in expandable section
            if st.session_state.api_info.get("description"):
                with st.expander("Description"):
                    st.markdown(st.session_state.api_info["description"])

            # Show endpoint count
            if hasattr(st.session_state, "endpoints"):
                st.markdown(f"**Endpoints:** {len(st.session_state.endpoints)}")

                # Add a quick endpoint filter
                search = st.text_input(
                    "Filter Endpoints", key="sidebar_endpoint_filter"
                )
                if search:
                    filtered = [
                        endpoint
                        for endpoint in st.session_state.endpoints
                        if search.lower() in endpoint.path.lower()
                        or search.lower() in endpoint.method.lower()
                        or (
                            hasattr(endpoint, "name")
                            and search.lower() in endpoint.name.lower()
                        )
                    ]
                    if filtered:
                        with st.expander(f"Matching Endpoints ({len(filtered)})"):
                            for endpoint in filtered:
                                st.markdown(
                                    f"- **{endpoint.method.upper()}** {endpoint.path}"
                                )
                    else:
                        st.info("No matching endpoints found")


def create_example_spec():
    """Create an example OpenAPI specification file."""
    example_dir = os.path.join("data", "example")
    os.makedirs(example_dir, exist_ok=True)

    # Simple example spec for demonstration
    example_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Example API",
            "version": "1.0.0",
            "description": "A simple example API for demonstration",
        },
        "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
        "paths": {
            "/posts": {
                "get": {
                    "summary": "Get all posts",
                    "operationId": "getPosts",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "userId": {"type": "integer"},
                                                "id": {"type": "integer"},
                                                "title": {"type": "string"},
                                                "body": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/posts/{id}": {
                "get": {
                    "summary": "Get post by ID",
                    "operationId": "getPostById",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": "true",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "userId": {"type": "integer"},
                                            "id": {"type": "integer"},
                                            "title": {"type": "string"},
                                            "body": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }

    # Write to file
    spec_path = os.path.join(example_dir, "openapi.json")
    with open(spec_path, "w") as f:
        json.dump(example_spec, f, indent=2)
