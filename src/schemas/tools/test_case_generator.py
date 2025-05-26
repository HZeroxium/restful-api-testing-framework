# schemas/tools/test_case_generator.py

from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_script_generator import ValidationScript
from schemas.tools.test_data_generator import TestData


class TestCase(BaseModel):
    """A test case with test data and validation scripts."""

    id: str
    name: str
    description: str
    request_params: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[Any] = None
    expected_status_code: int
    expected_response_schema: Optional[Dict[str, Any]] = None
    expected_response_contains: Optional[List[str]] = None
    validation_scripts: List[ValidationScript]


class TestCaseGeneratorInput(BaseModel):
    """Input for TestCaseGeneratorTool."""

    endpoint_info: EndpointInfo
    test_data: TestData  # Now using the TestData model directly
    name: Optional[str] = None
    description: Optional[str] = None


class TestCaseGeneratorOutput(BaseModel):
    """Output from TestCaseGeneratorTool."""

    test_case: TestCase
