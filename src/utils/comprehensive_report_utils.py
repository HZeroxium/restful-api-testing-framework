# utils/comprehensive_report_utils.py

"""
Comprehensive reporting utilities for the API testing framework.
This module provides functions to save detailed reports with constraints,
test data, validation scripts, and execution results in a structured format.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from common.logger import LoggerFactory, LoggerType, LogLevel
from schemas.tools.constraint_miner import ApiConstraint
from schemas.tools.test_data_generator import TestData
from schemas.tools.test_script_generator import ValidationScript
from schemas.tools.test_executor import (
    TestSuiteExecutionResult,
    TestCaseExecutionResult,
)
from config.report_config import ReportingConfig, ReportConstants, get_config

# Initialize logger
logger = LoggerFactory.get_logger(
    name="utils.comprehensive_report_utils",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
)


@dataclass
class ReportConfig:
    """Configuration for comprehensive reporting."""

    base_output_dir: str = "test_reports"
    timestamp_format: str = "%Y%m%d_%H%M%S"
    include_verbose_details: bool = True
    save_raw_data: bool = True
    create_human_readable: bool = True

    @classmethod
    def from_reporting_config(cls, config: ReportingConfig) -> "ReportConfig":
        """Create ReportConfig from ReportingConfig."""
        return cls(
            base_output_dir=config.BASE_OUTPUT_DIR,
            timestamp_format=config.TIMESTAMP_FORMAT,
            include_verbose_details=config.INCLUDE_VERBOSE_DETAILS,
            save_raw_data=config.SAVE_RAW_DATA,
            create_human_readable=config.CREATE_HUMAN_READABLE,
        )


class ComprehensiveReportGenerator:
    """
    Generator for comprehensive test reports with detailed information
    about constraints, test data, validation scripts, and execution results.
    """

    def __init__(self, config: Optional[ReportConfig] = None, verbose: bool = False):
        self.config = config or ReportConfig()
        self.verbose = verbose

        # Initialize logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="utils.comprehensive_report_generator",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    def create_report_structure(
        self, api_name: str, api_version: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Create the comprehensive report directory structure.

        Args:
            api_name: Name of the API
            api_version: Version of the API

        Returns:
            Tuple of (base_report_dir, directory_structure)
        """
        timestamp = datetime.now().strftime(self.config.timestamp_format)
        base_report_dir = os.path.join(
            self.config.base_output_dir, f"{timestamp}_{api_name}_v{api_version}"
        )

        # Get report structure from centralized config
        reporting_config = get_config()
        directories = reporting_config.get_report_structure(base_report_dir)

        # Create all directories
        for dir_path in directories.values():
            os.makedirs(dir_path, exist_ok=True)

        self.logger.info(
            f"Created comprehensive report structure at: {base_report_dir}"
        )
        return base_report_dir, directories

    def save_constraints_report(
        self,
        constraints: List[ApiConstraint],
        endpoint_info: Dict[str, Any],
        output_dir: str,
        endpoint_name: str,
    ) -> str:
        """
        Save detailed constraints report for an endpoint.

        Args:
            constraints: List of constraints for the endpoint
            endpoint_info: Endpoint information
            output_dir: Output directory for constraints
            endpoint_name: Safe name for the endpoint

        Returns:
            Path to the saved constraints report
        """
        # Create endpoint-specific directory
        endpoint_dir = os.path.join(output_dir, endpoint_name)
        os.makedirs(endpoint_dir, exist_ok=True)

        # Group constraints by type
        constraints_by_type = {}
        for constraint in constraints:
            constraint_type = constraint.type
            if constraint_type not in constraints_by_type:
                constraints_by_type[constraint_type] = []
            constraints_by_type[constraint_type].append(constraint)

        # Save detailed constraints
        reporting_config = get_config()
        constraints_file = os.path.join(endpoint_dir, reporting_config.CONSTRAINTS_FILE)
        constraints_data = {
            "endpoint_info": {
                "path": endpoint_info.get("path"),
                "method": endpoint_info.get("method"),
                "name": endpoint_info.get("name"),
                "description": endpoint_info.get("description"),
            },
            "constraints_summary": {
                "total_constraints": len(constraints),
                "constraints_by_type": {
                    constraint_type: len(constraint_list)
                    for constraint_type, constraint_list in constraints_by_type.items()
                },
            },
            "constraints_by_type": {},
        }

        # Add detailed constraints by type
        for constraint_type, constraint_list in constraints_by_type.items():
            constraints_data["constraints_by_type"][constraint_type] = [
                {
                    "id": constraint.id,
                    "description": constraint.description,
                    "details": constraint.details,
                    "severity": constraint.severity,
                    "source": constraint.source,
                    "examples": getattr(
                        constraint, "examples", constraint.details.get("examples", [])
                    ),
                }
                for constraint in constraint_list
            ]

        with open(constraints_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            json.dump(constraints_data, f, indent=2, default=str)

        # Save human-readable constraints summary
        if self.config.create_human_readable:
            summary_file = os.path.join(
                endpoint_dir, reporting_config.CONSTRAINTS_SUMMARY_FILE
            )
            self._create_constraints_markdown(constraints_data, summary_file)

        self.logger.debug(
            f"Saved constraints report for {endpoint_name}: {constraints_file}"
        )
        return constraints_file

    def save_test_data_report(
        self,
        test_data_collection: List[TestData],
        verification_scripts: List[ValidationScript],
        verified_test_data: List[TestData],
        filtered_count: int,
        output_dir: str,
        endpoint_name: str,
    ) -> str:
        """
        Save detailed test data report including verification results.

        Args:
            test_data_collection: All generated test data
            verification_scripts: Scripts used for verification
            verified_test_data: Test data that passed verification
            filtered_count: Number of filtered test data items
            output_dir: Output directory for test data
            endpoint_name: Safe name for the endpoint

        Returns:
            Path to the saved test data report
        """
        # Create endpoint-specific directory
        endpoint_dir = os.path.join(output_dir, endpoint_name)
        os.makedirs(endpoint_dir, exist_ok=True)

        # Save test data report
        reporting_config = get_config()
        test_data_file = os.path.join(endpoint_dir, reporting_config.TEST_DATA_FILE)
        test_data_report = {
            "generation_summary": {
                "total_generated": len(test_data_collection),
                "total_verified": len(verified_test_data),
                "filtered_count": filtered_count,
                "verification_success_rate": (
                    (len(verified_test_data) / len(test_data_collection) * 100)
                    if test_data_collection
                    else 0
                ),
            },
            "verification_scripts": [
                {
                    "id": script.id,
                    "name": script.name,
                    "script_type": script.script_type,
                    "description": script.description,
                    "validation_code": script.validation_code,
                }
                for script in verification_scripts
            ],
            "generated_test_data": [
                {
                    "id": data.id,
                    "name": data.name,
                    "description": data.description,
                    "expected_status_code": data.expected_status_code,
                    "request_params": data.request_params,
                    "request_headers": data.request_headers,
                    "request_body": data.request_body,
                    "expected_response_schema": data.expected_response_schema,
                    "expected_response_contains": data.expected_response_contains,
                    "verification_status": (
                        "verified" if data in verified_test_data else "filtered"
                    ),
                }
                for data in test_data_collection
            ],
            "verified_test_data": [
                {
                    "id": data.id,
                    "name": data.name,
                    "description": data.description,
                    "expected_status_code": data.expected_status_code,
                    "request_params": data.request_params,
                    "request_headers": data.request_headers,
                    "request_body": data.request_body,
                    "expected_response_schema": data.expected_response_schema,
                    "expected_response_contains": data.expected_response_contains,
                }
                for data in verified_test_data
            ],
        }

        with open(test_data_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            json.dump(test_data_report, f, indent=2, default=str)

        # Save human-readable test data summary
        if self.config.create_human_readable:
            summary_file = os.path.join(
                endpoint_dir, reporting_config.TEST_DATA_SUMMARY_FILE
            )
            self._create_test_data_markdown(test_data_report, summary_file)

        self.logger.debug(
            f"Saved test data report for {endpoint_name}: {test_data_file}"
        )
        return test_data_file

    def save_validation_scripts_report(
        self,
        validation_scripts: List[ValidationScript],
        output_dir: str,
        endpoint_name: str,
    ) -> str:
        """
        Save detailed validation scripts report.

        Args:
            validation_scripts: All validation scripts for the endpoint
            output_dir: Output directory for validation scripts
            endpoint_name: Safe name for the endpoint

        Returns:
            Path to the saved validation scripts report
        """
        # Create endpoint-specific directory
        endpoint_dir = os.path.join(output_dir, endpoint_name)
        os.makedirs(endpoint_dir, exist_ok=True)

        # Group scripts by type
        scripts_by_type = {}
        for script in validation_scripts:
            script_type = script.script_type
            if script_type not in scripts_by_type:
                scripts_by_type[script_type] = []
            scripts_by_type[script_type].append(script)

        # Save validation scripts report
        reporting_config = get_config()
        scripts_file = os.path.join(
            endpoint_dir, reporting_config.VALIDATION_SCRIPTS_FILE
        )
        scripts_report = {
            "scripts_summary": {
                "total_scripts": len(validation_scripts),
                "scripts_by_type": {
                    script_type: len(script_list)
                    for script_type, script_list in scripts_by_type.items()
                },
            },
            "scripts_by_type": {},
        }

        # Add detailed scripts by type
        for script_type, script_list in scripts_by_type.items():
            scripts_report["scripts_by_type"][script_type] = [
                {
                    "id": script.id,
                    "name": script.name,
                    "description": script.description,
                    "validation_code": script.validation_code,
                    "constraint_id": script.constraint_id,
                }
                for script in script_list
            ]

        with open(scripts_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            json.dump(scripts_report, f, indent=2, default=str)

        # Save individual script files for easy access
        scripts_dir = os.path.join(
            endpoint_dir, reporting_config.INDIVIDUAL_SCRIPTS_SUBDIR
        )
        os.makedirs(scripts_dir, exist_ok=True)

        for script in validation_scripts:
            script_file = os.path.join(
                scripts_dir, f"{script.id}{reporting_config.SCRIPT_FILE_EXTENSION}"
            )
            with open(script_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
                f.write(f"# Validation Script: {script.name}\n")
                f.write(f"# Description: {script.description}\n")
                f.write(f"# Type: {script.script_type}\n")
                f.write(f"# Constraint ID: {script.constraint_id}\n\n")
                f.write(script.validation_code)

        self.logger.debug(
            f"Saved validation scripts report for {endpoint_name}: {scripts_file}"
        )
        return scripts_file

    def save_execution_report(
        self,
        suite_result: TestSuiteExecutionResult,
        output_dir: str,
        endpoint_name: str,
    ) -> str:
        """
        Save detailed execution report for a test suite.

        Args:
            suite_result: Test suite execution result
            output_dir: Output directory for execution results
            endpoint_name: Safe name for the endpoint

        Returns:
            Path to the saved execution report
        """
        # Create endpoint-specific directory
        endpoint_dir = os.path.join(output_dir, endpoint_name)
        os.makedirs(endpoint_dir, exist_ok=True)

        # Save execution report
        reporting_config = get_config()
        execution_file = os.path.join(
            endpoint_dir, reporting_config.EXECUTION_RESULTS_FILE
        )
        execution_report = {
            "execution_summary": {
                "test_suite_id": suite_result.test_suite_id,
                "test_suite_name": suite_result.test_suite_name,
                "endpoint_path": suite_result.endpoint_path,
                "total_tests": suite_result.total_tests,
                "passed_tests": suite_result.passed_tests,
                "failed_tests": suite_result.failed_tests,
                "execution_time": suite_result.execution_time,
                "total_validation_scripts": suite_result.total_validation_scripts,
                "passed_validation_scripts": suite_result.passed_validation_scripts,
                "failed_validation_scripts": suite_result.failed_validation_scripts,
                "success_rate": (
                    (suite_result.passed_tests / suite_result.total_tests * 100)
                    if suite_result.total_tests > 0
                    else 0
                ),
                "validation_success_rate": (
                    (
                        suite_result.passed_validation_scripts
                        / suite_result.total_validation_scripts
                        * 100
                    )
                    if suite_result.total_validation_scripts > 0
                    else 0
                ),
            },
            "test_case_results": [],
            "failed_test_cases": [],
            "validation_failures": [],
        }

        # Process test case results
        for case_result in suite_result.test_case_results:
            case_data = {
                "test_case_id": case_result.test_case_id,
                "test_case_name": case_result.test_case_name,
                "passed": case_result.passed,
                "status_code": case_result.status_code,
                "expected_status_code": case_result.expected_status_code,
                "status_code_passed": case_result.status_code_passed,
                "validation_passed": case_result.validation_passed,
                "response_time": case_result.response_time,
                "error_message": case_result.error_message,
                "request_details": case_result.request_details,
                "response_body": case_result.response_body,
                "response_headers": case_result.response_headers,
                "validation_results": [
                    {
                        "script_id": val.script_id,
                        "script_name": val.script_name,
                        "passed": val.passed,
                        "result": val.result,
                        "error": val.error,
                        "description": val.description,
                        "execution_success": val.execution_success,
                        "execution_time": val.execution_time,
                    }
                    for val in case_result.validation_results
                ],
            }

            execution_report["test_case_results"].append(case_data)

            # Add to failed test cases if failed
            if not case_result.passed:
                execution_report["failed_test_cases"].append(case_data)

            # Add validation failures
            for val in case_result.validation_results:
                if not val.passed:
                    execution_report["validation_failures"].append(
                        {
                            "test_case_id": case_result.test_case_id,
                            "test_case_name": case_result.test_case_name,
                            "script_id": val.script_id,
                            "script_name": val.script_name,
                            "error": val.error,
                            "description": val.description,
                            "result": val.result,
                        }
                    )

        with open(execution_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            json.dump(execution_report, f, indent=2, default=str)

        # Save human-readable execution summary
        if self.config.create_human_readable:
            summary_file = os.path.join(
                endpoint_dir, reporting_config.EXECUTION_SUMMARY_FILE
            )
            self._create_execution_markdown(execution_report, summary_file)

        self.logger.debug(
            f"Saved execution report for {endpoint_name}: {execution_file}"
        )
        return execution_file

    def save_overall_summary(
        self,
        api_name: str,
        api_version: str,
        test_suite_results: List[TestSuiteExecutionResult],
        execution_summary: Dict[str, Any],
        output_dir: str,
    ) -> str:
        """
        Save overall summary report for the entire test execution.

        Args:
            api_name: Name of the API
            api_version: Version of the API
            test_suite_results: Results from all test suites
            execution_summary: Overall execution summary
            output_dir: Output directory for summary

        Returns:
            Path to the saved overall summary report
        """
        reporting_config = get_config()
        summary_file = os.path.join(output_dir, reporting_config.OVERALL_SUMMARY_FILE)

        # Create comprehensive summary
        overall_summary = {
            "api_info": {
                "name": api_name,
                "version": api_version,
                "test_timestamp": datetime.now().isoformat(),
            },
            "execution_summary": execution_summary,
            "test_suites_summary": [
                {
                    "test_suite_id": suite.test_suite_id,
                    "test_suite_name": suite.test_suite_name,
                    "endpoint_path": suite.endpoint_path,
                    "total_tests": suite.total_tests,
                    "passed_tests": suite.passed_tests,
                    "failed_tests": suite.failed_tests,
                    "execution_time": suite.execution_time,
                    "total_validation_scripts": suite.total_validation_scripts,
                    "passed_validation_scripts": suite.passed_validation_scripts,
                    "failed_validation_scripts": suite.failed_validation_scripts,
                    "success_rate": (
                        (suite.passed_tests / suite.total_tests * 100)
                        if suite.total_tests > 0
                        else 0
                    ),
                }
                for suite in test_suite_results
            ],
            "quality_metrics": {
                "average_success_rate": (
                    sum(
                        (
                            (suite.passed_tests / suite.total_tests * 100)
                            if suite.total_tests > 0
                            else 0
                        )
                        for suite in test_suite_results
                    )
                    / len(test_suite_results)
                    if test_suite_results
                    else 0
                ),
                "average_validation_success_rate": (
                    sum(
                        (
                            (
                                suite.passed_validation_scripts
                                / suite.total_validation_scripts
                                * 100
                            )
                            if suite.total_validation_scripts > 0
                            else 0
                        )
                        for suite in test_suite_results
                    )
                    / len(test_suite_results)
                    if test_suite_results
                    else 0
                ),
                "total_endpoints_tested": len(test_suite_results),
                "total_execution_time": sum(
                    suite.execution_time for suite in test_suite_results
                ),
            },
        }

        with open(summary_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            json.dump(overall_summary, f, indent=2, default=str)

        # Save human-readable overall summary
        if self.config.create_human_readable:
            markdown_file = os.path.join(
                output_dir, reporting_config.OVERALL_SUMMARY_MD_FILE
            )
            self._create_overall_summary_markdown(overall_summary, markdown_file)

        self.logger.info(f"Saved overall summary report: {summary_file}")
        return summary_file

    def _create_constraints_markdown(
        self, constraints_data: Dict[str, Any], output_file: str
    ):
        """Create human-readable markdown report for constraints."""
        with open(output_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            f.write(f"# Constraints Report\n\n")
            f.write(
                f"**Endpoint:** {constraints_data['endpoint_info']['method'].upper()} {constraints_data['endpoint_info']['path']}\n\n"
            )
            f.write(
                f"**Total Constraints:** {constraints_data['constraints_summary']['total_constraints']}\n\n"
            )

            f.write("## Constraints by Type\n\n")
            for constraint_type, constraints in constraints_data[
                "constraints_by_type"
            ].items():
                f.write(
                    f"### {constraint_type.replace('_', ' ').title()} ({len(constraints)} constraints)\n\n"
                )
                for i, constraint in enumerate(constraints, 1):
                    f.write(f"**{i}. {constraint['id']}**\n")
                    f.write(f"- **Description:** {constraint['description']}\n")
                    f.write(f"- **Severity:** {constraint['severity']}\n")
                    f.write(f"- **Source:** {constraint['source']}\n")
                    if constraint.get("examples"):
                        f.write(
                            f"- **Examples:** {', '.join(constraint['examples'])}\n"
                        )
                    f.write("\n")
                f.write("\n")

    def _create_test_data_markdown(
        self, test_data_report: Dict[str, Any], output_file: str
    ):
        """Create human-readable markdown report for test data."""
        with open(output_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            f.write(f"# Test Data Report\n\n")
            summary = test_data_report["generation_summary"]
            f.write(f"**Total Generated:** {summary['total_generated']}\n")
            f.write(f"**Total Verified:** {summary['total_verified']}\n")
            f.write(f"**Filtered Count:** {summary['filtered_count']}\n")
            f.write(
                f"**Verification Success Rate:** {summary['verification_success_rate']:.1f}%\n\n"
            )

            f.write("## Verification Scripts\n\n")
            for script in test_data_report["verification_scripts"]:
                f.write(f"### {script['name']}\n")
                f.write(f"- **Type:** {script['script_type']}\n")
                f.write(f"- **Description:** {script['description']}\n")
                f.write(f"- **ID:** {script['id']}\n\n")

            f.write("## Test Data Summary\n\n")
            f.write(
                f"**Verified Test Data:** {len(test_data_report['verified_test_data'])}\n"
            )
            f.write(
                f"**Generated Test Data:** {len(test_data_report['generated_test_data'])}\n\n"
            )

    def _create_execution_markdown(
        self, execution_report: Dict[str, Any], output_file: str
    ):
        """Create human-readable markdown report for execution results."""
        with open(output_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            f.write(f"# Test Execution Report\n\n")
            summary = execution_report["execution_summary"]
            f.write(f"**Test Suite:** {summary['test_suite_name']}\n")
            f.write(f"**Endpoint:** {summary['endpoint_path']}\n")
            f.write(f"**Total Tests:** {summary['total_tests']}\n")
            f.write(f"**Passed Tests:** {summary['passed_tests']}\n")
            f.write(f"**Failed Tests:** {summary['failed_tests']}\n")
            f.write(f"**Success Rate:** {summary['success_rate']:.1f}%\n")
            f.write(f"**Execution Time:** {summary['execution_time']:.2f}s\n\n")

            f.write("## Validation Scripts Summary\n\n")
            f.write(
                f"**Total Validation Scripts:** {summary['total_validation_scripts']}\n"
            )
            f.write(
                f"**Passed Validation Scripts:** {summary['passed_validation_scripts']}\n"
            )
            f.write(
                f"**Failed Validation Scripts:** {summary['failed_validation_scripts']}\n"
            )
            f.write(
                f"**Validation Success Rate:** {summary['validation_success_rate']:.1f}%\n\n"
            )

            if execution_report["failed_test_cases"]:
                f.write("## Failed Test Cases\n\n")
                for failed_case in execution_report["failed_test_cases"]:
                    f.write(f"### {failed_case['test_case_name']}\n")
                    f.write(
                        f"- **Status Code:** {failed_case['status_code']} (Expected: {failed_case['expected_status_code']})\n"
                    )
                    f.write(f"- **Error:** {failed_case['error_message']}\n")
                    f.write(
                        f"- **Response Time:** {failed_case['response_time']:.3f}s\n\n"
                    )

            if execution_report["validation_failures"]:
                f.write("## Validation Failures\n\n")
                for failure in execution_report["validation_failures"]:
                    f.write(
                        f"### {failure['test_case_name']} - {failure['script_name']}\n"
                    )
                    f.write(f"- **Error:** {failure['error']}\n")
                    f.write(f"- **Result:** {failure['result']}\n")
                    f.write(f"- **Description:** {failure['description']}\n\n")

    def _create_overall_summary_markdown(
        self, overall_summary: Dict[str, Any], output_file: str
    ):
        """Create human-readable markdown report for overall summary."""
        with open(output_file, "w", encoding=ReportConstants.ENCODING_UTF8) as f:
            f.write(f"# Overall Test Summary\n\n")
            api_info = overall_summary["api_info"]
            f.write(f"**API:** {api_info['name']} v{api_info['version']}\n")
            f.write(f"**Test Timestamp:** {api_info['test_timestamp']}\n\n")

            exec_summary = overall_summary["execution_summary"]
            f.write("## Execution Summary\n\n")
            f.write(f"**Total Test Suites:** {exec_summary['total_test_suites']}\n")
            f.write(f"**Total Tests:** {exec_summary['total_tests']}\n")
            f.write(f"**Passed Tests:** {exec_summary['total_passed']}\n")
            f.write(f"**Failed Tests:** {exec_summary['total_failed']}\n")
            f.write(f"**Pass Rate:** {exec_summary['pass_rate']:.1f}%\n")
            f.write(
                f"**Total Execution Time:** {exec_summary['execution_time']:.2f}s\n\n"
            )

            metrics = overall_summary["quality_metrics"]
            f.write("## Quality Metrics\n\n")
            f.write(
                f"**Average Success Rate:** {metrics['average_success_rate']:.1f}%\n"
            )
            f.write(
                f"**Average Validation Success Rate:** {metrics['average_validation_success_rate']:.1f}%\n"
            )
            f.write(
                f"**Total Endpoints Tested:** {metrics['total_endpoints_tested']}\n"
            )
            f.write(
                f"**Total Execution Time:** {metrics['total_execution_time']:.2f}s\n\n"
            )

            f.write("## Test Suites Summary\n\n")
            for suite in overall_summary["test_suites_summary"]:
                f.write(f"### {suite['test_suite_name']}\n")
                f.write(f"- **Endpoint:** {suite['endpoint_path']}\n")
                f.write(
                    f"- **Tests:** {suite['passed_tests']}/{suite['total_tests']} passed ({suite['success_rate']:.1f}%)\n"
                )
                f.write(f"- **Execution Time:** {suite['execution_time']:.2f}s\n\n")


def create_safe_endpoint_name(endpoint_info: Dict[str, Any]) -> str:
    """
    Create a safe filename from endpoint information.

    Args:
        endpoint_info: Endpoint information dictionary

    Returns:
        Safe filename string
    """
    method = endpoint_info.get("method", "unknown").upper()
    path = endpoint_info.get("path", "unknown")
    name = endpoint_info.get("name")

    # Use centralized config for safe name generation
    reporting_config = get_config()
    return reporting_config.get_endpoint_safe_name(method, path, name)
