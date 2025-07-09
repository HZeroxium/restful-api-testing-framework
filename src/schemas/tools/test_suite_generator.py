# schemas/tools/test_suite_generator.py

from pydantic import BaseModel, Field
from typing import List, Optional

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_case_generator import TestCase
from schemas.tools.test_data_generator import TestData
from schemas.tools.constraint_miner import ApiConstraint


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
    test_data_collection: Optional[List[TestData]] = Field(
        default=None, description="Pre-generated test data to use"
    )
    constraints: Optional[List[ApiConstraint]] = Field(
        default=None, description="Constraints for test case generation"
    )
    api_name: Optional[str] = Field(
        default=None, description="API name for test suite metadata"
    )
    api_version: Optional[str] = Field(
        default=None, description="API version for test suite metadata"
    )
    test_case_count: int = Field(1, description="Number of test cases to generate")
    include_invalid_data: bool = Field(
        False, description="Whether to include invalid test data"
    )


class TestSuiteGeneratorOutput(BaseModel):
    """Output from TestSuiteGeneratorTool."""

    test_suite: TestSuite
