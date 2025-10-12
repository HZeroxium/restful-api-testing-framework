# app/api/dto/constraint_dto.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from schemas.core.pagination import PaginationMetadata

from schemas.tools.constraint_miner import ApiConstraint, ConstraintType


class ConstraintCreateRequest(BaseModel):
    """Request for creating a new constraint."""

    endpoint_id: str = Field(..., description="ID of the endpoint")
    type: ConstraintType = Field(..., description="Type of constraint")
    description: str = Field(..., description="Constraint description")
    severity: str = Field(default="info", description="Severity level")
    source: str = Field(..., description="Source of the constraint")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Constraint details"
    )


class ConstraintResponse(BaseModel):
    """Response model for a constraint."""

    id: str
    endpoint_id: Optional[str] = None
    type: str
    description: str
    severity: str
    source: str
    details: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_constraint(cls, constraint: ApiConstraint) -> "ConstraintResponse":
        """Convert ApiConstraint to ConstraintResponse."""
        return cls(
            id=constraint.id,
            endpoint_id=constraint.endpoint_id,
            type=(
                constraint.type.value
                if isinstance(constraint.type, ConstraintType)
                else constraint.type
            ),
            description=constraint.description,
            severity=constraint.severity,
            source=constraint.source,
            details=constraint.details,
            created_at=constraint.created_at,
            updated_at=constraint.updated_at,
        )


class ConstraintListResponse(BaseModel):
    """Response model for a list of constraints."""

    constraints: List[ConstraintResponse]
    pagination: PaginationMetadata


class MineConstraintsRequest(BaseModel):
    """Request for mining constraints for an endpoint."""

    endpoint_id: str = Field(
        ..., description="ID of the endpoint to mine constraints for"
    )


class MineConstraintsResponse(BaseModel):
    """Response from mining constraints."""

    endpoint_id: str
    endpoint_method: str
    endpoint_path: str
    constraints: List[ConstraintResponse]
    request_param_constraints: List[ConstraintResponse]
    request_body_constraints: List[ConstraintResponse]
    response_property_constraints: List[ConstraintResponse]
    request_response_constraints: List[ConstraintResponse]
    total_constraints: int
    result: Dict[str, Any]

    @classmethod
    def from_miner_output(cls, output, endpoint_id: str) -> "MineConstraintsResponse":
        """Convert StaticConstraintMinerOutput to MineConstraintsResponse."""
        return cls(
            endpoint_id=endpoint_id,
            endpoint_method=output.endpoint_method,
            endpoint_path=output.endpoint_path,
            constraints=[
                ConstraintResponse.from_constraint(c) for c in output.constraints
            ],
            request_param_constraints=[
                ConstraintResponse.from_constraint(c)
                for c in output.request_param_constraints
            ],
            request_body_constraints=[
                ConstraintResponse.from_constraint(c)
                for c in output.request_body_constraints
            ],
            response_property_constraints=[
                ConstraintResponse.from_constraint(c)
                for c in output.response_property_constraints
            ],
            request_response_constraints=[
                ConstraintResponse.from_constraint(c)
                for c in output.request_response_constraints
            ],
            total_constraints=output.total_constraints,
            result=output.result,
        )
