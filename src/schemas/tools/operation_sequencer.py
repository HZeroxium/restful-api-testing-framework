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


class OperationNode(BaseModel):
    """Represents a node in the dependency graph."""

    id: str = Field(..., description="Unique identifier for the node")
    operation: str = Field(..., description="Operation string (e.g., 'GET /brands')")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Endpoint path")
    endpoint_id: Optional[str] = Field(None, description="Associated endpoint ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional node metadata"
    )


class DependencyEdge(BaseModel):
    """Represents an edge in the dependency graph."""

    id: str = Field(..., description="Unique identifier for the edge")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    dependency_type: str = Field(
        ...,
        description="Type of dependency: 'path_param', 'response_field', 'workflow'",
    )
    reason: str = Field(..., description="Reason for this dependency")
    data_mapping: Dict[str, Any] = Field(
        default_factory=dict, description="Data mapping between nodes"
    )
    confidence: float = Field(
        default=1.0, description="Confidence level (0-1), higher for schema-based"
    )


class DependencyGraph(BaseModel):
    """Represents the complete dependency graph."""

    nodes: List[OperationNode] = Field(..., description="List of operation nodes")
    edges: List[DependencyEdge] = Field(..., description="List of dependency edges")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph metadata")


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
    sequence_type: str = Field(
        default="workflow", description="Type: 'workflow', 'crud', 'data_flow'"
    )
    priority: int = Field(default=1, description="Execution priority")
    estimated_duration: Optional[float] = Field(
        None, description="Estimated duration in seconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional sequence metadata"
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
    graph: Optional[DependencyGraph] = Field(
        None, description="Dependency graph representation"
    )
    analysis_method: str = Field(
        default="hybrid", description="Analysis method used: 'schema', 'llm', 'hybrid'"
    )
    result: Dict[str, Any] = Field(..., description="Summary of the sequencing result")
