from oas_parser.helpers import find_object_with_key
from oas_parser.operation_utils import extract_operations, is_success_status_code
from oas_parser.schema_parser import get_schema_params
from oas_parser.spec_loader import get_ref

import re
import copy

convert_path_fn = lambda x: re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", x))

"""
Analyze parameters and requestBody
"""


def get_operation_params(
    spec: dict,
    only_get_parameter_types: bool = False,
    get_not_required_params: bool = True,
    get_test_object: bool = False,
    insert_test_data_file_link: bool = False,
    get_description: bool = False,
    get_response_body: bool = True,
):
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]

        operation_params_only_entry = {}

        if "tags" in obj:
            operation_params_only_entry["tags"] = obj["tags"]
        if "summary" in obj:
            operation_params_only_entry["summary"] = obj["summary"]
        if "description" in obj:
            operation_params_only_entry["description"] = obj["description"]

        if get_test_object:
            if "test_object" in obj and obj["test_object"] is not None:
                operation_params_only_entry["test_object"] = obj["test_object"].strip(
                    "\n"
                )

        # parameters
        if "parameters" in obj and obj["parameters"]:
            if only_get_parameter_types == False:
                params = obj["parameters"]
                param_entry = {}

                if get_not_required_params:
                    for param in params:
                        if "$ref" in param:
                            param = get_ref(spec, param["$ref"])

                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(
                                param, "description"
                            )
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
                            param_schema = get_ref(spec, param_schema_parent["$ref"])
                            param_entry[name] = get_schema_params(param_schema, spec)
                        elif name is not None and dtype is not None:
                            param_entry[name] = dtype + description_string
                else:
                    for param in params:
                        if "$ref" in param:
                            param = get_ref(spec, param["$ref"])

                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(
                                param, "description"
                            )
                            if description_parent and not isinstance(
                                description_parent["description"], dict
                            ):
                                description_string = (
                                    " (description: "
                                    + description_parent["description"].strip(" .")
                                    + ")"
                                )

                        name, dtype, required = None, None, None
                        name_parent = find_object_with_key(param, "name")
                        type_parent = find_object_with_key(param, "type")
                        param_schema_parent = find_object_with_key(param, "$ref")

                        required_parent = find_object_with_key(param, "required")
                        if name_parent:
                            name = name_parent["name"]
                        if type_parent:
                            dtype = type_parent["type"]

                        required = False
                        if required_parent:
                            required = required_parent["required"]

                        if required:
                            if name is not None and param_schema_parent is not None:
                                param_schema = get_ref(
                                    spec, param_schema_parent["$ref"]
                                )
                                param_entry[name] = get_schema_params(
                                    param_schema, spec
                                )
                            elif name is not None and dtype is not None:
                                param_entry[name] = dtype + description_string
            else:
                # In detailed parameters mode, we will return the whole parameters object instead of just the name and type
                # Only keep 'name' and 'in' field
                param_entry = {}
                for param in obj["parameters"]:
                    if "name" in param and "in" in param:
                        if param["in"] == "path":
                            param_entry[param["name"]] = "PATH VARIABLE"
                        else:
                            param_entry[param["name"]] = "QUERY PARAMETER"

            if param_entry:
                operation_params_only_entry["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}

            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                if "$ref" in request_body_schema:
                    schema_name = request_body_schema["$ref"].split("/")[-1]
                    body_entry[f"schema of {schema_name}"] = get_schema_params(
                        request_body_schema, spec, get_description=get_description
                    )
                else:
                    body_entry = get_schema_params(
                        request_body_schema, spec, get_description=get_description
                    )

            if body_entry:
                operation_params_only_entry["requestBody"] = body_entry

        # responseBody (single response body)
        if get_response_body and ("responses" in obj or "response" in obj):
            response_entry = {}

            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"]
                else:
                    responses = obj["response"]

                success_response = None
                for rk, rv in responses.items():
                    if is_success_status_code(rk):
                        success_response = rv
                        break

                if success_response is not None:
                    schema_object_ref = find_object_with_key(success_response, "$ref")

                    if schema_object_ref is not None:
                        schema_name = schema_object_ref["$ref"].split("/")[-1]
                        response_entry[f"schema of {schema_name}"] = get_schema_params(
                            success_response, spec, get_description=get_description
                        )
                    else:
                        response_entry = get_schema_params(
                            success_response, spec, get_description=get_description
                        )

                if response_entry:
                    operation_params_only_entry["responseBody"] = response_entry

        if insert_test_data_file_link:
            test_data = {}
            try:
                operation_id = spec["paths"][object_name][method]["operationId"]
            except:
                operation_id = method.upper()
            unique_name = f"{convert_path_fn(object_name)}_{operation_id}"

            if (
                "parameters" in obj
                and obj["parameters"]
                and operation_params_only_entry["parameters"] is not None
            ):
                test_data["Parameter data"] = f"Data Files/{unique_name}_param"

            if (
                "requestBody" in obj
                and obj["requestBody"]
                and operation_params_only_entry["requestBody"] is not None
            ):
                test_data["Request body data"] = f"Data Files/{unique_name}_body"

            operation_params_only_entry["available_test_data"] = test_data

        operation_params_only_dict[operation] = (
            operation_params_only_entry  # dict[str, dict[str, ]
        )

    return operation_params_only_dict


def list_all_param_names(spec, d, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    if d is None:
        return []

    if "$ref" in d:
        ref = d["$ref"]
        if ref in visited_refs:
            return []
        visited_refs.add(ref)
        return list_all_param_names(spec, get_ref(spec, ref), visited_refs)

    if d.get("type") == "object":
        res = list(d.get("properties", {}).keys())
        for val in d.get("properties", {}).values():
            res += list_all_param_names(spec, val, visited_refs)
        return res
    elif d.get("type") == "array":
        return list_all_param_names(spec, d.get("items", {}), visited_refs)
    elif "name" in d:
        return [d.get("name")]
    else:
        return []


def filter_params_has_description(operation_param_description):
    """
    Filter out the parameters that do not have description
    This is for the purpose of detecting the inter-parameter dependencies. If a parameter does not have description, it is likely that it does not have any dependency.
    """
    filtered_operation_param_description = {}
    for operation in operation_param_description:
        filtered_operation_param_description[operation] = {}
        if (
            "parameters" in operation_param_description[operation]
            and operation_param_description[operation]["parameters"] is not None
        ):
            filtered_operation_param_description[operation]["parameters"] = {}
            for param, value in operation_param_description[operation][
                "parameters"
            ].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["parameters"][
                        param
                    ] = value
        if (
            "requestBody" in operation_param_description[operation]
            and operation_param_description[operation]["requestBody"] is not None
        ):
            filtered_operation_param_description[operation]["requestBody"] = {}
            for param, value in operation_param_description[operation][
                "requestBody"
            ].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["requestBody"][
                        param
                    ] = value
    return filtered_operation_param_description
