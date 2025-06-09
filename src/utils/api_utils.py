# utils/api_utils.py

"""Utility functions for API operations."""

import time
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Tuple

from tools import OpenAPIParserTool
from utils.rest_api_caller_factory import RestApiCallerFactory
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    OpenAPIParserOutput,
    EndpointInfo,
)
from schemas.tools.test_data_generator import TestDataGeneratorInput
from schemas.tools.test_case_generator import TestCaseGeneratorInput, TestCase
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
    """
    Run tests for selected endpoints and return test reports.

    Args:
        selected_endpoints: List of endpoints to test
        test_case_count: Number of test cases per endpoint
        include_invalid_data: Whether to include invalid test data

    Returns:
        List of test reports
    """
    test_results = []

    # Initialize tools
    test_data_generator = TestDataGeneratorTool(verbose=True)
    test_case_generator = TestCaseGeneratorTool(verbose=True)

    for endpoint in selected_endpoints:
        with st.spinner(f"Testing {endpoint.method.upper()} {endpoint.path}..."):
            try:
                # Generate test data for this endpoint
                test_data_input = TestDataGeneratorInput(
                    endpoint_info=endpoint,
                    test_case_count=test_case_count,
                    include_invalid_data=include_invalid_data,
                )

                test_data_output = await test_data_generator.execute(test_data_input)

                for test_data in test_data_output.test_data_collection:
                    case_input = TestCaseGeneratorInput(
                        endpoint_info=endpoint, test_data=test_data
                    )
                    case_output = await test_case_generator.execute(case_input)
                    test_case = case_output.test_case

                    # Execute API call
                    factory = st.session_state.factory
                    tool_key = f"{endpoint.method.lower()}_{factory._path_to_name(endpoint.path)}"

                    if tool_key in st.session_state.endpoint_tools:
                        endpoint_tool = st.session_state.endpoint_tools[tool_key][
                            "tool"
                        ]

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
                            # Execute the API call
                            api_response = await endpoint_tool.execute(params)

                            # Store the result for further processing
                            test_results.append(
                                {
                                    "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                                    "test_case": test_case.name,
                                    "test_data": test_data.model_dump(),
                                    "response": (
                                        api_response.model_dump()
                                        if hasattr(api_response, "model_dump")
                                        else str(api_response)
                                    ),
                                    "success": True,
                                    "summary": {
                                        "total_tests": 1,
                                        "passed": 1,
                                        "failed": 0,
                                        "errors": 0,
                                        "skipped": 0,
                                    },
                                }
                            )

                        except Exception as e:
                            # Store the error for reporting
                            test_results.append(
                                {
                                    "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                                    "test_case": test_case.name,
                                    "test_data": test_data.model_dump(),
                                    "error": str(e),
                                    "success": False,
                                    "summary": {
                                        "total_tests": 1,
                                        "passed": 0,
                                        "failed": 0,
                                        "errors": 1,
                                        "skipped": 0,
                                    },
                                }
                            )
                            continue
                    else:
                        # No tool found for this endpoint
                        test_results.append(
                            {
                                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                                "test_case": test_case.name,
                                "error": f"No tool found for endpoint: {tool_key}",
                                "success": False,
                                "summary": {
                                    "total_tests": 1,
                                    "passed": 0,
                                    "failed": 0,
                                    "errors": 1,
                                    "skipped": 0,
                                },
                            }
                        )

            except Exception as e:
                # Handle endpoint-level errors
                test_results.append(
                    {
                        "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                        "error": f"Error processing endpoint: {str(e)}",
                        "success": False,
                        "summary": {
                            "total_tests": 1,
                            "passed": 0,
                            "failed": 0,
                            "errors": 1,
                            "skipped": 0,
                        },
                    }
                )

    return test_results
