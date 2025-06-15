"""Main module for the API Testing tab component."""

import streamlit as st
from ui.components.tester.adhoc_testing import render_adhoc_testing
from ui.components.tester.collection_testing import render_collection_testing


def render_tester_tab():
    """Render the API Testing tab."""
    st.markdown("## API Testing")

    # Create two tabs for testing: Ad-hoc Testing and Collection-based Testing
    test_tabs = st.tabs(["🧪 Ad-hoc Testing", "📚 Collection Tests"])

    with test_tabs[0]:
        render_adhoc_testing()

    with test_tabs[1]:
        render_collection_testing()
