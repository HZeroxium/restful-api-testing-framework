# utils/schema_utils.py

"""Utilities for handling schema dictionaries."""

from typing import Dict, Any, List, Optional, Union, TypedDict, Set
from enum import Enum


class SchemaType(str, Enum):
    """Enum representing possible schema types."""

    STRING = "STRING"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"
    NULL = "NULL"


class SchemaFormat(str, Enum):
    """Common schema formats."""

    DATE = "date"
    DATE_TIME = "date-time"
    UUID = "uuid"
    EMAIL = "email"
    URI = "uri"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    BYTE = "byte"
    BINARY = "binary"
    PASSWORD = "password"
    INT32 = "int32"
    INT64 = "int64"
    FLOAT = "float"
    DOUBLE = "double"


class PropertySchema(TypedDict, total=False):
    """TypedDict for property schema information."""

    type: str
    format: Optional[str]
    description: Optional[str]
    enum: Optional[List[Any]]
    minimum: Optional[Union[int, float]]
    maximum: Optional[Union[int, float]]
    minLength: Optional[int]
    maxLength: Optional[int]
    pattern: Optional[str]
    default: Optional[Any]
    example: Optional[Any]
    items: Optional["PropertySchema"]
    properties: Optional[Dict[str, "PropertySchema"]]
    required: Optional[List[str]]
    nullable: Optional[bool]


class MediaTypeSchema(TypedDict, total=False):
    """TypedDict for media type schema."""

    schema: PropertySchema


class ResponseSchema(TypedDict, total=False):
    """TypedDict for response schema."""

    description: str
    content: Dict[str, MediaTypeSchema]


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


def convert_openapi_type_to_schema_type(openapi_type: str) -> SchemaType:
    """Convert OpenAPI type string to SchemaType enum.

    Args:
        openapi_type: Type string from OpenAPI

    Returns:
        Corresponding SchemaType enum value
    """
    type_mapping = {
        "string": SchemaType.STRING,
        "number": SchemaType.NUMBER,
        "integer": SchemaType.INTEGER,
        "boolean": SchemaType.BOOLEAN,
        "array": SchemaType.ARRAY,
        "object": SchemaType.OBJECT,
        "null": SchemaType.NULL,
    }

    return type_mapping.get(openapi_type.lower(), SchemaType.STRING)


def extract_schema_properties(schema_obj: Any) -> PropertySchema:
    """Extract properties from a schema object with proper typing.

    Args:
        schema_obj: The schema object to extract properties from

    Returns:
        A PropertySchema with extracted properties
    """
    if not schema_obj:
        return {}

    result: PropertySchema = {}

    # Process basic properties with proper null checks
    if hasattr(schema_obj, "type") and schema_obj.type:
        result["type"] = convert_openapi_type_to_schema_type(schema_obj.type)

    if hasattr(schema_obj, "format") and schema_obj.format:
        result["format"] = schema_obj.format

    if hasattr(schema_obj, "description") and schema_obj.description:
        result["description"] = schema_obj.description

    # Handle constraints
    if hasattr(schema_obj, "enum") and schema_obj.enum:
        result["enum"] = schema_obj.enum

    # Numeric constraints
    if hasattr(schema_obj, "minimum") and schema_obj.minimum is not None:
        result["minimum"] = schema_obj.minimum

    if hasattr(schema_obj, "maximum") and schema_obj.maximum is not None:
        result["maximum"] = schema_obj.maximum

    # String constraints
    if hasattr(schema_obj, "minLength") and schema_obj.minLength is not None:
        result["minLength"] = schema_obj.minLength

    if hasattr(schema_obj, "maxLength") and schema_obj.maxLength is not None:
        result["maxLength"] = schema_obj.maxLength

    if hasattr(schema_obj, "pattern") and schema_obj.pattern:
        result["pattern"] = schema_obj.pattern

    # Example and default values
    if hasattr(schema_obj, "example") and schema_obj.example is not None:
        result["example"] = schema_obj.example

    if hasattr(schema_obj, "default") and schema_obj.default is not None:
        result["default"] = schema_obj.default

    # Handle object properties recursively
    if hasattr(schema_obj, "properties") and schema_obj.properties:
        properties: Dict[str, PropertySchema] = {}
        for prop_name, prop_schema in schema_obj.properties.items():
            prop_details = extract_schema_properties(prop_schema)
            if prop_details:  # Only add if there are details
                properties[prop_name] = prop_details

        if properties:
            result["properties"] = properties

    # Handle array items
    if hasattr(schema_obj, "items") and schema_obj.items:
        items_schema = extract_schema_properties(schema_obj.items)
        if items_schema:
            result["items"] = items_schema

    # Required properties
    if hasattr(schema_obj, "required") and schema_obj.required:
        result["required"] = schema_obj.required

    # Nullable
    if hasattr(schema_obj, "nullable") and schema_obj.nullable is not None:
        result["nullable"] = schema_obj.nullable

    return result


def extract_response_content(content_obj: Any) -> Dict[str, MediaTypeSchema]:
    """Extract content information from a response content object.

    Args:
        content_obj: Response content object

    Returns:
        Dictionary mapping content types to their schemas
    """
    if not content_obj:
        return {}

    content_schemas: Dict[str, MediaTypeSchema] = {}

    for content_type, media_type in content_obj.items():
        if hasattr(media_type, "schema_"):
            schema = extract_schema_properties(media_type.schema_)
            if schema:
                content_schemas[content_type] = {"schema": schema}

    return content_schemas


def extract_response_object(response_obj: Any) -> ResponseSchema:
    """Extract information from a response object.

    Args:
        response_obj: The response object

    Returns:
        ResponseSchema with description and content
    """
    response: ResponseSchema = {}

    # Extract description
    if hasattr(response_obj, "description"):
        response["description"] = response_obj.description

    # Extract content
    if hasattr(response_obj, "content") and response_obj.content:
        content = extract_response_content(response_obj.content)
        if content:
            response["content"] = content

    return response


def normalize_schema_type(raw_type: Any) -> SchemaType:
    """Normalize various schema type representations to a standard SchemaType enum.

    Args:
        raw_type: A type value that could be a string, enum, or other representation

    Returns:
        SchemaType enum value
    """
    if isinstance(raw_type, SchemaType):
        return raw_type

    if isinstance(raw_type, str):
        try:
            # Try direct conversion first
            return SchemaType(raw_type.upper())
        except ValueError:
            # If that fails, use the mapping function
            return convert_openapi_type_to_schema_type(raw_type)

    # Default to STRING for unknown types
    return SchemaType.STRING


def create_normalized_schema(
    schema: Dict[str, Any], processed_schemas: Optional[Set[int]] = None
) -> Dict[str, Any]:
    """Create a normalized schema with consistent types and structure.

    Args:
        schema: The schema to normalize
        processed_schemas: Set of object IDs that have been processed (for circular reference handling)

    Returns:
        Normalized schema dictionary
    """
    if processed_schemas is None:
        processed_schemas = set()

    # Guard against circular references
    schema_id = id(schema)
    if schema_id in processed_schemas:
        return {"type": "OBJECT", "description": "Circular reference detected"}

    processed_schemas.add(schema_id)

    result = {}

    # Normalize type
    if "type" in schema:
        result["type"] = normalize_schema_type(schema["type"])

    # Copy simple fields
    for field in [
        "description",
        "format",
        "pattern",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "example",
        "default",
    ]:
        if field in schema and schema[field] is not None:
            result[field] = schema[field]

    # Handle enum differently to ensure it's a list
    if "enum" in schema and schema["enum"] is not None:
        if isinstance(schema["enum"], list):
            result["enum"] = schema["enum"]
        else:
            result["enum"] = [schema["enum"]]

    # Handle properties recursively
    if "properties" in schema and isinstance(schema["properties"], dict):
        result["properties"] = {}
        for prop_name, prop_schema in schema["properties"].items():
            if isinstance(prop_schema, dict):
                result["properties"][prop_name] = create_normalized_schema(
                    prop_schema, processed_schemas
                )
            else:
                # Handle non-dict property schemas
                result["properties"][prop_name] = {"type": SchemaType.STRING}

    # Handle items for arrays
    if "items" in schema and isinstance(schema["items"], dict):
        result["items"] = create_normalized_schema(schema["items"], processed_schemas)

    # Copy required list
    if "required" in schema and isinstance(schema["required"], list):
        result["required"] = schema["required"]

    return result
