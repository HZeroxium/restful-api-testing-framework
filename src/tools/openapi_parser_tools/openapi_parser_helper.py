import json
import yaml
from typing import Any, Dict, List, Optional
from copy import deepcopy
from common.logger import LoggerFactory, LoggerType, LogLevel


class OpenAPISpecNormalizer:
    """Helper class to normalize OpenAPI specifications for better compatibility."""

    def __init__(self, verbose: bool = False):
        """Initialize the normalizer.

        Args:
            verbose: Enable verbose logging
        """
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="openapi.normalizer",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    def normalize_spec(self, spec_content: str, spec_format: str = "json") -> str:
        """Normalize an OpenAPI specification to fix common compatibility issues.

        Args:
            spec_content: Raw OpenAPI specification content
            spec_format: Format of the spec ('json' or 'yaml')

        Returns:
            Normalized OpenAPI specification as a string

        Raises:
            ValueError: If the spec format is unsupported or parsing fails
        """
        try:
            # Parse the specification
            if spec_format.lower() == "json":
                spec_dict = json.loads(spec_content)
            elif spec_format.lower() in ("yaml", "yml"):
                spec_dict = yaml.safe_load(spec_content)
            else:
                raise ValueError(f"Unsupported spec format: {spec_format}")

            self.logger.debug(
                f"Loaded OpenAPI spec: {spec_dict.get('info', {}).get('title', 'Unknown')}"
            )

            # Apply normalization fixes
            normalized_spec = self._apply_normalizations(spec_dict)

            # Convert back to string
            if spec_format.lower() == "json":
                return json.dumps(normalized_spec, indent=2)
            else:
                return yaml.dump(normalized_spec, default_flow_style=False)

        except Exception as e:
            self.logger.error(f"Error normalizing OpenAPI spec: {e}")
            raise

    def _apply_normalizations(self, spec_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all normalization fixes to the specification.

        Args:
            spec_dict: Parsed OpenAPI specification dictionary

        Returns:
            Normalized specification dictionary
        """
        # Work with a deep copy to avoid modifying the original
        normalized_spec = deepcopy(spec_dict)

        fixes_applied = []

        # Fix 1: Normalize parameter schemas
        if self._fix_parameter_schemas(normalized_spec):
            fixes_applied.append("parameter_schemas")

        # Fix 2: Normalize response schemas
        if self._fix_response_schemas(normalized_spec):
            fixes_applied.append("response_schemas")

        # Fix 3: Normalize request body schemas
        if self._fix_request_body_schemas(normalized_spec):
            fixes_applied.append("request_body_schemas")

        # Fix 4: Add missing required fields
        if self._add_missing_required_fields(normalized_spec):
            fixes_applied.append("missing_required_fields")

        # Fix 5: Normalize component schemas
        if self._fix_component_schemas(normalized_spec):
            fixes_applied.append("component_schemas")

        if fixes_applied:
            self.logger.info(f"Applied normalization fixes: {', '.join(fixes_applied)}")
        else:
            self.logger.debug("No normalization fixes needed")

        return normalized_spec

    def _fix_parameter_schemas(self, spec_dict: Dict[str, Any]) -> bool:
        """Fix parameter schema definitions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if fixes were applied, False otherwise
        """
        fixes_applied = False
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                parameters = operation.get("parameters", [])
                if not isinstance(parameters, list):
                    continue

                for i, param in enumerate(parameters):
                    if not isinstance(param, dict):
                        continue

                    # Fix schema field if it's a dict without proper structure
                    if "schema" in param:
                        schema = param["schema"]
                        if isinstance(
                            schema, dict
                        ) and not self._is_valid_schema_object(schema):
                            # Convert dict to proper schema object
                            param["schema"] = self._normalize_schema_dict(schema)
                            fixes_applied = True
                            self.logger.debug(
                                f"Fixed parameter schema in {method.upper()} {path}"
                            )

        return fixes_applied

    def _fix_response_schemas(self, spec_dict: Dict[str, Any]) -> bool:
        """Fix response schema definitions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if fixes were applied, False otherwise
        """
        fixes_applied = False
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                responses = operation.get("responses", {})
                if not isinstance(responses, dict):
                    continue

                for status_code, response in responses.items():
                    if not isinstance(response, dict):
                        continue

                    # Fix content schemas
                    content = response.get("content", {})
                    if isinstance(content, dict):
                        for media_type, media_content in content.items():
                            if (
                                isinstance(media_content, dict)
                                and "schema" in media_content
                            ):
                                schema = media_content["schema"]
                                if isinstance(
                                    schema, dict
                                ) and not self._is_valid_schema_object(schema):
                                    media_content["schema"] = (
                                        self._normalize_schema_dict(schema)
                                    )
                                    fixes_applied = True
                                    self.logger.debug(
                                        f"Fixed response schema in {method.upper()} {path} ({status_code})"
                                    )

        return fixes_applied

    def _fix_request_body_schemas(self, spec_dict: Dict[str, Any]) -> bool:
        """Fix request body schema definitions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if fixes were applied, False otherwise
        """
        fixes_applied = False
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                request_body = operation.get("requestBody", {})
                if not isinstance(request_body, dict):
                    continue

                content = request_body.get("content", {})
                if isinstance(content, dict):
                    for media_type, media_content in content.items():
                        if (
                            isinstance(media_content, dict)
                            and "schema" in media_content
                        ):
                            schema = media_content["schema"]
                            if isinstance(
                                schema, dict
                            ) and not self._is_valid_schema_object(schema):
                                media_content["schema"] = self._normalize_schema_dict(
                                    schema
                                )
                                fixes_applied = True
                                self.logger.debug(
                                    f"Fixed request body schema in {method.upper()} {path}"
                                )

        return fixes_applied

    def _add_missing_required_fields(self, spec_dict: Dict[str, Any]) -> bool:
        """Add missing required fields to the specification.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if fixes were applied, False otherwise
        """
        fixes_applied = False

        # Ensure info section has required fields
        info = spec_dict.get("info", {})
        if "title" not in info:
            info["title"] = "API"
            fixes_applied = True
        if "version" not in info:
            info["version"] = "1.0.0"
            fixes_applied = True

        spec_dict["info"] = info

        # Ensure paths exist
        if "paths" not in spec_dict:
            spec_dict["paths"] = {}
            fixes_applied = True

        return fixes_applied

    def _fix_component_schemas(self, spec_dict: Dict[str, Any]) -> bool:
        """Fix component schema definitions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            True if fixes were applied, False otherwise
        """
        fixes_applied = False
        components = spec_dict.get("components", {})

        if not isinstance(components, dict):
            return fixes_applied

        schemas = components.get("schemas", {})
        if isinstance(schemas, dict):
            for schema_name, schema_def in schemas.items():
                if isinstance(schema_def, dict) and not self._is_valid_schema_object(
                    schema_def
                ):
                    components["schemas"][schema_name] = self._normalize_schema_dict(
                        schema_def
                    )
                    fixes_applied = True
                    self.logger.debug(f"Fixed component schema: {schema_name}")

        return fixes_applied

    def _is_valid_schema_object(self, schema: Dict[str, Any]) -> bool:
        """Check if a schema dict is a valid OpenAPI schema object.

        Args:
            schema: Schema dictionary to validate

        Returns:
            True if the schema appears to be valid, False otherwise
        """
        # A valid schema should have at least one of these fields
        valid_fields = {
            "type",
            "properties",
            "items",
            "allOf",
            "oneOf",
            "anyOf",
            "$ref",
            "format",
            "enum",
            "const",
            "pattern",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
        }

        return any(field in schema for field in valid_fields)

    def _normalize_schema_dict(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a schema dictionary to be a proper OpenAPI schema.

        Args:
            schema: Schema dictionary to normalize

        Returns:
            Normalized schema dictionary
        """
        normalized = deepcopy(schema)

        # Ensure description field exists (this is the main fix for the error)
        if "description" not in normalized:
            normalized["description"] = ""

        # Add type if missing
        if "type" not in normalized and "properties" in normalized:
            normalized["type"] = "object"
        elif "type" not in normalized and "items" in normalized:
            normalized["type"] = "array"
        elif "type" not in normalized and "$ref" not in normalized:
            # Try to infer type from other fields
            if "enum" in normalized:
                # Infer type from enum values
                enum_values = normalized["enum"]
                if enum_values and isinstance(enum_values[0], str):
                    normalized["type"] = "string"
                elif enum_values and isinstance(enum_values[0], (int, float)):
                    normalized["type"] = "number"
                else:
                    normalized["type"] = "string"
            else:
                normalized["type"] = "string"  # Default fallback

        # Normalize properties if they exist
        if "properties" in normalized and isinstance(normalized["properties"], dict):
            for prop_name, prop_schema in normalized["properties"].items():
                if isinstance(prop_schema, dict):
                    normalized["properties"][prop_name] = self._normalize_schema_dict(
                        prop_schema
                    )

        # Normalize items if they exist (for arrays)
        if "items" in normalized and isinstance(normalized["items"], dict):
            normalized["items"] = self._normalize_schema_dict(normalized["items"])

        return normalized


class OpenAPICompatibilityChecker:
    """Helper class to check OpenAPI specification compatibility."""

    def __init__(self, verbose: bool = False):
        """Initialize the compatibility checker.

        Args:
            verbose: Enable verbose logging
        """
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="openapi.compatibility",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    def check_spec_compatibility(
        self, spec_dict: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Check OpenAPI specification for compatibility issues.

        Args:
            spec_dict: Parsed OpenAPI specification dictionary

        Returns:
            Dictionary mapping issue types to lists of specific issues
        """
        issues = {"errors": [], "warnings": [], "info": []}

        # Check OpenAPI version
        openapi_version = spec_dict.get("openapi", spec_dict.get("swagger"))
        if not openapi_version:
            issues["errors"].append("Missing OpenAPI/Swagger version")
        elif openapi_version.startswith("2."):
            issues["warnings"].append("Using Swagger 2.0 (OpenAPI 3.x recommended)")

        # Check required fields
        if "info" not in spec_dict:
            issues["errors"].append("Missing required 'info' section")
        else:
            info = spec_dict["info"]
            if "title" not in info:
                issues["errors"].append("Missing required 'info.title'")
            if "version" not in info:
                issues["errors"].append("Missing required 'info.version'")

        if "paths" not in spec_dict:
            issues["errors"].append("Missing required 'paths' section")

        # Check for schema compatibility issues
        self._check_schema_issues(spec_dict, issues)

        return issues

    def _check_schema_issues(
        self, spec_dict: Dict[str, Any], issues: Dict[str, List[str]]
    ) -> None:
        """Check for schema-related compatibility issues.

        Args:
            spec_dict: OpenAPI specification dictionary
            issues: Issues dictionary to populate
        """
        paths = spec_dict.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                # Check parameters
                parameters = operation.get("parameters", [])
                for param in parameters:
                    if isinstance(param, dict) and "schema" in param:
                        schema = param["schema"]
                        if isinstance(schema, dict) and not hasattr(schema, "get"):
                            issues["warnings"].append(
                                f"Unusual parameter schema in {method.upper()} {path}"
                            )

                # Check request body
                request_body = operation.get("requestBody", {})
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    for media_type, media_content in content.items():
                        if (
                            isinstance(media_content, dict)
                            and "schema" in media_content
                        ):
                            schema = media_content["schema"]
                            if isinstance(schema, dict) and not hasattr(schema, "get"):
                                issues["warnings"].append(
                                    f"Unusual request body schema in {method.upper()} {path}"
                                )

                # Check responses
                responses = operation.get("responses", {})
                if isinstance(responses, dict):
                    for status_code, response in responses.items():
                        if isinstance(response, dict):
                            content = response.get("content", {})
                            for media_type, media_content in content.items():
                                if (
                                    isinstance(media_content, dict)
                                    and "schema" in media_content
                                ):
                                    schema = media_content["schema"]
                                    if isinstance(schema, dict) and not hasattr(
                                        schema, "get"
                                    ):
                                        issues["warnings"].append(
                                            f"Unusual response schema in {method.upper()} {path} ({status_code})"
                                        )


class OpenAPISpecSchemaFixer:
    """Helper class to fix specific OpenAPI schema issues that cause toolset creation failures."""

    def __init__(self, verbose: bool = False):
        """Initialize the schema fixer.

        Args:
            verbose: Enable verbose logging
        """
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="openapi.schema_fixer",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    def fix_schema_description_errors(
        self, spec_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix the specific 'dict' object has no attribute 'description' error.

        This error typically occurs when schema objects are plain dictionaries
        instead of proper schema objects with required fields.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Fixed specification dictionary
        """
        fixed_spec = deepcopy(spec_dict)
        fixes_applied = 0

        self.logger.debug("Fixing schema description errors")

        # Fix definitions/components schemas
        fixes_applied += self._fix_definitions_schemas(fixed_spec)
        fixes_applied += self._fix_components_schemas(fixed_spec)

        # Fix inline schemas in paths
        fixes_applied += self._fix_path_schemas(fixed_spec)

        # Fix parameter schemas
        fixes_applied += self._fix_parameter_schemas_descriptions(fixed_spec)

        # Fix response schemas
        fixes_applied += self._fix_response_schemas_descriptions(fixed_spec)

        if fixes_applied > 0:
            self.logger.info(f"Fixed {fixes_applied} schema description issues")
        else:
            self.logger.debug("No schema description issues found")

        return fixed_spec

    def _fix_definitions_schemas(self, spec_dict: Dict[str, Any]) -> int:
        """Fix schemas in the definitions section (Swagger 2.0).

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
        definitions = spec_dict.get("definitions", {})

        if not isinstance(definitions, dict):
            return fixes_applied

        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                if self._fix_schema_object_descriptions(def_schema):
                    fixes_applied += 1
                    self.logger.debug(f"Fixed definition schema: {def_name}")

        return fixes_applied

    def _fix_components_schemas(self, spec_dict: Dict[str, Any]) -> int:
        """Fix schemas in the components section (OpenAPI 3.0+).

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
        components = spec_dict.get("components", {})

        if not isinstance(components, dict):
            return fixes_applied

        schemas = components.get("schemas", {})
        if isinstance(schemas, dict):
            for schema_name, schema_def in schemas.items():
                if isinstance(schema_def, dict):
                    if self._fix_schema_object_descriptions(schema_def):
                        fixes_applied += 1
                        self.logger.debug(f"Fixed component schema: {schema_name}")

        return fixes_applied

    def _fix_path_schemas(self, spec_dict: Dict[str, Any]) -> int:
        """Fix schemas in path definitions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
        paths = spec_dict.get("paths", {})

        if not isinstance(paths, dict):
            return fixes_applied

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict) or method.startswith("x-"):
                    continue

                # Fix request body schemas
                request_body = operation.get("requestBody", {})
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    if isinstance(content, dict):
                        for media_type, media_content in content.items():
                            if (
                                isinstance(media_content, dict)
                                and "schema" in media_content
                            ):
                                schema = media_content["schema"]
                                if isinstance(schema, dict):
                                    if self._fix_schema_object_descriptions(schema):
                                        fixes_applied += 1

                # Fix response schemas
                responses = operation.get("responses", {})
                if isinstance(responses, dict):
                    for status_code, response in responses.items():
                        if isinstance(response, dict):
                            content = response.get("content", {})
                            if isinstance(content, dict):
                                for media_type, media_content in content.items():
                                    if (
                                        isinstance(media_content, dict)
                                        and "schema" in media_content
                                    ):
                                        schema = media_content["schema"]
                                        if isinstance(schema, dict):
                                            if self._fix_schema_object_descriptions(
                                                schema
                                            ):
                                                fixes_applied += 1

        return fixes_applied

    def _fix_parameter_schemas_descriptions(self, spec_dict: Dict[str, Any]) -> int:
        """Fix parameter schemas that lack descriptions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
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
                        if isinstance(param, dict) and "schema" in param:
                            schema = param["schema"]
                            if isinstance(schema, dict):
                                if self._fix_schema_object_descriptions(schema):
                                    fixes_applied += 1

        return fixes_applied

    def _fix_response_schemas_descriptions(self, spec_dict: Dict[str, Any]) -> int:
        """Fix response schemas that lack descriptions.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
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
                            # Fix response description
                            if "description" not in response:
                                response["description"] = (
                                    self._generate_response_description(status_code)
                                )
                                fixes_applied += 1

                            # Fix response content schemas
                            content = response.get("content", {})
                            if isinstance(content, dict):
                                for media_type, media_content in content.items():
                                    if (
                                        isinstance(media_content, dict)
                                        and "schema" in media_content
                                    ):
                                        schema = media_content["schema"]
                                        if isinstance(schema, dict):
                                            if self._fix_schema_object_descriptions(
                                                schema
                                            ):
                                                fixes_applied += 1

        return fixes_applied

    def _fix_schema_object_descriptions(self, schema: Dict[str, Any]) -> bool:
        """Fix a single schema object by adding missing descriptions recursively.

        Args:
            schema: Schema dictionary to fix

        Returns:
            True if any fixes were applied, False otherwise
        """
        fixes_applied = False

        # Add description if missing
        if "description" not in schema:
            schema["description"] = self._generate_schema_description(schema)
            fixes_applied = True

        # Recursively fix nested schemas
        if "properties" in schema and isinstance(schema["properties"], dict):
            for prop_name, prop_schema in schema["properties"].items():
                if isinstance(prop_schema, dict):
                    if self._fix_schema_object_descriptions(prop_schema):
                        fixes_applied = True

        # Fix array items
        if "items" in schema and isinstance(schema["items"], dict):
            if self._fix_schema_object_descriptions(schema["items"]):
                fixes_applied = True

        # Fix composition schemas (allOf, oneOf, anyOf)
        for composition_key in ["allOf", "oneOf", "anyOf"]:
            if composition_key in schema and isinstance(schema[composition_key], list):
                for sub_schema in schema[composition_key]:
                    if isinstance(sub_schema, dict):
                        if self._fix_schema_object_descriptions(sub_schema):
                            fixes_applied = True

        # Fix additional properties
        if "additionalProperties" in schema and isinstance(
            schema["additionalProperties"], dict
        ):
            if self._fix_schema_object_descriptions(schema["additionalProperties"]):
                fixes_applied = True

        return fixes_applied

    def _generate_schema_description(self, schema: Dict[str, Any]) -> str:
        """Generate a meaningful description for a schema based on its properties.

        Args:
            schema: Schema dictionary

        Returns:
            Generated description string
        """
        # Try to infer description from schema structure
        schema_type = schema.get("type", "unknown")

        if "properties" in schema:
            prop_count = len(schema["properties"])
            return f"Object with {prop_count} properties"
        elif schema_type == "array" and "items" in schema:
            items_type = schema["items"].get("type", "items")
            return f"Array of {items_type}"
        elif "enum" in schema:
            enum_count = len(schema["enum"])
            return f"Enumeration with {enum_count} possible values"
        elif schema_type != "unknown":
            return f"{schema_type.capitalize()} value"
        else:
            return "Schema definition"

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

    def fix_toolset_specific_errors(self, spec_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Fix errors that are specific to OpenAPIToolset creation.

        Args:
            spec_dict: OpenAPI specification dictionary

        Returns:
            Fixed specification dictionary
        """
        fixed_spec = deepcopy(spec_dict)

        # Ensure all referenced schemas exist
        self._ensure_referenced_schemas_exist(fixed_spec)

        # Fix circular references
        self._fix_circular_references(fixed_spec)

        # Ensure proper schema structure
        self._ensure_proper_schema_structure(fixed_spec)

        return fixed_spec

    def _ensure_referenced_schemas_exist(self, spec_dict: Dict[str, Any]) -> None:
        """Ensure all referenced schemas exist in definitions or components.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        # Collect all $ref references
        refs = set()
        self._collect_refs(spec_dict, refs)

        # Check if definitions/components contain all referenced schemas
        definitions = spec_dict.get("definitions", {})
        components_schemas = spec_dict.get("components", {}).get("schemas", {})

        for ref in refs:
            if ref.startswith("#/definitions/"):
                schema_name = ref.replace("#/definitions/", "")
                if schema_name not in definitions:
                    definitions[schema_name] = {
                        "type": "object",
                        "description": f"Auto-generated schema for {schema_name}",
                        "properties": {},
                    }
                    self.logger.debug(f"Created missing definition: {schema_name}")
            elif ref.startswith("#/components/schemas/"):
                schema_name = ref.replace("#/components/schemas/", "")
                if schema_name not in components_schemas:
                    if "components" not in spec_dict:
                        spec_dict["components"] = {}
                    if "schemas" not in spec_dict["components"]:
                        spec_dict["components"]["schemas"] = {}

                    spec_dict["components"]["schemas"][schema_name] = {
                        "type": "object",
                        "description": f"Auto-generated schema for {schema_name}",
                        "properties": {},
                    }
                    self.logger.debug(
                        f"Created missing component schema: {schema_name}"
                    )

    def _collect_refs(self, obj: Any, refs: set) -> None:
        """Recursively collect all $ref references in the specification.

        Args:
            obj: Object to search for references
            refs: Set to collect references
        """
        if isinstance(obj, dict):
            if "$ref" in obj:
                refs.add(obj["$ref"])
            for value in obj.values():
                self._collect_refs(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_refs(item, refs)

    def _fix_circular_references(self, spec_dict: Dict[str, Any]) -> None:
        """Fix circular references in schema definitions.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        # This is a simplified approach - in practice, you might need more sophisticated
        # circular reference detection and resolution
        definitions = spec_dict.get("definitions", {})

        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                self._break_circular_refs_in_schema(def_schema, def_name, set())

    def _break_circular_refs_in_schema(
        self, schema: Dict[str, Any], current_def: str, visited: set
    ) -> None:
        """Break circular references in a specific schema.

        Args:
            schema: Schema to check for circular references
            current_def: Current definition name
            visited: Set of visited definitions
        """
        if current_def in visited:
            # Circular reference detected - replace with a simple reference
            schema.clear()
            schema.update(
                {
                    "type": "object",
                    "description": f"Circular reference to {current_def}",
                    "properties": {},
                }
            )
            return

        visited.add(current_def)

        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_name = schema["$ref"].replace("#/definitions/", "")
                if ref_name == current_def:
                    # Direct self-reference
                    schema.clear()
                    schema.update(
                        {
                            "type": "object",
                            "description": f"Self-reference to {current_def}",
                            "properties": {},
                        }
                    )
            else:
                for value in schema.values():
                    if isinstance(value, (dict, list)):
                        self._break_circular_refs_in_schema(
                            value, current_def, visited.copy()
                        )

    def _ensure_proper_schema_structure(self, spec_dict: Dict[str, Any]) -> None:
        """Ensure all schemas have proper structure for toolset creation.

        Args:
            spec_dict: OpenAPI specification dictionary
        """
        # Fix definitions
        definitions = spec_dict.get("definitions", {})
        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                self._normalize_schema_for_toolset(def_schema)

        # Fix components
        components = spec_dict.get("components", {})
        if isinstance(components, dict):
            schemas = components.get("schemas", {})
            for schema_name, schema_def in schemas.items():
                if isinstance(schema_def, dict):
                    self._normalize_schema_for_toolset(schema_def)

    def _normalize_schema_for_toolset(self, schema: Dict[str, Any]) -> None:
        """Normalize a schema for toolset compatibility.

        Args:
            schema: Schema dictionary to normalize
        """
        # Ensure description exists
        if "description" not in schema:
            schema["description"] = ""

        # Ensure type is present where needed
        if "type" not in schema and "$ref" not in schema:
            if "properties" in schema:
                schema["type"] = "object"
            elif "items" in schema:
                schema["type"] = "array"
            elif "enum" in schema:
                schema["type"] = "string"  # Default for enums
            else:
                schema["type"] = "object"  # Safe default

        # Recursively normalize nested schemas
        if "properties" in schema and isinstance(schema["properties"], dict):
            for prop_schema in schema["properties"].values():
                if isinstance(prop_schema, dict):
                    self._normalize_schema_for_toolset(prop_schema)

        if "items" in schema and isinstance(schema["items"], dict):
            self._normalize_schema_for_toolset(schema["items"])

        # Handle composition schemas
        for composition_key in ["allOf", "oneOf", "anyOf"]:
            if composition_key in schema and isinstance(schema[composition_key], list):
                for sub_schema in schema[composition_key]:
                    if isinstance(sub_schema, dict):
                        self._normalize_schema_for_toolset(sub_schema)
