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
from datetime import datetime
from typing import List, Dict, Any

from tools import OpenAPIParserTool
from tools.static_constraint_miner import StaticConstraintMinerTool
from tools.test_data_generator import TestDataGeneratorTool
from tools.test_script_generator import TestScriptGeneratorTool
from tools.test_case_generator import TestCaseGeneratorTool

from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    EndpointInfo,
)
from schemas.tools.test_data_generator import TestDataGeneratorInput
from schemas.tools.constraint_miner import StaticConstraintMinerInput
from schemas.tools.test_script_generator import TestScriptGeneratorInput
from schemas.tools.test_case_generator import TestCaseGeneratorInput


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
        "\nEnter endpoint numbers to generate test cases for (comma-separated, or 'all'): "
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


async def generate_test_case(
    endpoint: EndpointInfo,
    test_case_count: int,
    include_invalid_data: bool,
    output_dir: str,
    output_format: str = "json",
    verbose: bool = False,
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

    Returns:
        Dictionary containing test case information
    """
    endpoint_name = f"{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}"
    print(f"\nGenerating test cases for: [{endpoint.method.upper()}] {endpoint.path}")

    # 1. Generate test data
    test_data_generator = TestDataGeneratorTool(verbose=verbose)
    data_input = TestDataGeneratorInput(
        endpoint_info=endpoint,
        test_case_count=test_case_count,
        include_invalid_data=include_invalid_data,
    )

    print("Step 1: Generating test data...")
    test_data_output = await test_data_generator.execute(data_input)
    test_data_collection = test_data_output.test_data_collection

    print(f"  Generated {len(test_data_collection)} test data items")

    # 2. Mine constraints
    constraint_miner = StaticConstraintMinerTool(verbose=verbose)
    constraint_input = StaticConstraintMinerInput(
        endpoint_info=endpoint,
        include_examples=True,
        include_schema_constraints=True,
        include_correlation_constraints=True,
    )

    print("Step 2: Mining API constraints...")
    constraint_output = await constraint_miner.execute(constraint_input)

    constraints = []
    constraints.extend(constraint_output.request_response_constraints)
    constraints.extend(constraint_output.response_property_constraints)

    print(f"  Mined {len(constraints)} constraints")

    # 3. Create test cases with validation scripts for each test data
    test_cases = []
    test_script_generator = TestScriptGeneratorTool(verbose=verbose)
    test_case_generator = TestCaseGeneratorTool(verbose=verbose)

    print("Step 3: Generating test cases with validation scripts...")
    for i, test_data in enumerate(test_data_collection):
        print(
            f"  Generating validation scripts for test case {i+1}/{len(test_data_collection)}"
        )

        # Generate validation scripts based on constraints and test data
        script_input = TestScriptGeneratorInput(
            endpoint_info=endpoint,
            test_data=test_data,
            constraints=constraints,
        )
        script_output = await test_script_generator.execute(script_input)
        validation_scripts = script_output.validation_scripts

        # Generate a complete test case
        case_input = TestCaseGeneratorInput(
            endpoint_info=endpoint,
            test_data=test_data,
            validation_scripts=validation_scripts,
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
        },
    }

    # Save to file
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{endpoint_name}_test_cases.json")

    with open(output_file, "w") as f:
        json.dump(test_case_package, f, indent=2, default=str)

    print(f"Test cases saved to: {output_file}")
    print(f"Summary: {len(test_cases)} test cases with {len(constraints)} constraints")

    return test_case_package


async def main():
    """Main function for the test case generator tool."""
    parser = argparse.ArgumentParser(
        description="Generate test cases for API endpoints"
    )
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
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", "test_cases", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to generate test cases for
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

    # Generate test cases for each selected endpoint
    all_test_cases = []
    for endpoint in selected_endpoints:
        test_case = await generate_test_case(
            endpoint=endpoint,
            test_case_count=test_case_count,
            include_invalid_data=include_invalid_data,
            output_dir=output_dir,
            verbose=args.verbose,
        )
        all_test_cases.append(test_case)

    # Create a summary file
    summary = {
        "api_name": api_info["title"],
        "api_version": api_info["version"],
        "timestamp": timestamp,
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

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nTest case generation completed. Summary saved to: {summary_path}")
    print(f"Generated test cases for {len(selected_endpoints)} endpoints")
    print(f"Total test cases generated: {summary['total_test_cases']}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
