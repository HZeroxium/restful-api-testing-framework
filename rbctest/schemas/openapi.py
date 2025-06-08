"""
Pydantic models for OpenAPI specifications and parser inputs/outputs.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class SpecSourceType(str, Enum):
    """Enumeration for OpenAPI specification source types."""

    FILE = "file"
    URL = "url"
    JSON = "json"
    YAML = "yaml"


class ServerInfo(BaseModel):
    """OpenAPI server information."""

    url: str
    description: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


class Parameter(BaseModel):
    """API endpoint parameter."""

    name: str
    in_location: str = Field(..., alias="in")
    required: bool = False
    description: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    example: Optional[Any] = None

    class Config:
        populate_by_name = True


class RequestBodyContent(BaseModel):
    """Content of a request body."""

    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    examples: Optional[Dict[str, Any]] = None
    example: Optional[Any] = None

    class Config:
        populate_by_name = True


class RequestBody(BaseModel):
    """API endpoint request body."""

    description: Optional[str] = None
    content: Optional[Dict[str, RequestBodyContent]] = None
    required: bool = False


class ResponseContent(BaseModel):
    """Content of a response."""

    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    examples: Optional[Dict[str, Any]] = None
    example: Optional[Any] = None

    class Config:
        populate_by_name = True


class Response(BaseModel):
    """API endpoint response."""

    description: str
    content: Optional[Dict[str, ResponseContent]] = None
    headers: Optional[Dict[str, Any]] = None


class EndpointInfo(BaseModel):
    """Information about an API endpoint."""

    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: Dict[str, Response] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    deprecated: bool = False
    security: Optional[List[Dict[str, List[str]]]] = None


class SchemaProperty(BaseModel):
    """Property of a schema."""

    type: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    example: Optional[Any] = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, "SchemaProperty"]] = None
    items: Optional[Union["SchemaProperty", Dict[str, Any]]] = None
    required: Optional[List[str]] = None
    ref: Optional[str] = Field(None, alias="$ref")

    class Config:
        populate_by_name = True


class SchemaObject(BaseModel):
    """Schema object in OpenAPI spec."""

    type: Optional[str] = None
    properties: Optional[Dict[str, SchemaProperty]] = None
    required: Optional[List[str]] = None
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None
    items: Optional[Union[SchemaProperty, Dict[str, Any]]] = None


class OpenAPISpec(BaseModel):
    """OpenAPI specification structure."""

    openapi: str
    info: Dict[str, Any]
    paths: Dict[str, Dict[str, Any]]
    components: Optional[Dict[str, Dict[str, Any]]] = None
    servers: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[Dict[str, Any]]] = None
    security: Optional[List[Dict[str, List[str]]]] = None


class OpenAPIParserInput(BaseModel):
    """Input parameters for the OpenAPI parser."""

    spec_source: str = Field(
        ...,
        description="Path to OpenAPI spec file, URL, or raw content",
    )
    spec_source_type: SpecSourceType = Field(
        default=SpecSourceType.FILE,
        description="Type of the specification source",
    )
    filter_paths: Optional[List[str]] = Field(
        default=None,
        description="List of paths to include (if None, include all)",
    )
    filter_methods: Optional[List[str]] = Field(
        default=None,
        description="List of HTTP methods to include (if None, include all)",
    )
    filter_tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags to include (if None, include all)",
    )
    include_deprecated: bool = Field(
        default=False,
        description="Whether to include deprecated endpoints",
    )


class SimplifiedEndpoint(BaseModel):
    """Simplified information about an API endpoint."""

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="API endpoint path")
    summary: Optional[str] = Field(None, description="Operation summary")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Request parameters")
    requestBody: Optional[Dict[str, Any]] = Field(
        None, description="Request body schema"
    )
    responseBody: Optional[Dict[str, Any]] = Field(
        None, description="Response body schema"
    )
    tags: List[str] = Field(default_factory=list)


class SimplifiedSchema(BaseModel):
    """Simplified schema representation."""

    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class OpenAPIParserOutput(BaseModel):
    """Output from the OpenAPI parser."""

    title: str
    version: str
    description: Optional[str] = None
    servers: List[str] = Field(default_factory=list)
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    simplified_endpoints: Dict[str, Any] = Field(default_factory=dict)
    simplified_schemas: Dict[str, Any] = Field(default_factory=dict)
    full_spec: Dict[str, Any] = Field(default_factory=dict)

    # Add alias for backward compatibility
    raw_spec: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        # Ensure raw_spec is populated with full_spec for backward compatibility
        if "full_spec" in data and "raw_spec" not in data:
            data["raw_spec"] = data["full_spec"]
        super().__init__(**data)
