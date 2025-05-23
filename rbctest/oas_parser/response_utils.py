from oas_parser.helpers import find_object_with_key
from oas_parser.operation_utils import isSuccessStatusCode
from oas_parser.schema_parser import get_schema_recursive

"""
Analyze the response & response schema
"""


def get_main_response_schemas_of_operation(openapi_spec, operation):
    main_response_schemas = []

    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(
                    operation_spec["responses"][response_code], "$ref"
                )
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split("/")[-1])
    return main_response_schemas


def get_response_body_name_and_type(openapi, operation):
    method = operation.split("-")[0]
    endpoint = "-".join(operation.split("-")[1:])

    operation_spec = openapi["paths"][endpoint][method]
    if "responses" not in operation_spec and "response" not in operation_spec:
        return

    response_spec = None
    if "responses" in operation_spec:
        response_spec = operation_spec["responses"]
    else:
        response_spec = operation_spec["response"]

    success_response = None
    for rk, rv in response_spec.items():
        if isSuccessStatusCode(rk):
            success_response = rv
            break

    if success_response is None:
        return

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


def get_relevent_response_schemas_of_operation(openapi_spec, operation):
    main_response_schemas = []
    relevant_schemas = []

    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(
                    operation_spec["responses"][response_code], "$ref"
                )
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split("/")[-1])
                    _, new_relevant_schemas = get_schema_recursive(
                        operation_spec["responses"][response_code], openapi_spec
                    )
                    relevant_schemas.extend(new_relevant_schemas)
    return main_response_schemas, list(set(relevant_schemas))
