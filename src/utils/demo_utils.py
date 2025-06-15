# utils/demo_utils.py

"""
Demo utilities for the RESTful API Testing Framework.
Contains shared functionality for demo scripts and tools.
"""

import os
from typing import List, Dict, Any
from datetime import datetime

from tools import OpenAPIParserTool
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    EndpointInfo,
)


async def parse_openapi_spec(spec_source: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Parse an OpenAPI specification and extract endpoints.

    Args:
        spec_source: Path to the OpenAPI specification file
        verbose: Whether to print verbose output

    Returns:
        Dictionary containing API info and endpoints
    """
    parser_tool = OpenAPIParserTool(verbose=verbose)

    parser_input = OpenAPIParserInput(
        spec_source=spec_source, source_type=SpecSourceType.FILE
    )

    if verbose:
        print(f"Parsing OpenAPI specification: {spec_source}")

    parser_output = await parser_tool.execute(parser_input)

    api_info = {
        "title": parser_output.title,
        "version": parser_output.version,
        "description": parser_output.description,
        "servers": parser_output.servers,
        "endpoints": parser_output.endpoints,
    }

    if verbose:
        print(f"API: {api_info['title']} v{api_info['version']}")
        print(f"Found {len(parser_output.endpoints)} endpoints")

    return api_info


def select_endpoints(
    endpoints: List[EndpointInfo],
    prompt_message: str = "Enter endpoint numbers to analyze (comma-separated, or 'all'): ",
) -> List[EndpointInfo]:
    """
    Allow user to select which endpoints to analyze.

    Args:
        endpoints: List of available endpoints
        prompt_message: Custom prompt message for user input

    Returns:
        List of selected endpoints
    """
    print("\nAvailable endpoints:")
    for i, endpoint in enumerate(endpoints):
        print(f"{i+1}. [{endpoint.method.upper()}] {endpoint.path}")

    # Allow selection of multiple endpoints
    selected_indices = input(f"\n{prompt_message}")

    if selected_indices.lower() == "all":
        return endpoints

    try:
        indices = [int(idx.strip()) - 1 for idx in selected_indices.split(",")]
        selected = [endpoints[idx] for idx in indices if 0 <= idx < len(endpoints)]
        if not selected:
            print("No valid endpoints selected, using the first endpoint by default.")
            return [endpoints[0]] if endpoints else []
        return selected
    except (ValueError, IndexError):
        print("Invalid selection, using the first endpoint by default.")
        return [endpoints[0]] if endpoints else []


def create_timestamped_output_dir(base_path: str, folder_name: str) -> str:
    """
    Create a timestamped output directory.

    Args:
        base_path: Base path for output
        folder_name: Name of the folder

    Returns:
        Path to the created directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_path, folder_name, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def print_endpoint_summary(endpoint: EndpointInfo, action: str = "Processing") -> None:
    """
    Print a formatted summary of an endpoint.

    Args:
        endpoint: The endpoint to summarize
        action: Action being performed on the endpoint
    """
    print(f"\n{action}: [{endpoint.method.upper()}] {endpoint.path}")
    if endpoint.description:
        print(f"Description: {endpoint.description}")


def save_summary_file(
    output_dir: str,
    api_info: Dict[str, Any],
    summary_data: Dict[str, Any],
    filename: str = "summary.json",
) -> str:
    """
    Save a summary file with API and processing information.

    Args:
        output_dir: Output directory
        api_info: API information
        summary_data: Additional summary data
        filename: Name of the summary file

    Returns:
        Path to the saved summary file
    """
    import json

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary = {
        "api_name": api_info.get("title", "Unknown API"),
        "api_version": api_info.get("version", "Unknown"),
        "timestamp": timestamp,
        **summary_data,
    }

    summary_path = os.path.join(output_dir, filename)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return summary_path


def validate_file_exists(file_path: str) -> bool:
    """
    Validate that a file exists and is readable.

    Args:
        file_path: Path to the file

    Returns:
        True if file exists and is readable, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    if not os.path.isfile(file_path):
        print(f"Error: Path is not a file: {file_path}")
        return False

    try:
        with open(file_path, "r") as f:
            f.read(1)  # Try to read at least one character
        return True
    except (PermissionError, OSError) as e:
        print(f"Error: Cannot read file {file_path}: {e}")
        return False


def format_constraint_summary(constraints: List[Any]) -> str:
    """
    Format a summary of constraints for display.

    Args:
        constraints: List of constraint objects

    Returns:
        Formatted summary string
    """
    if not constraints:
        return "No constraints found"

    summary_lines = [f"Found {len(constraints)} constraints:"]

    # Group by type if constraints have a 'type' attribute
    constraint_types = {}
    for constraint in constraints:
        constraint_type = getattr(constraint, "type", "unknown")
        if constraint_type not in constraint_types:
            constraint_types[constraint_type] = 0
        constraint_types[constraint_type] += 1

    for constraint_type, count in constraint_types.items():
        summary_lines.append(f"  - {count} {constraint_type} constraints")

    return "\n".join(summary_lines)


def get_default_spec_path() -> str:
    """
    Get the default OpenAPI specification path.

    Returns:
        Default path to OpenAPI specification
    """
    return "data/toolshop/openapi.json"


def setup_output_directory(tool_name: str) -> str:
    """
    Set up output directory for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Path to the output directory
    """
    return create_timestamped_output_dir("output", tool_name)


def get_user_test_preferences():
    """Get user preferences for test configuration."""
    # Test case count
    test_case_count_input = input(
        "\nEnter number of test cases per endpoint (default: 2): "
    )
    try:
        test_case_count = (
            int(test_case_count_input) if test_case_count_input.strip() else 2
        )
    except ValueError:
        print("Invalid input, using default of 2 test cases per endpoint.")
        test_case_count = 2

    # Validate test case count
    if test_case_count < 1:
        test_case_count = 1
        print("Test case count must be at least 1, using 1.")
    elif test_case_count > 10:
        test_case_count = 10
        print("Maximum test case count is 10, using 10.")

    # Include invalid data
    include_invalid_input = input(
        "Include invalid test data for negative testing? (Y/n): "
    )
    include_invalid_data = include_invalid_input.strip().lower() not in ["n", "no"]

    return test_case_count, include_invalid_data


def setup_api_factory(server_url: str, verbose: bool = False):
    """Set up REST API factory with common configuration."""
    from utils.rest_api_caller_factory import RestApiCallerFactory

    return RestApiCallerFactory(
        server_url=server_url,
        default_headers={"Content-Type": "application/json"},
        timeout=10.0,
        verbose=verbose,
        cache_enabled=False,
    )


def get_server_url_from_api_info(api_info: Dict[str, Any]) -> str:
    """Extract server URL from API info."""
    return api_info["servers"][0] if api_info["servers"] else "http://localhost"
