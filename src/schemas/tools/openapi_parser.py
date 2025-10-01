# schemas/tools/openapi_parser.py

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from schemas.core.base_tool import ToolInput, ToolOutput


class SpecSourceType(str, Enum):
    """Source type for OpenAPI specification."""

    FILE = "file"
    URL = "url"
    JSON = "json"
    YAML = "yaml"


class AuthType(str, Enum):
    """Authentication type."""

    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    BEARER = "bearer"


class EndpointInfo(BaseModel):
    """Information about an API endpoint."""

    name: str = Field(..., description="Name of the endpoint")
    description: Optional[str] = Field(None, description="Description of the endpoint")
    path: str = Field(..., description="Path of the endpoint")
    method: str = Field(..., description="HTTP method for the endpoint")
    tags: List[str] = Field(default_factory=list, description="Tags for the endpoint")
    auth_required: bool = Field(False, description="Whether authentication is required")
    auth_type: Optional[AuthType] = Field(
        None, description="Authentication type if required"
    )
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Schema for request"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Schema for response"
    )

    # Additional fields for database storage (optional)
    id: Optional[str] = Field(None, description="Unique identifier for the endpoint")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class OpenAPIParserInput(ToolInput):
    """Input for OpenAPI parser tool."""

    spec_source: str = Field(
        ..., description="Path/URL to OpenAPI spec file or JSON/YAML content"
    )
    source_type: SpecSourceType = Field(
        default=SpecSourceType.FILE, description="Type of spec source"
    )
    filter_tags: Optional[List[str]] = Field(
        default=None, description="Filter endpoints by tags"
    )
    filter_paths: Optional[List[str]] = Field(
        default=None, description="Filter endpoints by paths"
    )
    filter_methods: Optional[List[str]] = Field(
        default=None, description="Filter endpoints by HTTP methods"
    )


class OpenAPIParserOutput(ToolOutput):
    """Output from OpenAPI parser tool."""

    title: str = Field(..., description="Title of the API")
    version: str = Field(..., description="Version of the API")
    description: Optional[str] = Field(None, description="Description of the API")
    endpoints: List[EndpointInfo] = Field(
        default_factory=list, description="API endpoints"
    )
    endpoint_count: int = Field(..., description="Number of endpoints")
    servers: List[str] = Field(default_factory=list, description="API server URLs")
    result: Dict[str, Any] = Field(..., description="The parsed OpenAPI specification")
