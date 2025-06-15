"""
OpenAPI specification loader module.
"""

import json
import yaml
import os
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """
    Check if the given string is a valid URL.

    Args:
        url: String to check

    Returns:
        True if the string is a valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def load_spec_from_url(url: str) -> Dict[str, Any]:
    """
    Load an OpenAPI specification from a URL.

    Args:
        url: URL of the OpenAPI specification

    Returns:
        Parsed OpenAPI specification as a dictionary

    Raises:
        ValueError: If the URL is invalid or the request fails
        JSONDecodeError: If the response is not valid JSON
    """
    if not is_valid_url(url):
        raise ValueError(f"Invalid URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            return response.json()
        elif "application/yaml" in content_type or "application/x-yaml" in content_type:
            return yaml.safe_load(response.text)
        else:
            # Try to guess the format
            try:
                return response.json()
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(response.text)
                except yaml.YAMLError:
                    raise ValueError(
                        f"Could not parse response as JSON or YAML from {url}"
                    )
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {str(e)}")


def load_openapi(path: str) -> Optional[Dict[str, Any]]:
    """
    Load and read OpenAPI specification from a file.

    Args:
        path: Path to the OpenAPI specification file (JSON or YAML)

    Returns:
        Parsed OpenAPI specification as a dictionary, or None if the file doesn't exist
        or is in an unsupported format
    """
    # Check if file exists
    if not os.path.exists(path):
        print(f"File {path} does not exist")
        return None

    if path.endswith(".yml") or path.endswith(".yaml"):
        # Read YAML file
        with open(path, "r", encoding="utf-8") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML file {path}: {exc}")
                return None

    elif path.endswith(".json"):
        # Read JSON file
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as exc:
                print(f"Error parsing JSON file {path}: {exc}")
                return None
    else:
        print(f"File {path} is not supported. Must be in YAML or JSON format.")
        return None


def get_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """
    Resolve a reference in an OpenAPI specification.

    Args:
        spec: OpenAPI specification dictionary
        ref: Reference string (e.g., "#/components/schemas/Pet")

    Returns:
        The referenced object or an empty dict if not found
    """
    if not ref.startswith("#/"):
        return {}

    sub = ref[2:].split("/")
    schema = spec
    for e in sub:
        schema = schema.get(e, {})
    return schema
