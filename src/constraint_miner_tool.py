# src/constraint_miner_tool.py

import asyncio
import os
import json
import argparse
from typing import Dict, Any

from tools import StaticConstraintMinerTool
from schemas.tools.openapi_parser import (
    EndpointInfo,
)
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
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
from report_visualizer import export_constraint_report_to_excel


async def mine_constraints(endpoint: EndpointInfo, output_dir: str) -> Dict[str, Any]:
    """
    Mine constraints from an endpoint using the StaticConstraintMinerTool.

    Args:
        endpoint: The endpoint to analyze
        output_dir: Directory to save output

    Returns:
        Dictionary containing constraint information
    """
    print_endpoint_summary(endpoint, "Mining constraints for")

    # Create the miner tool
    miner_tool = StaticConstraintMinerTool(verbose=True)

    # Create input for the tool
    miner_input = StaticConstraintMinerInput(
        endpoint_info=endpoint,
        include_examples=True,
        include_schema_constraints=True,
        include_correlation_constraints=True,
    )

    # Execute the tool
    try:
        print("Running constraint miner...")
        output: StaticConstraintMinerOutput = await miner_tool.execute(miner_input)

        print(f"Found {output.total_constraints} constraints:")
        print(
            f"  - {len(output.request_response_constraints)} request-response constraints"
        )
        print(
            f"  - {len(output.response_property_constraints)} response property constraints"
        )

        # Display a few example constraints if available
        if output.request_response_constraints:
            print("\nExample request-response constraints:")
            for i, constraint in enumerate(output.request_response_constraints[:3]):
                print(
                    f"  {i+1}. {constraint.description} (Severity: {constraint.severity})"
                )

        if output.response_property_constraints:
            print("\nExample response property constraints:")
            for i, constraint in enumerate(output.response_property_constraints[:3]):
                print(
                    f"  {i+1}. {constraint.description} (Severity: {constraint.severity})"
                )

        # Save the result to a file
        safe_endpoint_name = (
            endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
        )
        filename = f"constraints_{endpoint.method.lower()}{safe_endpoint_name}.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        print(f"Constraints saved to: {output_path}")

        # Export to Excel automatically
        try:
            excel_path = export_constraint_report_to_excel(
                output_path,
                output_path.replace(".json", ".xlsx"),
                include_analysis=True,
            )
            print(f"Excel report created: {excel_path}")
        except Exception as e:
            print(f"Warning: Could not create Excel report: {str(e)}")

        # Return the output for potential further processing
        return output.model_dump()

    except Exception as e:
        print(f"Error mining constraints: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the constraint mining demo."""
    parser = argparse.ArgumentParser(description="Mine constraints from API endpoints")
    parser.add_argument(
        "--spec",
        type=str,
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    # Validate input file
    if not validate_file_exists(args.spec):
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "constraints")

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=True)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to analyze (comma-separated, or 'all'): ",
    )

    # Mine constraints from selected endpoints
    all_constraints = []
    for endpoint in selected_endpoints:
        constraints = await mine_constraints(endpoint, output_dir)
        all_constraints.append(constraints)

    # Create a summary file
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "constraints": all_constraints,
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)
    print(f"\nAnalysis completed. Summary saved to: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
