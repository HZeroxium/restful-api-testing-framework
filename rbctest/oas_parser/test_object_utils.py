import re

convert_path_fn = lambda x: re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", x))

"""
Process the test object to attach the OpenAPI
"""


def get_test_object_path(api_title, operation_id, path):
    return f"Object Repository/{convert_path_fn(api_title)}/{convert_path_fn(path)}/{operation_id}"


def add_test_object_to_openapi(openapi, object_repo_name="API"):
    """
    Add test object path to each of the operation's method in openapi Spec.

    Args:
        openapi (dict): openapi data
    """
    # Find the paths and method and add the new key-value pair of test_object
    for path in openapi["paths"]:
        for method in openapi["paths"][path]:
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            if object_repo_name == "API":
                try:
                    object_repo_name = openapi["info"]["title"]
                except:
                    pass

            try:
                operation_id = openapi["paths"][path][method]["operationId"]
            except:
                operation_id = method.upper()

            openapi["paths"][path][method]["test_object"] = get_test_object_path(
                object_repo_name, operation_id, path
            )
    return openapi
