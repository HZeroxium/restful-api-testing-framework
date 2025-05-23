# tools/openapi_parser.py

import os
import json
import yaml
import re
from typing import Any, Dict, List, Optional
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import (
    OpenAPIToolset,
    RestApiTool,
)

from src.core import BaseTool
from src.schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    OpenAPIParserOutput,
    EndpointInfo,
    SpecSourceType,
)
from src.utils.schema_utils import clean_schema_dict


class OpenAPIParserTool(BaseTool):
    """A tool that parses OpenAPI specifications."""

    def __init__(
        self,
        name: str = "openapi_parser",
        description: str = "Parses OpenAPI specifications and extracts API information",
        config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        cache_enabled: bool = True,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=OpenAPIParserInput,
            output_schema=OpenAPIParserOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(self, input_data: OpenAPIParserInput) -> OpenAPIParserOutput:
        """Execute the OpenAPI parser tool."""
        spec_content = await self._load_spec(
            input_data.spec_source, input_data.source_type
        )

        # Parse the specification
        toolset = OpenAPIToolset(
            spec_str=spec_content,
            spec_str_type=(
                input_data.source_type.value
                if input_data.source_type != SpecSourceType.FILE
                else "yaml"
            ),
        )

        # Get the API tools
        api_tools: List[RestApiTool] = toolset.get_tools()

        # Extract API metadata
        api_info = self._extract_api_info(spec_content, input_data.source_type)

        # Process endpoints
        endpoints = []
        for tool in api_tools:
            # Apply filtering if specified
            # Add hasattr check for tags to avoid attribute errors
            if (
                input_data.filter_tags
                and hasattr(tool, "tags")
                and not any(tag in tool.tags for tag in input_data.filter_tags)
            ):
                continue

            # if input_data.filter_paths and not self._matches_path_filter(
            #     tool.path, input_data.filter_paths
            # ):
            #     continue

            endpoint_info = self._extract_endpoint_info(tool)
            endpoints.append(endpoint_info)

        # When creating the output, include a result field that contains the most important data
        parsed_spec_data = {
            "title": api_info.get("title", "Unknown API"),
            "version": api_info.get("version", "Unknown"),
            "description": api_info.get("description"),
            # "endpoints": [endpoint.model_dump() for endpoint in endpoints],
            # "endpoint_count": len(endpoints),
        }

        return OpenAPIParserOutput(
            title=api_info.get("title", "Unknown API"),
            version=api_info.get("version", "Unknown"),
            description=api_info.get("description"),
            endpoints=endpoints,
            # Fix the field name to match the schema definition
            servers=api_info.get("servers", []),
            endpoint_count=len(endpoints),
            result=parsed_spec_data,  # Ensure result field is set
        )

    async def _load_spec(self, source: str, source_type: SpecSourceType) -> str:
        """Load the OpenAPI specification from various sources."""
        if source_type == SpecSourceType.FILE:
            # Load from file
            if not os.path.exists(source):
                raise FileNotFoundError(f"Specification file not found: {source}")

            with open(source, "r") as f:
                return f.read()

        elif source_type in (SpecSourceType.YAML_STRING, SpecSourceType.JSON_STRING):
            # Direct string content
            return source

        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _extract_api_info(
        self, spec_content: str, source_type: SpecSourceType
    ) -> Dict[str, Any]:
        """Extract basic API information from the specification."""
        if source_type == SpecSourceType.JSON:
            spec_dict = json.loads(spec_content)
        else:  # YAML_STRING or loaded from file/URL
            spec_dict = yaml.safe_load(spec_content)

        info = spec_dict.get("info", {})
        servers = [server.get("url") for server in spec_dict.get("servers", [])]

        return {
            "title": info.get("title", "Unknown API"),
            "version": info.get("version", "Unknown"),
            "description": info.get("description"),
            "servers": servers,
        }

    def _extract_endpoint_info(self, tool: RestApiTool) -> EndpointInfo:
        """Extract information about an API endpoint from a RestApiTool."""
        # Get input schema
        try:
            input_schema = {}
            # Try to get function declaration parameters
            func_decl = tool._get_declaration()
            if func_decl and hasattr(func_decl.parameters, "model_dump"):
                input_schema = func_decl.parameters.model_dump()
            else:
                # Fallback to operation parser
                input_schema = tool._operation_parser.get_json_schema().get(
                    "parameters", {}
                )
            # Clean the input schema to remove null values
            input_schema = clean_schema_dict(input_schema)
        except Exception as e:
            self.logger.warning(f"Error extracting input schema: {e}")
            input_schema = {"error": str(e)}

        # Get output schema
        try:
            output_schema = tool._operation_parser.get_json_schema().get(
                "responses", {}
            )
            # Clean the output schema to remove null values
            output_schema = clean_schema_dict(output_schema)
        except Exception as e:
            self.logger.warning(f"Error extracting output schema: {e}")
            output_schema = {"error": str(e)}

        # Parse the method from the endpoint string
        endpoint_str = str(tool.endpoint)
        method = "GET"  # Default method
        path = ""  # Default path

        # Extract method using regex
        import re

        method_match = re.search(r"method='([^']*)'", endpoint_str)
        if method_match:
            method = method_match.group(1).upper()

        # Extract path using regex
        path_match = re.search(r"path='([^']*)'", endpoint_str)
        if path_match:
            path = path_match.group(1)

        # Determine auth requirements safely
        auth_required = False
        if hasattr(tool, "auth_scheme") and tool.auth_scheme is not None:
            auth_required = True

        # Extract other information
        return EndpointInfo(
            name=tool.name,
            description=tool.description or "",
            method=method,
            path=path,
            input_schema=input_schema,
            output_schema=output_schema,
            auth_required=auth_required,
            tags=tool.tags if hasattr(tool, "tags") else [],
        )

    def _matches_path_filter(self, path: str, path_filters: List[str]) -> bool:
        """Check if an endpoint path matches any of the filter patterns."""
        for pattern in path_filters:
            # Convert API path pattern to regex
            # Replace {param} with .*
            regex_pattern = re.sub(r"\{[^}]+\}", ".*", pattern)
            # Make sure we're matching the entire path
            if not regex_pattern.startswith("^"):
                regex_pattern = "^" + regex_pattern
            if not regex_pattern.endswith("$"):
                regex_pattern = regex_pattern + "$"

            if re.match(regex_pattern, path):
                return True

        return False
