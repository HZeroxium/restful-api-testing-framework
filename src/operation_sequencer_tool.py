# src/operation_sequencer_tool.py

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
from typing import List, Dict, Any

from tools import OperationSequencerTool
from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.operation_sequencer import (
    OperationSequencerInput,
    OperationSequencerOutput,
)
from utils.demo_utils import (
    parse_openapi_spec,
    select_endpoints,
    create_timestamped_output_dir,
    save_summary_file,
    validate_file_exists,
    get_default_spec_path,
)


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
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Validate input file
    if not validate_file_exists(args.spec):
        return

    # Create timestamped output directory
    output_dir = create_timestamped_output_dir("output", "operation_sequences")

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=args.verbose)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to analyze (comma-separated, or 'all'): ",
    )

    # Sequence operations
    sequencing_result = await sequence_operations(
        selected_endpoints, api_info, output_dir
    )

    # Create a summary file
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "total_sequences": sequencing_result.get("total_sequences", 0),
        "result": sequencing_result.get("result", {}),
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)

    print(f"\nAnalysis completed. Summary saved to: {summary_path}")
    print(f"\nTo visualize these sequences, use the sequences_visualizer.py tool:")
    print(
        f"python src/sequences_visualizer.py --input {output_dir}/operation_sequences.json"
    )


if __name__ == "__main__":
    asyncio.run(main())

    # Usage:
    # python operation_sequencer_tool.py --spec path/to/openapi.json
