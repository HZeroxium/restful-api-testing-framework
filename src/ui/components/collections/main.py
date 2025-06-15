"""Main collections tab component for the API Testing Platform."""

import streamlit as st
from .list import render_collections_list
from .create import render_collection_creation
from .execution import render_execution_history


def render_collections_tab():
    """Render the Test Collections management tab with all subcomponents."""
    st.markdown("## Test Collections")

    # Tabs for different operations
    collection_tabs = st.tabs(
        ["📋 All Collections", "➕ Create Collection", "📊 Execution History"]
    )

    # Tab 1: List all collections
    with collection_tabs[0]:
        render_collections_list()

    # Tab 2: Create new collection
    with collection_tabs[1]:
        render_collection_creation()

    # Tab 3: Execution history
    with collection_tabs[2]:
        render_execution_history()
