# ui/tester.py

"""API Testing tab component for the API Testing Platform."""

# Simply import and export the refactored tester components
from ui.components.tester import render_tester_tab

# Maintain backwards compatibility with existing code
render_adhoc_testing = None
render_collection_testing = None
render_test_results = None
render_detailed_test_results = None
render_test_case_results = None
render_test_results_chart = None
render_test_case_results_from_report = None
save_results_as_collection = None

try:
    from ui.components.tester.adhoc_testing import (
        render_adhoc_testing,
        save_results_as_collection,
    )
    from ui.components.tester.collection_testing import render_collection_testing
    from ui.components.tester.test_results import (
        render_test_results,
        render_detailed_test_results,
        render_test_case_results,
        render_test_results_chart,
        render_test_case_results_from_report,
    )
except ImportError:
    # Fall back to original implementations if modules not found
    pass
