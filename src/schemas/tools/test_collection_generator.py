# schemas/tools/test_collection_generator.py

from pydantic import BaseModel, Field
from typing import List, Optional

from .openapi_parser import EndpointInfo
from .test_suite_generator import TestSuite


class TestCollection(BaseModel):
    """A collection of test suites across multiple endpoints."""

    name: str
    description: Optional[str] = None
    test_suites: List[TestSuite]


class TestCollectionGeneratorInput(BaseModel):
    """Input for TestCollectionGeneratorTool."""

    api_name: str
    api_version: str
    endpoints: List[EndpointInfo]
    test_case_count: int = Field(1, description="Number of test cases per endpoint")
    include_invalid_data: bool = Field(
        False, description="Whether to include invalid test data"
    )


class TestCollectionGeneratorOutput(BaseModel):
    """Output from TestCollectionGeneratorTool."""

    test_collection: TestCollection
