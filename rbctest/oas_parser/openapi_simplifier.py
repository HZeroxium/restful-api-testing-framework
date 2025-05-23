from oas_parser.helpers import find_object_with_key
from oas_parser.operation_utils import extract_operations, isSuccessStatusCode
from oas_parser.schema_parser import get_schema_params
from oas_parser.spec_loader import get_ref

import copy

"""
Simplify the openapi spec
"""


def simplify_openapi(openapi: dict):
    operations = extract_operations(openapi)
    simple_openapi = {}

    for operation in operations:
        method = operation.split("-")[0]
        path = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(openapi["paths"][path][method])

        simple_operation_spec = {}

        if "summary" in obj:
            simple_operation_spec["summary"] = obj["summary"]

        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}

            for param in params:
                if "$ref" in param:
                    param = get_ref(openapi, param["$ref"])

                # get description string
                description_string = ""
                description_parent = find_object_with_key(param, "description")
                if description_parent and not isinstance(
                    description_parent["description"], dict
                ):
                    description_string = (
                        " (description: "
                        + description_parent["description"].strip(" .")
                        + ")"
                    )

                name, dtype = None, None
                name_parent = find_object_with_key(param, "name")
                type_parent = find_object_with_key(param, "type")
                param_schema_parent = find_object_with_key(param, "$ref")

                if name_parent:
                    name = name_parent["name"]
                if type_parent:
                    dtype = type_parent["type"]

                if name is not None and param_schema_parent is not None:
                    param_schema = get_ref(openapi, param_schema_parent["$ref"])
                    param_entry[name] = get_schema_params(param_schema, openapi)
                elif name is not None and dtype is not None:
                    param_entry[name] = dtype + description_string

            if param_entry:
                simple_operation_spec["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}

            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                body_entry = get_schema_params(
                    request_body_schema, openapi, get_description=True
                )

            if body_entry:
                simple_operation_spec["requestBody"] = body_entry

        # responseBody (single response body)
        if "responses" in obj or "response" in obj:
            response_entry = {}

            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"]
                else:
                    responses = obj["response"]

                success_response = None

                for rk, rv in responses.items():
                    if isSuccessStatusCode(rk):
                        success_response = rv
                        break

                if success_response is not None:
                    response_entry = get_schema_params(
                        success_response, openapi, get_description=True
                    )

                if response_entry:
                    simple_operation_spec["responseBody"] = response_entry

        simple_openapi[operation] = simple_operation_spec

    return simple_openapi
