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
        # Parse the OpenAPI spec
        parser_input = OpenAPIParserInput(
            spec_source=self.spec_source,
            source_type=self.source_type,
        )
        result = await self.parser_tool.execute(parser_input)

        # Store API information
        self.api_info = {
            "title": result.title,
            "version": result.version,
            "description": result.description,
            "servers": result.servers,
        }
        self.endpoints = result.endpoints

        # Select the base server URL
        server_url = result.servers[0] if result.servers else "http://localhost"

        # Create API tools from endpoints
        factory = RestApiCallerFactory(
            server_url=server_url,
            default_headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verbose=self.verbose,
            cache_enabled=self.cache_enabled,
        )

        self.api_tools = factory.create_tools_from_endpoints(self.endpoints)
        return self.api_tools

    def get_tool_by_name(self, name: str) -> Optional[RestApiCallerTool]:
        """
        Get an API tool by its name.

        Args:
            name: Name of the API tool

        Returns:
            RestApiCallerTool if found, None otherwise
        """
        return self.api_tools.get(name)

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
        for name, tool in self.api_tools.items():
            if (
                isinstance(tool, RestApiCallerTool)
                and hasattr(tool, "endpoint")
                and tool.endpoint.path == path
                and tool.endpoint.method.upper() == method
            ):
                return tool
        return None

    def print_available_tools(self) -> None:
        """Print information about all available API tools."""
        print(f"API: {self.api_info['title']} v{self.api_info['version']}")
        print(
            f"Server: {self.api_info['servers'][0] if self.api_info['servers'] else 'Not specified'}"
        )
        print(f"Available API Tools ({len(self.api_tools)}):")

        for name, tool in sorted(self.api_tools.items()):
            if hasattr(tool, "endpoint"):
                print(
                    f"  {name}: [{tool.endpoint.method.upper()}] {tool.endpoint.path}"
                )
            else:
                print(f"  {name}")


async def demo():
    """
    Demo showcasing how to use ApiTestSuiteGenerator to create and use API testing tools.
    """
    # Create timestamped output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "api_test_suite", ts)
    os.makedirs(out_dir, exist_ok=True)

    # Example 1: Toolshop API
    print("\n=== Example 1: Toolshop API ===")
    toolshop_api = ApiTestSuiteGenerator(
        spec_source="data/toolshop/openapi.json",
        source_type=SpecSourceType.FILE,
        verbose=True,
    )

    # Initialize and get available tools
    await toolshop_api.initialize()
    toolshop_api.print_available_tools()

    # Example of getting a specific tool
    product_search_tool = toolshop_api.get_tool_by_name("get_products_search")
    if product_search_tool:
        print("\nTesting product search endpoint...")
        try:
            # Option 1: Using direct parameters (now works with our fix)
            search_params = {"q": "hammer"}
            result = await product_search_tool.execute(search_params)

            # Write the result to a file
            with open(os.path.join(out_dir, "product_search_result.json"), "w") as f:
                json.dump(result.model_dump(), f, indent=2)
            print(f"Search result saved to {out_dir}/product_search_result.json")

            # Option 2: Using properly formatted input (best practice)
            # request = RestRequest(
            #     method="GET",
            #     url=f"{toolshop_api.api_info['servers'][0]}/products/search",
            #     params={"q": "hammer"}
            # )
            # input_obj = RestApiCallerInput(request=request)
            # result = await product_search_tool.execute(input_obj)
            # print(f"Search result: {result}")

        except Exception as e:
            print(f"API call failed: {e}")

    # Save API tool info for documentation
    with open(os.path.join(out_dir, "toolshop_api_tools.json"), "w") as f:
        tool_info = {
            name: {
                "method": tool.endpoint.method,
                "path": tool.endpoint.path,
                "description": tool.description,
            }
            for name, tool in toolshop_api.api_tools.items()
        }
        json.dump(tool_info, f, indent=2)

    print(f"\nAPI tool information saved to {out_dir}")


if __name__ == "__main__":
    asyncio.run(demo())
