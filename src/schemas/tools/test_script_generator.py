# schemas/tools/test_script_generator.py

from pydantic import BaseModel, Field
from typing import List

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_data_generator import TestData


class TestScriptGeneratorInput(BaseModel):
    """Input for TestScriptGeneratorTool."""

    endpoint_info: EndpointInfo
    test_data: TestData = Field(
        ..., description="Test data to generate validation scripts for"
    )


class ValidationScript(BaseModel):
    """Validation script for a test case."""

    id: str
    name: str
    script_type: str  # 'request', 'response', 'status_code', etc.
    validation_code: str
    description: str


class TestScriptGeneratorOutput(BaseModel):
    """Output from TestScriptGeneratorTool."""

    validation_scripts: List[ValidationScript]
