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
from typing import List

from tools.test_data_generator import TestDataGeneratorTool
from schemas.tools.openapi_parser import (
    EndpointInfo,
)
from schemas.tools.test_data_generator import (
    TestDataGeneratorInput,
    TestDataGeneratorOutput,
    TestData,
)
from utils.demo_utils import (
    parse_openapi_spec,
    select_endpoints,
    create_timestamped_output_dir,
    print_endpoint_summary,
    save_summary_file,
    validate_file_exists,
    get_default_spec_path,
)


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
    print_endpoint_summary(endpoint, "Generating test data for")

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


def get_user_preferences():
    """Get user preferences for test data generation."""
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


async def main():
    """Main function to run the test data generator tool."""
    parser = argparse.ArgumentParser(description="Generate test data for API endpoints")
    parser.add_argument(
        "--spec",
        type=str,
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        help="Number of test cases to generate per endpoint",
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
    args = parser.parse_args()

    # Validate input file
    if not validate_file_exists(args.spec):
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "test_data")

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=True)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to generate test data for (comma-separated, or 'all'): ",
    )

    # Get user preferences if not provided via arguments
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
        user_test_case_count, user_include_invalid = get_user_preferences()
        if test_case_count is None:
            test_case_count = user_test_case_count
        if include_invalid_data is None:
            include_invalid_data = user_include_invalid

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
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "test_cases_per_endpoint": test_case_count,
        "include_invalid_data": include_invalid_data,
        "total_test_cases": sum(len(data) for data in all_test_data.values()),
        "endpoint_summary": {
            endpoint_key: len(data) for endpoint_key, data in all_test_data.items()
        },
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)

    print(f"\nTest data generation completed. Summary saved to: {summary_path}")
    print(f"Generated test data for {len(selected_endpoints)} endpoints")
    print(f"Total test cases generated: {summary_data['total_test_cases']}")


if __name__ == "__main__":
    asyncio.run(main())

    # Example usage:
    # python src/test_data_generator_tool.py --spec data/toolshop/openapi.json --test-cases 5 --invalid
