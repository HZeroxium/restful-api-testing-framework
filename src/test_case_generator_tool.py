# src/test_case_generator_tool.py

"""
Test Case Generator Tool

This tool generates comprehensive test cases for API endpoints based on OpenAPI specifications.
It combines test data generation, constraint mining, and validation script generation.
"""

import asyncio
import os
import json
import argparse
from typing import List, Dict, Any

from tools.static_constraint_miner import StaticConstraintMinerTool
from tools.test_data_generator import TestDataGeneratorTool
from tools.test_case_generator import TestCaseGeneratorTool

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    ApiConstraint,
)
from schemas.tools.test_case_generator import TestCaseGeneratorInput
from schemas.tools.test_data_generator import TestDataGeneratorInput
from utils.demo_utils import (
    parse_openapi_spec,
    select_endpoints,
    create_timestamped_output_dir,
    print_endpoint_summary,
    save_summary_file,
    validate_file_exists,
    get_default_spec_path,
    get_user_test_preferences,
)
from common.logger import LoggerFactory, LoggerType, LogLevel


async def generate_test_case(
    endpoint: EndpointInfo,
    test_case_count: int,
    include_invalid_data: bool,
    output_dir: str,
    output_format: str = "json",
    verbose: bool = False,
    logger=None,
) -> Dict[str, Any]:
    """
    Generate comprehensive test cases for an endpoint.

    Args:
        endpoint: The endpoint to generate test cases for
        test_case_count: Number of test cases to generate
        include_invalid_data: Whether to include invalid test data
        output_dir: Directory to save output
        output_format: Output format (json or yaml)
        verbose: Enable verbose logging
        logger: Logger instance

    Returns:
        Dictionary containing test case information
    """
    if logger is None:
        logger = LoggerFactory.get_logger(
            name="test-case-generator",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        )

    endpoint_name = f"{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}"

    logger.info(
        f"Starting test case generation for endpoint: {endpoint.method.upper()} {endpoint.path}"
    )
    logger.add_context(
        endpoint_name=endpoint_name,
        endpoint_method=endpoint.method.upper(),
        endpoint_path=endpoint.path,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
        output_format=output_format,
    )

    print_endpoint_summary(endpoint, "Generating test cases for")

    # 1. Generate test data
    test_data_generator = TestDataGeneratorTool(verbose=verbose)
    data_input = TestDataGeneratorInput(
        endpoint_info=endpoint,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
    )

    logger.info("Step 1: Generating test data...")
    test_data_output = await test_data_generator.execute(data_input)
    test_data_collection = test_data_output.test_data_collection

    logger.info(f"Generated {len(test_data_collection)} test data items")

    # 2. Mine constraints
    constraint_miner = StaticConstraintMinerTool(verbose=verbose)
    constraint_input = StaticConstraintMinerInput(
        endpoint_info=endpoint,
        include_examples=True,
        include_schema_constraints=True,
        include_correlation_constraints=True,
    )

    logger.info("Step 2: Mining API constraints...")
    constraint_output: StaticConstraintMinerOutput = await constraint_miner.execute(
        constraint_input
    )

    # Combine all constraint types from the new structure
    constraints: List[ApiConstraint] = []
    constraints.extend(constraint_output.request_param_constraints)
    constraints.extend(constraint_output.request_body_constraints)
    constraints.extend(constraint_output.response_property_constraints)
    constraints.extend(constraint_output.request_response_constraints)

    logger.info(f"Mined {len(constraints)} constraints")

    # 3. Create test cases with validation scripts for each test data
    test_cases = []
    test_case_generator = TestCaseGeneratorTool(verbose=verbose)

    logger.info("Step 3: Generating test cases with validation scripts...")
    for i, test_data in enumerate(test_data_collection):
        logger.debug(f"Generating test case {i+1}/{len(test_data_collection)}")

        # Generate a complete test case with validation scripts
        # The TestCaseGeneratorTool now handles script generation internally
        case_input = TestCaseGeneratorInput(
            endpoint_info=endpoint,
            constraints=constraints,
            test_data=test_data,
            name=f"Test case {i+1} for {endpoint.method.upper()} {endpoint.path}",
            description=f"Generated test case {i+1} based on constraints and test data",
        )
        case_output = await test_case_generator.execute(case_input)
        test_case = case_output.test_case

        # Add to our collection
        test_cases.append(test_case.model_dump())

    # Create summary and complete test case package
    test_case_package = {
        "api_name": endpoint.name,
        "endpoint": {
            "method": endpoint.method,
            "path": endpoint.path,
            "description": endpoint.description,
            "auth_required": endpoint.auth_required,
        },
        "test_data": [td.model_dump() for td in test_data_collection],
        "constraints": [c.model_dump() for c in constraints],
        "test_cases": test_cases,
        "summary": {
            "total_test_cases": len(test_cases),
            "total_constraints": len(constraints),
            "total_validation_scripts": sum(
                len(tc.get("validation_scripts", [])) for tc in test_cases
            ),
            "include_invalid_data": include_invalid_data,
            "constraint_breakdown": {
                "request_param_constraints": len(
                    constraint_output.request_param_constraints
                ),
                "request_body_constraints": len(
                    constraint_output.request_body_constraints
                ),
                "response_property_constraints": len(
                    constraint_output.response_property_constraints
                ),
                "request_response_constraints": len(
                    constraint_output.request_response_constraints
                ),
            },
        },
    }

    # Save to file
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{endpoint_name}_test_cases.json")

    with open(output_file, "w") as f:
        json.dump(test_case_package, f, indent=2, default=str)

    logger.info(f"Test cases saved to: {output_file}")
    logger.info(
        f"Summary: {len(test_cases)} test cases with {len(constraints)} constraints"
    )

    logger.add_context(
        output_file=output_file,
        total_test_cases=len(test_cases),
        total_constraints=len(constraints),
        total_validation_scripts=test_case_package["summary"][
            "total_validation_scripts"
        ],
    )

    return test_case_package


async def main():
    """Main function for the test case generator tool."""
    parser = argparse.ArgumentParser(
        description="Generate test cases for API endpoints"
    )
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
        name="test-case-generator-main",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info("Starting test case generator tool")
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

    # Create timestamped output directory
    output_dir = create_timestamped_output_dir("output", "test_cases")
    logger.add_context(output_directory=output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=args.verbose)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification.")
        return

    logger.info(
        f"Found {len(api_info['endpoints'])} endpoints in API: {api_info['title']} v{api_info['version']}"
    )

    # Select endpoints to generate test cases for
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to generate test cases for (comma-separated, or 'all'): ",
    )

    logger.info(
        f"Selected {len(selected_endpoints)} endpoints for test case generation"
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
        user_test_case_count, user_include_invalid = get_user_test_preferences()
        if test_case_count is None:
            test_case_count = user_test_case_count
        if include_invalid_data is None:
            include_invalid_data = user_include_invalid

    logger.add_context(
        test_case_count=test_case_count, include_invalid_data=include_invalid_data
    )

    # Generate test cases for each selected endpoint
    all_test_cases = []
    for i, endpoint in enumerate(selected_endpoints, 1):
        logger.info(f"Processing endpoint {i}/{len(selected_endpoints)}")

        test_case = await generate_test_case(
            endpoint=endpoint,
            test_case_count=test_case_count,
            include_invalid_data=include_invalid_data,
            output_dir=output_dir,
            verbose=args.verbose,
            logger=logger,
        )
        all_test_cases.append(test_case)

    # Create a summary file
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "test_cases_per_endpoint": test_case_count,
        "include_invalid_data": include_invalid_data,
        "total_test_cases": sum(
            tc["summary"]["total_test_cases"] for tc in all_test_cases
        ),
        "total_constraints": sum(
            tc["summary"]["total_constraints"] for tc in all_test_cases
        ),
        "endpoint_summary": {
            f"{tc['endpoint']['method'].upper()} {tc['endpoint']['path']}": {
                "test_cases": tc["summary"]["total_test_cases"],
                "constraints": tc["summary"]["total_constraints"],
                "validation_scripts": tc["summary"]["total_validation_scripts"],
            }
            for tc in all_test_cases
        },
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)

    logger.info("Test case generation completed successfully")
    logger.add_context(
        summary_path=summary_path,
        endpoints_processed=len(selected_endpoints),
        total_test_cases=summary_data["total_test_cases"],
        total_constraints=summary_data["total_constraints"],
    )

    # Final output using logger instead of print
    logger.info(f"Test case generation completed. Summary saved to: {summary_path}")
    logger.info(f"Generated test cases for {len(selected_endpoints)} endpoints")
    logger.info(f"Total test cases generated: {summary_data['total_test_cases']}")
    logger.info(f"Output directory: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
