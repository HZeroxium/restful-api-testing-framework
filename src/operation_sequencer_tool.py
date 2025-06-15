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
from common.logger import LoggerFactory, LoggerType, LogLevel


async def sequence_operations(
    endpoints: List[EndpointInfo],
    api_info: Dict[str, Any],
    output_dir: str,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Sequence operations based on dependencies using OperationSequencerTool.

    Args:
        endpoints: List of endpoints to analyze
        api_info: Information about the API
        output_dir: Directory to save output
        verbose: Enable verbose logging

    Returns:
        Dictionary containing sequencing information
    """
    # Initialize logger for operation sequencing
    log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="operation-sequencer-demo",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info(f"Sequencing operations for {len(endpoints)} endpoints")
    logger.add_context(
        endpoints_count=len(endpoints),
        api_name=api_info.get("title", "Unknown"),
        api_version=api_info.get("version", "Unknown"),
        output_directory=output_dir,
    )

    # Create the sequencer tool
    sequencer_tool = OperationSequencerTool(verbose=verbose)

    # Create input for the tool
    sequencer_input = OperationSequencerInput(
        endpoints=endpoints,
        collection_name=f"{api_info['title']} Operations",
        include_data_mapping=True,
    )

    # Execute the tool
    try:
        logger.info("Running operation sequencer...")
        output: OperationSequencerOutput = await sequencer_tool.execute(sequencer_input)

        logger.info(f"Found {output.total_sequences} operation sequences")
        logger.add_context(
            total_sequences=output.total_sequences,
            has_dependencies=any(seq.dependencies for seq in output.sequences),
        )

        # Display a few example sequences
        if output.sequences:
            logger.info("Example operation sequences:")
            for i, sequence in enumerate(output.sequences[:3]):
                logger.info(f"Sequence {i+1}: {sequence.name}")
                logger.add_context(sequence_name=sequence.name)

                if verbose:
                    logger.debug(f"Description: {sequence.description}")
                    logger.debug(f"Operations ({len(sequence.operations)}):")
                    for j, op in enumerate(sequence.operations):
                        logger.debug(f"  {j+1}. {op}")

                    if sequence.dependencies:
                        logger.debug(f"Dependencies ({len(sequence.dependencies)}):")
                        for j, dep in enumerate(sequence.dependencies[:3]):
                            logger.debug(
                                f"  {j+1}. {dep.source_operation} depends on {dep.target_operation}"
                            )
                            logger.debug(f"     Reason: {dep.reason}")
                            if dep.data_mapping:
                                logger.debug(f"     Data mapping: {dep.data_mapping}")

        # Save the result to a file
        filename = f"operation_sequences.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        logger.info(f"Operation sequences saved to: {output_path}")

        # Return the output for potential further processing
        return output.model_dump()

    except Exception as e:
        logger.error(f"Error sequencing operations: {str(e)}")
        if verbose:
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
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

    # Initialize main logger
    log_level = LogLevel.DEBUG if args.verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="operation-sequencer-main",
        logger_type=LoggerType.STANDARD,
        level=log_level,
    )

    logger.info("Starting operation sequencing demo")
    logger.add_context(
        spec_file=args.spec,
        verbose=args.verbose,
    )

    # Validate input file
    if not validate_file_exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        return

    # Create timestamped output directory
    output_dir = create_timestamped_output_dir("output", "operation_sequences")
    logger.add_context(output_directory=output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=args.verbose)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification.")
        return

    logger.info(
        f"Found {len(api_info['endpoints'])} endpoints in API: {api_info['title']} v{api_info['version']}"
    )

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to analyze (comma-separated, or 'all'): ",
    )

    logger.info(f"Selected {len(selected_endpoints)} endpoints for analysis")

    # Sequence operations
    sequencing_result = await sequence_operations(
        selected_endpoints, api_info, output_dir, verbose=args.verbose
    )

    # Create a summary file
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "total_sequences": sequencing_result.get("total_sequences", 0),
        "result": sequencing_result.get("result", {}),
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)

    logger.info("Analysis completed successfully")
    logger.add_context(
        summary_path=summary_path,
        endpoints_analyzed=len(selected_endpoints),
        total_sequences=sequencing_result.get("total_sequences", 0),
    )

    # Final output
    print(f"\nAnalysis completed. Summary saved to: {summary_path}")
    print(f"\nTo visualize these sequences, use the sequences_visualizer.py tool:")
    print(
        f"python src/sequences_visualizer.py --input {output_dir}/operation_sequences.json"
    )


if __name__ == "__main__":
    asyncio.run(main())

    # Usage:
    # python operation_sequencer_tool.py --spec path/to/openapi.json
