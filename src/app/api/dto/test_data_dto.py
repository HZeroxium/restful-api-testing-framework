# app/api/dto/test_data_dto.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


class GenerateTestDataRequest(BaseModel):
    """Request for generating test data."""

    count: int = Field(
        5, description="Number of test data items to generate", ge=1, le=20
    )
    include_invalid_data: bool = Field(
        True, description="Whether to include invalid test data"
    )
    override_existing: bool = Field(
        True, description="Whether to delete existing test data first"
    )


class TestDataResponse(BaseModel):
    """Response for a single test data item."""

    id: str = Field(..., description="Unique identifier")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    name: str = Field(..., description="Name of the test data")
    description: str = Field(..., description="Description of the test data")
    request_params: Optional[Dict[str, Any]] = Field(
        None, description="Request query parameters"
    )
    request_headers: Optional[Dict[str, str]] = Field(
        None, description="Request headers"
    )
    request_body: Optional[Any] = Field(None, description="Request body data")
    expected_status_code: int = Field(200, description="Expected HTTP status code")
    expected_response_schema: Optional[Dict[str, Any]] = Field(
        None, description="Expected response schema"
    )
    expected_response_contains: Optional[List[str]] = Field(
        None, description="Expected response content"
    )
    is_valid: bool = Field(True, description="Whether this is valid test data")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TestDataListResponse(BaseModel):
    """Response for a list of test data items."""

    test_data_items: List[TestDataResponse] = Field(
        default_factory=list, description="List of test data items"
    )
    total_count: int = Field(0, description="Total number of test data items")
    valid_count: int = Field(0, description="Number of valid test data items")
    invalid_count: int = Field(0, description="Number of invalid test data items")


class GenerateTestDataResponse(BaseModel):
    """Response for test data generation."""

    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
    test_data_items: List[TestDataResponse] = Field(
        default_factory=list, description="Generated test data items"
    )
    total_count: int = Field(0, description="Total number of generated test data items")
    valid_count: int = Field(0, description="Number of valid test data items")
    invalid_count: int = Field(0, description="Number of invalid test data items")
    generation_success: bool = Field(
        ..., description="Whether generation was successful"
    )
    deleted_existing_count: int = Field(
        0, description="Number of existing test data items that were deleted"
    )
    execution_timestamp: str = Field(
        ..., description="Timestamp when the operation was executed"
    )


class UpdateTestDataRequest(BaseModel):
    """Request for updating test data."""

    name: Optional[str] = Field(None, description="Name of the test data")
    description: Optional[str] = Field(None, description="Description of the test data")
    request_params: Optional[Dict[str, Any]] = Field(
        None, description="Request query parameters"
    )
    request_headers: Optional[Dict[str, str]] = Field(
        None, description="Request headers"
    )
    request_body: Optional[Any] = Field(None, description="Request body data")
    expected_status_code: Optional[int] = Field(
        None, description="Expected HTTP status code"
    )
    expected_response_schema: Optional[Dict[str, Any]] = Field(
        None, description="Expected response schema"
    )
    expected_response_contains: Optional[List[str]] = Field(
        None, description="Expected response content"
    )
    is_valid: Optional[bool] = Field(
        None, description="Whether this is valid test data"
    )
