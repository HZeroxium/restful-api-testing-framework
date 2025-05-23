import json
import yaml
import os

"""
  Load and read OpenAPI from JSON/YAML
"""


def get_ref(spec: dict, ref: str):
    sub = ref[2:].split("/")
    schema = spec
    for e in sub:
        schema = schema.get(e, {})
    return schema


def load_openapi(path):
    """
    Break the openapi spec into semantic parts
    ---
    Input:
        path: path to the openapi spec
    """
    # Check if file is existed
    if not os.path.exists(path):
        print(f"File {path} is not existed")
        return None

    if path.endswith(".yml") or path.endswith(".yaml"):
        # Read YAML file
        with open(path, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    elif path.endswith(".json"):
        # Read JSON file
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"File {path} is not supported. Must be in YAML or JSON format.")
        return None
