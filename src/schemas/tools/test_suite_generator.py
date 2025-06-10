# schemas/tools/test_suite_generator.py

from pydantic import BaseModel, Field
from typing import List, Optional

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_case_generator import TestCase


class TestSuite(BaseModel):
    """A suite of test cases for a specific API endpoint."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    endpoint_info: EndpointInfo
    test_cases: List[TestCase]


class TestSuiteGeneratorInput(BaseModel):
    """Input for TestSuiteGeneratorTool."""

    endpoint_info: EndpointInfo
    test_case_count: int = Field(1, description="Number of test cases to generate")
    include_invalid_data: bool = Field(
        False, description="Whether to include invalid test data"
    )


class TestSuiteGeneratorOutput(BaseModel):
    """Output from TestSuiteGeneratorTool."""

    test_suite: TestSuite
