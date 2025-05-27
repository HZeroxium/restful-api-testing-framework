# utils/api_utils.py

"""Utility functions for API operations."""

import time
import streamlit as st
from datetime import datetime

from tools import OpenAPIParserTool
from utils.rest_api_caller_factory import RestApiCallerFactory
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    OpenAPIParserOutput,
    EndpointInfo,
)
from schemas.tools.test_data_generator import TestDataGeneratorInput
from schemas.tools.test_case_generator import TestCaseGeneratorInput
from schemas.tools.test_execution_reporter import (
    TestExecutionReporterInput,
    TestCaseResult,
    TestStatus,
    ValidationResult,
)
from tools.test_data_generator import TestDataGeneratorTool
from tools.test_case_generator import TestCaseGeneratorTool
from tools.test_script_generator import TestScriptGeneratorTool
from tools.test_execution_reporter import TestExecutionReporterTool
from tools.code_executor import CodeExecutorTool
from typing import Dict, List, Any, Tuple


async def load_openapi_spec(
    spec_path: str,
) -> Tuple[dict, List[EndpointInfo], RestApiCallerFactory]:
    """Load and parse OpenAPI specification

    Args:
        spec_path: Path to the OpenAPI specification file

    Returns:
        Tuple of (api_info, endpoints, factory)
    """
    parser_tool = OpenAPIParserTool(verbose=False)

    parser_input = OpenAPIParserInput(
        spec_source=spec_path, source_type=SpecSourceType.FILE
    )

    with st.spinner("Loading API specification..."):
        parser_output: OpenAPIParserOutput = await parser_tool.execute(parser_input)

    api_info = {
        "title": parser_output.title,
        "version": parser_output.version,
        "description": parser_output.description,
        "servers": parser_output.servers,
    }

    server_url = (
        parser_output.servers[0] if parser_output.servers else "http://localhost"
    )

    # Create API caller factory
    factory = RestApiCallerFactory(
        server_url=server_url,
        default_headers={"Content-Type": "application/json"},
        timeout=10.0,
        verbose=False,
        cache_enabled=False,
    )

    # Create tools for all endpoints
    endpoint_tools = {}
    for endpoint in parser_output.endpoints:
        tool = factory.create_tool_from_endpoint(endpoint=endpoint)
        tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"
        endpoint_tools[tool_key] = {
            "endpoint": endpoint,
            "tool": tool,
        }

    st.session_state.endpoint_tools = endpoint_tools

    return api_info, parser_output.endpoints, factory


async def execute_api_call(endpoint: EndpointInfo, params: Dict[str, Any]) -> Any:
    """Execute a single API call using the appropriate tool

    Args:
        endpoint: EndpointInfo for the endpoint to call
        params: Parameters for the API call

    Returns:
        API response
    """
    factory = st.session_state.factory
    tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"

    if tool_key in st.session_state.endpoint_tools:
        tool_info = st.session_state.endpoint_tools[tool_key]
        return await tool_info["tool"].execute(params)
    else:
        # Create the tool if not found
        tool = factory.create_tool_from_endpoint(endpoint=endpoint)
        st.session_state.endpoint_tools[tool_key] = {
            "endpoint": endpoint,
            "tool": tool,
        }
        return await tool.execute(params)


async def run_tests_for_endpoints(
    selected_endpoints: List[EndpointInfo],
    test_case_count: int = 2,
    include_invalid_data: bool = True,
) -> List[dict]:
    """Run tests for multiple endpoints and return results

    Args:
        selected_endpoints: List of endpoints to test
        test_case_count: Number of test cases per endpoint
        include_invalid_data: Whether to include invalid test data

    Returns:
        List of test results
    """
    results = []

    api_info = st.session_state.api_info
    api_name = api_info["title"]
    api_version = api_info["version"]

    test_data_generator = TestDataGeneratorTool(verbose=False)
    test_case_generator = TestCaseGeneratorTool(verbose=False)
    test_script_generator = TestScriptGeneratorTool(verbose=False)

    code_executor = CodeExecutorTool(verbose=False)

    for endpoint in selected_endpoints:
        with st.spinner(f"Testing {endpoint.method.upper()} {endpoint.path}..."):
            # Record start time
            started_at = datetime.now()

            # Generate test data - Convert endpoint to dict to avoid type validation issues
            endpoint_dict = (
                endpoint.model_dump()
                if hasattr(endpoint, "model_dump")
                else endpoint.dict()
            )
            test_data_input = TestDataGeneratorInput(
                endpoint_info=endpoint_dict,  # Pass as dict instead of direct object
                test_case_count=test_case_count,  # Use the parameter value
                include_invalid_data=include_invalid_data,  # Use the parameter value
            )
            test_data_output = await test_data_generator.execute(test_data_input)

            # Now we need to convert TestData to TestCase
            all_test_case_results = []

            for test_data in test_data_output.test_data_collection:
                # Use TestCaseGenerator to create TestCase with validation scripts
                case_input = TestCaseGeneratorInput(
                    endpoint_info=endpoint, test_data=test_data
                )
                case_output = await test_case_generator.execute(case_input)
                test_case = case_output.test_case

                # Execute API call
                factory = st.session_state.factory
                tool_key = (
                    f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"
                )

                if tool_key in st.session_state.endpoint_tools:
                    endpoint_tool = st.session_state.endpoint_tools[tool_key]["tool"]

                    params = {}
                    if test_case.request_params:
                        params.update(test_case.request_params)

                    if test_case.request_headers:
                        for k, v in test_case.request_headers.items():
                            params[f"header_{k}"] = v

                    if test_case.request_body:
                        if isinstance(test_case.request_body, dict):
                            params.update(test_case.request_body)
                        else:
                            params["body"] = str(test_case.request_body)

                    try:
                        test_start_time = time.perf_counter()
                        api_response = await endpoint_tool.execute(params)
                        test_elapsed_time = time.perf_counter() - test_start_time

                        # Run validation scripts
                        validation_results = []
                        test_status = TestStatus.PASS

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
                                    r"def\s+([a-zA-Z0-9_]+)\s*\(",
                                    script.validation_code,
                                )
                                function_name = (
                                    function_match.group(1) if function_match else None
                                )

                                # Add code to call the function with the context variables
                                modified_code = script.validation_code
                                if function_name:
                                    modified_code += f"\n\n_result = {function_name}(request, response)"

                                # Execute the validation script using CodeExecutorTool
                                executor_input = {
                                    "code": modified_code,
                                    "context_variables": context_variables,
                                    "timeout": 5.0,  # 5 seconds timeout should be enough for validation scripts
                                }

                                execution_result = await code_executor.execute(
                                    executor_input
                                )

                                # Determine if the script passed based on execution result
                                script_passed = (
                                    execution_result.success and execution_result.result
                                )
                                # The result should be 'True' string for passing validation
                                if script_passed:
                                    script_passed = (
                                        execution_result.result.lower() == "true"
                                    )

                                status = (
                                    TestStatus.PASS
                                    if script_passed
                                    else TestStatus.FAIL
                                )

                                if script_passed:
                                    message = "Validation passed"
                                else:
                                    # Get detailed error message from execution result
                                    message = (
                                        execution_result.error or "Validation failed"
                                    )
                                    if execution_result.stderr:
                                        message += f": {execution_result.stderr}"

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
                            except Exception as e:
                                # Handle execution errors for individual scripts
                                validation_results.append(
                                    ValidationResult(
                                        script_id=script.id,
                                        script_name=script.name,
                                        status=TestStatus.ERROR,
                                        message=f"Error executing script: {str(e)}",
                                        validation_code=script.validation_code,
                                    )
                                )
                                # Don't fail the entire test for script execution errors
                                # unless there are no passing validations
                                if all(
                                    v.status != TestStatus.PASS
                                    for v in validation_results
                                ):
                                    test_status = TestStatus.ERROR

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

                    all_test_case_results.append(test_case_result)

            # Record finish time
            finished_at = datetime.now()

            # Generate test report
            report_input = TestExecutionReporterInput(
                api_name=api_name,
                api_version=api_version,
                endpoint_name=endpoint.name,
                endpoint_path=endpoint.path,
                endpoint_method=endpoint.method,
                test_case_results=all_test_case_results,
                started_at=started_at,
                finished_at=finished_at,
            )

            test_report_tool = TestExecutionReporterTool(verbose=False)

            report_output = await test_report_tool.execute(report_input)
            results.append(report_output.report.model_dump())

    return results
