#!/usr/bin/env python
# src/test_data_generator_tool.py

"""
Test Data Generator Tool

This tool generates test data for API endpoints based on OpenAPI specifications.
It allows users to select endpoints and generate both valid and invalid test data.
"""

import asyncio
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

from tools import OpenAPIParserTool
from tools.test_data_generator import TestDataGeneratorTool
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    EndpointInfo,
)
from schemas.tools.test_data_generator import (
    TestDataGeneratorInput,
    TestDataGeneratorOutput,
    TestData,
)


async def parse_openapi_spec(spec_source: str) -> Dict[str, Any]:
    """
    Parse an OpenAPI specification and extract endpoints.

    Args:
        spec_source: Path to the OpenAPI specification file

    Returns:
        Dictionary containing API info and endpoints
    """
    parser_tool = OpenAPIParserTool(verbose=True)

    parser_input = OpenAPIParserInput(
        spec_source=spec_source, source_type=SpecSourceType.FILE
    )

    print(f"Parsing OpenAPI specification: {spec_source}")
    parser_output = await parser_tool.execute(parser_input)

    api_info = {
        "title": parser_output.title,
        "version": parser_output.version,
        "description": parser_output.description,
        "servers": parser_output.servers,
        "endpoints": parser_output.endpoints,
    }

    print(f"API: {api_info['title']} v{api_info['version']}")
    print(f"Found {len(parser_output.endpoints)} endpoints")

    return api_info


def select_endpoints(endpoints: List[EndpointInfo]) -> List[EndpointInfo]:
    """
    Allow user to select which endpoints to analyze.

    Args:
        endpoints: List of available endpoints

    Returns:
        List of selected endpoints
    """
    print("\nAvailable endpoints:")
    for i, endpoint in enumerate(endpoints):
        print(f"{i+1}. [{endpoint.method.upper()}] {endpoint.path}")

    # Allow selection of multiple endpoints
    selected_indices = input(
        "\nEnter endpoint numbers to generate test data for (comma-separated, or 'all'): "
    )

    if selected_indices.lower() == "all":
        return endpoints

    try:
        indices = [int(idx.strip()) - 1 for idx in selected_indices.split(",")]
        selected = [endpoints[idx] for idx in indices if 0 <= idx < len(endpoints)]
        if not selected:
            print("No valid endpoints selected, using the first endpoint by default.")
            return [endpoints[0]]
        return selected
    except (ValueError, IndexError):
        print("Invalid selection, using the first endpoint by default.")
        return [endpoints[0]]


async def generate_test_data(
    endpoint: EndpointInfo,
    test_case_count: int,
    include_invalid_data: bool,
    output_dir: str,
) -> List[TestData]:
    """
    Generate test data for an endpoint using TestDataGeneratorTool.

    Args:
        endpoint: The endpoint to generate test data for
        test_case_count: Number of test cases to generate
        include_invalid_data: Whether to include invalid test data
        output_dir: Directory to save output

    Returns:
        List of generated TestData objects
    """
    print(f"\nGenerating test data for: [{endpoint.method.upper()}] {endpoint.path}")

    # Create the test data generator tool
    generator_tool = TestDataGeneratorTool(verbose=True)

    # Create input for the tool
    generator_input = TestDataGeneratorInput(
        endpoint_info=endpoint,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
    )

    # Execute the tool
    try:
        print("Running test data generator...")
        output: TestDataGeneratorOutput = await generator_tool.execute(generator_input)

        test_data_collection = output.test_data_collection
        print(f"Generated {len(test_data_collection)} test cases")

        # Display summary of test data
        valid_count = sum(
            1 for td in test_data_collection if td.expected_status_code < 400
        )
        invalid_count = len(test_data_collection) - valid_count
        print(f"  - {valid_count} valid test cases (expected success)")
        print(f"  - {invalid_count} invalid test cases (expected failure)")

        # Save the test data to a file
        safe_endpoint_name = (
            endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
        )
        filename = f"test_data_{endpoint.method.lower()}{safe_endpoint_name}.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w") as f:
            # Convert to dict for JSON serialization
            data_list = [td.model_dump() for td in test_data_collection]
            json.dump(data_list, f, indent=2, default=str)

        print(f"Test data saved to: {output_path}")

        return test_data_collection

    except Exception as e:
        print(f"Error generating test data: {str(e)}")
        return []


async def main():
    """Main function to run the test data generator tool."""
    parser = argparse.ArgumentParser(description="Generate test data for API endpoints")
    parser.add_argument(
        "--spec",
        type=str,
        default="data/toolshop/openapi.json",
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        default=2,
        help="Number of test cases to generate per endpoint",
    )
    parser.add_argument(
        "--invalid",
        action="store_true",
        help="Include invalid test data for negative testing",
    )
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", "test_data", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(api_info["endpoints"])

    # Allow user to configure test parameters interactively if not provided via arguments
    if args.test_cases is None:
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
    else:
        test_case_count = args.test_cases

    # Validate test case count
    if test_case_count < 1:
        test_case_count = 1
        print("Test case count must be at least 1, using 1.")
    elif test_case_count > 10:
        test_case_count = 10
        print("Maximum test case count is 10, using 10.")

    if args.invalid is None:
        include_invalid_input = input(
            "Include invalid test data for negative testing? (Y/n): "
        )
        include_invalid_data = include_invalid_input.strip().lower() not in ["n", "no"]
    else:
        include_invalid_data = args.invalid

    # Generate test data for each selected endpoint
    all_test_data = {}
    for endpoint in selected_endpoints:
        test_data_collection = await generate_test_data(
            endpoint, test_case_count, include_invalid_data, output_dir
        )

        # Store in dictionary by endpoint identifier
        endpoint_key = f"{endpoint.method.upper()} {endpoint.path}"
        all_test_data[endpoint_key] = [td.model_dump() for td in test_data_collection]

    # Create a summary file
    summary = {
        "api_name": api_info["title"],
        "api_version": api_info["version"],
        "timestamp": timestamp,
        "endpoints_analyzed": len(selected_endpoints),
        "test_cases_per_endpoint": test_case_count,
        "include_invalid_data": include_invalid_data,
        "total_test_cases": sum(len(data) for data in all_test_data.values()),
        "endpoint_summary": {
            endpoint_key: len(data) for endpoint_key, data in all_test_data.items()
        },
    }

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nTest data generation completed. Summary saved to: {summary_path}")
    print(f"Generated test data for {len(selected_endpoints)} endpoints")
    print(f"Total test cases generated: {summary['total_test_cases']}")


if __name__ == "__main__":
    asyncio.run(main())

    # Example usage:
    # python src/test_data_generator_tool.py --spec data/toolshop/openapi.json --test-cases 5 --invalid
