"""
Dependency detection logic for operation sequencing.
Extracted from schema_analyzer.py to improve modularity.
"""

import re
import uuid
from typing import List, Set, Dict, Any
from schemas.tools.operation_sequencer import (
    OperationNode,
    DependencyEdge,
)


class DependencyDetector:
    """Detect dependencies between operations."""

    def detect_path_param_dependencies(
        self, nodes: List[OperationNode]
    ) -> List[DependencyEdge]:
        """Detect dependencies based on path parameters."""
        edges = []

        for node in nodes:
            # Extract path parameters
            path_params = self._extract_path_params_from_path(node.path)

            for param in path_params:
                # Find nodes that might produce this parameter
                for potential_source in nodes:
                    if potential_source.id == node.id:
                        continue

                    # Enhanced logic: Check for hierarchical dependencies
                    dependency_found = False

                    # 1. Check if potential source is a POST/PUT that creates resources
                    if potential_source.method in ["POST", "PUT"]:
                        resource_name = self._extract_resource_name(
                            potential_source.path
                        )
                        if resource_name and param.lower() in [
                            resource_name.lower(),
                            "id",
                        ]:
                            dependency_found = True

                    # 2. Check for hierarchical relationships (parent-child)
                    elif self._is_hierarchical_dependency(
                        potential_source.path, node.path, param
                    ):
                        dependency_found = True

                    # 3. Check for parameter name matching (e.g., billId in both paths)
                    elif self._has_parameter_match(potential_source.path, param):
                        dependency_found = True

                    if dependency_found:
                        edges.append(
                            DependencyEdge(
                                id=str(uuid.uuid4()),
                                source_node_id=node.id,
                                target_node_id=potential_source.id,
                                dependency_type="path_param",
                                reason=f"{node.operation} requires {param} from {potential_source.operation}",
                                data_mapping={param: f"response.{param}"},
                                confidence=0.9,  # High confidence for path parameter dependencies
                            )
                        )

        return edges

    def detect_hierarchical_dependencies(
        self, nodes: List[OperationNode]
    ) -> List[DependencyEdge]:
        """Detect hierarchical parent-child dependencies."""
        edges = []

        for node in nodes:
            # Check if this node is a child in a hierarchical relationship
            for potential_parent in nodes:
                if potential_parent.id == node.id:
                    continue

                # Check if potential_parent is a hierarchical parent of node
                if self._is_hierarchical_parent(potential_parent.path, node.path, None):
                    # Extract the parameter that links them
                    parent_params = self._extract_path_params_from_path(
                        potential_parent.path
                    )
                    child_params = self._extract_path_params_from_path(node.path)

                    # Find the parameter that connects them
                    linking_param = None
                    for param in child_params:
                        if param in parent_params or self._has_parameter_match(
                            potential_parent.path, param
                        ):
                            linking_param = param
                            break

                    if linking_param:
                        edges.append(
                            DependencyEdge(
                                id=str(uuid.uuid4()),
                                source_node_id=node.id,
                                target_node_id=potential_parent.id,
                                dependency_type="hierarchical",
                                reason=f"{node.operation} is a child of {potential_parent.operation} in hierarchy",
                                data_mapping={
                                    linking_param: f"response.{linking_param}"
                                },
                                confidence=0.8,
                            )
                        )

        return edges

    def detect_method_ordering_dependencies(
        self, nodes: List[OperationNode]
    ) -> List[DependencyEdge]:
        """Detect HTTP method ordering dependencies."""
        edges = []

        # Method priority: POST -> GET -> PUT -> DELETE
        method_priority = {"POST": 1, "GET": 2, "PUT": 3, "DELETE": 4}

        # Group nodes by resource path
        resource_groups = {}
        for node in nodes:
            resource_path = self._extract_resource_path(node.path)
            if resource_path not in resource_groups:
                resource_groups[resource_path] = []
            resource_groups[resource_path].append(node)

        # For each resource group, create ordering dependencies
        for resource_path, group_nodes in resource_groups.items():
            if len(group_nodes) <= 1:
                continue

            # Sort by method priority
            sorted_nodes = sorted(
                group_nodes, key=lambda n: method_priority.get(n.method, 5)
            )

            # Create dependencies between consecutive methods
            for i in range(len(sorted_nodes) - 1):
                current = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]

                # Only create dependency if there's a logical flow
                if self._is_logical_method_flow(current.method, next_node.method):
                    edges.append(
                        DependencyEdge(
                            id=str(uuid.uuid4()),
                            source_node_id=current.id,
                            target_node_id=next_node.id,
                            dependency_type="method_ordering",
                            reason=f"{current.operation} should precede {next_node.operation} in typical CRUD flow",
                            data_mapping={},
                            confidence=0.6,
                        )
                    )

        return edges

    def detect_response_field_dependencies(
        self, nodes: List[OperationNode]
    ) -> List[DependencyEdge]:
        """Detect response field to request parameter dependencies."""
        edges = []

        # This is a simplified implementation
        # In a full implementation, we would parse OpenAPI specs to understand response schemas

        for node in nodes:
            if node.method in [
                "POST",
                "PUT",
            ]:  # Operations that typically return created/updated resource
                # Look for nodes that might use the response data
                for potential_consumer in nodes:
                    if potential_consumer.id == node.id:
                        continue

                    # Check if consumer has path parameters that might come from the producer's response
                    consumer_params = self._extract_path_params_from_path(
                        potential_consumer.path
                    )
                    producer_resource = self._extract_resource_name(node.path)

                    if producer_resource and any(
                        param.lower() in [producer_resource.lower(), "id"]
                        for param in consumer_params
                    ):
                        # Find the matching parameter
                        matching_param = next(
                            (
                                param
                                for param in consumer_params
                                if param.lower() in [producer_resource.lower(), "id"]
                            ),
                            None,
                        )

                        if matching_param:
                            edges.append(
                                DependencyEdge(
                                    id=str(uuid.uuid4()),
                                    source_node_id=node.id,
                                    target_node_id=potential_consumer.id,
                                    dependency_type="response_field",
                                    reason=f"{potential_consumer.operation} requires {matching_param} from {node.operation} response",
                                    data_mapping={
                                        matching_param: f"response.{matching_param}"
                                    },
                                    confidence=0.7,
                                )
                            )

        return edges

    def _extract_path_params_from_path(self, path: str) -> List[str]:
        """Extract path parameters from a path string."""
        pattern = r"\{([^}]+)\}"
        return re.findall(pattern, path)

    def _extract_resource_path(self, path: str) -> str:
        """Extract resource path without parameters."""
        # Remove path parameters
        clean_path = re.sub(r"\{[^}]+\}", "", path)
        # Remove trailing slashes and normalize
        return clean_path.rstrip("/")

    def _extract_resource_name(self, path: str) -> str:
        """Extract resource name from path."""
        # Get the last segment of the path before any parameters
        segments = path.split("/")
        for segment in reversed(segments):
            if segment and not segment.startswith("{"):
                return segment
        return ""

    def _is_hierarchical_dependency(
        self, source_path: str, target_path: str, param: str
    ) -> bool:
        """Check if there's a hierarchical dependency between paths."""
        # Check if source path is a parent of target path
        # e.g., /api/v1/Bills vs /api/v1/Bills/{billId}/Stages

        # Remove path parameters from both paths for comparison
        source_base = re.sub(r"\{[^}]+\}", "", source_path)
        target_base = re.sub(r"\{[^}]+\}", "", target_path)

        # Check if source is a prefix of target (hierarchical relationship)
        if target_base.startswith(source_base) and source_base != target_base:
            # Extract the resource name from source path
            source_resource = self._extract_resource_name(source_path)
            if source_resource and param.lower() in [source_resource.lower(), "id"]:
                return True

        return False

    def _has_parameter_match(self, source_path: str, param: str) -> bool:
        """Check if source path has a parameter that could provide the required param."""
        # Extract parameters from source path
        source_params = self._extract_path_params_from_path(source_path)

        # Check for exact match or common ID patterns
        for source_param in source_params:
            if source_param.lower() == param.lower() or (
                param.lower().endswith("id") and source_param.lower().endswith("id")
            ):
                return True

        return False

    def _is_hierarchical_parent(
        self, parent_path: str, child_path: str, param: str
    ) -> bool:
        """Check if parent_path is a hierarchical parent of child_path for the given parameter."""
        # Remove path parameters from both paths for comparison
        # Use a placeholder to avoid empty segments
        parent_base = re.sub(r"\{[^}]+\}", "PARAM", parent_path)
        child_base = re.sub(r"\{[^}]+\}", "PARAM", child_path)

        # Check if parent is a prefix of child (hierarchical relationship)
        if not child_base.startswith(parent_base) or parent_base == child_base:
            return False

        # Check if parent path is a direct parent (one level up)
        parent_segments = parent_base.strip("/").split("/")
        child_segments = child_base.strip("/").split("/")

        # Parent should be exactly one level shorter than child
        if len(child_segments) != len(parent_segments) + 1:
            return False

        # Child should start with all parent segments
        if child_segments[: len(parent_segments)] != parent_segments:
            return False

        # For hierarchical APIs, if the parent is a direct parent of the child,
        # and the child requires parameters that could come from the parent,
        # then there's a dependency

        # Get parameters from both paths
        parent_params = self._extract_path_params_from_path(parent_path)
        child_params = self._extract_path_params_from_path(child_path)

        # Check if the parameter is in the child path
        if param and param not in child_params:
            return False

        # If the parameter is directly in the parent path, it's a direct dependency
        if param and param in parent_params:
            return True

        # For hierarchical relationships, check if the parent can provide the parameter
        # This is a heuristic: if parent is a direct parent and child has additional parameters,
        # the parent likely provides the context for the child's parameters
        return True

    def _is_logical_method_flow(self, source_method: str, target_method: str) -> bool:
        """Check if there's a logical flow between two HTTP methods."""
        logical_flows = {
            "POST": ["GET", "PUT", "DELETE"],
            "GET": ["PUT", "DELETE"],
            "PUT": ["GET", "DELETE"],
            "DELETE": [],  # DELETE typically doesn't lead to other operations
        }

        return target_method in logical_flows.get(source_method, [])
