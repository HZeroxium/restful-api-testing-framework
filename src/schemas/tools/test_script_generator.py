# schemas/tools/test_script_generator.py

from pydantic import BaseModel, Field
from typing import List, Optional

from .openapi_parser import EndpointInfo
from .constraint_miner import ApiConstraint


class TestScriptGeneratorInput(BaseModel):
    """Input for TestScriptGeneratorTool."""

    endpoint_info: EndpointInfo
    constraints: List[ApiConstraint] = Field(
        description="Constraints mined from the endpoint for validation"
    )


class ValidationScript(BaseModel):
    """Validation script for a test case."""

    id: str
    name: str
    script_type: str  # 'request', 'response', 'status_code', etc.
    validation_code: str
    description: str
    constraint_id: Optional[str] = None


class TestScriptGeneratorOutput(BaseModel):
    """Output from TestScriptGeneratorTool."""

    validation_scripts: List[ValidationScript]
