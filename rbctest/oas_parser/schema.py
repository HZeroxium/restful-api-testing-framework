"""
OpenAPI Schema processing functionality.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from .loaders import get_ref
from .utils import (
    find_object_with_key,
    extract_ref_values,
    extract_operations,
    is_success_status_code,
)
import copy


class SchemaProcessor:
    """
    Processes and extracts information from OpenAPI schema objects.
    """

    def __init__(self, spec: Dict[str, Any]):
        """
        Initialize the schema processor.

        Args:
            spec: OpenAPI specification
        """
        self.spec = spec

    def get_simplified_schema(self) -> Dict[str, Any]:
        """
        Get a simplified version of all schemas in the specification.

        Returns:
            Dictionary of simplified schemas
        """
        simplified_schema_dict = {}
        operations = extract_operations(self.spec)

        for operation in operations:
            method = operation.split("-")[0]
            object_name = "-".join(operation.split("-")[1:])
            obj = copy.deepcopy(self.spec["paths"][object_name][method])

            # Process success responses
            if "responses" in obj:
                responses = obj["responses"]
                for rk, rv in responses.items():
                    if is_success_status_code(rk):
                        schema_ref = find_object_with_key(rv, "$ref")
                        if schema_ref is None:
                            continue

                        simplified_schema, _ = self.get_schema_recursive(rv)
                        simplified_schema_dict.update(simplified_schema)

        return simplified_schema_dict

    def get_schema_params(
        self,
        body: Dict[str, Any],
        visited_refs: Optional[Set[str]] = None,
        get_description: bool = False,
        max_depth: Optional[int] = None,
        current_depth: int = 0,
        ignore_attr_with_schema_ref: bool = False,
    ) -> Any:
        """
        Process a schema and extract its parameters.

        Args:
            body: Schema body
            visited_refs: Set of visited references to prevent infinite recursion
            get_description: Whether to include descriptions
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
            ignore_attr_with_schema_ref: Whether to ignore attributes with schema references

        Returns:
            Processed schema parameters
        """
        if visited_refs is None:
            visited_refs = set()

        if max_depth is not None and current_depth > max_depth:
            return None

        properties = find_object_with_key(body, "properties")
        ref = find_object_with_key(body, "$ref")
        schema = find_object_with_key(body, "schema")

        new_schema = {}

        # Process object properties
        if properties:
            for p, prop_details in properties["properties"].items():
                p_ref = find_object_with_key(prop_details, "$ref")

                if p_ref and ignore_attr_with_schema_ref:
                    continue

                # Initialize the description string
                description_string = ""

                # Check the get_description flag
                if get_description:
                    description_parent = find_object_with_key(
                        prop_details, "description"
                    )
                    if description_parent and not isinstance(
                        description_parent["description"], dict
                    ):
                        description_string = (
                            " (description: "
                            + description_parent["description"].strip(" .")
                            + ")"
                        )

                if "type" in prop_details:
                    if prop_details["type"] == "array":
                        if p_ref:
                            new_schema[p] = {}
                            new_schema[p][
                                f'array of \'{p_ref["$ref"].split("/")[-1]}\' objects'
                            ] = [
                                self.get_schema_params(
                                    prop_details,
                                    visited_refs=visited_refs,
                                    get_description=get_description,
                                    max_depth=max_depth,
                                    current_depth=current_depth + 1,
                                )
                            ]
                        else:
                            new_schema[p] = {}
                            new_schema[p][
                                f'array of {prop_details["items"]["type"]} objects'
                            ] = [
                                self.get_schema_params(
                                    prop_details["items"],
                                    visited_refs=visited_refs,
                                    get_description=get_description,
                                    max_depth=max_depth,
                                    current_depth=current_depth + 1,
                                )
                            ]
                    else:
                        new_schema[p] = prop_details["type"] + description_string

                elif p_ref:
                    if p_ref["$ref"] in visited_refs:
                        new_schema[p] = {
                            f'schema of {p_ref["$ref"].split("/")[-1]}': {}
                        }
                        continue

                    visited_refs.add(p_ref["$ref"])
                    ref_schema = get_ref(self.spec, p_ref["$ref"])
                    child_schema = self.get_schema_params(
                        ref_schema,
                        visited_refs=visited_refs,
                        get_description=get_description,
                        max_depth=max_depth,
                        current_depth=current_depth + 1,
                    )
                    if child_schema is not None:
                        new_schema[p] = {}
                        new_schema[p][
                            f'schema of {p_ref["$ref"].split("/")[-1]}'
                        ] = child_schema

        # Process schema reference
        elif ref:
            if ref["$ref"] in visited_refs:
                return None

            visited_refs.add(ref["$ref"])
            ref_schema = get_ref(self.spec, ref["$ref"])
            new_schema = self.get_schema_params(
                ref_schema,
                visited_refs=visited_refs,
                get_description=get_description,
                max_depth=max_depth,
                current_depth=current_depth + 1,
            )

        # Process schema property
        elif schema:
            return self.get_schema_params(
                schema["schema"],
                visited_refs=visited_refs,
                get_description=get_description,
                max_depth=max_depth,
                current_depth=current_depth + 1,
            )

        # Return simple value for primitive types
        else:
            field_value = ""
            if body is not None and "type" in body:
                field_value = body["type"]

            if field_value != "":
                return field_value
            else:
                return None

        return new_schema

    def get_schema_required_fields(
        self, body: Dict[str, Any], visited_refs: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract required fields from a schema.

        Args:
            body: Schema body
            visited_refs: Set of visited references to prevent infinite recursion

        Returns:
            Dictionary of required fields
        """
        if visited_refs is None:
            visited_refs = set()

        properties = find_object_with_key(body, "properties")
        ref = find_object_with_key(body, "$ref")
        schema = find_object_with_key(body, "schema")

        required_fields = []
        required_fields_spec = find_object_with_key(body, "required")
        if required_fields_spec is None:
            if properties is not None:
                return {}
        else:
            required_fields = required_fields_spec["required"]

        new_schema = {}
        if properties:
            for p, prop_details in properties["properties"].items():
                if p not in required_fields:
                    continue

                p_ref = find_object_with_key(prop_details, "$ref")

                if "type" in prop_details:
                    if prop_details["type"] == "array":
                        if p_ref:
                            new_schema[p] = {}
                            new_schema[p] = self.get_schema_required_fields(
                                prop_details, visited_refs=visited_refs
                            )
                        else:
                            new_schema[p] = "array"
                    else:
                        new_schema[p] = prop_details["type"]

                elif p_ref:
                    if p_ref["$ref"] in visited_refs:
                        continue

                    visited_refs.add(p_ref["$ref"])
                    schema = get_ref(self.spec, p_ref["$ref"])
                    child_schema = self.get_schema_required_fields(
                        schema, visited_refs=visited_refs
                    )
                    if child_schema is not None:
                        new_schema[p] = child_schema

        elif ref:
            if ref["$ref"] in visited_refs:
                return None

            visited_refs.add(ref["$ref"])
            schema = get_ref(self.spec, ref["$ref"])
            new_schema = self.get_schema_required_fields(
                schema, visited_refs=visited_refs
            )
        else:
            return {}

        return new_schema

    def get_schema_recursive(
        self, body: Dict[str, Any], visited_refs: Optional[Set[str]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Recursively process a schema and its references.

        Args:
            body: Schema body
            visited_refs: Set of visited references to prevent infinite recursion

        Returns:
            Tuple containing:
                - Dictionary of processed schemas
                - List of schema names
        """
        if visited_refs is None:
            visited_refs = set()

        schema_dict = {}
        schema_name_list = []
        schema_refs = extract_ref_values(body)

        for ref in schema_refs:
            schema_name = ref.split("/")[-1]

            if ref not in visited_refs:
                visited_refs.add(ref)

                schema_body = get_ref(self.spec, ref)

                new_schema = self.get_schema_params(
                    schema_body,
                    get_description=True,
                    max_depth=0,
                    ignore_attr_with_schema_ref=False,
                )
                if isinstance(new_schema, dict):
                    schema_dict[schema_name] = new_schema
                    schema_name_list.append(schema_name)

                nested_schemas_body, nested_schemas_name = self.get_schema_recursive(
                    schema_body, visited_refs=visited_refs
                )
                schema_dict.update(nested_schemas_body)
                schema_name_list.extend(nested_schemas_name)

        return schema_dict, schema_name_list

    def get_relevant_schemas_of_operation(
        self, operation: str
    ) -> Tuple[List[str], List[str]]:
        """
        Get schemas related to the response of an operation.

        Args:
            operation: Operation identifier in the format "method-path"

        Returns:
            Tuple containing:
                - List of main response schemas
                - List of all relevant schemas
        """
        main_response_schemas = []
        relevant_schemas = []
        method = operation.split("-")[0]
        path = "-".join(operation.split("-")[1:])

        operation_spec = self.spec["paths"][path][method]

        if "responses" in operation_spec:
            for response_code in operation_spec["responses"]:
                if is_success_status_code(response_code):
                    _, new_relevant_schemas = self.get_schema_recursive(
                        operation_spec["responses"][response_code]
                    )
                    if new_relevant_schemas:
                        main_response_schemas.append(new_relevant_schemas[0])
                    relevant_schemas.extend(new_relevant_schemas)
        return list(set(main_response_schemas)), list(set(relevant_schemas))

    def get_response_body_name_and_type(
        self, operation: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the name and type of the response body schema for an operation.

        Args:
            operation: Operation identifier in the format "method-path"

        Returns:
            Tuple containing:
                - Schema name (or None)
                - Schema type (or None)
        """
        method = operation.split("-")[0]
        endpoint = "-".join(operation.split("-")[1:])

        operation_spec = self.spec["paths"][endpoint][method]
        if "responses" not in operation_spec and "response" not in operation_spec:
            return None, None

        response_spec = None
        if "responses" in operation_spec:
            response_spec = operation_spec["responses"]
        else:
            response_spec = operation_spec["response"]

        success_response = None
        for rk, rv in response_spec.items():
            if is_success_status_code(rk):
                success_response = rv
                break

        if success_response is None:
            return None, None

        response_type = None
        main_response_schema = None

        schema = find_object_with_key(success_response, "schema")
        if schema:
            response_type = schema["schema"].get("type", "object")

        properties = find_object_with_key(success_response, "properties")
        if properties:
            return None, response_type

        main_schema_ref = find_object_with_key(success_response, "$ref")
        if main_schema_ref:
            schema_name = main_schema_ref["$ref"].split("/")[-1]
            return schema_name, response_type

        return None, response_type


schema_processor = SchemaProcessor({})  # Empty spec for compatibility
