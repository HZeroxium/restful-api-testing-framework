"""
Extended schemas for OpenAPI processing.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SimplifiedParameter(BaseModel):
    """Simplified parameter representation."""

    name: str = Field(..., description="Parameter name")
    data_type: str = Field(..., description="Parameter data type")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")


class SimplifiedOperation(BaseModel):
    """Simplified operation representation."""

    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="API path")
    summary: Optional[str] = Field(None, description="Operation summary")
    parameters: Dict[str, str] = Field(
        default_factory=dict, description="Operation parameters"
    )
    request_body: Dict[str, Any] = Field(
        default_factory=dict, description="Request body schema"
    )
    response_body: Dict[str, Any] = Field(
        default_factory=dict, description="Response body schema"
    )


class SimplifiedSchema(BaseModel):
    """Simplified schema representation."""

    name: str = Field(..., description="Schema name")
    properties: Dict[str, str] = Field(
        default_factory=dict, description="Schema properties with descriptions"
    )


class OperationAnalysis(BaseModel):
    """Analysis result for an operation."""

    operation_id: str = Field(..., description="Operation identifier")
    has_parameters_with_description: bool = Field(
        default=False, description="Has parameters with descriptions"
    )
    has_request_body_with_description: bool = Field(
        default=False, description="Has request body with descriptions"
    )
    main_response_schemas: List[str] = Field(
        default_factory=list, description="Main response schema names"
    )
    all_response_schemas: List[str] = Field(
        default_factory=list, description="All related response schemas"
    )
