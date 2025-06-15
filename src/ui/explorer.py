"""API Explorer tab component for the API Testing Platform."""

# Import and re-export the refactored components
from ui.components.explorer import (
    render_explorer_tab,
    render_endpoint_listing,
    render_endpoint_details,
    render_endpoint_test_form,
    render_headers_section,
    render_request_body_section,
    render_api_response,
    render_explorer_test_results,
)

# Maintain backwards compatibility with original code
show_constraints_section = None

try:
    from ui.components.common.constraints import show_constraints_section
except ImportError:
    # Fall back to original implementation if module not found
    from ui.components.explorer.endpoint_details import show_constraints_section
