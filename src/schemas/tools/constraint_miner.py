# schemas/tools/constraint_miner.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from schemas.tools.openapi_parser import EndpointInfo
from schemas.core.base_tool import ToolInput, ToolOutput


class ConstraintType(str, Enum):
    """Types of API constraints."""

    REQUEST_RESPONSE = "request_response"  # Constraints between request and response
    RESPONSE_PROPERTY = "response_property"  # Constraints on response properties


class ApiConstraint(BaseModel):
    """Represents a single API constraint."""

    id: str = Field(..., description="Unique identifier for the constraint")
    type: ConstraintType = Field(..., description="Type of constraint")
    description: str = Field(
        ..., description="Human-readable description of the constraint"
    )
    severity: str = Field(
        default="info", description="Severity level (info, warning, error)"
    )
    source: str = Field(
        ..., description="Source of the constraint (schema, examples, etc.)"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional constraint details"
    )


class StaticConstraintMinerInput(ToolInput):
    """Input for StaticConstraintMinerTool."""

    endpoint_info: EndpointInfo = Field(
        ..., description="Endpoint information to analyze"
    )
    include_examples: bool = Field(
        default=True, description="Whether to include examples in analysis"
    )
    include_schema_constraints: bool = Field(
        default=True, description="Whether to include schema-based constraints"
    )
    include_correlation_constraints: bool = Field(
        default=True, description="Whether to include correlated constraints"
    )


class StaticConstraintMinerOutput(ToolOutput):
    """Output from StaticConstraintMinerTool."""

    endpoint_method: str = Field(
        ..., description="HTTP method of the analyzed endpoint"
    )
    endpoint_path: str = Field(..., description="Path of the analyzed endpoint")
    request_response_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints between requests and responses"
    )
    response_property_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on response properties"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")
