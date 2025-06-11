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
from common.logger import LoggerFactory, LoggerType, LogLevel


async def mine_constraints(
    endpoint: EndpointInfo, output_dir: str, logger
) -> Dict[str, Any]:
    """
    Mine constraints from an endpoint using the StaticConstraintMinerTool.

    Args:
        endpoint: The endpoint to analyze
        output_dir: Directory to save output
        logger: Logger instance for logging

    Returns:
        Dictionary containing constraint information
    """
    print_endpoint_summary(endpoint, "Mining constraints for")

    logger.info(
        f"Starting constraint mining for endpoint: {endpoint.method.upper()} {endpoint.path}"
    )
    logger.add_context(
        endpoint_method=endpoint.method.upper(),
        endpoint_path=endpoint.path,
        endpoint_name=endpoint.name,
    )

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
        logger.debug("Executing constraint mining tool")
        output: StaticConstraintMinerOutput = await miner_tool.execute(miner_input)

        constraint_summary = {
            "total": output.total_constraints,
            "request_response": len(output.request_response_constraints),
            "response_property": len(output.response_property_constraints),
            "request_param": len(output.request_param_constraints),
            "request_body": len(output.request_body_constraints),
        }

        logger.info(f"Constraint mining completed successfully")
        logger.add_context(**constraint_summary)

        logger.debug(f"Found {output.total_constraints} constraints:")
        logger.debug(
            f"  - {len(output.request_response_constraints)} request-response constraints"
        )
        logger.debug(
            f"  - {len(output.response_property_constraints)} response property constraints"
        )
        logger.debug(
            f"  - {len(output.request_param_constraints)} request parameter constraints"
        )
        logger.debug(
            f"  - {len(output.request_body_constraints)} request body constraints"
        )

        # Save the result to a file
        safe_endpoint_name = (
            endpoint.path.replace("/", "_").replace("{", "").replace("}", "")
        )
        filename = f"constraints_{endpoint.method.lower()}{safe_endpoint_name}.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        logger.info(f"Constraints saved to: {output_path}")

        # Export to Excel automatically
        try:
            excel_path = export_constraint_report_to_excel(
                output_path,
                output_path.replace(".json", ".xlsx"),
                include_analysis=True,
            )
            logger.info(f"Excel report created: {excel_path}")
        except Exception as e:
            logger.warning(f"Could not create Excel report: {str(e)}")

        # Return the output for potential further processing
        return output.model_dump()

    except Exception as e:
        logger.error(f"Error mining constraints: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the constraint mining demo."""
    # Initialize logger for the demo
    logger = LoggerFactory.get_logger(
        name="constraint-miner-demo",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.INFO,
    )

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

    # Update logger level if verbose
    if args.verbose:
        logger.set_level(LogLevel.DEBUG)

    logger.info("Starting constraint mining demo")
    logger.add_context(spec_file=args.spec, verbose=args.verbose)

    # Validate input file
    if not validate_file_exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "constraints")
    logger.add_context(output_directory=output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=True)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification")
        return

    logger.info(
        f"Found {len(api_info['endpoints'])} endpoints in API: {api_info['title']} v{api_info['version']}"
    )

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to analyze (comma-separated, or 'all'): ",
    )

    logger.info(f"Selected {len(selected_endpoints)} endpoints for constraint mining")

    # Mine constraints from selected endpoints
    all_constraints = []
    for i, endpoint in enumerate(selected_endpoints, 1):
        logger.info(f"Processing endpoint {i}/{len(selected_endpoints)}")
        constraints = await mine_constraints(endpoint, output_dir, logger)
        all_constraints.append(constraints)

    # Create a summary file
    summary_data = {
        "endpoints_analyzed": len(selected_endpoints),
        "constraints": all_constraints,
    }

    summary_path = save_summary_file(output_dir, api_info, summary_data)
    logger.info(f"Analysis completed successfully. Summary saved to: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
