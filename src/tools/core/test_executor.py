# tools/core/test_executor.py

import asyncio
import time
from typing import Dict, Optional
from urllib.parse import urljoin

from ...core.base_tool import BaseTool
from ...schemas.tools.test_executor import (
    TestExecutorInput,
    TestExecutorOutput,
    TestCaseExecutionResult,
    TestSuiteExecutionResult,
)
from ...schemas.tools.test_case_generator import TestCase
from ...schemas.tools.test_suite_generator import TestSuite
from ...schemas.tools.code_executor import CodeExecutorInput
from ...schemas.tools.rest_api_caller import RestApiCallerInput, RestRequest
from .code_executor import CodeExecutorTool
from .rest_api_caller import RestApiCallerTool
from ...common.logger import LoggerFactory, LoggerType, LogLevel


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
        }

        self.logger.info(
            f"Execution complete: {total_passed}/{total_tests} tests passed "
            f"({execution_summary['pass_rate']:.1f}%) in {total_execution_time:.2f}s"
        )

        return TestExecutorOutput(
            execution_summary=execution_summary,
            test_suite_results=test_suite_results,
            total_execution_time=total_execution_time,
            overall_passed=overall_passed,
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

        self.logger.info(
            f"Test suite {test_suite.name} completed: {passed_tests}/{len(test_case_results)} passed "
            f"in {execution_time:.2f}s"
        )

        return TestSuiteExecutionResult(
            test_suite_id=test_suite.id,
            test_suite_name=test_suite.name,
            total_tests=len(test_case_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            execution_time=execution_time,
            test_case_results=test_case_results,
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
                    # status_code_passed=status_code_passed,
                    # validation_passed=validation_passed,
                    error_message=(
                        None
                        if test_passed
                        else f"Expected status code {test_case.expected_status_code}, got {status_code}"
                    ),
                )

            for script in test_case.validation_scripts:
                try:
                    # Create request and response objects for validation script
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

                    # Prepare complete validation script with function call
                    script_code = script.validation_code

                    # Extract function name from the validation script
                    import re

                    func_match = re.search(r"def (\w+)\(", script_code)
                    if func_match:
                        func_name = func_match.group(1)
                        # Add code to call the function and return the result
                        full_script = f"""{script_code}

# Execute the validation function
try:
    result = {func_name}(request, response)
    print(result)
except Exception as e:
    print(f"Error in validation: {{e}}")
    result = False
"""
                    else:
                        # Fallback if function name cannot be extracted
                        full_script = f"""{script_code}

# Fallback execution
try:
    # Assume the last defined function is the validation function
    result = False
    print(result)
except Exception as e:
    print(f"Error in validation: {{e}}")
    result = False
"""

                    # Prepare context for validation script
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

                    # Execute validation script
                    code_input = CodeExecutorInput(
                        code=full_script,
                        context_variables=context_vars,
                        timeout=inp.timeout,
                    )

                    script_result = await self.code_executor.execute(code_input)
                    script_passed = (
                        script_result.success
                        and self._extract_boolean_result(script_result.stdout)
                    )

                    validation_results.append(
                        {
                            "script_id": script.id,
                            "script_name": script.name,
                            "passed": script_passed,
                            "result": script_result.stdout,
                            "error": script_result.error,
                            "description": script.description,
                        }
                    )

                    if not script_passed:
                        validation_passed = False

                except Exception as e:
                    self.logger.error(
                        f"Error executing validation script {script.id}: {str(e)}"
                    )
                    validation_results.append(
                        {
                            "script_id": script.id,
                            "script_name": script.name,
                            "passed": False,
                            "result": None,
                            "error": str(e),
                            "description": script.description,
                        }
                    )
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
                # status_code_passed=status_code_passed,
                # validation_passed=validation_passed,
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

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up TestExecutorTool resources")

        # Cleanup sub-tools
        if hasattr(self.code_executor, "cleanup"):
            await self.code_executor.cleanup()

        if hasattr(self.rest_api_caller, "cleanup"):
            await self.rest_api_caller.cleanup()
