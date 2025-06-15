"""Component for running test collections."""

import asyncio
import streamlit as st


async def run_collection_tests(collection):
    """Run tests for a collection.

    Args:
        collection: The collection to run tests for

    Returns:
        List of test reports
    """
    from utils.api_utils import run_tests_for_endpoints

    # Extract endpoints from test suites
    endpoints = [suite.endpoint_info for suite in collection.test_suites]

    # Display progress information
    if hasattr(st, "status"):
        with st.status("Running tests...", expanded=True) as status:
            st.write(f"Starting tests for {len(endpoints)} endpoints")

            # Run tests with specific parameters from collection if available
            test_case_count = getattr(collection, "test_case_count", 2)
            include_invalid_data = getattr(collection, "include_invalid_data", True)

            # Run tests
            reports = await run_tests_for_endpoints(
                endpoints,
                test_case_count=test_case_count,
                include_invalid_data=include_invalid_data,
            )

            st.write(f"Completed tests for {len(reports)} endpoints")
            status.update(label="Tests completed", state="complete")
    else:
        # Fallback for older Streamlit versions
        # Run tests
        reports = await run_tests_for_endpoints(endpoints)

    # Calculate overall summary
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0

    for report in reports:
        if isinstance(report, dict) and "summary" in report:
            total_tests += report["summary"].get("total_tests", 0)
            total_passed += report["summary"].get("passed", 0)
            total_failed += report["summary"].get("failed", 0)
            total_errors += report["summary"].get("errors", 0)
            total_skipped += report["summary"].get("skipped", 0)
        elif hasattr(report, "summary"):
            total_tests += getattr(report.summary, "total_tests", 0)
            total_passed += getattr(report.summary, "passed", 0)
            total_failed += getattr(report.summary, "failed", 0)
            total_errors += getattr(report.summary, "errors", 0)
            total_skipped += getattr(report.summary, "skipped", 0)

    # Add overall summary to each report if needed
    for report in reports:
        if not hasattr(report, "overall_summary"):
            report["overall_summary"] = {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "errors": total_errors,
                "skipped": total_skipped,
                "success_rate": (
                    (total_passed / total_tests) * 100 if total_tests > 0 else 0
                ),
            }

    return reports
