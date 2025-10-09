"""
DTOs for aggregator endpoints.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .constraint_dto import ConstraintResponse, MineConstraintsResponse
from .validation_script_dto import ValidationScriptResponse, GenerateScriptsResponse


class ConstraintsScriptsAggregatorResponse(BaseModel):
    """Response for the constraints and scripts aggregator endpoint."""

    endpoint_name: str = Field(..., description="Name of the endpoint")
    endpoint_id: str = Field(..., description="ID of the endpoint")

    # Constraint mining results
    constraints_result: MineConstraintsResponse = Field(
        ..., description="Result from constraint mining"
    )

    # Validation script generation results
    scripts_result: GenerateScriptsResponse = Field(
        ..., description="Result from validation script generation"
    )

    # Aggregated statistics
    total_constraints: int = Field(..., description="Total number of constraints mined")
    total_scripts: int = Field(..., description="Total number of scripts generated")
    total_execution_time: float = Field(
        ..., description="Total execution time in seconds"
    )
    
    # Override information
    deleted_constraints_count: int = Field(
        default=0, description="Number of existing constraints that were deleted"
    )
    deleted_scripts_count: int = Field(
        default=0, description="Number of existing validation scripts that were deleted"
    )

    # Status indicators
    constraints_mining_success: bool = Field(
        ..., description="Whether constraint mining was successful"
    )
    scripts_generation_success: bool = Field(
        ..., description="Whether script generation was successful"
    )
    overall_success: bool = Field(
        ..., description="Whether both operations were successful"
    )

    # Error information (if any)
    constraints_error: Optional[str] = Field(
        None, description="Error message from constraint mining"
    )
    scripts_error: Optional[str] = Field(None, description="Error message from script generation")

    # Metadata
    execution_timestamp: str = Field(
        ..., description="Timestamp when the operation was executed"
    )
