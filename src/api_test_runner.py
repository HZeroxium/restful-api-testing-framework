# src/api_test_runner.py

import asyncio
import os
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

from tools import OpenAPIParserTool, RestApiCallerTool, CodeExecutorTool
from tools.test_execution_reporter import TestExecutionReporterTool
from tools.test_collection_generator import TestCollectionGeneratorTool
from utils.rest_api_caller_factory import RestApiCallerFactory

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.rest_api_caller import RestApiCallerOutput
from schemas.tools.test_collection_generator import TestCollectionGeneratorInput
from schemas.tools.test_suite_generator import TestSuite
from schemas.tools.test_execution_reporter import (
    TestExecutionReporterInput,
    TestCaseResult,
    ValidationResult,
    TestStatus,
)
from utils.demo_utils import (
    parse_openapi_spec,
    select_endpoints,
    create_timestamped_output_dir,
    save_summary_file,
    validate_file_exists,
    get_default_spec_path,
    get_user_test_preferences,
    setup_api_factory,
    get_server_url_from_api_info,
)


async def execute_test_suite(
    api_name: str,
    api_version: str,
    test_suite: TestSuite,
    endpoint_tool: RestApiCallerTool,
    verbose: bool = False,
) -> List[TestCaseResult]:
    """
    Execute all test cases in a test suite.

    Args:
        api_name: Name of the API
        api_version: Version of the API
        test_suite: The test suite to execute
        endpoint_tool: Tool to call the endpoint
        verbose: Enable verbose logging

    Returns:
        List of test case results
    """
    endpoint = test_suite.endpoint_info
    if verbose:
        print(
            f"\nExecuting test suite for: [{endpoint.method.upper()}] {endpoint.path}"
        )
        print(f"  Test cases: {len(test_suite.test_cases)}")

    # Initialize the code executor tool for validating scripts
    code_executor = CodeExecutorTool(
        verbose=verbose,
        cache_enabled=False,
        restricted_modules=["os", "sys", "subprocess"],
    )

    test_case_results = []

    for test_case in test_suite.test_cases:
        if verbose:
            print(f"  Running test case: {test_case.name}")

        # Execute the API call
        test_start_time = time.perf_counter()

        try:
            # Prepare parameters for API call
            params = {}

            # Handle request parameters
            if test_case.request_params:
                params.update(test_case.request_params)

            # Handle headers
            if test_case.request_headers:
                for k, v in test_case.request_headers.items():
                    params[f"header_{k}"] = v

            # Handle body
            if test_case.request_body:
                if isinstance(test_case.request_body, dict):
                    params.update(test_case.request_body)
                else:
                    params["body"] = str(test_case.request_body)

            # Execute API call
            if verbose:
                print(
                    f"    Executing API call: {endpoint.method.upper()} {endpoint.path}"
                )

            api_response: RestApiCallerOutput = await endpoint_tool.execute(params)
            test_elapsed_time = time.perf_counter() - test_start_time

            if verbose:
                print(
                    f"    Received response with status code: {api_response.response.status_code}"
                )

            # Run validation scripts
            validation_results = []
            test_status = TestStatus.PASS  # Assume success initially

            for script in test_case.validation_scripts:
                try:
                    # Create context variables for the script execution
                    context_variables = {
                        "request": api_response.request.model_dump(),
                        "response": api_response.response.model_dump(),
                        "expected_status_code": test_case.expected_status_code,
                    }

                    # Extract the main function name from the validation script
                    import re

                    function_match = re.search(
                        r"def\s+([a-zA-Z0-9_]+)\s*\(", script.validation_code
                    )
                    function_name = function_match.group(1) if function_match else None

                    # Add code to call the function and capture the result
                    modified_code = script.validation_code
                    if function_name:
                        # Add code to call the function and print the result so we can capture it
                        modified_code += f"""

# Execute the validation function and capture result
try:
    _validation_result = {function_name}(request, response)
    print(f"VALIDATION_RESULT: {{_validation_result}}")
except Exception as e:
    print(f"VALIDATION_ERROR: {{str(e)}}")
    _validation_result = False
"""

                    # Execute the validation script using CodeExecutorTool
                    from schemas.tools.code_executor import CodeExecutorInput

                    executor_input = CodeExecutorInput(
                        code=modified_code,
                        context_variables=context_variables,
                        timeout=5.0,  # 5 seconds timeout should be enough for validation scripts
                    )

                    if verbose:
                        print(f"    Executing validation script: {script.name}")

                    execution_result = await code_executor.execute(executor_input)

                    # Extract validation result from stdout
                    script_passed = False
                    error_message = "Validation failed"

                    if execution_result.success:
                        # Look for validation result in stdout
                        if execution_result.stdout:
                            stdout_lines = execution_result.stdout.strip().split("\n")
                            for line in stdout_lines:
                                if line.startswith("VALIDATION_RESULT:"):
                                    result_str = line.replace(
                                        "VALIDATION_RESULT:", ""
                                    ).strip()
                                    script_passed = result_str.lower() == "true"
                                    break
                                elif line.startswith("VALIDATION_ERROR:"):
                                    error_message = line.replace(
                                        "VALIDATION_ERROR:", ""
                                    ).strip()
                                    script_passed = False
                                    break

                        # If no explicit result found, check if there were any errors
                        if not any(
                            line.startswith(("VALIDATION_RESULT:", "VALIDATION_ERROR:"))
                            for line in execution_result.stdout.split("\n")
                        ):
                            # Fallback: assume success if no errors and code executed successfully
                            script_passed = True
                            error_message = "Validation passed"
                    else:
                        # Execution failed
                        script_passed = False
                        error_message = (
                            execution_result.error or "Script execution failed"
                        )
                        if execution_result.stderr:
                            error_message += f": {execution_result.stderr}"

                    status = TestStatus.PASS if script_passed else TestStatus.FAIL
                    message = "Validation passed" if script_passed else error_message

                    # If any script fails, the whole test fails
                    if status == TestStatus.FAIL:
                        test_status = TestStatus.FAIL

                    validation_results.append(
                        ValidationResult(
                            script_id=script.id,
                            script_name=script.name,
                            status=status,
                            message=message,
                            validation_code=script.validation_code,
                        )
                    )

                    if verbose:
                        print(f"    Validation '{script.name}': {status}")
                        if status == TestStatus.FAIL:
                            print(f"    Error: {message}")

                except Exception as e:
                    # If an exception occurs, mark as error
                    validation_results.append(
                        ValidationResult(
                            script_id=script.id,
                            script_name=script.name,
                            status=TestStatus.ERROR,
                            message=f"Error executing script: {str(e)}",
                            validation_code=script.validation_code,
                        )
                    )
                    test_status = TestStatus.ERROR
                    if verbose:
                        print(f"    Validation '{script.name}': ERROR - {str(e)}")

            # Create test case result
            test_case_result = TestCaseResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                status=test_status,
                elapsed_time=test_elapsed_time,
                request=api_response.request.model_dump(),
                response=api_response.response.model_dump(),
                validation_results=validation_results,
                message=(
                    "Test completed successfully"
                    if test_status == TestStatus.PASS
                    else "Test failed"
                ),
                # Include the original test data for reference
                test_data={
                    "expected_status_code": test_case.expected_status_code,
                    "request_params": test_case.request_params,
                    "request_headers": test_case.request_headers,
                    "request_body": test_case.request_body,
                    "expected_response_schema": test_case.expected_response_schema,
                    "expected_response_contains": test_case.expected_response_contains,
                },
            )

            if verbose:
                print(f"    Test case status: {test_status}")

            test_case_results.append(test_case_result)

        except Exception as e:
            test_elapsed_time = time.perf_counter() - test_start_time
            # Create a result with error status
            test_case_result = TestCaseResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                status=TestStatus.ERROR,
                elapsed_time=test_elapsed_time,
                request={"error": "API call failed"},
                response={"error": str(e)},
                validation_results=[],
                message=f"Error executing API call: {str(e)}",
                # Include the original test data even for errors
                test_data={
                    "expected_status_code": test_case.expected_status_code,
                    "request_params": test_case.request_params,
                    "request_headers": test_case.request_headers,
                    "request_body": test_case.request_body,
                    "expected_response_schema": test_case.expected_response_schema,
                    "expected_response_contains": test_case.expected_response_contains,
                },
            )
            test_case_results.append(test_case_result)
            if verbose:
                print(f"    Error executing API call: {str(e)}")

    return test_case_results


async def generate_and_execute_test_collection(
    api_name: str,
    api_version: str,
    endpoints: List[EndpointInfo],
    factory: RestApiCallerFactory,
    report_output_dir: str,
    test_case_count: int = 2,
    include_invalid_data: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Generate a test collection, execute tests, and generate reports.

    Args:
        api_name: Name of the API
        api_version: Version of the API
        endpoints: List of endpoints to test
        factory: Factory for creating endpoint-specific tools
        report_output_dir: Directory to save test reports
        test_case_count: Number of test cases per endpoint
        include_invalid_data: Whether to include invalid test data
        verbose: Enable verbose logging

    Returns:
        Summary of test results
    """
    if verbose:
        print(f"\nGenerating test collection for {api_name} v{api_version}")
        print(f"Endpoints to test: {len(endpoints)}")
        print(f"Test cases per endpoint: {test_case_count}")
        print(f"Include invalid data: {include_invalid_data}")

    # Initialize the test collection generator
    test_collection_generator = TestCollectionGeneratorTool(verbose=verbose)

    # Generate the test collection
    collection_input = TestCollectionGeneratorInput(
        api_name=api_name,
        api_version=api_version,
        endpoints=endpoints,
        test_case_count=test_case_count,  # Use the parameter value
        include_invalid_data=include_invalid_data,  # Use the parameter value
    )

    collection_output = await test_collection_generator.execute(collection_input)
    test_collection = collection_output.test_collection

    if verbose:
        print(
            f"Generated test collection with {len(test_collection.test_suites)} test suites"
        )

    # Initialize the report tool
    test_report_tool = TestExecutionReporterTool(verbose=verbose)

    # Execute each test suite and generate reports
    all_reports = []
    summary = {
        "total_suites": len(test_collection.test_suites),
        "total_cases": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
    }

    for test_suite in test_collection.test_suites:
        # Get the endpoint-specific tool
        endpoint = test_suite.endpoint_info
        tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"

        if tool_key not in factory.create_tools_from_endpoints([endpoint]):
            if verbose:
                print(
                    f"No tool found for endpoint: {endpoint.method.upper()} {endpoint.path}"
                )
            continue

        endpoint_tool = factory.create_tool_from_endpoint(endpoint)

        # Record start time
        started_at = datetime.now()

        # Execute all test cases in the suite
        test_case_results = await execute_test_suite(
            api_name=api_name,
            api_version=api_version,
            test_suite=test_suite,
            endpoint_tool=endpoint_tool,
            verbose=verbose,
        )

        # Record finish time
        finished_at = datetime.now()

        # Update summary statistics
        summary["total_cases"] += len(test_case_results)
        for result in test_case_results:
            if result.status == TestStatus.PASS:
                summary["passed"] += 1
            elif result.status == TestStatus.FAIL:
                summary["failed"] += 1
            elif result.status == TestStatus.ERROR:
                summary["errors"] += 1
            elif result.status == TestStatus.SKIPPED:
                summary["skipped"] += 1

        # Generate a report for this test suite
        report_input = TestExecutionReporterInput(
            api_name=api_name,
            api_version=api_version,
            endpoint_name=endpoint.name or endpoint.path,
            endpoint_path=endpoint.path,
            endpoint_method=endpoint.method,
            test_case_results=test_case_results,
            started_at=started_at,
            finished_at=finished_at,
        )

        report_output = await test_report_tool.execute(report_input)

        # Save the report to a file
        safe_endpoint_name = (
            (endpoint.name or endpoint.path)
            .replace("/", "_")
            .replace("{", "")
            .replace("}", "")
        )
        filename = f"{api_name}_{safe_endpoint_name}.json"
        report_path = os.path.join(report_output_dir, filename)

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report_output.report.model_dump(), f, indent=2, default=str)

        # Add the report path to the output
        report_data = report_output.report.model_dump()
        report_data["report_path"] = report_path
        all_reports.append(report_data)

        if verbose:
            print(f"Test report saved to: {report_path}")
            print(
                f"\nTest Report Summary for {endpoint.method.upper()} {endpoint.path}:"
            )
            print(f"  Total tests: {report_output.report.summary.total_tests}")
            print(f"  Passed: {report_output.report.summary.passed}")
            print(f"  Failed: {report_output.report.summary.failed}")
            print(f"  Errors: {report_output.report.summary.errors}")
            print(f"  Success rate: {report_output.report.summary.success_rate:.1f}%")
            print(f"  Total time: {report_output.report.total_time:.2f} seconds")

    # Calculate overall success rate
    total_tests = summary["total_cases"]
    if total_tests > 0:
        summary["success_rate"] = (summary["passed"] / total_tests) * 100
    else:
        summary["success_rate"] = 0

    # Add reports to summary
    summary["reports"] = all_reports

    # Create a summary file
    summary_path = os.path.join(report_output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if verbose:
        print("\nOverall Test Summary:")
        print(f"  Total test suites: {summary['total_suites']}")
        print(f"  Total test cases: {summary['total_cases']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Errors: {summary['errors']}")
        print(f"  Skipped: {summary['skipped']}")
        print(f"  Overall success rate: {summary['success_rate']:.1f}%")
        print(f"  Summary saved to: {summary_path}")

    return summary


async def main():
    """Demo showcasing the complete API testing workflow using the new component structure."""
    parser = argparse.ArgumentParser(description="Execute API tests")
    parser.add_argument(
        "--spec",
        type=str,
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        help="Number of test cases per endpoint",
    )
    parser.add_argument(
        "--invalid",
        action="store_true",
        help="Include invalid test data for negative testing",
    )
    parser.add_argument(
        "--no-invalid",
        action="store_true",
        help="Exclude invalid test data",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Validate input file
    if not validate_file_exists(args.spec):
        return

    # Create timestamped output directory for test reports
    report_output_dir = create_timestamped_output_dir("output", "test_reports")

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=True)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    api_name = api_info["title"]
    api_version = api_info["version"]
    server_url = get_server_url_from_api_info(api_info)

    print(f"\nAPI: {api_name} v{api_version}")
    print(f"Server URL: {server_url}")

    # Create factory for endpoint-specific tools
    factory = setup_api_factory(server_url, verbose=args.verbose)

    # Select endpoints to test
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to test (comma-separated, or 'all'): ",
    )

    # Get test configuration
    if args.test_cases is not None:
        test_case_count = args.test_cases
        # Validate test case count
        if test_case_count < 1:
            test_case_count = 1
            print("Test case count must be at least 1, using 1.")
        elif test_case_count > 10:
            test_case_count = 10
            print("Maximum test case count is 10, using 10.")
    else:
        test_case_count = None

    if args.invalid:
        include_invalid_data = True
    elif args.no_invalid:
        include_invalid_data = False
    else:
        include_invalid_data = None

    # Get user input if not provided via command line
    if test_case_count is None or include_invalid_data is None:
        user_test_case_count, user_include_invalid = get_user_test_preferences()
        if test_case_count is None:
            test_case_count = user_test_case_count
        if include_invalid_data is None:
            include_invalid_data = user_include_invalid

    # Generate test collection, execute tests, and create reports
    summary = await generate_and_execute_test_collection(
        api_name=api_name,
        api_version=api_version,
        endpoints=selected_endpoints,
        factory=factory,
        report_output_dir=report_output_dir,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
        verbose=args.verbose,
    )

    # Save summary
    summary_data = {
        "endpoints_tested": len(selected_endpoints),
        "test_case_count": test_case_count,
        "include_invalid_data": include_invalid_data,
        **summary,
    }

    summary_path = save_summary_file(report_output_dir, api_info, summary_data)

    print(f"\nTest execution completed. Reports saved to: {report_output_dir}")
    print(f"Summary saved to: {summary_path}")
    print(
        f"Summary: {summary['passed']}/{summary['total_cases']} tests passed ({summary['success_rate']:.1f}%)"
    )


if __name__ == "__main__":
    asyncio.run(main())
