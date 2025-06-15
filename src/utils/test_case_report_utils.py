"""Utility functions for working with test case reports and validation script analysis."""

from typing import Dict, Any, List, Optional, Tuple
import json
import os
from datetime import datetime
from collections import defaultdict, Counter


def load_test_case_report(report_path: str) -> Dict[str, Any]:
    """Load a test case report from file."""
    if not os.path.exists(report_path):
        return {"error": f"Report file not found: {report_path}"}

    try:
        with open(report_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in report file: {report_path}"}
    except Exception as e:
        return {"error": f"Error loading report: {str(e)}"}


def analyze_test_case_report(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a test case report to extract comprehensive statistics and insights.

    Args:
        test_case_data: Test case report data

    Returns:
        Dictionary with detailed analysis results
    """
    analysis = {
        "endpoint_info": {
            "method": test_case_data.get("endpoint", {}).get("method", ""),
            "path": test_case_data.get("endpoint", {}).get("path", ""),
            "description": test_case_data.get("endpoint", {}).get("description", ""),
            "auth_required": test_case_data.get("endpoint", {}).get(
                "auth_required", False
            ),
            "endpoint": f"{test_case_data.get('endpoint', {}).get('method', '').upper()} {test_case_data.get('endpoint', {}).get('path', '')}",
        },
        "summary": _analyze_test_case_summary(test_case_data),
        "constraint_analysis": _analyze_constraints(
            test_case_data.get("constraints", [])
        ),
        "validation_script_analysis": _analyze_validation_scripts(test_case_data),
        "constraint_coverage": _analyze_constraint_coverage(test_case_data),
        "test_data_analysis": _analyze_test_data(test_case_data.get("test_data", [])),
        "quality_metrics": _calculate_quality_metrics(test_case_data),
        "script_complexity": _analyze_script_complexity(test_case_data),
    }

    return analysis


def _analyze_test_case_summary(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze basic summary statistics."""
    summary = test_case_data.get("summary", {})

    return {
        "total_test_cases": summary.get("total_test_cases", 0),
        "total_constraints": summary.get("total_constraints", 0),
        "total_validation_scripts": summary.get("total_validation_scripts", 0),
        "include_invalid_data": summary.get("include_invalid_data", False),
        "constraint_breakdown": summary.get("constraint_breakdown", {}),
        "scripts_per_test_case": _calculate_scripts_per_test_case(test_case_data),
        "constraints_per_test_case": _calculate_constraints_per_test_case(
            test_case_data
        ),
    }


def _analyze_constraints(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze constraint distribution and characteristics."""
    if not constraints:
        return {"total": 0, "by_type": {}, "by_severity": {}, "by_source": {}}

    by_type = Counter(c.get("type", "unknown") for c in constraints)
    by_severity = Counter(c.get("severity", "unknown") for c in constraints)
    by_source = Counter(c.get("source", "unknown") for c in constraints)

    # Analyze constraint details
    constraint_types = Counter()
    validation_rules = Counter()

    for constraint in constraints:
        details = constraint.get("details", {})
        constraint_types[details.get("constraint_type", "unknown")] += 1
        validation_rules[details.get("validation_rule", "unknown")] += 1

    return {
        "total": len(constraints),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "by_source": dict(by_source),
        "constraint_types": dict(constraint_types),
        "validation_rules": dict(validation_rules),
        "severity_distribution": _calculate_percentages(by_severity),
        "type_distribution": _calculate_percentages(by_type),
    }


def _analyze_validation_scripts(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze validation scripts across all test cases."""
    all_scripts = []
    test_cases = test_case_data.get("test_cases", [])

    for test_case in test_cases:
        scripts = test_case.get("validation_scripts", [])
        all_scripts.extend(scripts)

    if not all_scripts:
        return {"total": 0, "by_type": {}, "script_names": [], "unique_scripts": 0}

    by_type = Counter(script.get("script_type", "unknown") for script in all_scripts)
    script_names = [script.get("name", "unnamed") for script in all_scripts]
    unique_scripts = len(
        set(script.get("validation_code", "") for script in all_scripts)
    )

    # Analyze script characteristics
    script_lengths = [len(script.get("validation_code", "")) for script in all_scripts]
    avg_script_length = (
        sum(script_lengths) / len(script_lengths) if script_lengths else 0
    )

    return {
        "total": len(all_scripts),
        "by_type": dict(by_type),
        "script_names": script_names,
        "unique_scripts": unique_scripts,
        "duplication_rate": (
            round((1 - unique_scripts / len(all_scripts)) * 100, 2)
            if all_scripts
            else 0
        ),
        "average_script_length": round(avg_script_length, 2),
        "type_distribution": _calculate_percentages(by_type),
    }


def _analyze_constraint_coverage(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the mapping between constraints and validation scripts."""
    constraints = {c["id"]: c for c in test_case_data.get("constraints", [])}
    constraint_to_scripts = defaultdict(list)
    script_to_constraints = {}
    uncovered_constraints = set(constraints.keys())

    test_cases = test_case_data.get("test_cases", [])

    for test_case in test_cases:
        scripts = test_case.get("validation_scripts", [])
        for script in scripts:
            script_id = script.get("id", "")
            constraint_id = script.get("constraint_id")

            if constraint_id:
                constraint_to_scripts[constraint_id].append(script)
                script_to_constraints[script_id] = constraint_id
                uncovered_constraints.discard(constraint_id)

    # Calculate coverage statistics
    total_constraints = len(constraints)
    covered_constraints = len(constraint_to_scripts)
    coverage_rate = (
        (covered_constraints / total_constraints * 100) if total_constraints > 0 else 0
    )

    # Analyze constraint types coverage
    constraint_type_coverage = defaultdict(lambda: {"covered": 0, "total": 0})
    for constraint_id, constraint in constraints.items():
        constraint_type = constraint.get("type", "unknown")
        constraint_type_coverage[constraint_type]["total"] += 1
        if constraint_id in constraint_to_scripts:
            constraint_type_coverage[constraint_type]["covered"] += 1

    return {
        "total_constraints": total_constraints,
        "covered_constraints": covered_constraints,
        "uncovered_constraints": len(uncovered_constraints),
        "coverage_rate": round(coverage_rate, 2),
        "constraint_to_scripts_mapping": dict(constraint_to_scripts),
        "script_to_constraint_mapping": script_to_constraints,
        "uncovered_constraint_ids": list(uncovered_constraints),
        "constraint_type_coverage": dict(constraint_type_coverage),
        "multiple_scripts_per_constraint": sum(
            1 for scripts in constraint_to_scripts.values() if len(scripts) > 1
        ),
    }


def _analyze_test_data(test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze test data characteristics."""
    if not test_data:
        return {"total": 0, "with_params": 0, "with_body": 0, "with_headers": 0}

    with_params = sum(1 for td in test_data if td.get("request_params"))
    with_body = sum(1 for td in test_data if td.get("request_body"))
    with_headers = sum(1 for td in test_data if td.get("request_headers"))

    # Analyze expected status codes
    status_codes = Counter(
        td.get("expected_status_code")
        for td in test_data
        if td.get("expected_status_code")
    )

    # Analyze request parameters
    all_params = []
    for td in test_data:
        params = td.get("request_params", {})
        if isinstance(params, dict):
            all_params.extend(params.keys())

    param_frequency = Counter(all_params)

    return {
        "total": len(test_data),
        "with_params": with_params,
        "with_body": with_body,
        "with_headers": with_headers,
        "expected_status_codes": dict(status_codes),
        "common_parameters": dict(param_frequency.most_common(10)),
        "parameter_usage_rate": (
            round(with_params / len(test_data) * 100, 2) if test_data else 0
        ),
    }


def _calculate_quality_metrics(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate quality metrics for the test case generation."""
    constraints = test_case_data.get("constraints", [])
    test_cases = test_case_data.get("test_cases", [])

    # Script generation success rate
    total_expected_scripts = len(constraints) * len(test_cases)
    total_actual_scripts = sum(
        len(tc.get("validation_scripts", [])) for tc in test_cases
    )
    script_generation_rate = (
        (total_actual_scripts / total_expected_scripts * 100)
        if total_expected_scripts > 0
        else 0
    )

    # Constraint coverage rate
    coverage_analysis = _analyze_constraint_coverage(test_case_data)
    coverage_rate = coverage_analysis["coverage_rate"]

    # Test data quality
    test_data_analysis = _analyze_test_data(test_case_data.get("test_data", []))
    test_data_completeness = (
        test_data_analysis["parameter_usage_rate"]
        + (
            test_data_analysis["with_body"] / test_data_analysis["total"] * 100
            if test_data_analysis["total"] > 0
            else 0
        )
    ) / 2

    # Overall quality score (weighted average)
    quality_score = (
        script_generation_rate * 0.4
        + coverage_rate * 0.4
        + test_data_completeness * 0.2
    )

    return {
        "script_generation_rate": round(script_generation_rate, 2),
        "constraint_coverage_rate": round(coverage_rate, 2),
        "test_data_completeness": round(test_data_completeness, 2),
        "overall_quality_score": round(quality_score, 2),
        "quality_grade": _get_quality_grade(quality_score),
    }


def _analyze_script_complexity(test_case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the complexity of generated validation scripts."""
    all_scripts = []
    test_cases = test_case_data.get("test_cases", [])

    for test_case in test_cases:
        scripts = test_case.get("validation_scripts", [])
        all_scripts.extend(scripts)

    if not all_scripts:
        return {"total_scripts": 0}

    # Analyze script code complexity
    complexities = []
    for script in all_scripts:
        code = script.get("validation_code", "")
        complexity = _calculate_script_complexity(code)
        complexities.append(complexity)

    avg_complexity = sum(complexities) / len(complexities) if complexities else 0

    # Categorize scripts by complexity
    simple_scripts = sum(1 for c in complexities if c <= 5)
    medium_scripts = sum(1 for c in complexities if 5 < c <= 15)
    complex_scripts = sum(1 for c in complexities if c > 15)

    return {
        "total_scripts": len(all_scripts),
        "average_complexity": round(avg_complexity, 2),
        "simple_scripts": simple_scripts,
        "medium_scripts": medium_scripts,
        "complex_scripts": complex_scripts,
        "complexity_distribution": {
            "simple": round(simple_scripts / len(all_scripts) * 100, 2),
            "medium": round(medium_scripts / len(all_scripts) * 100, 2),
            "complex": round(complex_scripts / len(all_scripts) * 100, 2),
        },
    }


def generate_constraint_script_mapping(
    test_case_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate a detailed mapping between constraints and validation scripts."""
    constraints = {c["id"]: c for c in test_case_data.get("constraints", [])}
    mapping = []

    test_cases = test_case_data.get("test_cases", [])

    for test_case in test_cases:
        test_case_id = test_case.get("id", "")
        test_case_name = test_case.get("name", "")

        scripts = test_case.get("validation_scripts", [])
        for script in scripts:
            constraint_id = script.get("constraint_id")
            constraint_info = constraints.get(constraint_id) if constraint_id else None

            mapping_entry = {
                "test_case_id": test_case_id,
                "test_case_name": test_case_name,
                "script_id": script.get("id", ""),
                "script_name": script.get("name", ""),
                "script_type": script.get("script_type", ""),
                "constraint_id": constraint_id,
                "constraint_description": (
                    constraint_info.get("description", "")
                    if constraint_info
                    else "No constraint mapped"
                ),
                "constraint_type": (
                    constraint_info.get("type", "") if constraint_info else ""
                ),
                "constraint_severity": (
                    constraint_info.get("severity", "") if constraint_info else ""
                ),
                "validation_code_length": len(script.get("validation_code", "")),
                "has_constraint_mapping": constraint_id is not None,
            }
            mapping.append(mapping_entry)

    return mapping


def generate_test_case_insights(test_case_data: Dict[str, Any]) -> List[str]:
    """Generate human-readable insights from test case analysis."""
    analysis = analyze_test_case_report(test_case_data)
    insights = []

    # Basic statistics
    summary = analysis["summary"]
    insights.append(
        f"✅ Generated {summary['total_test_cases']} test cases with {summary['total_validation_scripts']} validation scripts"
    )

    # Constraint coverage insights
    coverage = analysis["constraint_coverage"]
    if coverage["coverage_rate"] >= 90:
        insights.append(
            f"🎯 Excellent constraint coverage: {coverage['coverage_rate']}% of constraints have validation scripts"
        )
    elif coverage["coverage_rate"] >= 70:
        insights.append(
            f"👍 Good constraint coverage: {coverage['coverage_rate']}% of constraints have validation scripts"
        )
    else:
        insights.append(
            f"⚠️ Low constraint coverage: Only {coverage['coverage_rate']}% of constraints have validation scripts"
        )

    # Quality metrics insights
    quality = analysis["quality_metrics"]
    insights.append(
        f"📊 Overall quality score: {quality['overall_quality_score']}/100 ({quality['quality_grade']})"
    )

    # Script complexity insights
    complexity = analysis["script_complexity"]
    if complexity["total_scripts"] > 0:
        if complexity["complex_scripts"] / complexity["total_scripts"] > 0.3:
            insights.append(
                f"🔧 {complexity['complex_scripts']} scripts are complex and may need review"
            )
        else:
            insights.append(f"✨ Most scripts are simple to medium complexity")

    # Constraint type distribution
    constraint_analysis = analysis["constraint_analysis"]
    most_common_type = (
        max(constraint_analysis["by_type"].items(), key=lambda x: x[1])
        if constraint_analysis["by_type"]
        else None
    )
    if most_common_type:
        insights.append(
            f"📋 Most constraints are {most_common_type[0].replace('_', ' ')} type ({most_common_type[1]} constraints)"
        )

    # Test data insights
    test_data = analysis["test_data_analysis"]
    if test_data["parameter_usage_rate"] > 80:
        insights.append(
            f"📝 High parameter usage: {test_data['parameter_usage_rate']}% of test cases include request parameters"
        )

    # Script duplication insights
    script_analysis = analysis["validation_script_analysis"]
    if script_analysis["duplication_rate"] > 20:
        insights.append(
            f"🔄 Script duplication detected: {script_analysis['duplication_rate']}% duplication rate"
        )

    return insights


def compare_test_case_reports(report_path1: str, report_path2: str) -> Dict[str, Any]:
    """Compare two test case reports and highlight differences."""
    report1 = load_test_case_report(report_path1)
    report2 = load_test_case_report(report_path2)

    if "error" in report1 or "error" in report2:
        return {"error": report1.get("error") or report2.get("error")}

    analysis1 = analyze_test_case_report(report1)
    analysis2 = analyze_test_case_report(report2)

    comparison = {
        "report1": {"path": report_path1, "analysis": analysis1},
        "report2": {"path": report_path2, "analysis": analysis2},
        "differences": {
            "test_cases": {
                "report1": analysis1["summary"]["total_test_cases"],
                "report2": analysis2["summary"]["total_test_cases"],
                "change": analysis2["summary"]["total_test_cases"]
                - analysis1["summary"]["total_test_cases"],
            },
            "constraints": {
                "report1": analysis1["summary"]["total_constraints"],
                "report2": analysis2["summary"]["total_constraints"],
                "change": analysis2["summary"]["total_constraints"]
                - analysis1["summary"]["total_constraints"],
            },
            "validation_scripts": {
                "report1": analysis1["summary"]["total_validation_scripts"],
                "report2": analysis2["summary"]["total_validation_scripts"],
                "change": analysis2["summary"]["total_validation_scripts"]
                - analysis1["summary"]["total_validation_scripts"],
            },
            "coverage_rate": {
                "report1": analysis1["constraint_coverage"]["coverage_rate"],
                "report2": analysis2["constraint_coverage"]["coverage_rate"],
                "change": analysis2["constraint_coverage"]["coverage_rate"]
                - analysis1["constraint_coverage"]["coverage_rate"],
            },
            "quality_score": {
                "report1": analysis1["quality_metrics"]["overall_quality_score"],
                "report2": analysis2["quality_metrics"]["overall_quality_score"],
                "change": analysis2["quality_metrics"]["overall_quality_score"]
                - analysis1["quality_metrics"]["overall_quality_score"],
            },
        },
    }

    return comparison


# Helper functions


def _calculate_scripts_per_test_case(test_case_data: Dict[str, Any]) -> float:
    """Calculate average number of scripts per test case."""
    test_cases = test_case_data.get("test_cases", [])
    if not test_cases:
        return 0.0

    total_scripts = sum(len(tc.get("validation_scripts", [])) for tc in test_cases)
    return round(total_scripts / len(test_cases), 2)


def _calculate_constraints_per_test_case(test_case_data: Dict[str, Any]) -> float:
    """Calculate average number of constraints per test case."""
    constraints = len(test_case_data.get("constraints", []))
    test_cases = len(test_case_data.get("test_cases", []))

    if test_cases == 0:
        return 0.0

    return round(constraints / test_cases, 2)


def _calculate_percentages(counter: Counter) -> Dict[str, float]:
    """Calculate percentages from a Counter object."""
    total = sum(counter.values())
    if total == 0:
        return {}

    return {key: round(count / total * 100, 2) for key, count in counter.items()}


def _calculate_script_complexity(code: str) -> int:
    """Calculate a simple complexity score for a script."""
    if not code:
        return 0

    complexity = 0
    complexity += code.count("if ") * 2
    complexity += code.count("for ") * 3
    complexity += code.count("while ") * 3
    complexity += code.count("try:") * 2
    complexity += code.count("except") * 2
    complexity += code.count("isinstance") * 1
    complexity += code.count("get(") * 1
    complexity += len(code.split("\n"))  # Lines of code

    return complexity


def _get_quality_grade(score: float) -> str:
    """Convert quality score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
