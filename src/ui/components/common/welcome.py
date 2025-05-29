"""Welcome screen for the API Testing Platform."""

import streamlit as st


def show_welcome_screen():
    """Show welcome screen when no API is loaded."""
    st.info("👈 Please select an OpenAPI specification file from the sidebar to start.")

    # Show some sample instructions
    with st.expander("How to use this tool"):
        st.markdown(
            """
        ### Getting Started
        
        1. Select an OpenAPI specification file from the sidebar dropdown
        2. Click "Load API" to parse the specification
        3. Use the tabs to interact with the API:
            - **Explorer**: Test individual endpoints with custom parameters
            - **Testing**: Run automated tests on selected endpoints
            - **Collections**: Create and manage reusable test collections
        
        ### Available Demo Specs
        
        - **Toolshop API**: A sample e-commerce API for testing
        - **JSON Placeholder API**: A simple API with common REST endpoints
        """
        )
