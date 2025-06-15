from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class OperationDependency(BaseModel):
    """Represents a dependency between operations."""

    source_operation: str = Field(..., description="The source operation (dependent)")
    target_operation: str = Field(..., description="The target operation (dependency)")
    reason: str = Field(..., description="Why this dependency exists")
    data_mapping: Dict[str, Any] = Field(
        default_factory=dict, description="How data maps between operations"
    )


class OperationSequence(BaseModel):
    """Represents a sequence of operations to execute in order."""

    id: str = Field(..., description="Unique identifier for the sequence")
    name: str = Field(..., description="Name of the sequence")
    description: str = Field(..., description="Description of what this sequence tests")
    operations: List[str] = Field(
        ..., description="List of operations in execution order"
    )
    dependencies: List[OperationDependency] = Field(
        default_factory=list, description="Dependencies between operations"
    )


class OperationSequencerInput(BaseModel):
    """Input for OperationSequencerTool."""

    endpoints: List[Any] = Field(..., description="List of endpoints to analyze")
    collection_name: Optional[str] = Field(
        None, description="Name of the test collection"
    )
    include_data_mapping: bool = Field(
        True, description="Whether to include data mapping details"
    )


class OperationSequencerOutput(BaseModel):
    """Output from OperationSequencerTool."""

    sequences: List[OperationSequence] = Field(
        ..., description="List of operation sequences"
    )
    total_sequences: int = Field(..., description="Total number of sequences")
    result: Dict[str, Any] = Field(..., description="Summary of the sequencing result")
