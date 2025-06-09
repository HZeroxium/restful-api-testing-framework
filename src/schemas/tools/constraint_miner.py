# schemas/tools/constraint_miner.py

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Union

from schemas.tools.openapi_parser import EndpointInfo
from schemas.core.base_tool import ToolInput, ToolOutput


class ConstraintType(str, Enum):
    """Types of API constraints."""

    REQUEST_PARAM = "request_param"  # Constraints on request parameters
    REQUEST_BODY = "request_body"  # Constraints on request body
    RESPONSE_PROPERTY = "response_property"  # Constraints on response properties
    REQUEST_RESPONSE = "request_response"  # Constraints between request and response


# Keep the original flexible constraint detail types but with strict schema configuration
class ParameterConstraintDetails(BaseModel):
    """Details for parameter constraints."""

    parameter_name: str = Field(..., description="Name of the parameter")
    parameter_type: str = Field(
        ..., description="Type of parameter (query/path/header)"
    )
    constraint_type: str = Field(..., description="Type of constraint")
    validation_rule: str = Field(..., description="Validation rule identifier")
    allowed_values: Optional[List[str]] = Field(None, description="Allowed enum values")
    min_value: Optional[float] = Field(None, description="Minimum value")
    max_value: Optional[float] = Field(None, description="Maximum value")
    pattern: Optional[str] = Field(None, description="Regex pattern")
    expected_type: Optional[str] = Field(None, description="Expected data type")


class RequestBodyConstraintDetails(BaseModel):
    """Details for request body constraints."""

    field_path: str = Field(..., description="Path to the field in request body")
    constraint_type: str = Field(..., description="Type of constraint")
    validation_rule: str = Field(..., description="Validation rule identifier")
    required: Optional[bool] = Field(None, description="Whether field is required")
    data_type: Optional[str] = Field(None, description="Expected data type")
    format: Optional[str] = Field(None, description="Expected format")


class ResponsePropertyConstraintDetails(BaseModel):
    """Details for response property constraints."""

    property_path: str = Field(..., description="Path to property in response")
    constraint_type: str = Field(..., description="Type of constraint")
    validation_rule: str = Field(..., description="Validation rule identifier")
    applies_to_status: List[int] = Field(
        default_factory=list, description="Status codes this applies to"
    )
    data_type: Optional[str] = Field(None, description="Expected data type")
    format: Optional[str] = Field(None, description="Expected format")


class RequestResponseConstraintDetails(BaseModel):
    """Details for request-response correlation constraints."""

    request_element: str = Field(..., description="Request parameter/field name")
    request_location: str = Field(..., description="Location of request element")
    response_element: str = Field(..., description="Response property/status affected")
    constraint_type: str = Field(..., description="Type of correlation constraint")
    validation_rule: str = Field(..., description="Validation rule identifier")
    condition: Optional[str] = Field(None, description="Condition for the constraint")


# Keep ApiConstraint flexible for backward compatibility, but handle schema conversion internally
class ApiConstraint(BaseModel):
    """Represents a single API constraint."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional properties for backward compatibility

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
    # Keep as flexible Dict for backward compatibility
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Constraint-specific details"
    )


# Base input for all constraint miners
class BaseConstraintMinerInput(BaseModel):
    """Base input for constraint mining tools."""

    endpoint_info: EndpointInfo = Field(
        ..., description="Endpoint information to analyze"
    )
    include_examples: bool = Field(
        default=True, description="Whether to include examples in analysis"
    )


# Input schemas for specialized constraint miners (unchanged)
class RequestParamConstraintMinerInput(BaseConstraintMinerInput):
    """Input for RequestParamConstraintMinerTool."""

    focus_on_validation: bool = Field(
        default=True, description="Whether to focus on parameter validation constraints"
    )


class RequestBodyConstraintMinerInput(BaseConstraintMinerInput):
    """Input for RequestBodyConstraintMinerTool."""

    focus_on_schema: bool = Field(
        default=True, description="Whether to focus on schema-based constraints"
    )


class ResponsePropertyConstraintMinerInput(BaseConstraintMinerInput):
    """Input for ResponsePropertyConstraintMinerTool."""

    analyze_structure: bool = Field(
        default=True, description="Whether to analyze response structure constraints"
    )


class RequestResponseConstraintMinerInput(BaseConstraintMinerInput):
    """Input for RequestResponseConstraintMinerTool."""

    include_correlations: bool = Field(
        default=True, description="Whether to include request-response correlations"
    )
    analyze_status_codes: bool = Field(
        default=True, description="Whether to analyze status code patterns"
    )


# Output schemas for specialized constraint miners (unchanged)
class RequestParamConstraintMinerOutput(BaseModel):
    """Output from RequestParamConstraintMinerTool."""

    endpoint_method: str = Field(
        ..., description="HTTP method of the analyzed endpoint"
    )
    endpoint_path: str = Field(..., description="Path of the analyzed endpoint")
    param_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on request parameters"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")


class RequestBodyConstraintMinerOutput(BaseModel):
    """Output from RequestBodyConstraintMinerTool."""

    endpoint_method: str = Field(
        ..., description="HTTP method of the analyzed endpoint"
    )
    endpoint_path: str = Field(..., description="Path of the analyzed endpoint")
    body_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on request body"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")


class ResponsePropertyConstraintMinerOutput(BaseModel):
    """Output from ResponsePropertyConstraintMinerTool."""

    endpoint_method: str = Field(
        ..., description="HTTP method of the analyzed endpoint"
    )
    endpoint_path: str = Field(..., description="Path of the analyzed endpoint")
    response_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on response properties"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")


class RequestResponseConstraintMinerOutput(BaseModel):
    """Output from RequestResponseConstraintMinerTool."""

    endpoint_method: str = Field(
        ..., description="HTTP method of the analyzed endpoint"
    )
    endpoint_path: str = Field(..., description="Path of the analyzed endpoint")
    correlation_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints between requests and responses"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")


# Main orchestrator schemas (unchanged)
class StaticConstraintMinerInput(BaseModel):
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


class StaticConstraintMinerOutput(BaseModel):
    """Output from StaticConstraintMinerTool."""

    endpoint_method: str
    endpoint_path: str
    request_param_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on request parameters"
    )
    request_body_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on request body"
    )
    response_property_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints on response properties"
    )
    request_response_constraints: List[ApiConstraint] = Field(
        default_factory=list, description="Constraints between requests and responses"
    )
    total_constraints: int = Field(..., description="Total number of constraints found")
    result: Dict[str, Any] = Field(..., description="Summary of the mining results")
