# src/api_test_runner_demo.py

import asyncio
import os
import time
import json
from datetime import datetime
from typing import List

from tools import OpenAPIParserTool, RestApiCallerTool
from tools.test_data_generator import TestDataGeneratorTool
from tools.test_script_generator import TestScriptGeneratorTool
from tools.test_report import TestReportTool
from utils.rest_api_caller_factory import (
    RestApiCallerFactory,
)

from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    OpenAPIParserOutput,
    EndpointInfo,
)

from schemas.tools.rest_api_caller import (
    RestApiCallerOutput,
)

from schemas.tools.test_data_generator import (
    TestDataGeneratorInput,
    TestDataGeneratorOutput,
    TestCase,
)
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
)
from schemas.tools.test_report import (
    TestReportInput,
    TestCaseResult,
    ValidationResult,
    TestStatus,
)


async def run_test_for_endpoint(
    api_name: str,
    api_version: str,
    endpoint: EndpointInfo,
    endpoint_tool: RestApiCallerTool,
    report_output_dir: str,
    verbose: bool = False,
) -> None:
    """Run tests for a single API endpoint."""
    print(f"\nTesting endpoint: [{endpoint.method.upper()}] {endpoint.path}")

    # Initialize tools
    test_data_generator = TestDataGeneratorTool(verbose=verbose)
    test_script_generator = TestScriptGeneratorTool(verbose=verbose)
    test_report_tool = TestReportTool(verbose=verbose)

    # Record start time
    started_at = datetime.now()

    # Step 1: Generate test data
    test_data_input = TestDataGeneratorInput(
        endpoint_info=endpoint, test_case_count=2, include_invalid_data=True
    )
    test_data_output: TestDataGeneratorOutput = await test_data_generator.execute(
        test_data_input
    )
    test_cases: list[TestCase] = test_data_output.test_cases

    print(f"  Generated {len(test_cases)} test cases")

    # Step 2: Generate test scripts for each test case
    all_test_case_results = []

    for test_case in test_cases:
        print(f"  Running test case: {test_case.name}")

        # Generate validation scripts
        script_input = TestScriptGeneratorInput(
            endpoint_info=endpoint, test_case=test_case
        )
        script_output: TestScriptGeneratorOutput = await test_script_generator.execute(
            script_input
        )
        validation_scripts = script_output.validation_scripts

        print(f"    Generated {len(validation_scripts)} validation scripts")

        # Step 3: Execute the API call using the endpoint-specific tool
        print(f"    Executing API call: {endpoint.method.upper()} {endpoint.path}")
        test_start_time = time.perf_counter()

        try:
            # Use the endpoint-specific tool directly with parameters
            # This tool handles all the URL construction and parameter mapping
            params = {}

            # For path parameters, use the request_params if they exist
            if hasattr(test_case, "request_params") and test_case.request_params:
                params.update(test_case.request_params)

            # For query parameters, also use request_params if available
            # (already handled in the previous step)

            # Add headers if any and if the attribute exists
            if hasattr(test_case, "request_headers") and test_case.request_headers:
                for k, v in test_case.request_headers.items():
                    # Add header prefix to parameter names for the RestApiCallerTool
                    params[f"header_{k}"] = v

            # Add body parameters if any and if the attribute exists
            if hasattr(test_case, "request_body") and test_case.request_body:
                if isinstance(test_case.request_body, dict):
                    params.update(test_case.request_body)
                else:
                    # If it's not a dict, convert it to a string and pass it as 'body'
                    params["body"] = str(test_case.request_body)

            # # Store the original request information
            # request_info = {
            #     "method": endpoint.method,
            #     "url": f"{factory.server_url}/{endpoint.path.lstrip('/')}",
            #     "headers": test_case.request_headers or {},
            #     "params": test_case.request_params or {},
            #     "json": test_case.request_body or None,
            # }

            # Execute the API call - directly pass the params dict like in api_test_suite_generator.py
            api_response: RestApiCallerOutput = await endpoint_tool.execute(params)
            test_elapsed_time = time.perf_counter() - test_start_time
            print(
                f"    Received response with status code: {api_response.response.status_code}"
            )

            # Step 4: Run validation scripts
            validation_results = []
            test_status = TestStatus.PASS  # Assume success initially

            for script in validation_scripts:
                try:
                    # In a real implementation, we'd execute the script.
                    # Here we'll just simulate success or failure based on expected status code
                    script_passed = True
                    if (
                        script.script_type == "status_code"
                        and api_response.response.status_code
                        != test_case.expected_status_code
                    ):
                        script_passed = False

                    status = TestStatus.PASS if script_passed else TestStatus.FAIL
                    message = (
                        "Validation passed"
                        if script_passed
                        else f"Expected status {test_case.expected_status_code}, got {api_response.response.status_code}"
                    )

                    # If any script fails, the whole test fails
                    if status == TestStatus.FAIL:
                        test_status = TestStatus.FAIL

                    validation_results.append(
                        ValidationResult(
                            script_id=script.id,
                            script_name=script.name,
                            status=status,
                            message=message,
                        )
                    )

                    print(f"    Validation '{script.name}': {status}")

                except Exception as e:
                    # If an exception occurs, mark as error
                    validation_results.append(
                        ValidationResult(
                            script_id=script.id,
                            script_name=script.name,
                            status=TestStatus.ERROR,
                            message=f"Error executing script: {str(e)}",
                        )
                    )
                    test_status = TestStatus.ERROR
                    print(f"    Validation '{script.name}': ERROR - {str(e)}")

            # Step 5: Create test case result
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
            )

            print(f"    Test case status: {test_status}")
            all_test_case_results.append(test_case_result)

        except Exception as e:
            test_elapsed_time = time.perf_counter() - test_start_time
            # Create a result with error status since the API call failed
            test_case_result = TestCaseResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                status=TestStatus.ERROR,
                elapsed_time=test_elapsed_time,
                request={"error": "API call failed"},
                response={"error": str(e)},
                validation_results=[],
                message=f"Error executing API call: {str(e)}",
            )
            all_test_case_results.append(test_case_result)
            print(f"    Error executing API call: {str(e)}")

    # Record finish time
    finished_at = datetime.now()

    # Step 6: Generate test report
    report_input = TestReportInput(
        api_name=api_name,
        api_version=api_version,
        endpoint_name=endpoint.name,
        endpoint_path=endpoint.path,
        endpoint_method=endpoint.method,
        test_case_results=all_test_case_results,
        started_at=started_at,
        finished_at=finished_at,
    )

    report_output = await test_report_tool.execute(report_input)

    # Save the report to file (moved from TestReportTool)
    safe_endpoint_name = (
        endpoint.name.replace("/", "_").replace("{", "").replace("}", "")
    )
    filename = f"{api_name}_{safe_endpoint_name}.json"
    report_path = os.path.join(report_output_dir, filename)

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report_output.report.model_dump(), f, indent=2, default=str)

    # Update the report_output with the saved path
    report_output.report_path = report_path

    if verbose:
        print(f"Test report saved to: {report_path}")

    # Print report summary
    report = report_output.report
    print(f"\nTest Report Summary for {endpoint.method.upper()} {endpoint.path}:")
    print(f"  Total tests: {report.summary.total_tests}")
    print(f"  Passed: {report.summary.passed}")
    print(f"  Failed: {report.summary.failed}")
    print(f"  Errors: {report.summary.errors}")
    print(f"  Success rate: {report.summary.success_rate:.1f}%")
    print(f"  Total time: {report.total_time:.2f} seconds")
    print(f"  Report saved to: {report_path}")


def select_endpoints_to_test(endpoints: List[EndpointInfo]) -> List[EndpointInfo]:
    """
    Allow user to select which endpoints to test.

    Args:
        endpoints: List of available endpoints

    Returns:
        List of selected endpoints to test
    """
    print("\nAvailable endpoints:")
    for i, endpoint in enumerate(endpoints):
        print(f"{i+1}. [{endpoint.method.upper()}] {endpoint.path}")

    # Allow selection of multiple endpoints
    selected_indices = input(
        "\nEnter endpoint numbers to test (comma-separated, or 'all'): "
    )

    if selected_indices.lower() == "all":
        return endpoints

    try:
        indices = [int(idx.strip()) - 1 for idx in selected_indices.split(",")]
        selected = [endpoints[idx] for idx in indices if 0 <= idx < len(endpoints)]
        if not selected:
            print("No valid endpoints selected, testing the first endpoint by default.")
            return [endpoints[0]]
        return selected
    except (ValueError, IndexError):
        print("Invalid selection, testing the first endpoint by default.")
        return [endpoints[0]]


async def main():
    """Demo showcasing the complete API testing workflow."""
    # Create timestamped output directory for test reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_output_dir = os.path.join("output", "test_reports", timestamp)
    os.makedirs(report_output_dir, exist_ok=True)

    # Step 1: Parse OpenAPI spec
    parser_tool = OpenAPIParserTool(verbose=True)

    # Choose one of the available specs
    spec_source = "data/toolshop/openapi.json"
    # spec_source = "data/json_place_holder/openapi.yaml"

    parser_input = OpenAPIParserInput(
        spec_source=spec_source, source_type=SpecSourceType.FILE
    )

    print(f"Parsing OpenAPI spec: {spec_source}")
    parser_output: OpenAPIParserOutput = await parser_tool.execute(parser_input)

    api_name = parser_output.title
    api_version = parser_output.version
    server_url = (
        parser_output.servers[0] if parser_output.servers else "http://localhost"
    )

    print(f"\nAPI: {api_name} v{api_version}")
    print(f"Server URL: {server_url}")
    print(f"Found {len(parser_output.endpoints)} endpoints")

    if not parser_output.endpoints:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Step 2: Create a factory to generate endpoint-specific tools
    factory = RestApiCallerFactory(
        server_url=server_url,
        default_headers={"Content-Type": "application/json"},
        timeout=10.0,
        verbose=True,
        cache_enabled=False,
    )

    # Create tools for all endpoints
    endpoint_tools = {}
    for endpoint in parser_output.endpoints:
        tool = factory.create_tool_from_endpoint(endpoint=endpoint)
        # Use the same path transformation method here as in the lookup
        tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"
        endpoint_tools[tool_key] = {
            "endpoint": endpoint,
            "tool": tool,
        }

    # Step 3: Let user select which endpoints to test
    selected_endpoints = select_endpoints_to_test(parser_output.endpoints)

    # Step 4: Run tests for each selected endpoint
    for endpoint in selected_endpoints:
        tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"
        if tool_key in endpoint_tools:
            await run_test_for_endpoint(
                api_name=api_name,
                api_version=api_version,
                endpoint=endpoint,
                endpoint_tool=endpoint_tools[tool_key]["tool"],
                report_output_dir=report_output_dir,
                verbose=True,
            )
        else:
            print(
                f"No tool found for endpoint: {endpoint.method.upper()} {endpoint.path}"
            )


if __name__ == "__main__":
    asyncio.run(main())
