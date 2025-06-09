# utils/report_utils.py

"""Utility functions for working with test reports."""

from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime


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

    # Check status code - handle both object and dict access
    expected_status = test_data.get("expected_status_code")
    actual_status = None

    # Handle different response formats
    if isinstance(response, dict):
        actual_status = response.get("status_code")
    else:
        actual_status = getattr(response, "status_code", None)

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

    # Provide clearer analysis of common issues
    for validation in validation_results:
        if validation.get("status") != "pass":
            message = validation.get("message", "")

            # Check for common attribute errors
            if "'dict' object has no attribute" in message:
                analysis.setdefault("common_issues", []).append(
                    {
                        "issue_type": "dict_attribute_access",
                        "message": "Validation script is trying to access attributes on a dictionary object. Use dict['key'] instead of dict.key",
                        "validation": validation.get("script_name"),
                        "details": message,
                    }
                )
            elif "AttributeError" in message:
                analysis.setdefault("common_issues", []).append(
                    {
                        "issue_type": "attribute_error",
                        "message": "Validation script is trying to access a non-existent attribute",
                        "validation": validation.get("script_name"),
                        "details": message,
                    }
                )

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


def analyze_constraint_mining_result(
    constraint_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze constraint mining results to extract useful statistics and insights.

    Args:
        constraint_result: A constraint mining result dictionary

    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "endpoint_info": {
            "method": constraint_result.get("endpoint_method", ""),
            "path": constraint_result.get("endpoint_path", ""),
            "endpoint": f"{constraint_result.get('endpoint_method', '').upper()} {constraint_result.get('endpoint_path', '')}",
        },
        "constraint_summary": {
            "total_constraints": constraint_result.get("total_constraints", 0),
            "request_param_count": len(
                constraint_result.get("request_param_constraints", [])
            ),
            "request_body_count": len(
                constraint_result.get("request_body_constraints", [])
            ),
            "response_property_count": len(
                constraint_result.get("response_property_constraints", [])
            ),
            "request_response_count": len(
                constraint_result.get("request_response_constraints", [])
            ),
        },
        "constraint_breakdown": {},
        "severity_analysis": {},
        "constraint_types": {},
        "mining_quality": {},
    }

    # Analyze all constraint categories
    constraint_categories = [
        ("request_param_constraints", "Request Parameters"),
        ("request_body_constraints", "Request Body"),
        ("response_property_constraints", "Response Properties"),
        ("request_response_constraints", "Request-Response Correlations"),
    ]

    for category_key, category_name in constraint_categories:
        constraints = constraint_result.get(category_key, [])
        analysis["constraint_breakdown"][category_name] = _analyze_constraint_category(
            constraints
        )

    # Overall severity analysis
    all_constraints = []
    for category_key, _ in constraint_categories:
        all_constraints.extend(constraint_result.get(category_key, []))

    analysis["severity_analysis"] = _analyze_constraint_severity(all_constraints)
    analysis["constraint_types"] = _analyze_constraint_types(all_constraints)
    analysis["mining_quality"] = _analyze_mining_quality(constraint_result)

    return analysis


def _analyze_constraint_category(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a specific category of constraints."""
    if not constraints:
        return {"count": 0, "severities": {}, "types": {}, "sources": {}}

    analysis = {"count": len(constraints), "severities": {}, "types": {}, "sources": {}}

    for constraint in constraints:
        # Severity analysis
        severity = constraint.get("severity", "unknown")
        analysis["severities"][severity] = analysis["severities"].get(severity, 0) + 1

        # Type analysis
        constraint_type = constraint.get("details", {}).get(
            "constraint_type", "unknown"
        )
        analysis["types"][constraint_type] = (
            analysis["types"].get(constraint_type, 0) + 1
        )

        # Source analysis
        source = constraint.get("source", "unknown")
        analysis["sources"][source] = analysis["sources"].get(source, 0) + 1

    return analysis


def _analyze_constraint_severity(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze severity distribution across all constraints."""
    severity_counts = {"error": 0, "warning": 0, "info": 0, "unknown": 0}

    for constraint in constraints:
        severity = constraint.get("severity", "unknown")
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts["unknown"] += 1

    total = len(constraints)
    severity_percentages = {}
    if total > 0:
        for severity, count in severity_counts.items():
            severity_percentages[severity] = round((count / total) * 100, 2)

    return {
        "counts": severity_counts,
        "percentages": severity_percentages,
        "total": total,
    }


def _analyze_constraint_types(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze constraint type distribution."""
    type_counts = {}

    for constraint in constraints:
        constraint_type = constraint.get("details", {}).get(
            "constraint_type", "unknown"
        )
        type_counts[constraint_type] = type_counts.get(constraint_type, 0) + 1

    # Sort by frequency
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "distribution": type_counts,
        "most_common": sorted_types[:5],
        "unique_types": len(type_counts),
    }


def _analyze_mining_quality(constraint_result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality of constraint mining."""
    mining_results = constraint_result.get("result", {}).get("mining_results", {})

    quality_analysis = {
        "successful_miners": 0,
        "failed_miners": 0,
        "skipped_miners": 0,
        "llm_sourced": 0,
        "fallback_sourced": 0,
        "miner_details": {},
    }

    for miner_name, miner_result in mining_results.items():
        status = miner_result.get("status", "unknown")
        source = miner_result.get("source", "unknown")

        # Status analysis
        if status == "success":
            quality_analysis["successful_miners"] += 1
        elif status == "failed":
            quality_analysis["failed_miners"] += 1
        elif status == "skipped":
            quality_analysis["skipped_miners"] += 1

        # Source analysis
        if source == "llm":
            quality_analysis["llm_sourced"] += 1
        elif source == "fallback":
            quality_analysis["fallback_sourced"] += 1

        quality_analysis["miner_details"][miner_name] = {
            "status": status,
            "source": source,
            "constraints": miner_result.get("total_constraints", 0),
        }

    return quality_analysis


def load_constraint_mining_report(report_path: str) -> Dict[str, Any]:
    """Load a constraint mining report from file."""
    if not os.path.exists(report_path):
        return {"error": f"Report file not found: {report_path}"}

    try:
        with open(report_path, "r") as f:
            data = json.load(f)

        # Handle both individual constraint files and summary files
        if "constraints" in data and isinstance(data["constraints"], list):
            # This is a summary file
            return data
        else:
            # This is an individual constraint mining result
            return data

    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in report file: {report_path}"}
    except Exception as e:
        return {"error": f"Error loading report: {str(e)}"}


def compare_constraint_mining_reports(
    report_path1: str, report_path2: str
) -> Dict[str, Any]:
    """Compare two constraint mining reports and highlight differences."""
    report1 = load_constraint_mining_report(report_path1)
    report2 = load_constraint_mining_report(report_path2)

    if "error" in report1 or "error" in report2:
        return {"error": report1.get("error") or report2.get("error")}

    analysis1 = analyze_constraint_mining_result(report1)
    analysis2 = analyze_constraint_mining_result(report2)

    comparison = {
        "report1": {"path": report_path1, "analysis": analysis1},
        "report2": {"path": report_path2, "analysis": analysis2},
        "differences": {
            "total_constraints": {
                "report1": analysis1["constraint_summary"]["total_constraints"],
                "report2": analysis2["constraint_summary"]["total_constraints"],
                "change": analysis2["constraint_summary"]["total_constraints"]
                - analysis1["constraint_summary"]["total_constraints"],
            },
            "severity_changes": {},
            "category_changes": {},
        },
    }

    # Compare severity distributions
    sev1 = analysis1["severity_analysis"]["counts"]
    sev2 = analysis2["severity_analysis"]["counts"]

    for severity in ["error", "warning", "info"]:
        comparison["differences"]["severity_changes"][severity] = {
            "report1": sev1.get(severity, 0),
            "report2": sev2.get(severity, 0),
            "change": sev2.get(severity, 0) - sev1.get(severity, 0),
        }

    # Compare category counts
    cat1 = analysis1["constraint_summary"]
    cat2 = analysis2["constraint_summary"]

    for category in [
        "request_param_count",
        "request_body_count",
        "response_property_count",
        "request_response_count",
    ]:
        comparison["differences"]["category_changes"][category] = {
            "report1": cat1.get(category, 0),
            "report2": cat2.get(category, 0),
            "change": cat2.get(category, 0) - cat1.get(category, 0),
        }

    return comparison


def generate_constraint_insights(constraint_result: Dict[str, Any]) -> List[str]:
    """Generate human-readable insights from constraint analysis."""
    analysis = analyze_constraint_mining_result(constraint_result)
    insights = []

    # Overall insights
    total = analysis["constraint_summary"]["total_constraints"]
    if total == 0:
        insights.append("⚠️ No constraints were identified for this endpoint")
        return insights

    insights.append(f"✅ Successfully identified {total} constraints for the endpoint")

    # Severity insights
    severity = analysis["severity_analysis"]
    error_count = severity["counts"]["error"]
    warning_count = severity["counts"]["warning"]

    if error_count > 0:
        insights.append(
            f"🔴 {error_count} critical constraints require immediate attention"
        )

    if warning_count > 0:
        insights.append(
            f"🟡 {warning_count} warning-level constraints should be reviewed"
        )

    # Category insights
    summary = analysis["constraint_summary"]
    if summary["response_property_count"] > summary["request_param_count"]:
        insights.append(
            "📊 Response validation is more comprehensive than request validation"
        )

    if summary["request_response_count"] > 0:
        insights.append(
            f"🔗 {summary['request_response_count']} request-response correlations identified"
        )

    # Mining quality insights
    quality = analysis["mining_quality"]
    if quality["llm_sourced"] > quality["fallback_sourced"]:
        insights.append("🤖 LLM successfully analyzed most constraints")
    else:
        insights.append("⚙️ Fallback rules were used for most constraints")

    # Type diversity
    types = analysis["constraint_types"]
    if types["unique_types"] > 5:
        insights.append(
            f"🎯 Good constraint diversity with {types['unique_types']} different types"
        )

    return insights
