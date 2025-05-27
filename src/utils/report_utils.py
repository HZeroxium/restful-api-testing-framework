# utils/report_utils.py

"""Utility functions for working with test reports."""

from typing import Dict, Any
import json
import os


def analyze_test_result(test_case_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a test case result to extract useful information and highlight discrepancies
    between expected and actual results.

    Args:
        test_case_result: A test case result dictionary from a test report

    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "status": test_case_result.get("status"),
        "discrepancies": [],
        "validation_summary": {},
    }

    # Check if we have both test data and response
    test_data = test_case_result.get("test_data", {})
    response = test_case_result.get("response", {})

    if not test_data or not response:
        analysis["error"] = "Missing test data or response for comparison"
        return analysis

    # Check status code
    expected_status = test_data.get("expected_status_code")
    actual_status = response.get("status_code")

    if expected_status and actual_status and expected_status != actual_status:
        analysis["discrepancies"].append(
            {
                "type": "status_code",
                "expected": expected_status,
                "actual": actual_status,
            }
        )

    # Analyze validation results
    validation_results = test_case_result.get("validation_results", [])
    passes = sum(1 for v in validation_results if v.get("status") == "pass")
    failures = sum(1 for v in validation_results if v.get("status") == "fail")
    errors = sum(1 for v in validation_results if v.get("status") == "error")

    analysis["validation_summary"] = {
        "total": len(validation_results),
        "pass": passes,
        "fail": failures,
        "error": errors,
        "pass_rate": (
            (passes / len(validation_results) * 100) if validation_results else 0
        ),
    }

    return analysis


def load_test_report(report_path: str) -> Dict[str, Any]:
    """Load a test report from file."""
    if not os.path.exists(report_path):
        return {"error": f"Report file not found: {report_path}"}

    try:
        with open(report_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in report file: {report_path}"}
    except Exception as e:
        return {"error": f"Error loading report: {str(e)}"}


def compare_test_reports(report_path1: str, report_path2: str) -> Dict[str, Any]:
    """Compare two test reports and highlight differences."""
    report1 = load_test_report(report_path1)
    report2 = load_test_report(report_path2)

    if "error" in report1 or "error" in report2:
        return {"error": report1.get("error") or report2.get("error")}

    comparison = {
        "report1": {
            "path": report_path1,
            "summary": report1.get("summary", {}),
        },
        "report2": {
            "path": report_path2,
            "summary": report2.get("summary", {}),
        },
        "differences": [],
    }

    # Compare success rates
    rate1 = report1.get("summary", {}).get("success_rate", 0)
    rate2 = report2.get("summary", {}).get("success_rate", 0)

    comparison["success_rate_change"] = rate2 - rate1

    # Compare test case results
    results1 = {r.get("test_case_id"): r for r in report1.get("test_case_results", [])}
    results2 = {r.get("test_case_id"): r for r in report2.get("test_case_results", [])}

    # Find common test cases with different results
    common_ids = set(results1.keys()) & set(results2.keys())
    for test_id in common_ids:
        if results1[test_id].get("status") != results2[test_id].get("status"):
            comparison["differences"].append(
                {
                    "test_case_id": test_id,
                    "test_case_name": results1[test_id].get("test_case_name"),
                    "report1_status": results1[test_id].get("status"),
                    "report2_status": results2[test_id].get("status"),
                }
            )

    return comparison
