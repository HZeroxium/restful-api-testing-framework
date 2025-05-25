# schemas/tools/test_data_generator.py

from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from schemas.tools.openapi_parser import EndpointInfo


class TestDataGeneratorInput(BaseModel):
    """Input for TestDataGeneratorTool."""

    endpoint_info: EndpointInfo
    test_case_count: int = 1
    include_invalid_data: bool = False


class TestCase(BaseModel):
    """A single test case with test data."""

    id: str
    name: str
    description: str
    request_params: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[Any] = None
    expected_status_code: int
    expected_response_schema: Optional[Dict[str, Any]] = None
    expected_response_contains: Optional[List[str]] = None


class TestDataGeneratorOutput(BaseModel):
    """Output from TestDataGeneratorTool."""

    test_cases: List[TestCase]
