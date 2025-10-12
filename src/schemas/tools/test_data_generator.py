# schemas/tools/test_data_generator.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from schemas.tools.openapi_parser import EndpointInfo


class TestDataGeneratorInput(BaseModel):
    """Input for TestDataGeneratorTool."""

    endpoint_info: Union[EndpointInfo, Dict[str, Any]] = Field(
        ..., description="Endpoint information (can be EndpointInfo object or dict)"
    )
    test_case_count: int = Field(1, description="Number of test cases to generate")
    include_invalid_data: bool = Field(
        False, description="Whether to include invalid test data"
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def get_endpoint_info(self) -> EndpointInfo:
        """Convert endpoint_info to EndpointInfo object if it's a dict"""
        if isinstance(self.endpoint_info, dict):
            return EndpointInfo(**self.endpoint_info)
        return self.endpoint_info


class TestData(BaseModel):
    """Raw test data for a single test scenario."""

    id: str
    endpoint_id: str = Field(
        ..., description="ID of the endpoint this test data belongs to"
    )
    name: str
    description: str
    request_params: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[Any] = None
    expected_status_code: int
    expected_response_schema: Optional[Dict[str, Any]] = None
    expected_response_contains: Optional[List[str]] = None
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


class TestDataGeneratorOutput(BaseModel):
    """Output from TestDataGeneratorTool."""

    test_data_collection: List[TestData]


# TestCase class has been removed - use the one from schemas.tools.test_case
