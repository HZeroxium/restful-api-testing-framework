from oas_parser.helpers import find_object_with_key


success_code = lambda x: 200 <= x < 300

"""
  Process endpoint, method, and response code
"""


def extract_operations(spec):
    """
    Currently work well with OAS 3.0
    """
    operations = []
    paths = spec["paths"]
    valid_methods = [
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "head",
        "options",
        "trace",
    ]
    for path in paths:
        for method in paths[path]:
            if method.startswith("x-") or method not in valid_methods:
                continue
            operations.append(method + "-" + path)

    return operations


def isSuccessStatusCode(x):
    if isinstance(x, int):
        return success_code(x)
    elif isinstance(x, str):
        return x.isdigit() and success_code(int(x))
    return False


def contains_required_parameters(operation, origin_spec):
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    obj = origin_spec["paths"][path][method]
    parameters_obj = find_object_with_key(obj, "parameters")
    if parameters_obj is None:
        return False
    parameters_obj = str(parameters_obj["parameters"])
    return "'required': True" in parameters_obj
