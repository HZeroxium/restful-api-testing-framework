# src/spec_to_rest_tools.py

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Optional

from tools import OpenAPIParserTool, RestApiCallerTool
from utils.rest_api_caller_factory import RestApiCallerFactory
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    SpecSourceType,
)
from common.logger import LoggerFactory, LoggerType, LogLevel


class ApiTestSuiteGenerator:
    """
    Generates a suite of API testing tools from OpenAPI specifications.
    This class bridges the OpenAPIParserTool with RestApiCallerTool to create
    a complete API testing environment.
    """

    def __init__(
        self,
        spec_source: str,
        source_type: SpecSourceType = SpecSourceType.FILE,
        verbose: bool = False,
        cache_enabled: bool = False,
        timeout: float = 10.0,
    ):
        """
        Initialize with an OpenAPI specification source.

        Args:
            spec_source: Path/URL to OpenAPI spec file or JSON/YAML content
            source_type: Type of specification source
            verbose: Enable verbose logging
            cache_enabled: Enable response caching
            timeout: Request timeout in seconds
        """
        self.spec_source = spec_source
        self.source_type = source_type
        self.verbose = verbose
        self.cache_enabled = cache_enabled
        self.timeout = timeout

        # Initialize logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="api-test-suite-generator",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize parser tool
        self.parser_tool = OpenAPIParserTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # These will be populated after parsing
        self.api_info = None
        self.endpoints = None
        self.api_tools = {}

    async def initialize(self) -> Dict[str, RestApiCallerTool]:
        """
        Parse the OpenAPI specification and create API testing tools.

        Returns:
            Dictionary of API tools mapped by name
        """
        self.logger.info("Initializing API test suite generator")
        self.logger.add_context(
            spec_source=(
                self.spec_source[:100]
                if len(self.spec_source) > 100
                else self.spec_source
            ),
            source_type=self.source_type.value,
            timeout=self.timeout,
        )

        # Parse the OpenAPI spec
        parser_input = OpenAPIParserInput(
            spec_source=self.spec_source,
            source_type=self.source_type,
        )

        self.logger.debug("Parsing OpenAPI specification")
        result = await self.parser_tool.execute(parser_input)

        # Store API information
        self.api_info = {
            "title": result.title,
            "version": result.version,
            "description": result.description,
            "servers": result.servers,
        }
        self.endpoints = result.endpoints

        self.logger.info(f"Parsed API: {result.title} v{result.version}")
        self.logger.add_context(
            api_title=result.title,
            api_version=result.version,
            endpoints_count=len(result.endpoints),
        )

        # Select the base server URL
        server_url = result.servers[0] if result.servers else "http://localhost"
        self.logger.debug(f"Using server URL: {server_url}")

        # Create API tools from endpoints
        factory = RestApiCallerFactory(
            server_url=server_url,
            default_headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verbose=self.verbose,
            cache_enabled=self.cache_enabled,
        )

        self.api_tools = factory.create_tools_from_endpoints(self.endpoints)

        self.logger.info(f"Created {len(self.api_tools)} API tools")
        return self.api_tools

    def get_tool_by_name(self, name: str) -> Optional[RestApiCallerTool]:
        """
        Get an API tool by its name.

        Args:
            name: Name of the API tool

        Returns:
            RestApiCallerTool if found, None otherwise
        """
        tool = self.api_tools.get(name)
        if tool:
            self.logger.debug(f"Found tool: {name}")
        else:
            self.logger.warning(f"Tool not found: {name}")
        return tool

    def get_tool_by_path_method(
        self, path: str, method: str
    ) -> Optional[RestApiCallerTool]:
        """
        Find an API tool by its path and HTTP method.

        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, etc.)

        Returns:
            RestApiCallerTool if found, None otherwise
        """
        method = method.upper()
        self.logger.debug(f"Searching for tool: {method} {path}")

        for name, tool in self.api_tools.items():
            if (
                isinstance(tool, RestApiCallerTool)
                and hasattr(tool, "endpoint")
                and tool.endpoint.path == path
                and tool.endpoint.method.upper() == method
            ):
                self.logger.debug(f"Found matching tool: {name}")
                return tool

        self.logger.warning(f"No tool found for: {method} {path}")
        return None

    def print_available_tools(self) -> None:
        """Print information about all available API tools."""
        self.logger.info("Available API Tools Summary:")
        self.logger.add_context(
            api_title=self.api_info["title"],
            api_version=self.api_info["version"],
            server_url=(
                self.api_info["servers"][0]
                if self.api_info["servers"]
                else "Not specified"
            ),
            tools_count=len(self.api_tools),
        )

        # Log via the logger system instead of print
        print(f"API: {self.api_info['title']} v{self.api_info['version']}")
        print(
            f"Server: {self.api_info['servers'][0] if self.api_info['servers'] else 'Not specified'}"
        )
        print(f"Available API Tools ({len(self.api_tools)}):")

        for name, tool in sorted(self.api_tools.items()):
            if hasattr(tool, "endpoint"):
                endpoint_info = f"[{tool.endpoint.method.upper()}] {tool.endpoint.path}"
                print(f"  {name}: {endpoint_info}")
                self.logger.debug(f"Tool: {name} -> {endpoint_info}")
            else:
                print(f"  {name}")
                self.logger.debug(f"Tool: {name} (no endpoint info)")


async def demo():
    """
    Demo showcasing how to use ApiTestSuiteGenerator to create and use API testing tools.
    """
    # Initialize main logger
    logger = LoggerFactory.get_logger(
        name="spec-to-rest-tools-demo",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.INFO,
    )

    # Create timestamped output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "api_test_suite", ts)
    os.makedirs(out_dir, exist_ok=True)

    logger.info("Starting Spec to REST Tools demo")
    logger.add_context(output_directory=out_dir, timestamp=ts)

    # Example 1: Toolshop API
    logger.info("=== Example 1: Toolshop API ===")
    toolshop_api = ApiTestSuiteGenerator(
        spec_source="data/toolshop/openapi.json",
        source_type=SpecSourceType.FILE,
        verbose=True,
    )

    try:
        # Initialize and get available tools
        await toolshop_api.initialize()
        toolshop_api.print_available_tools()

        # Example of getting a specific tool
        product_search_tool = toolshop_api.get_tool_by_name("get_products_search")
        if product_search_tool:
            logger.info("Testing product search endpoint...")
            logger.add_context(tool_name="get_products_search")

            try:
                # Option 1: Using direct parameters (now works with our fix)
                search_params = {"q": "hammer"}
                result = await product_search_tool.execute(search_params)

                # Write the result to a file
                result_file = os.path.join(out_dir, "product_search_result.json")
                with open(result_file, "w") as f:
                    json.dump(result.model_dump(), f, indent=2)

                logger.info(f"Search result saved to {result_file}")
                logger.add_context(
                    search_query="hammer",
                    status_code=result.response.status_code,
                    response_time=f"{result.elapsed:.3f}s",
                    result_file=result_file,
                )

            except Exception as e:
                logger.error(f"API call failed: {str(e)}")
                logger.add_context(error=str(e))
        else:
            logger.warning("Product search tool not found")

        # Save API tool info for documentation
        tools_info_file = os.path.join(out_dir, "toolshop_api_tools.json")
        with open(tools_info_file, "w") as f:
            tool_info = {
                name: {
                    "method": tool.endpoint.method,
                    "path": tool.endpoint.path,
                    "description": tool.description,
                }
                for name, tool in toolshop_api.api_tools.items()
                if hasattr(tool, "endpoint")
            }
            json.dump(tool_info, f, indent=2)

        logger.info(f"API tool information saved to {tools_info_file}")

    except Exception as e:
        logger.error(f"Error during demo execution: {str(e)}")
        if logger.verbose:
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")

    logger.info("Demo completed successfully")
    logger.add_context(output_saved_to=out_dir)

    # Final output message
    print(f"\nAPI tool information saved to {out_dir}")


if __name__ == "__main__":
    asyncio.run(demo())
