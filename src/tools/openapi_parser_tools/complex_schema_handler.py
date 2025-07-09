"""
Complex Schema Handler for OpenAPI specifications with intricate schema issues.
This module handles advanced schema normalization and repair scenarios.
"""

import json
import yaml
from typing import Any, Dict, List, Optional, Set, Union
from copy import deepcopy
from common.logger import LoggerFactory, LoggerType, LogLevel


class ComplexSchemaHandler:
    """Handles complex schema issues in OpenAPI specifications."""

    def __init__(self, verbose: bool = False):
        """Initialize the complex schema handler.

        Args:
            verbose: Enable verbose logging
        """
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="openapi.complex_schema",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    def handle_swagger_2_complex_issues(
        self, spec_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle complex issues specific to Swagger 2.0 specifications.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Fixed specification dictionary
        """
        fixed_spec = deepcopy(spec_dict)

        # Convert Swagger 2.0 to OpenAPI 3.0 structure for better compatibility
        if self._is_swagger_2(fixed_spec):
            self.logger.info("Converting Swagger 2.0 to OpenAPI 3.0 structure")
            fixed_spec = self._convert_swagger_to_openapi(fixed_spec)

        # Fix complex definition references
        self._fix_complex_definitions(fixed_spec)

        # Fix array schemas with missing items
        self._fix_array_schemas_missing_items(fixed_spec)

        # Fix response schemas with incomplete structure
        self._fix_incomplete_response_schemas(fixed_spec)

        # Fix parameter schemas with missing types
        self._fix_parameter_schema_types(fixed_spec)

        # Handle nested schema references
        self._handle_nested_schema_references(fixed_spec)

        return fixed_spec

    def _is_swagger_2(self, spec_dict: Dict[str, Any]) -> bool:
        """Check if the specification is Swagger 2.0.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if it's Swagger 2.0, False otherwise
        """
        return "swagger" in spec_dict and spec_dict["swagger"].startswith("2.")

    def _convert_swagger_to_openapi(self, spec_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Swagger 2.0 structure to OpenAPI 3.0 for better compatibility.

        Args:
            spec_dict: Swagger 2.0 specification dictionary

        Returns:
            OpenAPI 3.0 compatible specification dictionary
        """
        converted_spec = deepcopy(spec_dict)

        # Update version info
        converted_spec["openapi"] = "3.0.0"
        if "swagger" in converted_spec:
            del converted_spec["swagger"]

        # Convert host and basePath to servers
        if "host" in converted_spec or "basePath" in converted_spec:
            host = converted_spec.get("host", "localhost")
            base_path = converted_spec.get("basePath", "")
            schemes = converted_spec.get("schemes", ["https"])

            servers = []
            for scheme in schemes:
                url = f"{scheme}://{host}{base_path}"
                servers.append({"url": url})

            converted_spec["servers"] = servers

            # Remove old fields
            for field in ["host", "basePath", "schemes"]:
                if field in converted_spec:
                    del converted_spec[field]

        # Convert definitions to components/schemas
        if "definitions" in converted_spec:
            if "components" not in converted_spec:
                converted_spec["components"] = {}
            converted_spec["components"]["schemas"] = converted_spec["definitions"]
            del converted_spec["definitions"]

        # Update $ref paths
        self._update_ref_paths(converted_spec)

        return converted_spec

    def _update_ref_paths(self, spec_dict: Dict[str, Any]) -> None:
        """Update $ref paths from Swagger 2.0 to OpenAPI 3.0 format.

        Args:
            spec_dict: Specification dictionary to update
        """

        def update_refs(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "$ref" and isinstance(value, str):
                        if value.startswith("#/definitions/"):
                            obj[key] = value.replace(
                                "#/definitions/", "#/components/schemas/"
                            )
                    else:
                        update_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    update_refs(item)

        update_refs(spec_dict)

    def _fix_complex_definitions(self, spec_dict: Dict[str, Any]) -> None:
        """Fix complex definition issues.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        components = spec_dict.get("components", {})
        schemas = components.get("schemas", {})

        for schema_name, schema_def in schemas.items():
            if isinstance(schema_def, dict):
                self._fix_schema_structure_recursively(schema_def, schema_name)

    def _fix_array_schemas_missing_items(self, spec_dict: Dict[str, Any]) -> None:
        """Fix array schemas that are missing items definitions.

        Args:
            spec_dict: OpenAPI specification dictionary
        """

        def fix_array_items(obj, path=""):
            if isinstance(obj, dict):
                if obj.get("type") == "array" and "items" not in obj:
                    # Add default items schema
                    obj["items"] = {
                        "type": "object",
                        "description": f"Array item for {path}",
                        "properties": {},
                    }
                    self.logger.debug(f"Fixed missing items for array at {path}")

                for key, value in obj.items():
                    fix_array_items(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    fix_array_items(item, f"{path}[{i}]")

        fix_array_items(spec_dict)

    def _fix_incomplete_response_schemas(self, spec_dict: Dict[str, Any]) -> None:
        """Fix response schemas with incomplete structure.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                responses = operation.get("responses", {})
                if isinstance(responses, dict):
                    for status_code, response in responses.items():
                        if isinstance(response, dict):
                            self._fix_single_response_schema(
                                response, f"{method} {path} {status_code}"
                            )

    def _fix_single_response_schema(
        self, response: Dict[str, Any], context: str
    ) -> None:
        """Fix a single response schema.

        Args:
            response: Response dictionary to fix
            context: Context string for logging
        """
        # Ensure description exists
        if "description" not in response:
            response["description"] = f"Response for {context}"

        # Fix content schemas
        content = response.get("content", {})
        if isinstance(content, dict):
            for media_type, media_content in content.items():
                if isinstance(media_content, dict) and "schema" in media_content:
                    schema = media_content["schema"]
                    if isinstance(schema, dict):
                        self._fix_schema_structure_recursively(
                            schema, f"{context} {media_type}"
                        )

    def _fix_parameter_schema_types(self, spec_dict: Dict[str, Any]) -> None:
        """Fix parameter schemas with missing or incorrect types.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                parameters = operation.get("parameters", [])
                if isinstance(parameters, list):
                    for param in parameters:
                        if isinstance(param, dict):
                            self._fix_parameter_schema(param, f"{method} {path}")

    def _fix_parameter_schema(self, param: Dict[str, Any], context: str) -> None:
        """Fix a single parameter schema.

        Args:
            param: Parameter dictionary to fix
            context: Context string for logging
        """
        # Ensure required fields exist
        if "name" not in param:
            param["name"] = "unknown_param"

        if "in" not in param:
            param["in"] = "query"  # Default location

        # Fix schema
        schema = param.get("schema", {})
        if not isinstance(schema, dict):
            schema = {"type": "string", "description": ""}
            param["schema"] = schema
        else:
            self._fix_schema_structure_recursively(
                schema, f"{context} param {param.get('name', 'unknown')}"
            )

    def _handle_nested_schema_references(self, spec_dict: Dict[str, Any]) -> None:
        """Handle complex nested schema references.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        # Track visited schemas to prevent infinite recursion
        visited_schemas = set()

        def resolve_nested_refs(obj, current_path=""):
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref = obj["$ref"]
                    if ref in visited_schemas:
                        # Circular reference detected, replace with simple schema
                        obj.clear()
                        obj.update(
                            {
                                "type": "object",
                                "description": f"Circular reference to {ref}",
                                "properties": {},
                            }
                        )
                        return

                    visited_schemas.add(ref)

                    # Try to resolve the reference
                    resolved_schema = self._resolve_reference(spec_dict, ref)
                    if resolved_schema:
                        resolve_nested_refs(resolved_schema, f"{current_path}->{ref}")

                for key, value in obj.items():
                    if key != "$ref":
                        resolve_nested_refs(value, f"{current_path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    resolve_nested_refs(item, f"{current_path}[{i}]")

        resolve_nested_refs(spec_dict)

    def _resolve_reference(
        self, spec_dict: Dict[str, Any], ref: str
    ) -> Optional[Dict[str, Any]]:
        """Resolve a $ref reference to its actual schema.

        Args:
            spec_dict: OpenAPI specification dictionary
            ref: Reference string

        Returns:
            Resolved schema or None if not found
        """
        if not ref.startswith("#/"):
            return None

        path_parts = ref[2:].split("/")  # Remove "#/" prefix
        current = spec_dict

        try:
            for part in path_parts:
                current = current[part]
            return current if isinstance(current, dict) else None
        except (KeyError, TypeError):
            self.logger.warning(f"Could not resolve reference: {ref}")
            return None

    def _fix_schema_structure_recursively(
        self, schema: Dict[str, Any], context: str
    ) -> None:
        """Fix schema structure recursively with comprehensive validation.

        Args:
            schema: Schema dictionary to fix
            context: Context string for logging
        """
        # Ensure description exists
        if "description" not in schema:
            schema["description"] = ""

        # Fix type based on structure
        if "type" not in schema and "$ref" not in schema:
            if "properties" in schema:
                schema["type"] = "object"
            elif "items" in schema:
                schema["type"] = "array"
            elif "enum" in schema:
                # Infer type from enum values
                enum_values = schema.get("enum", [])
                if enum_values:
                    first_value = enum_values[0]
                    if isinstance(first_value, str):
                        schema["type"] = "string"
                    elif isinstance(first_value, bool):
                        schema["type"] = "boolean"
                    elif isinstance(first_value, int):
                        schema["type"] = "integer"
                    elif isinstance(first_value, float):
                        schema["type"] = "number"
                    else:
                        schema["type"] = "string"
                else:
                    schema["type"] = "string"
            else:
                schema["type"] = "object"  # Safe default

        # Fix properties recursively
        if "properties" in schema and isinstance(schema["properties"], dict):
            for prop_name, prop_schema in schema["properties"].items():
                if isinstance(prop_schema, dict):
                    self._fix_schema_structure_recursively(
                        prop_schema, f"{context}.{prop_name}"
                    )

        # Fix array items
        if "items" in schema and isinstance(schema["items"], dict):
            self._fix_schema_structure_recursively(schema["items"], f"{context}.items")

        # Fix composition schemas
        for composition_key in ["allOf", "oneOf", "anyOf"]:
            if composition_key in schema and isinstance(schema[composition_key], list):
                for i, sub_schema in enumerate(schema[composition_key]):
                    if isinstance(sub_schema, dict):
                        self._fix_schema_structure_recursively(
                            sub_schema, f"{context}.{composition_key}[{i}]"
                        )

        # Fix additionalProperties
        if "additionalProperties" in schema and isinstance(
            schema["additionalProperties"], dict
        ):
            self._fix_schema_structure_recursively(
                schema["additionalProperties"], f"{context}.additionalProperties"
            )

    def fix_gitlab_branch_specific_issues(
        self, spec_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix issues specific to GitLab Branch API specification.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Fixed specification dictionary
        """
        fixed_spec = deepcopy(spec_dict)

        # Fix the specific array definitions that cause issues
        self._fix_gitlab_array_definitions(fixed_spec)

        # Fix incomplete response schemas
        self._fix_gitlab_response_schemas(fixed_spec)

        # Fix parameter schemas
        self._fix_gitlab_parameter_schemas(fixed_spec)

        # Handle missing or incomplete definitions
        self._fix_gitlab_missing_definitions(fixed_spec)

        return fixed_spec

    def _fix_gitlab_array_definitions(self, spec_dict: Dict[str, Any]) -> None:
        """Fix GitLab-specific array definition issues.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        definitions = spec_dict.get("definitions", {})

        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                # Fix arrays without proper items
                if def_schema.get("type") == "array" and "items" not in def_schema:
                    # Try to infer items from the definition name
                    if def_name.endswith("s") and len(def_name) > 1:
                        singular_name = def_name[:-1]  # Remove 's'
                        if singular_name in definitions:
                            def_schema["items"] = {
                                "$ref": f"#/definitions/{singular_name}"
                            }
                        else:
                            def_schema["items"] = {
                                "type": "object",
                                "description": f"Item in {def_name} array",
                                "properties": {},
                            }
                    else:
                        def_schema["items"] = {
                            "type": "object",
                            "description": f"Item in {def_name} array",
                            "properties": {},
                        }

    def _fix_gitlab_response_schemas(self, spec_dict: Dict[str, Any]) -> None:
        """Fix GitLab-specific response schema issues.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                responses = operation.get("responses", {})
                for status_code, response in responses.items():
                    if isinstance(response, dict):
                        # Ensure description exists
                        if "description" not in response:
                            response["description"] = (
                                self._generate_response_description(status_code)
                            )

                        # Fix schema references in responses
                        self._fix_response_schema_refs(response)

    def _fix_response_schema_refs(self, response: Dict[str, Any]) -> None:
        """Fix schema references in a response object.

        Args:
            response: Response dictionary to fix
        """
        # Handle direct schema reference
        if "schema" in response:
            schema = response["schema"]
            if isinstance(schema, dict):
                self._fix_schema_structure_recursively(schema, "response")

        # Handle content schemas (OpenAPI 3.0 style)
        content = response.get("content", {})
        if isinstance(content, dict):
            for media_type, media_content in content.items():
                if isinstance(media_content, dict) and "schema" in media_content:
                    schema = media_content["schema"]
                    if isinstance(schema, dict):
                        self._fix_schema_structure_recursively(
                            schema, f"response.{media_type}"
                        )

    def _fix_gitlab_parameter_schemas(self, spec_dict: Dict[str, Any]) -> None:
        """Fix GitLab-specific parameter schema issues.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                parameters = operation.get("parameters", [])
                if isinstance(parameters, list):
                    for param in parameters:
                        if isinstance(param, dict):
                            # Ensure all required parameter fields exist
                            if "name" not in param:
                                param["name"] = "unknown_param"
                            if "in" not in param:
                                param["in"] = "query"
                            if "type" in param and "schema" not in param:
                                # Convert Swagger 2.0 style to OpenAPI 3.0 style
                                param_type = param.pop("type")
                                param["schema"] = {
                                    "type": param_type,
                                    "description": "",
                                }

    def _fix_gitlab_missing_definitions(self, spec_dict: Dict[str, Any]) -> None:
        """Fix missing or incomplete definitions in GitLab spec.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        definitions = spec_dict.get("definitions", {})

        # List of definitions that might be referenced but incomplete
        required_definitions = [
            "Error",
            "AccessLevel",
            "ProtectedBranch",
            "Branch",
            "Branches",
            "Contributors",
            "Contributor",
            "Compare",
            "RepoDiff",
            "RepoCommit",
            "Author",
            "Note",
            "CommitStatus",
            "MergeRequests",
            "TimeStats",
        ]

        for def_name in required_definitions:
            if def_name not in definitions:
                # Create a minimal definition
                definitions[def_name] = {
                    "type": "object",
                    "description": f"Auto-generated definition for {def_name}",
                    "properties": {
                        "id": {"type": "string", "description": "Identifier"}
                    },
                }
            elif isinstance(definitions[def_name], dict):
                # Ensure existing definitions have proper structure
                def_schema = definitions[def_name]
                if "description" not in def_schema:
                    def_schema["description"] = f"Definition for {def_name}"
                if "type" not in def_schema and "properties" in def_schema:
                    def_schema["type"] = "object"

    def _generate_response_description(self, status_code: str) -> str:
        """Generate a description for a response based on its status code.

        Args:
            status_code: HTTP status code

        Returns:
            Generated description string
        """
        status_descriptions = {
            "200": "Successful operation",
            "201": "Created successfully",
            "204": "No content",
            "400": "Bad request",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "Not found",
            "405": "Method not allowed",
            "409": "Conflict",
            "422": "Unprocessable entity",
            "500": "Internal server error",
            "default": "Default response",
        }

        return status_descriptions.get(
            status_code, f"Response with status {status_code}"
        )
