"""
Pydantic schemas for constraint mining and verification.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ConstraintType(str, Enum):
    """Types of constraints that can be extracted."""

    INPUT_PARAMETER = "input_parameter"
    RESPONSE_PROPERTY = "response_property"
    REQUEST_RESPONSE = "request_response"


class ParameterLocation(str, Enum):
    """Location of parameters in API operations."""

    PARAMETERS = "parameters"
    REQUEST_BODY = "requestBody"


class ConstraintStatus(str, Enum):
    """Status of constraint validation."""

    VALID = "yes"
    INVALID = "no"
    PENDING = "pending"


class ParameterConstraint(BaseModel):
    """Constraint for input parameters."""

    operation: str = Field(..., description="Operation identifier (method-path)")
    location: ParameterLocation = Field(..., description="Parameter location")
    parameter_name: str = Field(..., description="Name of the parameter")
    data_type: str = Field(..., description="Data type of the parameter")
    description: str = Field(..., description="Parameter description")
    constraint_description: Optional[str] = Field(
        None, description="Extracted constraint description"
    )


class ResponsePropertyConstraint(BaseModel):
    """Constraint for response properties."""

    schema_name: str = Field(..., description="Name of the response schema")
    property_name: str = Field(..., description="Name of the property")
    data_type: str = Field(..., description="Data type of the property")
    description: str = Field(..., description="Property description")
    constraint_description: Optional[str] = Field(
        None, description="Extracted constraint description"
    )


class RequestResponseMapping(BaseModel):
    """Mapping between request parameters and response properties."""

    operation: str = Field(..., description="Operation identifier")
    parameter_location: ParameterLocation = Field(
        ..., description="Location of the parameter"
    )
    parameter_name: str = Field(..., description="Name of the request parameter")
    schema_name: str = Field(..., description="Name of the response schema")
    property_name: str = Field(..., description="Name of the response property")
    confidence: float = Field(
        default=1.0, description="Confidence score of the mapping"
    )


class ConstraintExtractionResult(BaseModel):
    """Result of constraint extraction process."""

    service_name: str = Field(..., description="Name of the API service")
    input_parameter_constraints: Dict[str, Dict[str, Dict[str, str]]] = Field(
        default_factory=dict, description="Input parameter constraints by operation"
    )
    response_property_constraints: Dict[str, Dict[str, str]] = Field(
        default_factory=dict, description="Response property constraints by schema"
    )
    request_response_mappings: Dict[str, Dict[str, List[List[str]]]] = Field(
        default_factory=dict, description="Request-response mappings"
    )


class ConstraintValidationItem(BaseModel):
    """Item for constraint validation tracking."""

    identifier: List[Union[str, List[str]]] = Field(
        ..., description="Constraint identifier"
    )
    status: ConstraintStatus = Field(..., description="Validation status")
    validation_details: Optional[str] = Field(
        None, description="Additional validation details"
    )


class MiningProgress(BaseModel):
    """Progress tracking for constraint mining."""

    total_operations: int = Field(..., description="Total number of operations")
    completed_operations: int = Field(
        default=0, description="Number of completed operations"
    )
    current_operation: Optional[str] = Field(
        None, description="Current operation being processed"
    )
    progress_percentage: float = Field(default=0.0, description="Progress percentage")


class MiningConfiguration(BaseModel):
    """Configuration for constraint mining."""

    save_and_load: bool = Field(
        default=False, description="Whether to save and load progress"
    )
    experiment_folder: str = Field(
        default="experiment", description="Folder for experiment results"
    )
    selected_operations: Optional[List[str]] = Field(
        None, description="Specific operations to process"
    )
    selected_schemas: Optional[List[str]] = Field(
        None, description="Specific schemas to process"
    )
    max_retries: int = Field(
        default=3, description="Maximum number of retries for failed operations"
    )
