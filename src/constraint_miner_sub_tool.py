"""
Testing tool for individual constraint mining sub-tools.
Allows testing each constraint miner individually for debugging and validation.
"""

import asyncio
import os
import json
import argparse
from typing import List, Dict, Any, Optional

from tools.openapi_parser import OpenAPIParserTool
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
    OpenAPIParserInput,
    SpecSourceType,
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


class ConstraintMinerTester:
    """Test individual constraint mining tools."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
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
        print("\n" + "=" * 60)
        print("TESTING REQUEST PARAMETER CONSTRAINT MINER")
        print("=" * 60)
        print_endpoint_summary(endpoint, "Testing parameter constraints for")

        try:
            # Create input
            miner_input = RequestParamConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                focus_on_validation=True,
            )

            # Execute the tool
            print("Running parameter constraint miner...")
            output = await self.tools["param"].execute(miner_input)

            # Display results
            print(f"\nParameter Constraint Mining Results:")
            print(f"  - Total constraints found: {output.total_constraints}")
            print(f"  - Source: {output.result.get('source', 'unknown')}")
            print(f"  - Status: {output.result.get('status', 'unknown')}")

            if output.param_constraints:
                print(f"\nConstraints found:")
                for i, constraint in enumerate(output.param_constraints, 1):
                    print(f"  {i}. {constraint.description}")
                    print(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
                    print(f"     Details: {constraint.details}")
            else:
                print("  No parameter constraints found")

            # Save results
            filename = f"param_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            print(f"Error testing parameter miner: {str(e)}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {"error": str(e), "tool": "param_miner"}

    async def test_body_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test request body constraint miner."""
        print("\n" + "=" * 60)
        print("TESTING REQUEST BODY CONSTRAINT MINER")
        print("=" * 60)
        print_endpoint_summary(endpoint, "Testing body constraints for")

        try:
            # Create input
            miner_input = RequestBodyConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                focus_on_schema=True,
            )

            # Execute the tool
            print("Running body constraint miner...")
            output = await self.tools["body"].execute(miner_input)

            # Display results
            print(f"\nRequest Body Constraint Mining Results:")
            print(f"  - Total constraints found: {output.total_constraints}")
            print(f"  - Source: {output.result.get('source', 'unknown')}")
            print(f"  - Status: {output.result.get('status', 'unknown')}")

            if output.body_constraints:
                print(f"\nConstraints found:")
                for i, constraint in enumerate(output.body_constraints, 1):
                    print(f"  {i}. {constraint.description}")
                    print(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
                    print(f"     Details: {constraint.details}")
            else:
                print("  No body constraints found")

            # Save results
            filename = f"body_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            print(f"Error testing body miner: {str(e)}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {"error": str(e), "tool": "body_miner"}

    async def test_response_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test response property constraint miner."""
        print("\n" + "=" * 60)
        print("TESTING RESPONSE PROPERTY CONSTRAINT MINER")
        print("=" * 60)
        print_endpoint_summary(endpoint, "Testing response constraints for")

        try:
            # Create input
            miner_input = ResponsePropertyConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=True,
                analyze_structure=True,
            )

            # Execute the tool
            print("Running response constraint miner...")
            output = await self.tools["response"].execute(miner_input)

            # Display results
            print(f"\nResponse Property Constraint Mining Results:")
            print(f"  - Total constraints found: {output.total_constraints}")
            print(f"  - Source: {output.result.get('source', 'unknown')}")
            print(f"  - Status: {output.result.get('status', 'unknown')}")

            if output.response_constraints:
                print(f"\nConstraints found:")
                for i, constraint in enumerate(output.response_constraints, 1):
                    print(f"  {i}. {constraint.description}")
                    print(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
                    print(f"     Details: {constraint.details}")
            else:
                print("  No response constraints found")

            # Save results
            filename = f"response_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            print(f"Error testing response miner: {str(e)}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {"error": str(e), "tool": "response_miner"}

    async def test_correlation_miner(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test request-response correlation constraint miner."""
        print("\n" + "=" * 60)
        print("TESTING REQUEST-RESPONSE CORRELATION CONSTRAINT MINER")
        print("=" * 60)
        print_endpoint_summary(endpoint, "Testing correlation constraints for")

        try:
            # Create input
            miner_input = RequestResponseConstraintMinerInput(
                endpoint_info=endpoint,
                include_correlations=True,
                analyze_status_codes=True,
            )

            # Execute the tool
            print("Running correlation constraint miner...")
            output = await self.tools["correlation"].execute(miner_input)

            # Display results
            print(f"\nRequest-Response Correlation Constraint Mining Results:")
            print(f"  - Total constraints found: {output.total_constraints}")
            print(f"  - Source: {output.result.get('source', 'unknown')}")
            print(f"  - Status: {output.result.get('status', 'unknown')}")

            if output.correlation_constraints:
                print(f"\nConstraints found:")
                for i, constraint in enumerate(output.correlation_constraints, 1):
                    print(f"  {i}. {constraint.description}")
                    print(
                        f"     Type: {constraint.type.value}, Severity: {constraint.severity}"
                    )
                    print(f"     Details: {constraint.details}")
            else:
                print("  No correlation constraints found")

            # Save results
            filename = f"correlation_constraints_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}.json"
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump(output.model_dump(), f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")

            return output.model_dump()

        except Exception as e:
            print(f"Error testing correlation miner: {str(e)}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return {"error": str(e), "tool": "correlation_miner"}

    async def test_all_miners(
        self, endpoint: EndpointInfo, output_dir: str
    ) -> Dict[str, Any]:
        """Test all constraint miners on the given endpoint."""
        results = {}

        print("\n" + "=" * 80)
        print(f"TESTING ALL CONSTRAINT MINERS")
        print("=" * 80)
        print_endpoint_summary(endpoint, "Running comprehensive constraint mining for")

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

        print("\n" + "=" * 80)
        print("COMPREHENSIVE TESTING SUMMARY")
        print("=" * 80)
        print(f"Endpoint: {endpoint.method.upper()} {endpoint.path}")
        print(f"Total constraints found: {total_constraints}")
        print(f"Successful tools: {successful_tools}/4")
        if failed_tools:
            print(f"Failed tools: {', '.join(failed_tools)}")
        print(f"Summary saved to: {summary_path}")

        return summary

    async def cleanup(self):
        """Clean up all tools."""
        for tool in self.tools.values():
            await tool.cleanup()


async def main():
    """Main function to run the constraint miner sub-tool tester."""
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

    # Validate input file
    if not validate_file_exists(args.spec):
        return

    # Create output directory
    output_dir = create_timestamped_output_dir("output", "constraint_mining_tests")

    # Parse OpenAPI spec
    api_info = await parse_openapi_spec(args.spec, verbose=args.verbose)

    if not api_info["endpoints"]:
        print("No endpoints found in the OpenAPI specification.")
        return

    # Select endpoints to analyze
    selected_endpoints = select_endpoints(
        api_info["endpoints"],
        "Enter endpoint numbers to test (comma-separated, or 'all'): ",
    )

    # Initialize tester
    tester = ConstraintMinerTester(verbose=args.verbose)

    try:
        # Test each selected endpoint
        all_results = []
        for endpoint in selected_endpoints:
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

        print(f"\n{'='*80}")
        print("FINAL TESTING SUMMARY")
        print(f"{'='*80}")
        print(f"Tool(s) tested: {args.tool}")
        print(f"Endpoints tested: {len(selected_endpoints)}")
        print(f"Overall summary saved to: {summary_path}")

    finally:
        # Clean up
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
