# src/constraint_miner_sub_tool.py

"""
Testing tool for individual constraint mining sub-tools.
Allows testing each constraint miner individually for debugging and validation.
"""

import asyncio
import os
import json
import argparse
from typing import Dict, Any

from tools.constraint_miner.request_param_constraint_miner import (
    RequestParamConstraintMinerTool,
)
from tools.constraint_miner.request_body_constraint_miner import (
    RequestBodyConstraintMinerTool,
)
from tools.constraint_miner.response_property_constraint_miner import (
    ResponsePropertyConstraintMinerTool,
)
from tools.constraint_miner.request_response_constraint_miner import (
    RequestResponseConstraintMinerTool,
)

from schemas.tools.openapi_parser import (
    EndpointInfo,
)
from schemas.tools.constraint_miner import (
    RequestParamConstraintMinerInput,
    RequestBodyConstraintMinerInput,
    ResponsePropertyConstraintMinerInput,
    RequestResponseConstraintMinerInput,
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


class ConstraintMinerTester:
    """Test individual constraint mining tools."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

        # Initialize logger for the tester
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="constraint-miner-tester",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        self.tools = {
            "param": RequestParamConstraintMinerTool(verbose=verbose),
            "body": RequestBodyConstraintMinerTool(verbose=verbose),
            "response": ResponsePropertyConstraintMinerTool(verbose=verbose),
            "correlation": RequestResponseConstraintMinerTool(verbose=verbose),
        }

    async def test_param_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test request parameter constraint miner."""
        self.logger.info("Starting request parameter constraint miner test")
        self.logger.add_context(
            tool_type="param_miner",
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
        )

        print_endpoint_summary(endpoint, "Testing parameter constraints for")

        try:
            # Create input
            miner_input = RequestParamConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                focus_on_validation=True,
            )

            # Execute the tool
            self.logger.debug("Executing parameter constraint miner")
            output = await self.tools["param"].execute(miner_input)

            # Display results
            self.logger.info(f"Parameter constraint mining completed")
            self.logger.add_context(
                total_constraints=output.total_constraints,
                source=output.result.get("source", "unknown"),
                status=output.result.get("status", "unknown"),
            )

            if output.param_constraints:
                self.logger.debug(
                    f"Found {len(output.param_constraints)} parameter constraints:"
                )
                for i, constraint in enumerate(output.param_constraints, 1):
                    self.logger.debug(f"  {i}. {constraint.description}")
                    self.logger.debug(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
            else:
                self.logger.warning("No parameter constraints found")

            # Save results
            filename = f"param_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Results saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            self.logger.error(f"Error testing parameter miner: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "tool": "param_miner"}

    async def test_body_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test request body constraint miner."""
        self.logger.info("Starting request body constraint miner test")
        self.logger.add_context(
            tool_type="body_miner",
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
        )

        print_endpoint_summary(endpoint, "Testing body constraints for")

        try:
            # Create input
            miner_input = RequestBodyConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                focus_on_schema=True,
            )

            # Execute the tool
            self.logger.debug("Executing body constraint miner")
            output = await self.tools["body"].execute(miner_input)

            # Display results
            self.logger.info(f"Request body constraint mining completed")
            self.logger.add_context(
                total_constraints=output.total_constraints,
                source=output.result.get("source", "unknown"),
                status=output.result.get("status", "unknown"),
            )

            if output.body_constraints:
                self.logger.debug(
                    f"Found {len(output.body_constraints)} body constraints:"
                )
                for i, constraint in enumerate(output.body_constraints, 1):
                    self.logger.debug(f"  {i}. {constraint.description}")
                    self.logger.debug(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
            else:
                self.logger.warning("No body constraints found")

            # Save results
            filename = f"body_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Results saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            self.logger.error(f"Error testing body miner: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "tool": "body_miner"}

    async def test_response_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test response property constraint miner."""
        self.logger.info("Starting response property constraint miner test")
        self.logger.add_context(
            tool_type="response_miner",
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
        )

        print_endpoint_summary(endpoint, "Testing response constraints for")

        try:
            # Create input
            miner_input = ResponsePropertyConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                analyze_structure=True,
            )

            # Execute the tool
            self.logger.debug("Executing response constraint miner")
            output = await self.tools["response"].execute(miner_input)

            # Display results
            self.logger.info(f"Response property constraint mining completed")
            self.logger.add_context(
                total_constraints=output.total_constraints,
                source=output.result.get("source", "unknown"),
                status=output.result.get("status", "unknown"),
            )

            if output.response_constraints:
                self.logger.debug(
                    f"Found {len(output.response_constraints)} response constraints:"
                )
                for i, constraint in enumerate(output.response_constraints, 1):
                    self.logger.debug(f"  {i}. {constraint.description}")
                    self.logger.debug(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
            else:
                self.logger.warning("No response constraints found")

            # Save results
            filename = f"response_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Results saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            self.logger.error(f"Error testing response miner: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "tool": "response_miner"}

    async def test_correlation_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test request-response correlation constraint miner."""
        self.logger.info("Starting request-response correlation constraint miner test")
        self.logger.add_context(
            tool_type="correlation_miner",
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
        )

        print_endpoint_summary(endpoint, "Testing correlation constraints for")

        try:
            # Create input
            miner_input = RequestResponseConstraintMinerInput(
                endpoint_info=endpoint,
                include_correlations=True,
                analyze_status_codes=True,
            )

            # Execute the tool
            self.logger.debug("Executing correlation constraint miner")
            output = await self.tools["correlation"].execute(miner_input)

            # Display results
            self.logger.info(
                f"Request-response correlation constraint mining completed"
            )
            self.logger.add_context(
                total_constraints=output.total_constraints,
                source=output.result.get("source", "unknown"),
                status=output.result.get("status", "unknown"),
            )

            if output.correlation_constraints:
                self.logger.debug(
                    f"Found {len(output.correlation_constraints)} correlation constraints:"
                )
                for i, constraint in enumerate(output.correlation_constraints, 1):
                    self.logger.debug(f"  {i}. {constraint.description}")
                    self.logger.debug(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
            else:
                self.logger.warning("No correlation constraints found")

            # Save results
            filename = f"correlation_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            self.logger.info(f"Results saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            self.logger.error(f"Error testing correlation miner: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "tool": "correlation_miner"}

    async def test_all_miners(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test all constraint miners on the given endpoint."""
        self.logger.info("Starting comprehensive constraint mining test for all tools")
        self.logger.add_context(
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
            test_type="comprehensive",
        )

        print_endpoint_summary(endpoint, "Running comprehensive constraint mining for")

        results = {}

        # Test each miner
        results["param"] = await self.test_param_miner(endpoint, output_dir)
        results["body"] = await self.test_body_miner(endpoint, output_dir)
        results["response"] = await self.test_response_miner(endpoint, output_dir)
        results["correlation"] = await self.test_correlation_miner(endpoint, output_dir)

        # Create summary
        total_constraints = 0
        successful_tools = 0
        failed_tools = []

        for tool_name, result in results.items():
            if "error" not in result:
                successful_tools += 1
                total_constraints += result.get("total_constraints", 0)
            else:
                failed_tools.append(tool_name)

        summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints_found": total_constraints,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "tool_results": results,
            "status": "completed",
        }

        # Save comprehensive summary
        summary_filename = f"all_miners_summary_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
        summary_path = os.path.join(output_dir, summary_filename)
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        self.logger.info("Comprehensive testing completed")
        self.logger.add_context(
            total_constraints_found=total_constraints,
            successful_tools=successful_tools,
            failed_tools_count=len(failed_tools),
        )

        if failed_tools:
            self.logger.warning(f"Failed tools: {', '.join(failed_tools)}")

        self.logger.info(f"Summary saved to: {summary_path}")

        return summary

    async def cleanup(self):
        """Clean up all tools."""
        self.logger.debug("Cleaning up constraint miner tester tools")
        for tool in self.tools.values():
            await tool.cleanup()


async def main():
    """Main function to run the constraint miner sub-tool tester."""
    # Initialize logger for the demo
    logger = LoggerFactory.get_logger(
        name="constraint-miner-sub-tool-demo",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.INFO,
    )

    parser = argparse.ArgumentParser(
        description="Test individual constraint mining tools"
    )
    parser.add_argument(
        "--spec",
        type=str,
        default=get_default_spec_path(),
        help="Path to OpenAPI specification file",
    )
    parser.add_argument(
        "--tool",
        type=str,
        choices=["param", "body", "response", "correlation", "all"],
        default="all",
        help="Which tool to test (default: all)",
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

    logger.info("Starting constraint miner sub-tool testing")
    logger.add_context(
        spec_file=args.spec, tool_to_test=args.tool, verbose=args.verbose
    )

    # Validate input file
    if not validate_file_exists(args.spec):
        logger.error(f"Specification file not found: {args.spec}")
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "constraint_mining_tests")
    logger.add_context(output_directory=output_dir)

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=args.verbose)

    if not api_info["endpoints"]:
        logger.error("No endpoints found in the OpenAPI specification")
        return

    logger.info(
        f"Found {len(api_info['endpoints'])} endpoints in API: {api_info['title']} v{api_info['version']}"
    )

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to test (comma-separated, or 'all'): ",
    )

    logger.info(f"Selected {len(selected_endpoints)} endpoints for testing")

    # Initialize tester
    tester = ConstraintMinerTester(verbose=args.verbose)

    try:
        # Test each selected endpoint
        all_results = []
        for i, endpoint in enumerate(selected_endpoints, 1):
            logger.info(f"Testing endpoint {i}/{len(selected_endpoints)}")

            if args.tool == "all":
                result = await tester.test_all_miners(endpoint, output_dir)
            elif args.tool == "param":
                result = await tester.test_param_miner(endpoint, output_dir)
            elif args.tool == "body":
                result = await tester.test_body_miner(endpoint, output_dir)
            elif args.tool == "response":
                result = await tester.test_response_miner(endpoint, output_dir)
            elif args.tool == "correlation":
                result = await tester.test_correlation_miner(endpoint, output_dir)

            all_results.append(result)

        # Create overall summary
        overall_summary = {
            "tool_tested": args.tool,
            "endpoints_tested": len(selected_endpoints),
            "api_info": {
                "title": api_info.get("title", "Unknown"),
                "version": api_info.get("version", "Unknown"),
                "total_endpoints": len(api_info["endpoints"]),
            },
            "results": all_results,
            "timestamp": output_dir.split("_")[-1],
        }

        summary_path = save_summary_file(
            output_dir,
            api_info,
            overall_summary,
            filename="constraint_mining_test_summary.json",
        )

        logger.info("Testing completed successfully")
        logger.add_context(
            tool_tested=args.tool,
            endpoints_tested=len(selected_endpoints),
            summary_path=summary_path,
        )

    finally:
        # Clean up
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
