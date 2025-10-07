# app/api/dto/endpoint_dto.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from schemas.tools.openapi_parser import EndpointInfo, AuthType, SpecSourceType


class EndpointCreateRequest(BaseModel):
    """Request model for creating an endpoint."""

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


class EndpointUpdateRequest(BaseModel):
    """Request model for updating an endpoint."""

    name: Optional[str] = Field(None, description="Name of the endpoint")
    description: Optional[str] = Field(None, description="Description of the endpoint")
    path: Optional[str] = Field(None, description="Path of the endpoint")
    method: Optional[str] = Field(None, description="HTTP method for the endpoint")
    tags: Optional[List[str]] = Field(None, description="Tags for the endpoint")
    auth_required: Optional[bool] = Field(
        None, description="Whether authentication is required"
    )
    auth_type: Optional[AuthType] = Field(
        None, description="Authentication type if required"
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="Schema for request"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        None, description="Schema for response"
    )


class EndpointResponse(BaseModel):
    """Response model for endpoint data."""

    id: str = Field(..., description="Unique identifier for the endpoint")
    name: str = Field(..., description="Name of the endpoint")
    description: Optional[str] = Field(None, description="Description of the endpoint")
    path: str = Field(..., description="Path of the endpoint")
    method: str = Field(..., description="HTTP method for the endpoint")
    tags: List[str] = Field(default_factory=list, description="Tags for the endpoint")
    auth_required: bool = Field(False, description="Whether authentication is required")
    auth_type: Optional[str] = Field(
        None, description="Authentication type if required"
    )
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Schema for request"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Schema for response"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @classmethod
    def from_endpoint_info(cls, endpoint: EndpointInfo) -> "EndpointResponse":
        """Create EndpointResponse from EndpointInfo."""
        return cls(
            id=getattr(endpoint, "id", ""),
            name=endpoint.name,
            description=endpoint.description,
            path=endpoint.path,
            method=endpoint.method,
            tags=endpoint.tags,
            auth_required=endpoint.auth_required,
            auth_type=endpoint.auth_type.value if endpoint.auth_type else None,
            input_schema=endpoint.input_schema,
            output_schema=endpoint.output_schema,
            created_at=getattr(endpoint, "created_at", None),
            updated_at=getattr(endpoint, "updated_at", None),
        )


class EndpointListResponse(BaseModel):
    """Response model for endpoint list."""

    endpoints: List[EndpointResponse] = Field(..., description="List of endpoints")
    total: int = Field(..., description="Total number of endpoints")
    page: int = Field(1, description="Current page number")
    size: int = Field(10, description="Page size")


class ParseSpecRequest(BaseModel):
    """Request model for parsing OpenAPI specification."""

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
        default=None, description="Filter endpoints by methods"
    )


class ParseSpecResponse(BaseModel):
    """Response model for parse specification result."""

    success: bool = Field(..., description="Whether parsing was successful")
    message: str = Field(..., description="Result message")
    api_title: Optional[str] = Field(None, description="Title of the API")
    api_version: Optional[str] = Field(None, description="Version of the API")
    total_endpoints: int = Field(0, description="Total number of endpoints found")
    created_endpoints: int = Field(0, description="Number of endpoints created")
    skipped_endpoints: int = Field(0, description="Number of endpoints skipped")
    endpoints: List[EndpointResponse] = Field(
        default_factory=list, description="Created endpoints"
    )


class EndpointStatsResponse(BaseModel):
    """Response model for endpoint statistics."""

    total_endpoints: int = Field(..., description="Total number of endpoints")
    method_distribution: Dict[str, int] = Field(
        ..., description="Distribution by HTTP method"
    )
    auth_type_distribution: Dict[str, int] = Field(
        ..., description="Distribution by auth type"
    )
    tag_distribution: Dict[str, int] = Field(..., description="Distribution by tags")
    last_updated: str = Field(..., description="Last update timestamp")


class SearchEndpointsRequest(BaseModel):
    """Request model for searching endpoints."""

    tag: Optional[str] = Field(None, description="Search by tag")
    path_pattern: Optional[str] = Field(None, description="Search by path pattern")
    method: Optional[str] = Field(None, description="Filter by HTTP method")
    auth_required: Optional[bool] = Field(
        None, description="Filter by auth requirement"
    )


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Error timestamp",
    )
