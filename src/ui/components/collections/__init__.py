"""
Collection management components for the API Testing Platform.
This module provides UI components for managing test collections.
"""

# Export primary functions
from .list import render_collections_list
from .create import render_collection_creation
from .edit import render_edit_collection
from .execution import render_execution_history, render_execution_results_chart
from .runner import run_collection_tests
from ui.utils import get_summary_value  # Import from common location

# Main tab renderer that combines the components
from .main import render_collections_tab
