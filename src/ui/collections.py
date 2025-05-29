"""UI component for managing test collections."""

# Maintain backwards compatibility by re-exporting from the refactored components
from ui.components.collections import (
    render_collections_tab,
    render_collections_list,
    render_collection_creation,
    render_edit_collection,
    render_execution_history,
    render_execution_results_chart,
    run_collection_tests,
)  # noqa: F401
from ui.utils import get_summary_value  # Import from common location

# The original implementation is now in the ui.components.collections package
