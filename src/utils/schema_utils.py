# utils/schema_utils.py

"""Utilities for handling schema dictionaries."""

from typing import Dict, Any, List, Optional, Union


def clean_schema_dict(
    schema_dict: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Clean a schema dictionary by removing null-valued properties recursively.

    Args:
        schema_dict: Dictionary representation of a schema

    Returns:
        Cleaned dictionary with null values removed
    """
    if schema_dict is None:
        return None

    result = {}

    for key, value in schema_dict.items():
        # Skip null values
        if value is None:
            continue

        # Handle nested dictionaries recursively
        if isinstance(value, dict):
            cleaned_value = clean_schema_dict(value)
            if cleaned_value:  # Only add non-empty dictionaries
                result[key] = cleaned_value

        # Handle lists (might contain dictionaries)
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_item = clean_schema_dict(item)
                    if cleaned_item:  # Only add non-empty dictionaries
                        cleaned_list.append(cleaned_item)
                elif item is not None:
                    cleaned_list.append(item)

            if cleaned_list:  # Only add non-empty lists
                result[key] = cleaned_list

        # Add non-null primitives directly
        else:
            result[key] = value

    return result
