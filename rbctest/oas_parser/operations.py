"""
OpenAPI operation and parameter processing functionality.
"""

import copy
from typing import Dict, Any, List

from .utils import find_object_with_key
from .schema import SchemaProcessor
from .loaders import get_ref


def extract_operations(spec: Dict[str, Any]) -> List[str]:
    """
    Extract all operations from an OpenAPI specification.

    Args:
        spec: OpenAPI specification

    Returns:
        List of operation identifiers in the format "method-path"
    """
    operations = []
    paths = spec.get("paths", {})

    for path in paths:
        for method in paths[path]:
            if method.startswith("x-") or method not in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
                "trace",
            ]:
                continue
            operations.append(f"{method}-{path}")

    return operations


def is_success_status_code(status_code: Any) -> bool:
    """
    Check if a status code represents a successful HTTP response (2xx).

    Args:
        status_code: Status code as string or integer

    Returns:
        True if the status code is in the 2xx range
    """
    if isinstance(status_code, int):
        return 200 <= status_code < 300
    elif isinstance(status_code, str) and status_code.isdigit():
        return 200 <= int(status_code) < 300
    return False


def contains_required_parameters(operation: str, spec: Dict[str, Any]) -> bool:
    """
    Check if an operation contains any required parameters.

    Args:
        operation: Operation identifier in the format "method-path"
        spec: OpenAPI specification

    Returns:
        True if the operation has required parameters, False otherwise
    """
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    obj = spec["paths"][path][method]
    parameters_obj = find_object_with_key(obj, "parameters")
    if parameters_obj is None:
        return False
    parameters_obj = str(parameters_obj["parameters"])
    return "'required': True" in parameters_obj


class OperationProcessor:
    """
    Processes and extracts information from OpenAPI operations.
    """

    def __init__(self, spec: Dict[str, Any]):
        """
        Initialize the operation processor.

        Args:
            spec: OpenAPI specification
        """
        self.spec = spec
        self.schema_processor = SchemaProcessor(spec)

    def extract_parameters(
        self, operation: Dict[str, Any], path_item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract parameters from an operation.

        Args:
            operation: Operation object
            path_item: Path item containing the operation

        Returns:
            List of parameter objects
        """
        # Combine path-level parameters with operation-level parameters
        parameters = []

        # Add path-level parameters
        if "parameters" in path_item:
            for param in path_item["parameters"]:
                # Resolve $ref if present
                if "$ref" in param:
                    param = get_ref(self.spec, param["$ref"])
                parameters.append(param)

        # Add operation-level parameters (these take precedence)
        if "parameters" in operation:
            operation_params = operation["parameters"]

            # For each operation parameter, check if it overrides a path parameter
            for op_param in operation_params:
                # Resolve $ref if present
                if "$ref" in op_param:
                    op_param = get_ref(self.spec, op_param["$ref"])

                # If it has a name, check for overrides
                if "name" in op_param and "in" in op_param:
                    # Check if this parameter overrides a path parameter
                    override = False
                    for i, path_param in enumerate(parameters):
                        if (
                            "name" in path_param
                            and "in" in path_param
                            and path_param["name"] == op_param["name"]
                            and path_param["in"] == op_param["in"]
                        ):
                            # Override the path parameter
                            parameters[i] = op_param
                            override = True
                            break

                    # If not an override, add it
                    if not override:
                        parameters.append(op_param)
                else:
                    # No name/in, just add it
                    parameters.append(op_param)

        return parameters

    def simplify_openapi(self) -> Dict[str, Any]:
        """
        Create a simplified version of the OpenAPI specification.

        Returns:
            Dictionary with simplified operations
        """
        operations = extract_operations(self.spec)
        simple_openapi = {}

        for operation in operations:
            method = operation.split("-")[0]
            path = "-".join(operation.split("-")[1:])

            # Ensure the path exists in the spec
            if path not in self.spec.get("paths", {}):
                continue
            if method not in self.spec["paths"][path]:
                continue

            obj = copy.deepcopy(self.spec["paths"][path][method])
            path_item = self.spec["paths"][path]

            simple_operation_spec = {"method": method, "path": path}

            if "summary" in obj:
                simple_operation_spec["summary"] = obj["summary"]

            # Process parameters - combine path and operation level parameters
            all_parameters = self.extract_parameters(obj, path_item)

            if all_parameters:
                param_entry = {}

                for param in all_parameters:
                    # Get description string
                    description_string = ""
                    if "description" in param and isinstance(param["description"], str):
                        description_string = (
                            " (description: " + param["description"].strip(" .") + ")"
                        )

                    name = param.get("name")
                    dtype = None

                    # Get type from schema or direct type field
                    if "schema" in param:
                        schema = param["schema"]
                        if "$ref" in schema:
                            ref_schema = get_ref(self.spec, schema["$ref"])
                            param_entry[name] = self.schema_processor.get_schema_params(
                                ref_schema
                            )
                        elif "type" in schema:
                            dtype = schema["type"]
                        else:
                            dtype = "object"
                    elif "type" in param:
                        dtype = param["type"]
                    else:
                        dtype = "string"  # Default type

                    if name and dtype:
                        param_entry[name] = dtype + description_string

                if param_entry:
                    simple_operation_spec["parameters"] = param_entry

            # Process requestBody
            if "requestBody" in obj:
                body_entry = {}

                schema_obj = find_object_with_key(obj["requestBody"], "schema")
                if schema_obj is not None:
                    request_body_schema = schema_obj["schema"]
                    body_entry = self.schema_processor.get_schema_params(
                        request_body_schema, get_description=True
                    )

                if body_entry:
                    simple_operation_spec["requestBody"] = body_entry

            # Process responseBody
            if "responses" in obj:
                response_entry = {}

                if method.lower() != "delete":
                    responses = obj["responses"]
                    success_response = None

                    for rk, rv in responses.items():
                        if is_success_status_code(rk):
                            success_response = rv
                            break

                    if success_response is not None:
                        response_entry = self.schema_processor.get_schema_params(
                            success_response, get_description=True
                        )

                    if response_entry:
                        simple_operation_spec["responseBody"] = response_entry

            simple_openapi[operation] = simple_operation_spec

        return simple_openapi

    def get_response_body_name_and_type(self, operation: str) -> tuple:
        """
        Get the main response schema name and type for an operation.

        Args:
            operation: Operation identifier in format "method-path"

        Returns:
            Tuple of (schema_name, response_type)
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

    def get_main_response_schemas_of_operation(self, operation: str) -> list:
        """
        Get the main response schema names for an operation.

        Args:
            operation: Operation identifier in format "method-path"

        Returns:
            List of main schema names
        """
        main_response_schemas = []
        method = operation.split("-")[0]
        path = "-".join(operation.split("-")[1:])

        operation_spec = self.spec["paths"][path][method]

        if "responses" in operation_spec:
            for response_code in operation_spec["responses"]:
                if is_success_status_code(response_code):
                    main_schema_ref = find_object_with_key(
                        operation_spec["responses"][response_code], "$ref"
                    )
                    if main_schema_ref:
                        main_response_schemas.append(
                            main_schema_ref["$ref"].split("/")[-1]
                        )

        return main_response_schemas


operation_processor = OperationProcessor({})  # Empty spec for compatibility
