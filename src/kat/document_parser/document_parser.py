import copy
import os# This script is used to parse the OpenAPI specification file and extract the information about the API.
import json
import re
import sys
import os

# Thêm thư mục gốc vào sys.path (để import được Dataset và config)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from kat.document_parser.config import *  # hoặc chỉ import cần thiết
# Read the OpenAPI specification file and return a dictionary of the file.
def get_swagger_spec(openapi_path):
    with open(openapi_path, "r") as file:
        data = file.read()
    return json.loads(data)

def write_anything_to_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as file:
        file.write(data)

# Extract the endpoints from the OpenAPI specification file.
# data is a dictionary of the OpenAPI specification file.
def extract_endpoints(spec):
    '''
    Currently work well with OAS 3.0
    '''
    endpoints = []
    paths = spec['paths']
    valid_methods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']
    for path in paths:
        for method in paths[path]:
            if method.startswith('x-') or method not in valid_methods:
                continue
            endpoints.append(method + '-' + path)
    
    return endpoints

def get_endpoints_details_list(swagger_spec):
    endpoints_spec = {}
    for path in swagger_spec.get("paths"):
        for method in swagger_spec.get("paths").get(path):
            if method.startswith('x-') or method not in valid_methods:
                continue
            endpoints_spec[f"{method}-{path}"] = (
                swagger_spec.get("paths").get(path).get(method)
            )
    return endpoints_spec

def get_delete_operation_store(endpoint_data): 
    def any_elements_exist_in_list(A, B):
        for element in A:
            if element in B:
                return True
        return False

    delete_operation_store = {}
    delete_operation_filter = [endpoint for endpoint in endpoint_data.keys() if endpoint.split('-')[0] == 'delete' and 'parameters' in endpoint_data[endpoint]]

    for endpoint in endpoint_data.keys():
        delete_operation_store[endpoint] = []
        if 'parameters' not in endpoint_data[endpoint]:
            continue
        for delete_operation in delete_operation_filter:
            if any_elements_exist_in_list(endpoint_data[endpoint]['parameters'].keys(), endpoint_data[delete_operation]['parameters'].keys()):
                delete_operation_store[endpoint].append(delete_operation)
    return delete_operation_store

def get_schemas_from_spec(swagger_spec):
    schemas_spec = {}
    for k, v in swagger_spec.get("components", {}).get("schemas", {}).items():
        schemas_spec[k] = v
    return schemas_spec
def get_response_status_codes_from_endpoint_spec(endpoint_spec):
    return list(endpoint_spec.get("responses").keys())


def get_relevant_schemas_name_from_one_endpoint(endpoint_spec, schemas_spec):
    schemas_name = []
    endpoint_spec_str = json.dumps(endpoint_spec)
    for schema_name, schema_spec in schemas_spec.items():
        if f"#/components/schemas/{schema_name}" in endpoint_spec_str:
            schemas_name.append(schema_name)
    is_new = True
    while is_new == True:
        is_new = False
        temp = set()
        for name in schemas_name:
            for schema_name, schema_spec in schemas_spec.items():
                if f"#/components/schemas/{schema_name}" in json.dumps(schemas_spec[name]):
                    if schema_name not in schemas_name:
                        is_new = True
                        temp.add(schema_name)
        schemas_name.extend(list(temp))
    return schemas_name


def get_endpoint_data(swagger_spec: dict, endpoint: str):
    """
    Get the endpoint data from the Swagger spec. 

    Args:
        swagger_spec (dict): Swagger spec
        endpoint (str): Endpoint to get data. <method>-<path>

    Returns:
        dict: {
            "method": "GET" | "POST" | ...,
            "path": str,
            "definition": { ... "parameters": [...], "requestBody": ... },
            "responses": {...},
        }
    """
    method = endpoint.split('-')[0].lower()
    object_name = '-'.join(endpoint.split('-')[1:])

    path_item = copy.deepcopy(swagger_spec['paths'][object_name])          # path-level object
    method_def = copy.deepcopy(path_item[method])                          # operation-level object
    responses = method_def.get('responses', {})
    if 'responses' in method_def:
        del method_def['responses']

    # --- Merge path-level + operation-level parameters ---
    path_params = path_item.get('parameters', []) or []
    operation_params = method_def.get('parameters', []) or []

    merged = {}
    # path-level trước, operation-level sau (op-level override)
    for p in path_params + operation_params:
        # Luôn copy parameter để tránh modify object gốc
        param_copy = copy.deepcopy(p)
        key = (param_copy.get('name'), param_copy.get('in'))
        
        # BẢO ĐẢM: path params luôn required=True theo OpenAPI spec
        if param_copy.get('in') == 'path':
            param_copy['required'] = True
            
        merged[key] = param_copy

    if merged:
        method_def['parameters'] = list(merged.values())
    else:
        # Không có tham số nào
        method_def['parameters'] = []

    # dọn path_item cho gọn (không bắt buộc)
    if method in path_item:
        del path_item[method]

    return {
        "method": method.upper(),
        "path": object_name,
        "definition": method_def,
        "responses": responses,
    }

def get_all_reference_schema_path_in_endpoint_object(swagger_spec, endpoint_data, exclude_response=True):
    """
    Recursively collect all referenced schemas' paths in the endpoint data.

    Args:
        swagger_spec (dict): Swagger data
        endpoint (str): endpoint data. <method>-<path>
        exclude_response (bool): Defaults to True.

    Returns:
        list[str]: list of all referenced schema's paths
    """
    return_paths_set = set()
    visited_paths_set = set()

    stack = [endpoint_data]
    
    while stack:
        current_data = stack.pop()
        stack_string = json.dumps(current_data)
        if exclude_response:
            if r"'responses'" in stack_string: stack_string = stack_string.split(r"'responses'")[0]
            elif r'"responses"' in stack_string: stack_string = stack_string.split(r'"responses"')[0]
            elif r'responses' in stack_string: stack_string = stack_string.split(r'responses')[0]

        matches = re.findall(r'"\$ref": ".*?"', stack_string)

        for match in matches:
            path = match.split(": ")[1].replace('"', '')
            if path not in visited_paths_set:
                visited_paths_set.add(path)
                return_paths_set.add(path)
                paths = path.split("/")[1:]
                obj = swagger_spec
                for p in paths:
                    try:
                        obj = obj[p]
                    except KeyError:
                        # Handle the case where the path does not exist in the swagger_spec
                        print(f"Warning: Reference path {path} not found in swagger_spec.")
                        obj = None
                        break
                if obj is not None:
                    stack.append(obj)

    return list(return_paths_set)
def get_object_from_path(swagger_spec, paths_list):
    # đệ quy để lấy object từ swagger_spec
    if not paths_list:
        return swagger_spec
    
    removed_path = paths_list[0]

    try:
        return get_object_from_path(swagger_spec[removed_path], paths_list[1:])
    except:
        return None
def find_path_to_target(json_schema, schema_name, target_field, current_path=""):
    if isinstance(json_schema, dict):
        for key, value in json_schema.items():
            if key == "schema of " + schema_name or key == "array of " + schema_name + " objects":
                if isinstance(value, dict) and target_field in value:
                    return f"{current_path}.{target_field}"
                elif isinstance(value, list) and isinstance(value[0], dict):
                    for index, item in enumerate(value):
                        if target_field in item:
                            return f"{current_path}[{index}].{target_field}"
            elif isinstance(value, dict):
                new_path = f"{current_path}.{key}" if current_path else key
                result = find_path_to_target(value, schema_name, target_field, new_path)
                if result:
                    return result
            elif isinstance(value, list) and all(isinstance(i, dict) for i in value):
                for index, item in enumerate(value):
                    new_path = f"{current_path}.{key}[{index}]"
                    result = find_path_to_target(item, schema_name, target_field, new_path)
                    if result:
                        return result
    return None
def extract_endpoints_simplified_swagger_spec(simplified_swagger, sequence):
    if isinstance(sequence, list):
        endpoints_info = ""
        for i, endpoint in enumerate(sequence[:-1]):
            if endpoint != "":
                if "responseBody" in simplified_swagger[endpoint]:
                    endpoints_info += f"\nRequired endpoint {i+1}: `{endpoint}` \n\"responseBody\" (binded by the variable: response_{i+1}):\n{json.dumps(simplified_swagger[endpoint]['responseBody'])}\n"
                else:
                    endpoints_info += f"\nRequired endpoint {i+1}: `{endpoint}` \n\"responseBody\": null"
                
        # we do not mind the target endpoint's response body
        target_endpoint_spec = copy.deepcopy(simplified_swagger[sequence[-1]])
        if "responseBody" in target_endpoint_spec:
            del target_endpoint_spec["responseBody"]
        endpoints_info += f"\nTarget endpoint: `{sequence[-1]}` \n{json.dumps(target_endpoint_spec)}"    
        return endpoints_info
    else:
        target_endpoint_spec = copy.deepcopy(simplified_swagger[sequence])
        if "responseBody" in target_endpoint_spec:
            del target_endpoint_spec["responseBody"]
        return f"\nTarget endpoint: `{sequence}` \n{json.dumps(target_endpoint_spec)}" if sequence != "" else ""

# for spec_name in list_data_set_name:

#     path_input = "Dataset/" + spec_name + "/openapi.json"
#     path_output = "TestData/" + spec_name + "/document_parser/endpoints.json"

#     swagger_spec = get_swagger_spec(path_input)
#     endpoints_list = extract_endpoints(swagger_spec)
#     endpoints_detail_list = get_endpoints_details_list(swagger_spec)
#     schemas = get_schemas_from_spec(swagger_spec)

#     # Lấy response code cho mỗi endpoint
#     endpoint_status_codes = {
#         ep: get_response_status_codes_from_endpoint_spec(spec)
#         for ep, spec in endpoints_detail_list.items()
#     }
#     relevant_schemas_per_endpoint = {
#         ep: get_relevant_schemas_name_from_one_endpoint(spec, schemas)
#         for ep, spec in endpoints_detail_list.items()
#     }
#     # Tạo cấu trúc JSON mô tả output của từng function
#     final_output = {
#         "read_swagger_data": {
#             "description": "Parse OpenAPI JSON file into a Python dict",
#             "output": "Parsed successfully ✅"
#         },
#         "extract_endpoints": {
#             "description": "List of endpoints in method-path format",
#             "output": endpoints_list
#         },
#         "get_endpoints_details": {
#             "description": "Details of each endpoint including parameters, responses, etc.",
#             "output": endpoints_detail_list
#         },
#         "get_schemas_from_spec": {
#             "description": "All schemas under components.schemas",
#             "output": list(schemas.keys())  # chỉ in tên cho gọn
#         },
#         "get_response_status_codes_from_endpoint_spec": {
#             "description": "Response status codes (200, 404, etc.) per endpoint",
#             "output": endpoint_status_codes
#         },
#         "get_relevant_schemas_name": {
#             "description": "Relevant schemas name",
#             "output": relevant_schemas_per_endpoint
#         }
#     }

#     # Ghi ra file
#     write_anything_to_file(path_output, json.dumps(final_output, indent=4))


# print("Done")