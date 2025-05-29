# src/constraint_miner_tool.py

import asyncio
import os
import json
import argparse
from typing import List, Dict, Any
from datetime import datetime

from tools import OpenAPIParserTool, StaticConstraintMinerTool
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    EndpointInfo,
)
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
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
        "\nEnter endpoint numbers to analyze (comma-separated, or 'all'): "
    )

    if selected_indices.lower() == "all":
        return endpoints

    try:
        indices = [int(idx.strip()) - 1 for idx in selected_indices.split(",")]
        selected = [endpoints[idx] for idx in indices if 0 <= idx < len(endpoints)]
        if not selected:
            print(
                "No valid endpoints selected, analyzing the first endpoint by default."
            )
            return [endpoints[0]]
        return selected
    except (ValueError, IndexError):
        print("Invalid selection, analyzing the first endpoint by default.")
        return [endpoints[0]]


async def mine_constraints(endpoint: EndpointInfo, output_dir: str) -> Dict[str, Any]:
    """
    Mine constraints from an endpoint using the StaticConstraintMinerTool.

    Args:
        endpoint: The endpoint to analyze
        output_dir: Directory to save output

    Returns:
        Dictionary containing constraint information
    """
    print(f"\nMining constraints for: [{endpoint.method.upper()}] {endpoint.path}")

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
        default="data/toolshop/openapi.json",
        help="Path to OpenAPI specification file",
    )
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", "constraints", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(api_info["endpoints"])

    # Mine constraints from selected endpoints
    all_constraints = []
    for endpoint in selected_endpoints:
        constraints = await mine_constraints(endpoint, output_dir)
        all_constraints.append(constraints)

    # Create a summary file
    summary = {
        "api_name": api_info["title"],
        "api_version": api_info["version"],
        "timestamp": timestamp,
        "endpoints_analyzed": len(selected_endpoints),
        "constraints": all_constraints,
    }

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nAnalysis completed. Summary saved to: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
