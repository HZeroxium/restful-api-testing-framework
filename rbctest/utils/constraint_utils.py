"""
Utility functions for constraint processing.
"""

import re
from typing import Dict, Any, Optional, List


def extract_description_from_field(field_value: str) -> Optional[str]:
    """
    Extract description from a field value string.

    Args:
        field_value: Field value containing description

    Returns:
        Extracted description or None
    """
    if "(description:" not in field_value:
        return None

    return field_value.split("(description:")[-1][:-1].strip()


def extract_data_type_from_field(field_value: str) -> str:
    """
    Extract data type from a field value string.

    Args:
        field_value: Field value containing data type

    Returns:
        Extracted data type
    """
    return field_value.split("(description:")[0].strip()


def has_description(field_value: str) -> bool:
    """
    Check if a field value contains a description.

    Args:
        field_value: Field value to check

    Returns:
        True if description is present
    """
    return "(description:" in field_value


def extract_llm_answer(response: Optional[str]) -> Optional[str]:
    """
    Extract answer from LLM response.

    Args:
        response: LLM response text

    Returns:
        Extracted answer or None
    """
    if response is None:
        return None

    if "```answer" in response:
        pattern = r"```answer\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    return response.lower().strip()


def extract_corresponding_attribute(response: Optional[str]) -> str:
    """
    Extract corresponding attribute from LLM response.

    Args:
        response: LLM response text

    Returns:
        Extracted attribute name
    """
    if response is None:
        return ""

    pattern = r"```corresponding attribute\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        return match.group(1).strip().replace('"', "").replace("'", "")

    return ""


def filter_schema_by_data_type(
    schema_spec: Dict[str, Any], target_data_type: str
) -> Dict[str, Any]:
    """
    Filter schema attributes by data type.

    Args:
        schema_spec: Schema specification
        target_data_type: Target data type to filter by

    Returns:
        Filtered schema specification
    """
    if isinstance(schema_spec, str):
        data_type = extract_data_type_from_field(schema_spec)
        return schema_spec if data_type == target_data_type else {}

    if not isinstance(schema_spec, dict):
        return {}

    filtered_spec = {}

    for attribute, value in schema_spec.items():
        if isinstance(value, dict):
            filtered_value = filter_schema_by_data_type(value, target_data_type)
            if filtered_value:
                filtered_spec[attribute] = filtered_value
        elif isinstance(value, list) and value:
            filtered_value = filter_schema_by_data_type(value[0], target_data_type)
            if filtered_value:
                filtered_spec[attribute] = [filtered_value]
        elif isinstance(value, str):
            data_type = extract_data_type_from_field(value)
            if data_type == target_data_type:
                filtered_spec[attribute] = value

    return filtered_spec


def verify_attribute_in_schema(schema_spec: Dict[str, Any], attribute: str) -> bool:
    """
    Verify if an attribute exists in a schema.

    Args:
        schema_spec: Schema specification
        attribute: Attribute name to verify

    Returns:
        True if attribute exists in schema
    """
    if not isinstance(schema_spec, dict):
        return False

    for key, value in schema_spec.items():
        if key == attribute:
            return True

        if isinstance(value, dict):
            if verify_attribute_in_schema(value, attribute):
                return True
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            if verify_attribute_in_schema(value[0], attribute):
                return True

    return False


def find_common_fields(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> List[str]:
    """
    Find common field names between two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary

    Returns:
        List of common field names
    """
    return list(set(dict1.keys()) & set(dict2.keys()))
