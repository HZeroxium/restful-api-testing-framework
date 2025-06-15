"""
Utility functions for the OpenAPI parser.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import re

# HTTP Methods that are valid in OpenAPI specs
VALID_HTTP_METHODS = [
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "trace",
]


def find_object_with_key(json_obj: Any, target_key: str) -> Optional[Dict[str, Any]]:
    """
    Find the first object in a nested structure that contains the specified key.

    Args:
        json_obj: JSON object to search in
        target_key: Key to search for

    Returns:
        The object containing the key, or None if not found
    """
    if isinstance(json_obj, dict):
        if target_key in json_obj:
            return json_obj
        for value in json_obj.values():
            result = find_object_with_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_object_with_key(item, target_key)
            if result is not None:
                return result
    return None


def extract_ref_values(json_obj: Any) -> List[str]:
    """
    Extract all $ref values from a JSON object.

    Args:
        json_obj: JSON object to extract references from

    Returns:
        List of unique reference strings
    """
    refs = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == "$ref":
                refs.append(value)
            else:
                refs.extend(extract_ref_values(value))
    elif isinstance(json_obj, list):
        for item in json_obj:
            refs.extend(extract_ref_values(item))

    return list(set(refs))


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
            if method.startswith("x-") or method not in VALID_HTTP_METHODS:
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


def convert_path_to_filename(path: str) -> str:
    """
    Convert a URL path to a valid filename.

    Args:
        path: URL path

    Returns:
        Valid filename
    """
    return re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", path))
