"""Component for editing existing test collections."""

import asyncio
import streamlit as st
from datetime import datetime

from .utils import load_collections, collection_service


def render_edit_collection():
    """Render the form for editing an existing collection."""
    if "collection_to_edit" not in st.session_state:
        st.error("No collection selected for editing.")
        return

    collection = st.session_state.collection_to_edit
    st.markdown(f"### Edit Collection: {collection.name}")

    with st.form("edit_collection_form"):
        name = st.text_input("Collection Name", collection.name)
        description = st.text_area("Description", collection.description or "")

        # Tags
        current_tags = ", ".join(collection.tags) if collection.tags else ""
        tags_input = st.text_input("Tags (comma-separated)", current_tags)
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Validate inputs
            if not name:
                st.error("Please enter a collection name.")
                return

            # Update collection
            collection.name = name
            collection.description = description
            collection.tags = tags
            collection.updated_at = datetime.now()

            try:
                # Save to repository
                updated = asyncio.run(
                    collection_service.update_collection(collection.id, collection)
                )

                # Update session state
                if "collections" in st.session_state:
                    st.session_state.collections = asyncio.run(load_collections())

                # Show success message
                st.success(f"Collection '{updated.name}' updated successfully!")

                # Clear editing state
                st.session_state.collection_to_edit = None
                st.session_state.active_tab = "collections"
                st.rerun()

            except Exception as e:
                st.error(f"Error updating collection: {str(e)}")
