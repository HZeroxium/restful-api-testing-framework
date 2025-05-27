# tools/openapi_parser.py

import os
import json
import yaml
import re
import logging
from typing import Any, Dict, List, Optional
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import (
    OpenAPIToolset,
    RestApiTool,
)

from core import BaseTool
from schemas.tools.openapi_parser import (
    OpenAPIParserInput,
    OpenAPIParserOutput,
    EndpointInfo,
    SpecSourceType,
    AuthType,
)
from utils.schema_utils import (
    clean_schema_dict,
    extract_response_object,
    create_normalized_schema,
    ResponseSchema,
)


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
        self.logger = logging.getLogger(self.__class__.__name__)

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
            if self._should_filter_endpoint(tool, input_data):
                continue

            endpoint_info = self._extract_endpoint_info(tool)
            endpoints.append(endpoint_info)

        # When creating the output, include a result field that contains the most important data
        parsed_spec_data = {
            "title": api_info.get("title", "Unknown API"),
            "version": api_info.get("version", "Unknown"),
            "description": api_info.get("description"),
        }

        return OpenAPIParserOutput(
            title=api_info.get("title", "Unknown API"),
            version=api_info.get("version", "Unknown"),
            description=api_info.get("description"),
            endpoints=endpoints,
            servers=api_info.get("servers", []),
            endpoint_count=len(endpoints),
            result=parsed_spec_data,
        )

    def _should_filter_endpoint(
        self, tool: RestApiTool, input_data: OpenAPIParserInput
    ) -> bool:
        """Determine if an endpoint should be filtered out based on input criteria.

        Args:
            tool: The RestApiTool representing an endpoint
            input_data: The input data containing filter criteria

        Returns:
            True if the endpoint should be filtered out, False otherwise
        """
        # Filter by tags if specified
        if (
            input_data.filter_tags
            and hasattr(tool, "tags")
            and not any(tag in tool.tags for tag in input_data.filter_tags)
        ):
            return True

        # Filter by paths if specified
        if (
            input_data.filter_paths
            and hasattr(tool, "path")
            and not self._matches_path_filter(tool.path, input_data.filter_paths)
        ):
            return True

        # Filter by methods if specified
        if (
            input_data.filter_methods
            and hasattr(tool, "method")
            and tool.method.upper()
            not in [m.upper() for m in input_data.filter_methods]
        ):
            return True

        return False

    async def _load_spec(self, source: str, source_type: SpecSourceType) -> str:
        """Load the OpenAPI specification from various sources."""
        if source_type == SpecSourceType.FILE:
            # Load from file
            if not os.path.exists(source):
                raise FileNotFoundError(f"Specification file not found: {source}")

            with open(source, "r") as f:
                return f.read()

        elif source_type == SpecSourceType.URL:
            # For URL sources, you would need to implement HTTP fetching
            # This is a placeholder for that functionality
            raise NotImplementedError("URL source type is not yet implemented")

        elif source_type in (SpecSourceType.YAML, SpecSourceType.JSON):
            # Direct string content
            return source

        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _extract_api_info(
        self, spec_content: str, source_type: SpecSourceType
    ) -> Dict[str, Any]:
        """Extract basic API information from the specification."""
        try:
            if source_type == SpecSourceType.JSON:
                spec_dict = json.loads(spec_content)
            else:  # YAML or loaded from file
                spec_dict = yaml.safe_load(spec_content)

            info = spec_dict.get("info", {})
            servers = [server.get("url") for server in spec_dict.get("servers", [])]

            return {
                "title": info.get("title", "Unknown API"),
                "version": info.get("version", "Unknown"),
                "description": info.get("description"),
                "servers": servers,
            }
        except Exception as e:
            self.logger.error(f"Error extracting API info: {e}")
            return {
                "title": "Unknown API",
                "version": "Unknown",
                "description": "Error extracting API information",
                "servers": [],
            }

    def _extract_endpoint_info(self, tool: RestApiTool) -> EndpointInfo:
        """Extract information about an API endpoint from a RestApiTool."""
        # Parse the endpoint attributes
        endpoint_attrs = self._parse_endpoint_attributes(tool)

        # Get input schema with better error handling
        input_schema = self._extract_input_schema(tool)

        # Get output schema with enhanced extraction
        output_schema = self._extract_output_schema(tool)

        # Create the endpoint info with all extracted data
        return EndpointInfo(
            name=tool.name,
            description=tool.description or "",
            method=endpoint_attrs["method"],
            path=endpoint_attrs["path"],
            input_schema=input_schema,
            output_schema=output_schema,
            auth_required=endpoint_attrs["auth_required"],
            auth_type=endpoint_attrs["auth_type"],
            tags=endpoint_attrs["tags"],
        )

    def _parse_endpoint_attributes(self, tool: RestApiTool) -> Dict[str, Any]:
        """Parse various attributes from the endpoint tool.

        Args:
            tool: The RestApiTool to parse

        Returns:
            Dictionary of extracted attributes
        """
        # Default values
        attrs = {
            "method": "GET",
            "path": "",
            "auth_required": False,
            "auth_type": None,
            "tags": [],
        }

        # Extract method and path from endpoint string
        endpoint_str = str(tool.endpoint)

        # Extract method using regex
        method_match = re.search(r"method='([^']*)'", endpoint_str)
        if method_match:
            attrs["method"] = method_match.group(1).upper()

        # Extract path using regex
        path_match = re.search(r"path='([^']*)'", endpoint_str)
        if path_match:
            attrs["path"] = path_match.group(1)

        # Determine auth requirements
        if hasattr(tool, "auth_scheme") and tool.auth_scheme is not None:
            attrs["auth_required"] = True
            # Try to determine auth type
            if hasattr(tool.auth_scheme, "scheme"):
                scheme = tool.auth_scheme.scheme.lower()
                if scheme == "bearer":
                    attrs["auth_type"] = AuthType.BEARER
                elif scheme == "basic":
                    attrs["auth_type"] = AuthType.BASIC
            elif hasattr(tool.auth_scheme, "type_"):
                auth_type = str(tool.auth_scheme.type_).lower()
                if "apikey" in auth_type:
                    attrs["auth_type"] = AuthType.API_KEY
                elif "oauth2" in auth_type:
                    attrs["auth_type"] = AuthType.OAUTH2

        # Extract tags
        if hasattr(tool, "tags"):
            attrs["tags"] = tool.tags

        return attrs

    def _extract_input_schema(self, tool: RestApiTool) -> Dict[str, Any]:
        """Extract input schema from a RestApiTool with better error handling.

        Args:
            tool: The RestApiTool to extract input schema from

        Returns:
            Dictionary representation of the input schema
        """
        try:
            input_schema: Dict[str, Any] = {}

            # Try multiple approaches to get the input schema
            if hasattr(tool, "_get_declaration") and callable(
                getattr(tool, "_get_declaration")
            ):
                func_decl = tool._get_declaration()
                if func_decl and hasattr(func_decl.parameters, "model_dump"):
                    input_schema = func_decl.parameters.model_dump()
                elif func_decl and hasattr(func_decl.parameters, "dict"):
                    input_schema = func_decl.parameters.dict()

            # Fall back to operation parser if needed
            if not input_schema and hasattr(tool, "_operation_parser"):
                schema = tool._operation_parser.get_json_schema()
                if "parameters" in schema:
                    input_schema["properties"] = {}
                    required_params = []

                    for param in schema["parameters"]:
                        name = param.get("name", "")
                        if not name:
                            continue

                        # Convert name to snake_case for consistency
                        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

                        param_schema = param.get("schema", {})
                        prop_info = {"type": param_schema.get("type", "STRING").upper()}

                        if "description" in param:
                            prop_info["description"] = param["description"]

                        if "required" in param and param["required"]:
                            required_params.append(name)

                        input_schema["properties"][name] = prop_info

                    if required_params:
                        input_schema["required"] = required_params

                # Handle request body if present
                if "requestBody" in schema and "content" in schema["requestBody"]:
                    for content_type, content in schema["requestBody"][
                        "content"
                    ].items():
                        if "schema" in content:
                            body_schema = content["schema"]
                            if "properties" in body_schema:
                                for prop_name, prop_schema in body_schema[
                                    "properties"
                                ].items():
                                    name = re.sub(
                                        r"(?<!^)(?=[A-Z])", "_", prop_name
                                    ).lower()
                                    prop_info = {
                                        "type": prop_schema.get(
                                            "type", "STRING"
                                        ).upper()
                                    }
                                    if "description" in prop_schema:
                                        prop_info["description"] = prop_schema[
                                            "description"
                                        ]

                                    if "properties" not in input_schema:
                                        input_schema["properties"] = {}

                                    input_schema["properties"][name] = prop_info

                            # Add required fields from request body
                            if "required" in body_schema:
                                if "required" not in input_schema:
                                    input_schema["required"] = []
                                for req in body_schema["required"]:
                                    name = re.sub(r"(?<!^)(?=[A-Z])", "_", req).lower()
                                    if name not in input_schema["required"]:
                                        input_schema["required"].append(name)

            # Set some defaults if schema is still empty
            if not input_schema:
                input_schema = {"properties": {}, "required": [], "type": "OBJECT"}

            # Ensure type field is present
            if "type" not in input_schema:
                input_schema["type"] = "OBJECT"

            # Clean the schema
            return clean_schema_dict(input_schema)

        except Exception as e:
            self.logger.warning(f"Error extracting input schema: {e}")
            return {"properties": {}, "required": [], "type": "OBJECT", "error": str(e)}

    def _extract_output_schema(self, tool: RestApiTool) -> Dict[str, Any]:
        """Extract detailed output schema from a RestApiTool.

        Args:
            tool: The RestApiTool to extract output schema from

        Returns:
            Dictionary mapping status codes to response schemas
        """
        try:
            output_schema: Dict[str, Any] = {}

            # Try to get the operation object directly
            operation = None
            if hasattr(tool, "_operation"):
                operation = tool._operation
            elif hasattr(tool, "_operation_parser") and hasattr(
                tool._operation_parser, "operation"
            ):
                operation = tool._operation_parser.operation

            # Extract responses from operation object
            if operation and hasattr(operation, "responses"):
                for status_code, response in operation.responses.items():
                    response_schema = extract_response_object(response)
                    if response_schema:
                        output_schema[status_code] = response_schema

            # Fall back to JSON schema if needed
            if not output_schema and hasattr(tool, "_operation_parser"):
                operation_schema = tool._operation_parser.get_json_schema()
                if "responses" in operation_schema:
                    for status_code, response_data in operation_schema[
                        "responses"
                    ].items():
                        response_info: ResponseSchema = {
                            "description": response_data.get("description", "")
                        }

                        if "content" in response_data:
                            content_schemas = {}
                            for content_type, content_data in response_data[
                                "content"
                            ].items():
                                if "schema" in content_data:
                                    # Normalize the schema structure
                                    schema = create_normalized_schema(
                                        content_data["schema"]
                                    )
                                    content_schemas[content_type] = {"schema": schema}

                            if content_schemas:
                                response_info["content"] = content_schemas

                        output_schema[status_code] = response_info

            # If still empty, try a different approach using raw JSON
            if not output_schema:
                raw_schema = {}
                try:
                    # Try to get a JSON representation of the operation
                    if hasattr(tool, "_operation_parser") and hasattr(
                        tool._operation_parser, "get_json_schema"
                    ):
                        raw_schema = tool._operation_parser.get_json_schema()

                    if "responses" in raw_schema:
                        for status_code, response_data in raw_schema[
                            "responses"
                        ].items():
                            output_schema[status_code] = {
                                "description": response_data.get("description", "")
                            }

                            # Try to extract content schemas
                            if "content" in response_data:
                                output_schema[status_code]["content"] = {}
                except Exception as nested_e:
                    self.logger.warning(
                        f"Error in fallback schema extraction: {nested_e}"
                    )

            # Clean the schema
            return clean_schema_dict(output_schema)

        except Exception as e:
            self.logger.warning(f"Error extracting output schema: {e}")
            return {"error": str(e)}

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
