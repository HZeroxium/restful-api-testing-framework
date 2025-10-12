# tools/llm/operation_sequencer_helpers/schema_analyzer.py

import uuid
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.operation_sequencer import (
    OperationSequence,
    OperationNode,
    DependencyEdge,
    OperationDependency,
)
from .dependency_detector import DependencyDetector
from .sequence_strategies import CombinedStrategy


class Operation:
    """Internal operation representation for analysis."""

    def __init__(self, endpoint: EndpointInfo):
        self.endpoint = endpoint
        self.method = endpoint.method
        self.path = endpoint.path
        self.name = endpoint.name
        self.input_params = self._extract_input_params()
        self.output_params = self._extract_output_params()
        self.path_params = self._extract_path_params()

    def _extract_input_params(self) -> List[str]:
        """Extract input parameter names from endpoint schema."""
        params = []

        # Extract from input_schema parameters
        if hasattr(self.endpoint, "input_schema") and self.endpoint.input_schema:
            if "properties" in self.endpoint.input_schema:
                params.extend(self.endpoint.input_schema["properties"].keys())

        return list(set(params))

    def _extract_output_params(self) -> List[str]:
        """Extract output parameter names from endpoint schema."""
        params = []

        # Extract from output_schema
        if hasattr(self.endpoint, "output_schema") and self.endpoint.output_schema:
            if "properties" in self.endpoint.output_schema:
                params.extend(self.endpoint.output_schema["properties"].keys())

        return list(set(params))

    def _extract_path_params(self) -> List[str]:
        """Extract path parameter names from endpoint path."""
        import re

        pattern = r"\{([^}]+)\}"
        return re.findall(pattern, self.path)

    @property
    def operation(self) -> str:
        """Get operation identifier."""
        return f"{self.method} {self.path}"


class SchemaBasedAnalyzer:
    """Schema-based analyzer for operation dependencies."""

    def __init__(self, endpoints: List[EndpointInfo]):
        self.endpoints = endpoints
        self.dependency_detector = DependencyDetector()
        self.strategy = CombinedStrategy()

    def analyze_dependencies(self) -> Tuple[List[OperationNode], List[DependencyEdge]]:
        """Analyze dependencies between operations."""
        # Build operation nodes
        nodes = self._build_operation_nodes()

        # Use dependency detector to find dependencies
        edges = []
        edges.extend(self.dependency_detector.detect_path_param_dependencies(nodes))
        edges.extend(self.dependency_detector.detect_hierarchical_dependencies(nodes))
        edges.extend(
            self.dependency_detector.detect_method_ordering_dependencies(nodes)
        )
        edges.extend(self.dependency_detector.detect_response_field_dependencies(nodes))

        return nodes, edges

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate operation sequences from dependency graph."""
        # Use combined strategy to generate diverse sequences
        sequences = self.strategy.generate_sequences(nodes, edges)

        # Filter: minimum 2 operations per sequence
        filtered_sequences = [seq for seq in sequences if len(seq.operations) >= 2]

        return filtered_sequences

    def _build_operation_nodes(self) -> List[OperationNode]:
        """Build operation nodes from endpoints."""
        nodes = []

        for endpoint in self.endpoints:
            operation = Operation(endpoint)

            node = OperationNode(
                id=str(uuid.uuid4()),
                operation=operation.operation,
                method=operation.method,
                path=operation.path,
                name=operation.name,
                input_parameters=operation.input_params,
                output_parameters=operation.output_params,
                path_parameters=operation.path_params,
            )

            nodes.append(node)

        return nodes

    def _topological_sort(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationNode]:
        """Simple topological sort for ordering nodes by dependencies."""
        if not nodes:
            return []

        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in-degree for all nodes
        for node in nodes:
            in_degree[node.id] = 0

        # Build graph and calculate in-degrees
        for edge in edges:
            if edge.source_node_id in [n.id for n in nodes] and edge.target_node_id in [
                n.id for n in nodes
            ]:
                graph[edge.source_node_id].append(edge.target_node_id)
                in_degree[edge.target_node_id] += 1

        # Find nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            node = next((node for node in nodes if node.id == current), None)
            if node is not None:
                result.append(node)

            # Update in-degrees
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _create_workflow_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Create workflow sequences based on cross-resource dependencies."""
        sequences = []

        # Find cross-resource dependencies
        cross_resource_edges = []
        for edge in edges:
            source_node = next((n for n in nodes if n.id == edge.source_node_id), None)
            target_node = next((n for n in nodes if n.id == edge.target_node_id), None)

            if source_node is None or target_node is None:
                continue

            source_resource = self._extract_resource_path(source_node.path)
            target_resource = self._extract_resource_path(target_node.path)

            if source_resource != target_resource:
                cross_resource_edges.append(edge)

        # Group cross-resource dependencies into workflow sequences
        if cross_resource_edges:
            # Simple workflow: group by source resource
            workflow_groups = defaultdict(list)
            for edge in cross_resource_edges:
                source_node = next(
                    (n for n in nodes if n.id == edge.source_node_id), None
                )
                if source_node:
                    resource = self._extract_resource_path(source_node.path)
                    workflow_groups[resource].append(edge)

            for resource, group_edges in workflow_groups.items():
                if len(group_edges) >= 1:  # At least one cross-resource dependency
                    # Get all nodes involved in this workflow
                    involved_nodes = set()
                    for edge in group_edges:
                        involved_nodes.add(edge.source_node_id)
                        involved_nodes.add(edge.target_node_id)

                    workflow_nodes = [n for n in nodes if n.id in involved_nodes]

                    if len(workflow_nodes) >= 2:
                        operations = [node.operation for node in workflow_nodes]
                        dependencies = []

                        for edge in group_edges:
                            source_op = next(
                                (
                                    n.operation
                                    for n in workflow_nodes
                                    if n.id == edge.source_node_id
                                ),
                                None,
                            )
                            target_op = next(
                                (
                                    n.operation
                                    for n in workflow_nodes
                                    if n.id == edge.target_node_id
                                ),
                                None,
                            )

                            if source_op and target_op:
                                dependencies.append(
                                    OperationDependency(
                                        source_operation=source_op,
                                        target_operation=target_op,
                                        reason=edge.reason,
                                        data_mapping=edge.data_mapping,
                                    )
                                )

                        sequences.append(
                            OperationSequence(
                                id=str(uuid.uuid4()),
                                name=f"Cross-Resource Workflow: {resource}",
                                description=f"Workflow involving {resource} and related resources",
                                operations=operations,
                                dependencies=dependencies,
                                sequence_type="cross_resource_workflow",
                                priority=3,
                                metadata={
                                    "source_resource": resource,
                                    "cross_resource": True,
                                },
                            )
                        )

        return sequences

    def _extract_resource_path(self, path: str) -> str:
        """Extract resource path without parameters."""
        import re

        # Remove path parameters
        clean_path = re.sub(r"\{[^}]+\}", "", path)
        # Remove trailing slashes and normalize
        return clean_path.rstrip("/")

    def _extract_resource_name(self, path: str) -> str:
        """Extract resource name from path."""
        segments = path.split("/")
        for segment in reversed(segments):
            if segment and not segment.startswith("{"):
                return segment
        return ""

    def _are_related_resources(self, path1: str, path2: str) -> bool:
        """Check if two paths represent related resources."""
        resource1 = self._extract_resource_path(path1)
        resource2 = self._extract_resource_path(path2)

        # Check if one is a prefix of the other (hierarchical relationship)
        return resource1.startswith(resource2) or resource2.startswith(resource1)
