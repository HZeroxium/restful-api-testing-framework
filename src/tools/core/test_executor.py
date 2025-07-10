# tools/core/test_executor.py

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from urllib.parse import urljoin

from ...core.base_tool import BaseTool
from ...schemas.tools.test_executor import (
    TestExecutorInput,
    TestExecutorOutput,
    TestCaseExecutionResult,
    TestSuiteExecutionResult,
    ValidationScriptResult,
)
from ...schemas.tools.test_case_generator import TestCase
from ...schemas.tools.test_suite_generator import TestSuite
from ...schemas.tools.code_executor import CodeExecutorInput
from ...schemas.tools.rest_api_caller import RestApiCallerInput, RestRequest
from ...schemas.tools.constraint_miner import ApiConstraint
from .code_executor import CodeExecutorTool
from .rest_api_caller import RestApiCallerTool
from ...common.logger import LoggerFactory, LoggerType, LogLevel
from ...utils.code_script_utils import prepare_validation_script
from ...utils.comprehensive_report_utils import (
    ComprehensiveReportGenerator,
    ReportConfig,
)


class TestExecutorTool(BaseTool):
    """
    Tool for executing test suites and aggregating results.

    This tool:
    1. Executes HTTP requests for each test case
    2. Runs validation scripts on responses
    3. Aggregates results by test suite
    4. Provides comprehensive execution reporting
    """

    def __init__(
        self,
        *,
        name: str = "test_executor",
        description: str = "Executes test suites and aggregates results",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestExecutorInput,
            output_schema=TestExecutorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize sub-tools
        self.code_executor = CodeExecutorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        self.rest_api_caller = RestApiCallerTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config={"timeout": 30},  # Default timeout
        )

        # Initialize comprehensive report generator
        self.report_generator = ComprehensiveReportGenerator(
            config=ReportConfig(
                base_output_dir="test_reports",
                include_verbose_details=verbose,
                save_raw_data=True,
                create_human_readable=True,
            ),
            verbose=verbose,
        )

    async def _execute(self, inp: TestExecutorInput) -> TestExecutorOutput:
        """Execute test suites and aggregate results."""
        start_time = time.time()

        self.logger.info(f"Starting execution of {len(inp.test_suites)} test suites")
        self.logger.add_context(
            base_url=inp.base_url,
            parallel_execution=inp.parallel_execution,
            max_concurrent=inp.max_concurrent_requests,
        )

        # Execute test suites
        test_suite_results = []

        if inp.parallel_execution:
            # Execute test suites in parallel
            semaphore = asyncio.Semaphore(inp.max_concurrent_requests)
            tasks = [
                self._execute_test_suite_with_semaphore(test_suite, inp, semaphore)
                for test_suite in inp.test_suites
            ]
            test_suite_results = await asyncio.gather(*tasks)
        else:
            # Execute test suites sequentially
            for test_suite in inp.test_suites:
                result = await self._execute_test_suite(test_suite, inp)
                test_suite_results.append(result)

        total_execution_time = time.time() - start_time

        # Calculate overall statistics
        total_tests = sum(result.total_tests for result in test_suite_results)
        total_passed = sum(result.passed_tests for result in test_suite_results)
        total_failed = sum(result.failed_tests for result in test_suite_results)
        overall_passed = total_failed == 0

        execution_summary = {
            "total_test_suites": len(inp.test_suites),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
            "execution_time": total_execution_time,
            "total_validation_scripts": sum(
                result.total_validation_scripts for result in test_suite_results
            ),
            "passed_validation_scripts": sum(
                result.passed_validation_scripts for result in test_suite_results
            ),
            "failed_validation_scripts": sum(
                result.failed_validation_scripts for result in test_suite_results
            ),
        }

        self.logger.info(
            f"Execution complete: {total_passed}/{total_tests} tests passed "
            f"({execution_summary['pass_rate']:.1f}%) in {total_execution_time:.2f}s"
        )

        # Save results if requested
        output_directory = None
        saved_files = []

        if inp.save_results:
            try:
                output_directory, saved_files = (
                    await self._save_comprehensive_execution_results(
                        test_suite_results,
                        execution_summary,
                        inp.output_directory,
                        inp.comprehensive_report_data,
                    )
                )
                self.logger.info(f"Results saved to: {output_directory}")
            except Exception as e:
                self.logger.error(f"Failed to save results: {str(e)}")
                # Fallback to basic save
                try:
                    output_directory, saved_files = await self._save_execution_results(
                        test_suite_results, execution_summary, inp.output_directory
                    )
                    self.logger.info(f"Basic results saved to: {output_directory}")
                except Exception as e2:
                    self.logger.error(f"Failed to save basic results: {str(e2)}")

        return TestExecutorOutput(
            execution_summary=execution_summary,
            test_suite_results=test_suite_results,
            total_execution_time=total_execution_time,
            overall_passed=overall_passed,
            output_directory=output_directory,
            saved_files=saved_files,
        )

    async def _execute_test_suite_with_semaphore(
        self,
        test_suite: TestSuite,
        inp: TestExecutorInput,
        semaphore: asyncio.Semaphore,
    ) -> TestSuiteExecutionResult:
        """Execute a test suite with semaphore for concurrency control."""
        async with semaphore:
            return await self._execute_test_suite(test_suite, inp)

    async def _execute_test_suite(
        self, test_suite: TestSuite, inp: TestExecutorInput
    ) -> TestSuiteExecutionResult:
        """Execute a single test suite."""
        start_time = time.time()

        self.logger.info(f"Executing test suite: {test_suite.name}")
        self.logger.add_context(
            test_suite_id=test_suite.id,
            test_count=len(test_suite.test_cases),
        )

        # Execute test cases
        test_case_results = []

        if inp.parallel_execution:
            # Execute test cases in parallel
            semaphore = asyncio.Semaphore(inp.max_concurrent_requests)
            tasks = [
                self._execute_test_case_with_semaphore(
                    test_case, inp, semaphore, test_suite.endpoint_info
                )
                for test_case in test_suite.test_cases
            ]
            test_case_results = await asyncio.gather(*tasks)
        else:
            # Execute test cases sequentially
            for test_case in test_suite.test_cases:
                result = await self._execute_test_case(
                    test_case, inp, test_suite.endpoint_info
                )
                test_case_results.append(result)

        execution_time = time.time() - start_time

        # Calculate suite statistics
        passed_tests = sum(1 for result in test_case_results if result.passed)
        failed_tests = len(test_case_results) - passed_tests

        # Calculate validation script statistics
        total_validation_scripts = sum(
            len(result.validation_results) for result in test_case_results
        )
        passed_validation_scripts = sum(
            sum(1 for validation in result.validation_results if validation.passed)
            for result in test_case_results
        )
        failed_validation_scripts = total_validation_scripts - passed_validation_scripts

        self.logger.info(
            f"Test suite {test_suite.name} completed: {passed_tests}/{len(test_case_results)} passed "
            f"({passed_validation_scripts}/{total_validation_scripts} validation scripts passed) "
            f"in {execution_time:.2f}s"
        )

        return TestSuiteExecutionResult(
            test_suite_id=test_suite.id,
            test_suite_name=test_suite.name,
            endpoint_path=(
                test_suite.endpoint_info.path if test_suite.endpoint_info else None
            ),
            total_tests=len(test_case_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            execution_time=execution_time,
            test_case_results=test_case_results,
            total_validation_scripts=total_validation_scripts,
            passed_validation_scripts=passed_validation_scripts,
            failed_validation_scripts=failed_validation_scripts,
        )

    async def _execute_test_case_with_semaphore(
        self,
        test_case: TestCase,
        inp: TestExecutorInput,
        semaphore: asyncio.Semaphore,
        endpoint_info=None,
    ) -> TestCaseExecutionResult:
        """Execute a test case with semaphore for concurrency control."""
        async with semaphore:
            return await self._execute_test_case(test_case, inp, endpoint_info)

    async def _execute_test_case(
        self, test_case: TestCase, inp: TestExecutorInput, endpoint_info=None
    ) -> TestCaseExecutionResult:
        """Execute a single test case."""
        start_time = time.time()

        self.logger.debug(f"Executing test case: {test_case.name}")

        try:
            # Get endpoint path from endpoint_info if provided, otherwise try request params
            if endpoint_info:
                endpoint_path = endpoint_info.path
                method = endpoint_info.method.upper()
            else:
                endpoint_path = test_case.request_params.get("endpoint", "")
                method = test_case.request_params.get("method", "GET").upper()

            # Construct full URL
            if endpoint_path.startswith("/"):
                url = urljoin(inp.base_url.rstrip("/") + "/", endpoint_path.lstrip("/"))
            else:
                url = urljoin(inp.base_url, endpoint_path)

            # Prepare headers
            headers = {**(inp.headers or {}), **(test_case.request_headers or {})}

            # Extract query parameters (not path parameters)
            query_params = {}
            path_params = {}

            if test_case.request_params:
                for key, value in test_case.request_params.items():
                    if key not in ["endpoint", "method"]:
                        # Check if this is a path parameter (exists in URL path)
                        if f"{{{key}}}" in url:
                            path_params[key] = value
                        else:
                            query_params[key] = value

            # Replace path parameters in URL
            for param_name, param_value in path_params.items():
                url = url.replace(f"{{{param_name}}}", str(param_value))

            # Prepare request details for logging
            request_details = {
                "url": url,
                "method": method,
                "headers": headers,
                "query_params": query_params,
                "path_params": path_params,
                "body": test_case.request_body,
            }

            # Execute HTTP request using RestApiCallerTool
            rest_request = RestRequest(
                method=method,
                url=url,
                headers=headers,
                params=query_params,
                json_body=test_case.request_body if test_case.request_body else None,
            )

            rest_input = RestApiCallerInput(request=rest_request)

            request_start = time.time()
            rest_output = await self.rest_api_caller.execute(rest_input)
            response_time = time.time() - request_start

            # Extract response data
            response_body = rest_output.response.body
            response_headers = rest_output.response.headers
            status_code = rest_output.response.status_code

            # Check status code expectation
            status_code_passed = status_code == test_case.expected_status_code

            # Run validation scripts
            validation_results = []
            validation_passed = True

            # Skip validation scripts for error responses (status codes >= 400)
            if test_case.expected_status_code >= 400:
                self.logger.info(
                    f"Skipping validation scripts for test case {test_case.id} "
                    f"(expected status code: {test_case.expected_status_code})"
                )
                # For error responses, only check status code
                test_passed = status_code_passed
                execution_time = time.time() - start_time

                return TestCaseExecutionResult(
                    test_case_id=test_case.id,
                    test_case_name=test_case.name,
                    passed=test_passed,
                    response_time=execution_time,
                    request_details=request_details,
                    status_code=status_code,
                    response_body=response_body,
                    response_headers=response_headers,
                    validation_results=validation_results,
                    expected_status_code=test_case.expected_status_code,
                    status_code_passed=status_code_passed,
                    validation_passed=validation_passed,
                    error_message=(
                        None
                        if test_passed
                        else f"Expected status code {test_case.expected_status_code}, got {status_code}"
                    ),
                )

            # Execute validation scripts for successful responses
            if test_case.validation_scripts:
                self.logger.debug(
                    f"Running {len(test_case.validation_scripts)} validation scripts for test case {test_case.name}"
                )

                # Prepare request and response objects for validation scripts
                request_obj = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "params": query_params,
                    "path_params": path_params,
                    "json": test_case.request_body,
                }

                response_obj = {
                    "status_code": status_code,
                    "headers": response_headers,
                    "body": response_body,
                }

                # Context variables for script execution
                context_vars = {
                    "request": request_obj,
                    "response": response_obj,
                    "test_case": test_case.model_dump(),
                    "response_body": response_body,
                    "response_headers": response_headers,
                    "status_code": status_code,
                    "response_time": response_time,
                    "request_details": request_details,
                }

                # Execute each validation script
                for script in test_case.validation_scripts:
                    script_start_time = time.time()
                    try:
                        self.logger.debug(f"Executing validation script: {script.name}")

                        # Prepare the validation script with execution wrapper
                        prepared_script = prepare_validation_script(
                            script.validation_code
                        )

                        # Execute the prepared script
                        code_input = CodeExecutorInput(
                            code=prepared_script,
                            context_variables=context_vars,
                            timeout=inp.timeout,
                        )

                        script_result = await self.code_executor.execute(code_input)
                        script_execution_time = time.time() - script_start_time

                        # Parse the script result
                        script_passed = self._parse_script_result(
                            script_result, script.name
                        )

                        validation_result = ValidationScriptResult(
                            script_id=script.id,
                            script_name=script.name,
                            passed=script_passed,
                            result=script_result.stdout,
                            error=script_result.error,
                            description=script.description,
                            execution_success=script_result.success,
                            execution_time=script_execution_time,
                        )

                        validation_results.append(validation_result)

                        if not script_passed:
                            validation_passed = False
                            self.logger.warning(
                                f"Validation script {script.name} failed: {script_result.error or 'Script returned False'}"
                            )

                    except Exception as e:
                        script_execution_time = time.time() - script_start_time
                        error_msg = (
                            f"Error executing validation script {script.name}: {str(e)}"
                        )
                        self.logger.error(error_msg)

                        validation_result = ValidationScriptResult(
                            script_id=script.id,
                            script_name=script.name,
                            passed=False,
                            result=None,
                            error=error_msg,
                            description=script.description,
                            execution_success=False,
                            execution_time=script_execution_time,
                        )

                        validation_results.append(validation_result)
                        validation_passed = False

            # Determine overall test result
            test_passed = status_code_passed and validation_passed

            execution_time = time.time() - start_time

            self.logger.debug(
                f"Test case {test_case.name} {'PASSED' if test_passed else 'FAILED'} "
                f"(status: {status_code}, time: {response_time:.3f}s)"
            )

            return TestCaseExecutionResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                passed=test_passed,
                response_time=execution_time,
                request_details=request_details,
                status_code=status_code,
                response_body=response_body,
                response_headers=response_headers,
                validation_results=validation_results,
                expected_status_code=test_case.expected_status_code,
                status_code_passed=status_code_passed,
                validation_passed=validation_passed,
                error_message=None if test_passed else "Validation failed",
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = f"Test execution failed: {str(e)}"

            self.logger.error(f"Test case {test_case.name} FAILED: {error_message}")

            return TestCaseExecutionResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                passed=False,
                status_code=0,
                response_time=execution_time,
                error_message=error_message,
                validation_results=[],
                request_details=(
                    request_details if "request_details" in locals() else {}
                ),
            )

    def _parse_script_result(self, script_result, script_name: str) -> bool:
        """
        Parse the result of a validation script execution.

        Args:
            script_result: The result from code executor
            script_name: Name of the script for logging

        Returns:
            bool: True if script passed, False otherwise
        """
        if not script_result.success:
            self.logger.warning(
                f"Script {script_name} execution failed: {script_result.error}"
            )
            return False

        stdout = script_result.stdout.strip() if script_result.stdout else ""

        if not stdout:
            self.logger.warning(
                f"Script {script_name} produced no output, defaulting to False"
            )
            return False

        # Parse the stdout to determine if the script passed
        return self._extract_boolean_result(stdout)

    def _extract_boolean_result(self, result_string: str) -> bool:
        """Extract boolean result from script execution output."""
        if not result_string:
            return False

        result_lower = result_string.lower().strip()

        # Check for common boolean representations
        if result_lower in ["true", "1", "pass", "passed", "success", "valid"]:
            return True
        elif result_lower in ["false", "0", "fail", "failed", "error", "invalid"]:
            return False

        # Try to parse as boolean
        try:
            return bool(eval(result_string))
        except:
            # If all else fails, check if the result contains positive indicators
            positive_indicators = ["true", "pass", "valid", "success", "ok"]
            return any(indicator in result_lower for indicator in positive_indicators)

    async def _save_execution_results(
        self,
        test_suite_results: List[TestSuiteExecutionResult],
        execution_summary: Dict,
        output_directory: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """
        Save execution results to files in a structured directory.

        Args:
            test_suite_results: Results from test suite execution
            execution_summary: Overall execution summary
            output_directory: Optional output directory path

        Returns:
            Tuple of (output_directory_path, list_of_saved_files)
        """
        # Create output directory with timestamp
        if output_directory is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_directory = f"test_reports/{timestamp}"

        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []

        # Save overall execution summary
        summary_file = output_path / "execution_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(execution_summary, f, indent=2, default=str)
        saved_files.append(str(summary_file))

        # Save detailed results for each test suite
        for suite_result in test_suite_results:
            # Create suite-specific directory
            suite_dir = output_path / f"test_suite_{suite_result.test_suite_id}"
            suite_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            execution_dir = suite_dir / "test_execution"
            execution_dir.mkdir(parents=True, exist_ok=True)

            # Save suite summary
            suite_summary_file = suite_dir / "suite_summary.json"
            suite_summary = {
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
                "execution_timestamp": suite_result.execution_timestamp,
            }

            with open(suite_summary_file, "w", encoding="utf-8") as f:
                json.dump(suite_summary, f, indent=2, default=str)
            saved_files.append(str(suite_summary_file))

            # Save detailed test case results
            test_cases_file = execution_dir / "test_case_results.json"
            test_cases_data = []

            for case_result in suite_result.test_case_results:
                test_case_data = {
                    "test_case_id": case_result.test_case_id,
                    "test_case_name": case_result.test_case_name,
                    "passed": case_result.passed,
                    "status_code": case_result.status_code,
                    "expected_status_code": case_result.expected_status_code,
                    "status_code_passed": case_result.status_code_passed,
                    "validation_passed": case_result.validation_passed,
                    "response_time": case_result.response_time,
                    "error_message": case_result.error_message,
                    "execution_timestamp": case_result.execution_timestamp,
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
                test_cases_data.append(test_case_data)

            with open(test_cases_file, "w", encoding="utf-8") as f:
                json.dump(test_cases_data, f, indent=2, default=str)
            saved_files.append(str(test_cases_file))

            # Save failed test cases separately for easy analysis
            failed_cases = [
                case_data for case_data in test_cases_data if not case_data["passed"]
            ]

            if failed_cases:
                failed_cases_file = execution_dir / "failed_test_cases.json"
                with open(failed_cases_file, "w", encoding="utf-8") as f:
                    json.dump(failed_cases, f, indent=2, default=str)
                saved_files.append(str(failed_cases_file))

        self.logger.info(f"Saved {len(saved_files)} result files to {output_directory}")
        return str(output_path), saved_files

    async def _save_comprehensive_execution_results(
        self,
        test_suite_results: List[TestSuiteExecutionResult],
        execution_summary: Dict,
        output_directory: Optional[str] = None,
        comprehensive_report_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Save comprehensive execution results using the comprehensive report generator.

        Args:
            test_suite_results: Results from test suite execution
            execution_summary: Overall execution summary
            output_directory: Optional output directory path
            comprehensive_report_data: Comprehensive report data from pipeline

        Returns:
            Tuple of (output_directory_path, list_of_saved_files)
        """
        # Use comprehensive report generator for structured reporting
        if comprehensive_report_data and comprehensive_report_data.get("api_info"):
            api_info = comprehensive_report_data["api_info"]
            api_name = api_info.get("api_name", "UnknownAPI")
            api_version = api_info.get("api_version", "1.0")

            # Create comprehensive report structure
            base_report_dir, directories = (
                self.report_generator.create_report_structure(api_name, api_version)
            )

            saved_files = []

            # Save overall summary
            summary_file = self.report_generator.save_overall_summary(
                api_name,
                api_version,
                test_suite_results,
                execution_summary,
                directories["summary"],
            )
            saved_files.append(summary_file)

            # Save detailed reports for each test suite
            for suite_result in test_suite_results:
                if (
                    hasattr(suite_result, "endpoint_path")
                    and suite_result.endpoint_path
                ):
                    # Create safe endpoint name for this suite
                    from ...utils.comprehensive_report_utils import (
                        create_safe_endpoint_name,
                    )

                    endpoint_name = create_safe_endpoint_name(
                        {
                            "method": "GET",  # Default method if not available
                            "path": suite_result.endpoint_path,
                            "name": suite_result.test_suite_name,
                        }
                    )

                    # Find corresponding endpoint data in comprehensive report
                    endpoint_data = None
                    if comprehensive_report_data.get("endpoints_data"):
                        for key, data in comprehensive_report_data[
                            "endpoints_data"
                        ].items():
                            if suite_result.endpoint_path in str(
                                data.get("pipeline_metadata", {}).get(
                                    "endpoint_info", {}
                                )
                            ):
                                endpoint_data = data
                                break

                    # Save constraints report if available
                    if endpoint_data and endpoint_data.get("constraints"):
                        try:
                            constraints_file = (
                                self.report_generator.save_constraints_report(
                                    [
                                        ApiConstraint.model_validate(c)
                                        for c in endpoint_data["constraints"][
                                            "all_constraints"
                                        ]
                                    ],
                                    endpoint_data["pipeline_metadata"]["endpoint_info"],
                                    directories["constraints"],
                                    endpoint_name,
                                )
                            )
                            saved_files.append(constraints_file)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to save constraints report for {endpoint_name}: {str(e)}"
                            )

                    # Save test data report if available
                    if endpoint_data and endpoint_data.get("test_data"):
                        try:
                            from ...schemas.tools.test_data_generator import (
                                TestData,
                            )
                            from ...schemas.tools.test_script_generator import (
                                ValidationScript,
                            )

                            test_data_collection = [
                                TestData.model_validate(td)
                                for td in endpoint_data["test_data"][
                                    "test_data_collection"
                                ]
                            ]
                            verification_scripts = [
                                ValidationScript.model_validate(vs)
                                for vs in endpoint_data["test_data"][
                                    "verification_scripts"
                                ]
                            ]
                            verified_test_data = [
                                TestData.model_validate(td)
                                for td in endpoint_data["test_data"][
                                    "verified_test_data"
                                ]
                            ]

                            test_data_file = (
                                self.report_generator.save_test_data_report(
                                    test_data_collection,
                                    verification_scripts,
                                    verified_test_data,
                                    endpoint_data["test_data"]["filtered_count"],
                                    directories["test_data"],
                                    endpoint_name,
                                )
                            )
                            saved_files.append(test_data_file)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to save test data report for {endpoint_name}: {str(e)}"
                            )

                    # Save validation scripts report if available
                    if endpoint_data and endpoint_data.get("validation_scripts"):
                        try:
                            validation_scripts = [
                                ValidationScript.model_validate(vs)
                                for vs in endpoint_data["validation_scripts"][
                                    "all_validation_scripts"
                                ]
                            ]

                            scripts_file = (
                                self.report_generator.save_validation_scripts_report(
                                    validation_scripts,
                                    directories["validation_scripts"],
                                    endpoint_name,
                                )
                            )
                            saved_files.append(scripts_file)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to save validation scripts report for {endpoint_name}: {str(e)}"
                            )

                    # Save execution report
                    try:
                        execution_file = self.report_generator.save_execution_report(
                            suite_result,
                            directories["test_execution"],
                            endpoint_name,
                        )
                        saved_files.append(execution_file)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to save execution report for {endpoint_name}: {str(e)}"
                        )

            self.logger.info(
                f"Saved comprehensive reports: {len(saved_files)} files in {base_report_dir}"
            )
            return base_report_dir, saved_files

        else:
            # Fallback to basic save if no comprehensive data
            self.logger.warning(
                "No comprehensive report data available, using basic save"
            )
            return await self._save_execution_results(
                test_suite_results, execution_summary, output_directory
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up TestExecutorTool resources")

        # Cleanup sub-tools
        if hasattr(self.code_executor, "cleanup"):
            await self.code_executor.cleanup()

        if hasattr(self.rest_api_caller, "cleanup"):
            await self.rest_api_caller.cleanup()
