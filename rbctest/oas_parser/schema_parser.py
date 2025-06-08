from oas_parser.helpers import find_object_with_key, extract_ref_values
from oas_parser.loaders import get_ref
from oas_parser.operation_utils import extract_operations, is_success_status_code

import copy


def get_simplified_schema(
    spec: dict,
):
    simplified_schema_dict = {}

    operations = extract_operations(spec)

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]

        # responseBody (single response body)
        if "responses" in obj:
            responses = obj["responses"]
            success_response = None
            for rk, rv in responses.items():
                if is_success_status_code(rk):
                    success_response = rv

                    schema_ref = find_object_with_key(success_response, "$ref")
                    if schema_ref is None:
                        continue

                    simplified_schema, _ = get_schema_recursive(success_response, spec)
                    simplified_schema_dict.update(simplified_schema)

    return simplified_schema_dict


def get_schema_params(
    body,
    spec,
    visited_refs=None,
    get_description=False,
    max_depth=None,
    current_depth=0,
    ignore_attr_with_schema_ref=False,
):
    if visited_refs is None:
        visited_refs = set()

    if max_depth:
        if current_depth > max_depth:
            return None

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")

    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            p_ref = find_object_with_key(prop_details, "$ref")

            if p_ref and ignore_attr_with_schema_ref:
                continue

            # Initialize the description string
            description_string = ""

            # Check the get_description flag
            if get_description:
                description_parent = find_object_with_key(prop_details, "description")
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
                            get_schema_params(
                                prop_details,
                                spec,
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
                            get_schema_params(
                                prop_details["items"],
                                spec,
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
                    new_schema[p] = {f'schema of {p_ref["$ref"].split("/")[-1]}': {}}
                    continue

                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_params(
                    schema,
                    spec,
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

    elif ref:
        if ref["$ref"] in visited_refs:
            return None

        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_params(
            schema,
            spec,
            visited_refs=visited_refs,
            get_description=get_description,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
    elif schema:
        return get_schema_params(
            schema["schema"],
            spec,
            visited_refs=visited_refs,
            get_description=get_description,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
    else:
        field_value = ""
        if body is not None and "type" in body:
            field_value = body["type"]

        if field_value != "":
            return field_value
        else:
            return None

    return new_schema


def get_schema_required_fields(body, spec, visited_refs=None):
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
                        new_schema[p] = get_schema_required_fields(
                            prop_details, spec, visited_refs=visited_refs
                        )
                    else:
                        new_schema[p] = "array"
                else:
                    new_schema[p] = prop_details["type"]

            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    continue

                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_required_fields(
                    schema, spec, visited_refs=visited_refs
                )
                if child_schema is not None:
                    new_schema[p] = child_schema

    elif ref:
        if ref["$ref"] in visited_refs:
            return None

        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_required_fields(schema, spec, visited_refs=visited_refs)
    else:
        return {}

    return new_schema


def get_required_fields(spec: dict):
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]

        operation_params_only_entry = {}

        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}

            for param in params:
                if "$ref" in param:
                    param = get_ref(spec, param["$ref"])

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
                        param_schema = get_ref(spec, param_schema_parent["$ref"])
                        param_entry[name] = get_schema_required_fields(
                            param_schema, spec
                        )
                    elif name is not None and dtype is not None:
                        param_entry[name] = dtype

            operation_params_only_entry["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                operation_params_only_entry["requestBody"] = get_schema_required_fields(
                    request_body_schema, spec
                )
            else:
                operation_params_only_entry["requestBody"] = {}
        else:
            operation_params_only_entry["requestBody"] = None

        operation_params_only_dict[operation] = (
            operation_params_only_entry  # dict[str, dict[str, ]
        )

    return operation_params_only_dict


def get_schema_recursive(body, spec, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    schema_dict = {}
    schema_name_list = []
    schema_refs = extract_ref_values(body)

    for ref in schema_refs:
        schema_name = ref.split("/")[-1]

        if ref not in visited_refs:  # Check if schema_name is already processed
            visited_refs.add(ref)

            schema_body = get_ref(
                spec, ref
            )  # Assuming get_ref is a function that retrieves the schema

            new_schema = get_schema_params(
                schema_body,
                spec,
                get_description=True,
                max_depth=0,
                ignore_attr_with_schema_ref=False,
            )  # Assuming get_schema_params is a function that processes the schema
            if isinstance(new_schema, dict):
                schema_dict[schema_name] = new_schema
                schema_name_list.append(schema_name)  # Add schema_name only if it's new

            nested_schemas_body, nested_schemas_name = get_schema_recursive(
                schema_body, spec, visited_refs=visited_refs
            )
            schema_dict.update(nested_schemas_body)
            schema_name_list.extend(nested_schemas_name)

    return schema_dict, schema_name_list


def get_relevant_schemas_of_operation(operation, openapi_spec):
    main_response_schemas = []
    relevant_schemas = []
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if is_success_status_code(response_code):
                _, new_relevant_schemas = get_schema_recursive(
                    operation_spec["responses"][response_code], openapi_spec
                )
                if new_relevant_schemas:
                    main_response_schemas.append(new_relevant_schemas[0])
                relevant_schemas.extend(new_relevant_schemas)
    return list(set(main_response_schemas)), list(set(relevant_schemas))
