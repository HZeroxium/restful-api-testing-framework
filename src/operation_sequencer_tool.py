"""
Operation Sequencer Tool

This tool analyzes API endpoints and identifies dependencies between them,
then creates sequences of operations that should be executed in order.

It helps determine which operations depend on others (e.g., POST /order depends on GET /product)
and generates execution sequences that respect these dependencies.
"""

import asyncio
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

from tools import OpenAPIParserTool, OperationSequencerTool
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
    EndpointInfo,
)
from schemas.tools.operation_sequencer import (
    OperationSequencerInput,
    OperationSequencerOutput,
    OperationSequence,
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
            print("No valid endpoints selected, analyzing all endpoints by default.")
            return endpoints
        return selected
    except (ValueError, IndexError):
        print("Invalid selection, analyzing all endpoints by default.")
        return endpoints


async def sequence_operations(
    endpoints: List[EndpointInfo], api_info: Dict[str, Any], output_dir: str
) -> Dict[str, Any]:
    """
    Sequence operations based on dependencies using OperationSequencerTool.

    Args:
        endpoints: List of endpoints to analyze
        api_info: Information about the API
        output_dir: Directory to save output

    Returns:
        Dictionary containing sequencing information
    """
    print(f"\nSequencing operations for {len(endpoints)} endpoints")

    # Create the sequencer tool
    sequencer_tool = OperationSequencerTool(verbose=True)

    # Create input for the tool
    sequencer_input = OperationSequencerInput(
        endpoints=endpoints,
        collection_name=f"{api_info['title']} Operations",
        include_data_mapping=True,
    )

    # Execute the tool
    try:
        print("Running operation sequencer...")
        output: OperationSequencerOutput = await sequencer_tool.execute(sequencer_input)

        print(f"Found {output.total_sequences} operation sequences")

        # Display a few example sequences
        if output.sequences:
            print("\nExample operation sequences:")
            for i, sequence in enumerate(output.sequences[:3]):
                print(f"\nSequence {i+1}: {sequence.name}")
                print(f"Description: {sequence.description}")
                print(f"Operations ({len(sequence.operations)}):")
                for j, op in enumerate(sequence.operations):
                    print(f"  {j+1}. {op}")

                if sequence.dependencies:
                    print(f"Dependencies ({len(sequence.dependencies)}):")
                    for j, dep in enumerate(sequence.dependencies[:3]):
                        print(
                            f"  {j+1}. {dep.source_operation} depends on {dep.target_operation}"
                        )
                        print(f"     Reason: {dep.reason}")
                        if dep.data_mapping:
                            print(f"     Data mapping: {dep.data_mapping}")

        # Save the result to a file
        filename = f"operation_sequences.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        print(f"Operation sequences saved to: {output_path}")

        # Return the output for potential further processing
        return output.model_dump()

    except Exception as e:
        print(f"Error sequencing operations: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the operation sequencing demo."""
    parser = argparse.ArgumentParser(
        description="Sequence API operations based on dependencies"
    )
    parser.add_argument(
        "--spec",
        type=str,
        default="data/toolshop/openapi.json",
        help="Path to OpenAPI specification file",
    )
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", "operation_sequences", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(api_info["endpoints"])

    # Sequence operations
    sequencing_result = await sequence_operations(
        selected_endpoints, api_info, output_dir
    )

    # Create a summary file
    summary = {
        "api_name": api_info["title"],
        "api_version": api_info["version"],
        "timestamp": timestamp,
        "endpoints_analyzed": len(selected_endpoints),
        "total_sequences": sequencing_result.get("total_sequences", 0),
        "result": sequencing_result.get("result", {}),
    }

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nAnalysis completed. Summary saved to: {summary_path}")
    print(f"\nTo visualize these sequences, use the sequences_visualizer.py tool:")
    print(
        f"python src/sequences_visualizer.py --input {output_dir}/operation_sequences.json"
    )


if __name__ == "__main__":
    asyncio.run(main())

    # Usage:
    # python operation_sequencer_tool.py --spec path/to/openapi.json
