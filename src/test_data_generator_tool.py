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

from tools.llm.test_data_generator import TestDataGeneratorTool
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
from common.logger import LoggerFactory, LoggerType, LogLevel


async def generate_test_data(
    endpoint: EndpointInfo,
    test_case_count: int,
    include_invalid_data: bool,
    output_dir: str,
    logger=None,
) -> List[TestData]:
    """
    Generate test data for an endpoint using TestDataGeneratorTool.

    Args:
        endpoint: The endpoint to generate test data for
        test_case_count: Number of test cases to generate
        include_invalid_data: Whether to include invalid test data
        output_dir: Directory to save output
        logger: Logger instance

    Returns:
        List of generated TestData objects
    """
    if logger is None:
        logger = LoggerFactory.get_logger(
            name="test-data-generator",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    logger.info(
        f"Starting test data generation for endpoint: {endpoint.method.upper()} {endpoint.path}"
    )
    logger.add_context(
        endpoint_method=endpoint.method.upper(),
        endpoint_path=endpoint.path,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
    )

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
        logger.info("Running test data generator...")
        output: TestDataGeneratorOutput = await generator_tool.execute(generator_input)

        test_data_collection = output.test_data_collection
        logger.info(f"Generated {len(test_data_collection)} test cases")

        # Display summary of test data
        valid_count = sum(
            1 for td in test_data_collection if td.expected_status_code < 400
        )
        invalid_count = len(test_data_collection) - valid_count

        logger.info(f"Valid test cases (expected success): {valid_count}")
        logger.info(f"Invalid test cases (expected failure): {invalid_count}")

        logger.add_context(
            total_generated=len(test_data_collection),
            valid_count=valid_count,
            invalid_count=invalid_count,
        )

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

        logger.info(f"Test data saved to: {output_path}")
        logger.add_context(output_file=output_path)

        return test_data_collection

    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
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
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Initialize main logger
    log_level = LogLevel.DEBUG if args.verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="test-data-generator-main",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info("Starting test data generator tool")
    logger.add_context(
        spec_file=args.spec,
        verbose=args.verbose,
        test_cases_arg=args.test_cases,
        include_invalid=args.invalid,
        exclude_invalid=args.no_invalid,
    )

    # Validate input file
    if not validate_file_exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "test_data")
    logger.add_context(output_directory=output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=True)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification.")
        return

    logger.info(
        f"Found {len(api_info['endpoints'])} endpoints in API: {api_info['title']} v{api_info['version']}"
    )

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to generate test data for (comma-separated, or 'all'): ",
    )

    logger.info(
        f"Selected {len(selected_endpoints)} endpoints for test data generation"
    )

    # Get user preferences if not provided via arguments
    if args.test_cases is not None:
        test_case_count = args.test_cases
        # Validate test case count
        if test_case_count < 1:
            test_case_count = 1
            logger.warning("Test case count must be at least 1, using 1.")
        elif test_case_count > 10:
            test_case_count = 10
            logger.warning("Maximum test case count is 10, using 10.")
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

    logger.add_context(
        test_case_count=test_case_count, include_invalid_data=include_invalid_data
    )

    # Generate test data for each selected endpoint
    all_test_data = {}
    for i, endpoint in enumerate(selected_endpoints, 1):
        logger.info(f"Processing endpoint {i}/{len(selected_endpoints)}")

        test_data_collection = await generate_test_data(
            endpoint, test_case_count, include_invalid_data, output_dir, logger
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

    logger.info("Test data generation completed successfully")
    logger.add_context(
        summary_path=summary_path,
        endpoints_processed=len(selected_endpoints),
        total_test_cases=summary_data["total_test_cases"],
    )

    # Final output using logger instead of print
    logger.info(f"Test data generation completed. Summary saved to: {summary_path}")
    logger.info(f"Generated test data for {len(selected_endpoints)} endpoints")
    logger.info(f"Total test cases generated: {summary_data['total_test_cases']}")


if __name__ == "__main__":
    asyncio.run(main())

    # Example usage:
    # python src/test_data_generator_tool.py --spec data/toolshop/openapi.json --test-cases 5 --invalid
