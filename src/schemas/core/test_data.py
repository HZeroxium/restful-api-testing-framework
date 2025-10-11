# schemas/core/test_data.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


class TestData(BaseModel):
    """Core test data entity for API testing."""

    id: str = Field(..., description="Unique identifier for test data")
    endpoint_id: str = Field(
        ..., description="ID of the endpoint this test data belongs to"
    )
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
    is_valid: bool = Field(
        True,
        description="Whether this is valid test data (true) or invalid test data (false)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp",
    )


class TestDataCollection(BaseModel):
    """Collection of test data for an endpoint."""

    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
    test_data_items: List[TestData] = Field(
        default_factory=list, description="List of test data items"
    )
    total_count: int = Field(0, description="Total number of test data items")
    valid_count: int = Field(0, description="Number of valid test data items")
    invalid_count: int = Field(0, description="Number of invalid test data items")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Collection creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Collection last update timestamp"
    )

    def __post_init__(self):
        """Calculate counts after initialization."""
        self.total_count = len(self.test_data_items)
        self.valid_count = sum(1 for item in self.test_data_items if item.is_valid)
        self.invalid_count = self.total_count - self.valid_count
