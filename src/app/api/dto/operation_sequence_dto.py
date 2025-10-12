# app/api/dto/operation_sequence_dto.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from schemas.core.pagination import PaginationMetadata
from schemas.tools.operation_sequencer import OperationSequence


class GenerateSequencesRequest(BaseModel):
    """Request for generating operation sequences."""

    override_existing: bool = Field(
        default=True, description="Whether to override existing sequences"
    )


class OperationSequenceResponse(BaseModel):
    """Response for a single operation sequence."""

    id: str = Field(..., description="Unique identifier for the sequence")
    name: str = Field(..., description="Name of the sequence")
    description: str = Field(..., description="Description of what this sequence tests")
    operations: List[str] = Field(
        ..., description="List of operations in execution order"
    )
    dependencies: List[Dict[str, Any]] = Field(
        default_factory=list, description="Dependencies between operations"
    )
    sequence_type: str = Field(..., description="Type of sequence")
    priority: int = Field(..., description="Execution priority")
    estimated_duration: Optional[float] = Field(
        None, description="Estimated duration in seconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional sequence metadata"
    )

    @classmethod
    def from_sequence(cls, seq: OperationSequence) -> "OperationSequenceResponse":
        """Create response from OperationSequence."""
        return cls(
            id=seq.id,
            name=seq.name,
            description=seq.description,
            operations=seq.operations,
            dependencies=[dep.model_dump() for dep in seq.dependencies],
            sequence_type=seq.sequence_type,
            priority=seq.priority,
            estimated_duration=seq.estimated_duration,
            metadata=seq.metadata or {},
        )


class OperationSequenceListResponse(BaseModel):
    """Response for list of sequences."""

    sequences: List[OperationSequenceResponse] = Field(
        ..., description="List of operation sequences"
    )
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")


class GenerateSequencesResponse(BaseModel):
    """Response for sequence generation."""

    dataset_id: str = Field(..., description="Dataset ID")
    total_endpoints: int = Field(..., description="Total number of endpoints analyzed")
    sequences_generated: int = Field(..., description="Number of sequences generated")
    analysis_method: str = Field(..., description="Analysis method used")
    graph: Optional[Dict[str, Any]] = Field(
        None, description="Dependency graph representation"
    )
    sequences: List[OperationSequenceResponse] = Field(
        ..., description="Generated sequences"
    )
    result: Dict[str, Any] = Field(..., description="Detailed generation results")


class DependencyGraphResponse(BaseModel):
    """Response for dependency graph."""

    nodes: List[Dict[str, Any]] = Field(..., description="List of operation nodes")
    edges: List[Dict[str, Any]] = Field(..., description="List of dependency edges")
    metadata: Dict[str, Any] = Field(..., description="Graph metadata")


class UpdateSequenceRequest(BaseModel):
    """Request for updating a sequence."""

    name: Optional[str] = Field(None, description="Updated sequence name")
    description: Optional[str] = Field(None, description="Updated sequence description")
    operations: Optional[List[str]] = Field(None, description="Updated operations list")
    sequence_type: Optional[str] = Field(None, description="Updated sequence type")
    priority: Optional[int] = Field(None, description="Updated priority")
    estimated_duration: Optional[float] = Field(
        None, description="Updated estimated duration"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class SequenceStatisticsResponse(BaseModel):
    """Response for sequence statistics."""

    total_sequences: int = Field(..., description="Total number of sequences")
    sequences_by_type: Dict[str, int] = Field(
        ..., description="Count of sequences by type"
    )
    sequences_with_dependencies: int = Field(
        ..., description="Number of sequences with dependencies"
    )
    average_operations_per_sequence: float = Field(
        ..., description="Average number of operations per sequence"
    )
    sequences_by_priority: Dict[int, int] = Field(
        ..., description="Count of sequences by priority"
    )


class SequenceValidationResponse(BaseModel):
    """Response for sequence validation."""

    is_valid: bool = Field(..., description="Whether the sequence is valid")
    errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
