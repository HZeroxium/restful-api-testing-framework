"""
OpenAPI Parser implementation.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from .loaders import load_openapi, load_spec_from_url
from .schema import SchemaProcessor
from .operations import OperationProcessor
from rbctest.schemas.openapi import (
    OpenAPIParserInput,
    OpenAPIParserOutput,
    EndpointInfo,
    Parameter,
    RequestBody,
    Response,
    SpecSourceType,
)


class SchemaParser:
    """Convenience class for schema parsing operations."""

    def __init__(self, spec: Dict[str, Any]):
        """
        Initialize the schema parser.

        Args:
            spec: OpenAPI specification
        """
        self.processor = SchemaProcessor(spec)

    def get_schema_by_ref(self, ref: str) -> Dict[str, Any]:
        """
        Get a schema by reference.

        Args:
            ref: Schema reference string (e.g., "#/components/schemas/Pet")

        Returns:
            Schema object
        """
        from .loaders import get_ref

        return get_ref(self.processor.spec, ref)

    def resolve_schema(
        self, schema: Dict[str, Any], depth: int = 0, max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Resolve schema references recursively.

        Args:
            schema: Schema object or reference
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Resolved schema object
        """
        if depth > max_depth:
            return {"type": "object", "description": "Max recursion depth reached"}

        if not schema:
            return {}

        if "$ref" in schema:
            ref_schema = self.get_schema_by_ref(schema["$ref"])
            return self.resolve_schema(ref_schema, depth + 1, max_depth)

        result = dict(schema)

        # Handle nested objects in properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            resolved_props = {}
            for prop_name, prop_schema in schema["properties"].items():
                resolved_props[prop_name] = self.resolve_schema(
                    prop_schema, depth + 1, max_depth
                )
            result["properties"] = resolved_props

        # Handle nested arrays
        if "items" in schema and isinstance(schema["items"], dict):
            result["items"] = self.resolve_schema(schema["items"], depth + 1, max_depth)

        return result


class OpenAPIParser:
    """
    A class that parses OpenAPI specifications and extracts useful information.

    This parser can:
    - Load OpenAPI specs from file, URL, or direct JSON/YAML content
    - Extract endpoints, parameters, request bodies, and response schemas
    - Apply filters for paths, methods, and tags
    - Simplify the OpenAPI structure for easier use
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the OpenAPI parser.

        Args:
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = logging.getLogger("openapi_parser")
        if verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARNING)

        # Ensure the logger has a handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def parse(self, input_params: OpenAPIParserInput) -> OpenAPIParserOutput:
        """
        Parse an OpenAPI specification based on input parameters.

        Args:
            input_params: Parameters for parsing the OpenAPI spec

        Returns:
            Structured output containing parsed information
        """
        self.logger.info(f"Parsing OpenAPI spec from {input_params.spec_source}")

        # Load the OpenAPI specification
        spec = self._load_spec(input_params.spec_source, input_params.source_type)

        # Initialize processors
        schema_processor = SchemaProcessor(spec)
        operation_processor = OperationProcessor(spec)

        # Extract basic info
        title = spec.get("info", {}).get("title", "Unknown API")
        version = spec.get("info", {}).get("version", "Unknown")
        description = spec.get("info", {}).get("description", "")

        # Extract servers
        servers = []
        for server in spec.get("servers", []):
            if "url" in server:
                servers.append(server["url"])

        # Extract endpoints
        endpoints = self._extract_endpoints(
            spec,
            operation_processor,
            filter_paths=input_params.filter_paths,
            filter_methods=input_params.filter_methods,
            filter_tags=input_params.filter_tags,
            include_deprecated=input_params.include_deprecated,
        )

        # Simplify the OpenAPI structure
        simplified_spec = operation_processor.simplify_openapi()

        # Extract simplified schemas
        simplified_schemas = self._extract_simplified_schemas(spec)

        # Create output object
        output = OpenAPIParserOutput(
            title=title,
            version=version,
            description=description,
            servers=servers,
            endpoints=endpoints,
            simplified_endpoints=simplified_spec,
            simplified_schemas=simplified_schemas,
            raw_spec=spec,
            endpoint_count=len(endpoints),
        )

        self.logger.info(f"Parsed {len(endpoints)} endpoints from {title} v{version}")
        return output

    def _load_spec(
        self, spec_source: str, source_type: SpecSourceType
    ) -> Dict[str, Any]:
        """
        Load the OpenAPI specification from the given source.

        Args:
            spec_source: Path, URL, or content of the OpenAPI spec
            source_type: Type of the source

        Returns:
            Loaded OpenAPI specification as a dictionary
        """
        if source_type == SpecSourceType.FILE:
            self.logger.info(f"Loading spec from file: {spec_source}")
            return load_openapi(spec_source)
        elif source_type == SpecSourceType.URL:
            self.logger.info(f"Loading spec from URL: {spec_source}")
            return load_spec_from_url(spec_source)
        elif source_type == SpecSourceType.JSON:
            self.logger.info("Loading spec from JSON content")
            return json.loads(spec_source)
        elif source_type == SpecSourceType.YAML:
            self.logger.info("Loading spec from YAML content")
            import yaml

            return yaml.safe_load(spec_source)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _extract_endpoints(
        self,
        spec: Dict[str, Any],
        operation_processor: OperationProcessor,
        filter_paths: Optional[List[str]] = None,
        filter_methods: Optional[List[str]] = None,
        filter_tags: Optional[List[str]] = None,
        include_deprecated: bool = False,
    ) -> List[EndpointInfo]:
        """
        Extract endpoints from the OpenAPI specification.

        Args:
            spec: OpenAPI specification
            operation_processor: Operation processor instance
            filter_paths: List of paths to include (if None, include all)
            filter_methods: List of HTTP methods to include (if None, include all)
            filter_tags: List of tags to include (if None, include all)
            include_deprecated: Whether to include deprecated endpoints

        Returns:
            List of endpoint information
        """
        endpoints = []

        for path, path_item in spec.get("paths", {}).items():
            # Skip if path is not in filter_paths (if filter_paths is provided)
            if filter_paths and path not in filter_paths:
                continue

            # Process operations (HTTP methods) for the path
            for method, operation in path_item.items():
                # Skip if not a standard HTTP method
                if method not in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "head",
                    "options",
                ]:
                    continue

                # Skip if method is not in filter_methods (if filter_methods is provided)
                if filter_methods and method.lower() not in [
                    m.lower() for m in filter_methods
                ]:
                    continue

                # Skip if deprecated and include_deprecated is False
                if operation.get("deprecated", False) and not include_deprecated:
                    continue

                # Skip if none of the operation's tags match filter_tags (if filter_tags is provided)
                operation_tags = operation.get("tags", [])
                if filter_tags and not any(
                    tag in filter_tags for tag in operation_tags
                ):
                    continue

                # Extract operation details
                operation_id = operation.get("operationId", f"{method.upper()} {path}")
                summary = operation.get("summary", "")
                description = operation.get("description", "")

                # Extract parameters
                parameters = self._extract_parameters(
                    operation_processor, operation, path_item
                )

                # Extract request body
                request_body = self._extract_request_body(operation)

                # Extract responses
                responses = self._extract_responses(operation)

                # Create endpoint info
                endpoint = EndpointInfo(
                    path=path,
                    method=method.upper(),
                    operation_id=operation_id,
                    summary=summary,
                    description=description,
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    tags=operation_tags,
                    deprecated=operation.get("deprecated", False),
                    security=operation.get("security"),
                )

                endpoints.append(endpoint)

        return endpoints

    def _extract_parameters(
        self,
        operation_processor: OperationProcessor,
        operation: Dict[str, Any],
        path_item: Dict[str, Any],
    ) -> List[Parameter]:
        """
        Extract parameters from an operation.

        Args:
            operation_processor: Operation processor instance
            operation: Operation object
            path_item: Path item containing the operation

        Returns:
            List of parameter objects
        """
        result = []

        # Get raw parameters from the operation processor
        raw_params = operation_processor.extract_parameters(operation, path_item)

        # Convert to Parameter objects
        for param in raw_params:
            # Basic parameter properties
            name = param.get("name", "")
            in_location = param.get("in", "")
            required = param.get("required", False)
            description = param.get("description", None)

            # Schema
            schema = {}
            if "schema" in param:
                schema = param["schema"]

            # Example
            example = param.get("example", None)

            # Create Parameter object
            parameter = Parameter(
                name=name,
                in_location=in_location,
                required=required,
                description=description,
                schema_=schema,
                example=example,
            )

            result.append(parameter)

        return result

    def _extract_request_body(self, operation: Dict[str, Any]) -> Optional[RequestBody]:
        """
        Extract request body information from an operation.

        Args:
            operation: Operation object from OpenAPI spec

        Returns:
            Request body information or None if not present
        """
        if "requestBody" not in operation:
            return None

        request_body = operation["requestBody"]
        content = {}

        for media_type, content_info in request_body.get("content", {}).items():
            content[media_type] = {
                "schema": content_info.get("schema", {}),
                "examples": content_info.get("examples", {}),
                "example": content_info.get("example"),
            }

        return RequestBody(
            description=request_body.get("description", ""),
            content=content,
            required=request_body.get("required", False),
        )

    def _extract_responses(self, operation: Dict[str, Any]) -> Dict[str, Response]:
        """
        Extract response information from an operation.

        Args:
            operation: Operation object from OpenAPI spec

        Returns:
            Dictionary of responses keyed by status code
        """
        result = {}

        for status_code, response in operation.get("responses", {}).items():
            content = {}

            for media_type, content_info in response.get("content", {}).items():
                content[media_type] = {
                    "schema": content_info.get("schema", {}),
                    "examples": content_info.get("examples", {}),
                    "example": content_info.get("example"),
                }

            result[status_code] = Response(
                description=response.get("description", ""),
                content=content,
                headers=response.get("headers", {}),
            )

        return result

    def _extract_simplified_schemas(
        self, spec: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract simplified schema information from the OpenAPI spec.

        Args:
            spec: OpenAPI specification

        Returns:
            Dictionary of simplified schemas
        """
        schemas = {}

        # Extract from components/schemas if available
        if "components" in spec and "schemas" in spec["components"]:
            for schema_name, schema in spec["components"]["schemas"].items():
                simplified = {
                    "type": schema.get("type", "object"),
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                    "description": schema.get("description", ""),
                }
                schemas[schema_name] = simplified

        return schemas
