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
from common.logger import LoggerFactory, LoggerType, LogLevel
from tools.openapi_parser_tools.openapi_parser_helper import (
    OpenAPISpecNormalizer,
    OpenAPICompatibilityChecker,
    OpenAPISpecSchemaFixer,
)
from tools.openapi_parser_tools.complex_schema_handler import ComplexSchemaHandler


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

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize helper classes
        self.normalizer = OpenAPISpecNormalizer(verbose=verbose)
        self.compatibility_checker = OpenAPICompatibilityChecker(verbose=verbose)
        self.schema_fixer = OpenAPISpecSchemaFixer(verbose=verbose)
        self.complex_handler = ComplexSchemaHandler(verbose=verbose)

    async def _execute(self, input_data: OpenAPIParserInput) -> OpenAPIParserOutput:
        """Execute the OpenAPI parser tool."""
        self.logger.info(f"Starting OpenAPI specification parsing")
        self.logger.add_context(
            source_type=input_data.source_type.value,
            spec_source=(
                input_data.spec_source
                if len(input_data.spec_source) < 100
                else "large_spec"
            ),
        )

        try:
            spec_content = await self._load_spec(
                input_data.spec_source, input_data.source_type
            )
            self.logger.debug(
                f"Loaded specification content ({len(spec_content)} characters)"
            )

            # Determine spec format
            spec_format = self._determine_spec_format(
                spec_content, input_data.source_type
            )

            # Apply comprehensive specification fixes with enhanced error handling
            fixed_spec_content = await self._fix_specification_with_fallbacks(
                spec_content, spec_format, input_data.spec_source
            )

            # Parse the specification with the fixed content
            toolset = await self._create_toolset_safely(fixed_spec_content, spec_format)

            # Get the API tools
            api_tools: List[RestApiTool] = toolset.get_tools()
            self.logger.debug(
                f"Extracted {len(api_tools)} API tools from specification"
            )

            # Extract API metadata
            api_info = self._extract_api_info(
                fixed_spec_content, input_data.source_type
            )
            self.logger.debug(
                f"Extracted API info: {api_info.get('title', 'Unknown')} v{api_info.get('version', 'Unknown')}"
            )

            # Process endpoints
            endpoints = []
            filtered_count = 0
            for tool in api_tools:
                # Apply filtering if specified
                if self._should_filter_endpoint(tool, input_data):
                    filtered_count += 1
                    continue

                endpoint_info = self._extract_endpoint_info(tool)
                endpoints.append(endpoint_info)

            if filtered_count > 0:
                self.logger.debug(
                    f"Filtered out {filtered_count} endpoints based on criteria"
                )

            self.logger.info(
                f"Successfully parsed OpenAPI spec: {len(endpoints)} endpoints extracted"
            )

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
        except Exception as e:
            self.logger.error(f"Error parsing OpenAPI specification: {str(e)}")
            raise

    async def _fix_specification_with_fallbacks(
        self, spec_content: str, spec_format: str, spec_source: str
    ) -> str:
        """Apply comprehensive fixes with multiple fallback strategies.

        Args:
            spec_content: Raw specification content
            spec_format: Format of the specification
            spec_source: Source identifier for context

        Returns:
            Fixed specification content
        """
        try:
            # Parse the specification first
            if spec_format.lower() == "json":
                spec_dict = json.loads(spec_content)
            else:
                spec_dict = yaml.safe_load(spec_content)

            self.logger.debug(
                f"Applying comprehensive fixes to spec: {spec_dict.get('info', {}).get('title', 'Unknown')}"
            )

            # Strategy 1: Apply basic schema fixes
            fixed_spec_dict = self.schema_fixer.fix_schema_description_errors(spec_dict)

            # Strategy 2: Apply complex schema handling based on spec characteristics
            if self._requires_complex_handling(fixed_spec_dict, spec_source):
                self.logger.debug("Applying complex schema handling")
                fixed_spec_dict = await self._apply_complex_fixes(
                    fixed_spec_dict, spec_source
                )

            # Strategy 3: Apply normalization fixes
            normalized_spec_dict = self.normalizer._apply_normalizations(
                fixed_spec_dict
            )

            # Convert back to JSON for consistent toolset creation
            return json.dumps(normalized_spec_dict, indent=2)

        except Exception as e:
            self.logger.warning(f"Comprehensive spec fixes failed: {e}")
            # Fallback: try minimal fixes
            return await self._apply_minimal_fixes(spec_content, spec_format)

    def _requires_complex_handling(
        self, spec_dict: Dict[str, Any], spec_source: str
    ) -> bool:
        """Determine if the specification requires complex handling.

        Args:
            spec_dict: Parsed specification dictionary
            spec_source: Source identifier

        Returns:
            True if complex handling is required
        """
        # Check for Swagger 2.0
        if "swagger" in spec_dict:
            return True

        # Check for GitLab-specific patterns
        if "gitlab" in spec_source.lower() or "branch" in spec_source.lower():
            return True

        # Check for complex array definitions without items
        definitions = spec_dict.get("definitions", {})
        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                if def_schema.get("type") == "array" and "items" not in def_schema:
                    return True

        # Check for missing response descriptions
        paths = spec_dict.get("paths", {})
        for path_item in paths.values():
            if isinstance(path_item, dict):
                for operation in path_item.values():
                    if isinstance(operation, dict) and "responses" in operation:
                        responses = operation["responses"]
                        for response in responses.values():
                            if (
                                isinstance(response, dict)
                                and "description" not in response
                            ):
                                return True

        return False

    async def _apply_complex_fixes(
        self, spec_dict: Dict[str, Any], spec_source: str
    ) -> Dict[str, Any]:
        """Apply complex fixes based on the specification characteristics.

        Args:
            spec_dict: Specification dictionary
            spec_source: Source identifier

        Returns:
            Fixed specification dictionary
        """
        fixed_spec = spec_dict

        # Apply Swagger 2.0 specific fixes
        if self.complex_handler._is_swagger_2(fixed_spec):
            fixed_spec = self.complex_handler.handle_swagger_2_complex_issues(
                fixed_spec
            )

        # Apply GitLab-specific fixes
        if "gitlab" in spec_source.lower() or "branch" in spec_source.lower():
            fixed_spec = self.complex_handler.fix_gitlab_branch_specific_issues(
                fixed_spec
            )

        return fixed_spec

    async def _apply_minimal_fixes(self, spec_content: str, spec_format: str) -> str:
        """Apply minimal fixes as a last resort.

        Args:
            spec_content: Raw specification content
            spec_format: Format of the specification

        Returns:
            Minimally fixed specification content
        """
        try:
            if spec_format.lower() == "json":
                spec_dict = json.loads(spec_content)
            else:
                spec_dict = yaml.safe_load(spec_content)

            # Apply only the most critical fixes
            self._apply_critical_fixes(spec_dict)

            return json.dumps(spec_dict, indent=2)

        except Exception as e:
            self.logger.warning(f"Minimal fixes failed: {e}")
            # Return original content as absolute fallback
            if spec_format.lower() == "json":
                return spec_content
            else:
                # Convert YAML to JSON
                try:
                    spec_dict = yaml.safe_load(spec_content)
                    return json.dumps(spec_dict, indent=2)
                except:
                    return spec_content

    def _apply_critical_fixes(self, spec_dict: Dict[str, Any]) -> None:
        """Apply only the most critical fixes for toolset compatibility.

        Args:
            spec_dict: Specification dictionary to fix in-place
        """
        # Ensure info section exists
        if "info" not in spec_dict:
            spec_dict["info"] = {"title": "API", "version": "1.0.0"}

        # Ensure paths section exists
        if "paths" not in spec_dict:
            spec_dict["paths"] = {}

        # Fix all schema objects to have descriptions
        def add_descriptions_recursively(obj):
            if isinstance(obj, dict):
                # Add description to schema objects
                if (
                    "type" in obj or "properties" in obj or "$ref" in obj
                ) and "description" not in obj:
                    obj["description"] = ""

                for value in obj.values():
                    add_descriptions_recursively(value)
            elif isinstance(obj, list):
                for item in obj:
                    add_descriptions_recursively(item)

        add_descriptions_recursively(spec_dict)

    def _determine_spec_format(
        self, spec_content: str, source_type: SpecSourceType
    ) -> str:
        """Determine the format of the OpenAPI specification.

        Args:
            spec_content: Raw specification content
            source_type: Source type of the specification

        Returns:
            Format string ('json' or 'yaml')
        """
        if source_type == SpecSourceType.JSON:
            return "json"
        elif source_type == SpecSourceType.YAML:
            return "yaml"
        elif source_type == SpecSourceType.FILE:
            # Try to determine from content
            spec_content_stripped = spec_content.strip()
            if spec_content_stripped.startswith("{"):
                return "json"
            else:
                return "yaml"
        else:
            # Default fallback - try to parse as JSON first
            try:
                json.loads(spec_content)
                return "json"
            except json.JSONDecodeError:
                return "yaml"

    async def _create_toolset_safely(
        self, spec_content: str, spec_format: str
    ) -> OpenAPIToolset:
        """Create OpenAPIToolset with enhanced error handling and multiple fallback strategies.

        Args:
            spec_content: Fixed specification content
            spec_format: Format of the specification

        Returns:
            OpenAPIToolset instance

        Raises:
            Exception: If all attempts to create the toolset fail
        """
        # Attempt 1: Try with fixed content
        try:
            toolset = OpenAPIToolset(
                spec_str=spec_content,
                spec_str_type="json",  # Always use JSON after fixing
            )
            self.logger.debug("Successfully created toolset with fixed specification")
            return toolset
        except Exception as primary_error:
            self.logger.warning(f"Primary toolset creation failed: {primary_error}")

            # Attempt 2: Try with additional schema repairs
            try:
                repaired_spec_content = await self._repair_specification_for_toolset(
                    spec_content
                )
                toolset = OpenAPIToolset(
                    spec_str=repaired_spec_content,
                    spec_str_type="json",
                )
                self.logger.debug(
                    "Successfully created toolset with repaired specification"
                )
                return toolset
            except Exception as secondary_error:
                self.logger.warning(
                    f"Secondary toolset creation failed: {secondary_error}"
                )

                # Attempt 3: Try with manual schema fixing
                try:
                    return await self._create_toolset_with_manual_fixes(
                        spec_content, "json"
                    )
                except Exception as tertiary_error:
                    self.logger.warning(f"Manual fixes failed: {tertiary_error}")

                    # Attempt 4: Try with aggressive schema simplification
                    try:
                        return await self._create_toolset_with_aggressive_fixes(
                            spec_content
                        )
                    except Exception as quaternary_error:
                        self.logger.error(
                            f"All toolset creation attempts failed. Last error: {quaternary_error}"
                        )
                        raise Exception(
                            f"Unable to create OpenAPI toolset after multiple attempts: {primary_error}"
                        )

    async def _repair_specification_for_toolset(self, spec_content: str) -> str:
        """Apply additional repairs specifically for toolset creation.

        Args:
            spec_content: Specification content to repair

        Returns:
            Repaired specification content
        """
        try:
            spec_dict = json.loads(spec_content)

            # Apply toolset-specific repairs
            repaired_spec = self.schema_fixer.fix_toolset_specific_errors(spec_dict)

            # Apply complex handler repairs
            if self._requires_complex_handling(repaired_spec, ""):
                repaired_spec = self.complex_handler.handle_swagger_2_complex_issues(
                    repaired_spec
                )

            return json.dumps(repaired_spec, indent=2)

        except Exception as e:
            self.logger.warning(f"Specification repair failed: {e}")
            return spec_content

    async def _create_toolset_with_manual_fixes(
        self, spec_content: str, spec_format: str
    ) -> OpenAPIToolset:
        """Create toolset with manual schema fixes as a fallback.

        Args:
            spec_content: Specification content
            spec_format: Format of the specification

        Returns:
            OpenAPIToolset instance
        """
        self.logger.debug("Attempting manual schema fixes")

        # Parse the specification
        if spec_format == "json":
            spec_dict = json.loads(spec_content)
        else:
            spec_dict = yaml.safe_load(spec_content)

        # Apply manual fixes for known issues
        self._apply_manual_schema_fixes(spec_dict)

        # Convert to JSON and create toolset
        fixed_spec_content = json.dumps(spec_dict, indent=2)

        toolset = OpenAPIToolset(
            spec_str=fixed_spec_content,
            spec_str_type="json",
        )

        self.logger.info("Successfully created toolset with manual schema fixes")
        return toolset

    async def _create_toolset_with_aggressive_fixes(
        self, spec_content: str
    ) -> OpenAPIToolset:
        """Create toolset with aggressive schema simplification as last resort.

        Args:
            spec_content: Specification content

        Returns:
            OpenAPIToolset instance
        """
        self.logger.debug("Attempting aggressive schema fixes")

        spec_dict = json.loads(spec_content)

        # Apply aggressive simplification
        self._apply_aggressive_schema_fixes(spec_dict)

        # Convert to JSON and create toolset
        fixed_spec_content = json.dumps(spec_dict, indent=2)

        toolset = OpenAPIToolset(
            spec_str=fixed_spec_content,
            spec_str_type="json",
        )

        self.logger.info("Successfully created toolset with aggressive schema fixes")
        return toolset

    def _apply_aggressive_schema_fixes(self, spec_dict: Dict[str, Any]) -> None:
        """Apply aggressive schema fixes that simplify complex structures.

        Args:
            spec_dict: OpenAPI specification dictionary to fix in-place
        """

        # Replace all complex schemas with simple object schemas
        def simplify_schema(obj):
            if isinstance(obj, dict):
                # If this looks like a schema object
                if "type" in obj or "properties" in obj or "$ref" in obj:
                    # Ensure it has minimal required fields
                    if "description" not in obj:
                        obj["description"] = ""
                    if "type" not in obj and "$ref" not in obj:
                        obj["type"] = "object"
                    if obj.get("type") == "array" and "items" not in obj:
                        obj["items"] = {"type": "object", "description": ""}

                # Recursively process nested objects
                for key, value in list(obj.items()):
                    if isinstance(value, (dict, list)):
                        simplify_schema(value)
                    elif isinstance(value, str) and key == "$ref":
                        # Validate that the reference exists
                        if not self._reference_exists(spec_dict, value):
                            # Replace with simple object
                            obj.clear()
                            obj.update(
                                {"type": "object", "description": "Simplified schema"}
                            )
            elif isinstance(obj, list):
                for item in obj:
                    simplify_schema(item)

        simplify_schema(spec_dict)

    def _reference_exists(self, spec_dict: Dict[str, Any], ref: str) -> bool:
        """Check if a $ref reference exists in the specification.

        Args:
            spec_dict: OpenAPI specification dictionary
            ref: Reference string to check

        Returns:
            True if the reference exists, False otherwise
        """
        if not ref.startswith("#/"):
            return False

        path_parts = ref[2:].split("/")  # Remove "#/" prefix
        current = spec_dict

        try:
            for part in path_parts:
                current = current[part]
            return True
        except (KeyError, TypeError):
            return False

    def _should_filter_endpoint(
        self, tool: RestApiTool, input_data: OpenAPIParserInput
    ) -> bool:
        """Determine if an endpoint should be filtered out based on input criteria."""
        # Filter by tags if specified
        if (
            input_data.filter_tags
            and hasattr(tool, "tags")
            and not any(tag in tool.tags for tag in input_data.filter_tags)
        ):
            self.logger.debug(
                f"Filtering endpoint by tags: {getattr(tool, 'tags', [])}"
            )
            return True

        # Filter by paths if specified
        if (
            input_data.filter_paths
            and hasattr(tool, "path")
            and not self._matches_path_filter(tool.path, input_data.filter_paths)
        ):
            self.logger.debug(
                f"Filtering endpoint by path: {getattr(tool, 'path', '')}"
            )
            return True

        # Filter by methods if specified
        if (
            input_data.filter_methods
            and hasattr(tool, "method")
            and tool.method.upper()
            not in [m.upper() for m in input_data.filter_methods]
        ):
            self.logger.debug(
                f"Filtering endpoint by method: {getattr(tool, 'method', '')}"
            )
            return True

        return False

    async def _load_spec(self, source: str, source_type: SpecSourceType) -> str:
        """Load the OpenAPI specification from various sources."""
        self.logger.debug(f"Loading specification from {source_type.value}")

        if source_type == SpecSourceType.FILE:
            # Load from file
            if not os.path.exists(source):
                self.logger.error(f"Specification file not found: {source}")
                raise FileNotFoundError(f"Specification file not found: {source}")

            self.logger.debug(f"Reading specification file: {source}")
            with open(source, "r") as f:
                content = f.read()
            self.logger.debug(f"Successfully loaded file ({len(content)} characters)")
            return content

        elif source_type == SpecSourceType.URL:
            # For URL sources, you would need to implement HTTP fetching
            # This is a placeholder for that functionality
            self.logger.error("URL source type is not yet implemented")
            raise NotImplementedError("URL source type is not yet implemented")

        elif source_type in (SpecSourceType.YAML, SpecSourceType.JSON):
            # Direct string content
            self.logger.debug(f"Using direct {source_type.value} content")
            return source

        else:
            self.logger.error(f"Unsupported source type: {source_type}")
            raise ValueError(f"Unsupported source type: {source_type}")

    def _extract_api_info(
        self, spec_content: str, source_type: SpecSourceType
    ) -> Dict[str, Any]:
        """Extract basic API information from the specification."""
        try:
            if source_type == SpecSourceType.JSON or spec_content.strip().startswith(
                "{"
            ):
                spec_dict = json.loads(spec_content)
            else:  # YAML or loaded from file
                spec_dict = yaml.safe_load(spec_content)

            info = spec_dict.get("info", {})
            servers = [server.get("url") for server in spec_dict.get("servers", [])]

            api_info = {
                "title": info.get("title", "Unknown API"),
                "version": info.get("version", "Unknown"),
                "description": info.get("description"),
                "servers": servers,
            }

            self.logger.debug(
                f"Extracted API info: {api_info['title']} v{api_info['version']}"
            )
            return api_info
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
        self.logger.debug(f"Extracting endpoint info for: {tool.name}")

        # Parse the endpoint attributes
        endpoint_attrs = self._parse_endpoint_attributes(tool)

        # Get input schema with better error handling
        input_schema = self._extract_input_schema(tool)

        # Get output schema with enhanced extraction
        output_schema = self._extract_output_schema(tool)

        # Create the endpoint info with all extracted data
        endpoint_info = EndpointInfo(
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

        self.logger.debug(
            f"Successfully extracted endpoint: {endpoint_attrs['method']} {endpoint_attrs['path']}"
        )
        return endpoint_info

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
