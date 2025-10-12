"""
Sequence generation strategies for operation sequencing.
Implements multiple strategies to generate diverse operation sequences.
"""

import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Set, Tuple
from schemas.tools.operation_sequencer import (
    OperationNode,
    DependencyEdge,
    OperationSequence,
    OperationDependency,
)


class SequenceGenerationStrategy(ABC):
    """Base class for sequence generation strategies."""

    @abstractmethod
    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences using this strategy."""
        pass


class OperationTypeStrategy(SequenceGenerationStrategy):
    """Generate sequences by operation type (GET-only, POST-only, mixed CRUD)."""

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences grouped by HTTP method patterns."""
        sequences = []

        # Group nodes by HTTP method
        method_groups = defaultdict(list)
        for node in nodes:
            method_groups[node.method].append(node)

        # Create sequences for each method group
        for method, group_nodes in method_groups.items():
            if len(group_nodes) <= 1:
                continue

            # Sort by path depth (shallow to deep)
            sorted_nodes = sorted(group_nodes, key=lambda n: len(n.path.split("/")))

            if len(sorted_nodes) >= 2:
                operations = [node.operation for node in sorted_nodes]
                dependencies = _build_dependencies_for_nodes(sorted_nodes, edges)

                sequence_type = f"{method.lower()}_operations"
                sequence_name = f"{method} Operations Sequence"

                sequences.append(
                    OperationSequence(
                        id=str(uuid.uuid4()),
                        name=sequence_name,
                        description=f"All {method} operations in logical order",
                        operations=operations,
                        dependencies=dependencies,
                        sequence_type=sequence_type,
                        priority=2,
                        metadata={"method": method, "operation_count": len(operations)},
                    )
                )

        return sequences


class HierarchicalStrategy(SequenceGenerationStrategy):
    """Generate sequences by resource hierarchy depth."""

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences based on resource hierarchy."""
        sequences = []

        # Group by base resource path
        resource_groups = defaultdict(list)
        for node in nodes:
            base_path = _extract_base_resource_path(node.path)
            resource_groups[base_path].append(node)

        # Create sequences for different hierarchy levels
        for base_path, group_nodes in resource_groups.items():
            if len(group_nodes) <= 1:
                continue

            # Sort by hierarchy depth
            sorted_nodes = sorted(
                group_nodes, key=lambda n: _get_hierarchy_depth(n.path)
            )

            # Create sequences for different depth levels
            depth_groups = defaultdict(list)
            for node in sorted_nodes:
                depth = _get_hierarchy_depth(node.path)
                depth_groups[depth].append(node)

            # Create sequence for each depth level
            for depth, depth_nodes in depth_groups.items():
                if len(depth_nodes) >= 2:
                    operations = [node.operation for node in depth_nodes]
                    dependencies = _build_dependencies_for_nodes(depth_nodes, edges)

                    sequence_type = f"hierarchical_depth_{depth}"
                    sequence_name = f"Hierarchical Operations - Depth {depth}"

                    sequences.append(
                        OperationSequence(
                            id=str(uuid.uuid4()),
                            name=sequence_name,
                            description=f"Operations at hierarchy depth {depth} for {base_path}",
                            operations=operations,
                            dependencies=dependencies,
                            sequence_type=sequence_type,
                            priority=2,
                            metadata={
                                "base_path": base_path,
                                "depth": depth,
                                "operation_count": len(operations),
                            },
                        )
                    )

            # Create comprehensive hierarchical sequence
            if len(sorted_nodes) >= 2:
                operations = [node.operation for node in sorted_nodes]
                dependencies = _build_dependencies_for_nodes(sorted_nodes, edges)

                sequence_type = "hierarchical_comprehensive"
                sequence_name = f"Complete {base_path} Hierarchy"

                sequences.append(
                    OperationSequence(
                        id=str(uuid.uuid4()),
                        name=sequence_name,
                        description=f"Complete hierarchical sequence for {base_path}",
                        operations=operations,
                        dependencies=dependencies,
                        sequence_type=sequence_type,
                        priority=1,
                        metadata={
                            "base_path": base_path,
                            "max_depth": max(
                                _get_hierarchy_depth(n.path) for n in sorted_nodes
                            ),
                            "operation_count": len(operations),
                        },
                    )
                )

        return sequences


class WorkflowStrategy(SequenceGenerationStrategy):
    """Generate sequences by workflow patterns."""

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences based on workflow patterns."""
        sequences = []

        # Group by resource
        resource_groups = defaultdict(list)
        for node in nodes:
            resource = _extract_resource_name(node.path)
            resource_groups[resource].append(node)

        # Create workflow sequences for each resource
        for resource, group_nodes in resource_groups.items():
            if len(group_nodes) <= 1:
                continue

            # Create different workflow patterns
            workflows = _identify_workflow_patterns(group_nodes)

            for workflow_type, workflow_nodes in workflows.items():
                if len(workflow_nodes) >= 2:
                    operations = [node.operation for node in workflow_nodes]
                    dependencies = _build_dependencies_for_nodes(workflow_nodes, edges)

                    sequence_type = f"workflow_{workflow_type}"
                    sequence_name = f"{workflow_type.title()} {resource} Workflow"

                    sequences.append(
                        OperationSequence(
                            id=str(uuid.uuid4()),
                            name=sequence_name,
                            description=f"{workflow_type.title()} workflow for {resource} operations",
                            operations=operations,
                            dependencies=dependencies,
                            sequence_type=sequence_type,
                            priority=1,
                            metadata={
                                "resource": resource,
                                "workflow_type": workflow_type,
                                "operation_count": len(operations),
                            },
                        )
                    )

        return sequences


class CRUDStrategy(SequenceGenerationStrategy):
    """Generate sequences based on CRUD patterns."""

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences based on CRUD operations."""
        sequences = []

        # Group by resource
        resource_groups = defaultdict(list)
        for node in nodes:
            resource = _extract_resource_name(node.path)
            resource_groups[resource].append(node)

        # Create CRUD sequences
        for resource, group_nodes in resource_groups.items():
            if len(group_nodes) <= 1:
                continue

            # Identify CRUD operations
            crud_operations = _identify_crud_operations(group_nodes)

            if len(crud_operations) >= 2:
                # Sort by CRUD order: Create -> Read -> Update -> Delete
                crud_order = {"POST": 1, "GET": 2, "PUT": 3, "DELETE": 4}
                sorted_operations = sorted(
                    crud_operations, key=lambda n: crud_order.get(n.method, 5)
                )

                operations = [node.operation for node in sorted_operations]
                dependencies = _build_dependencies_for_nodes(sorted_operations, edges)

                sequence_type = "crud_complete"
                sequence_name = f"{resource} CRUD Operations"

                sequences.append(
                    OperationSequence(
                        id=str(uuid.uuid4()),
                        name=sequence_name,
                        description=f"Complete CRUD operations for {resource}",
                        operations=operations,
                        dependencies=dependencies,
                        sequence_type=sequence_type,
                        priority=1,
                        metadata={
                            "resource": resource,
                            "crud_methods": [n.method for n in sorted_operations],
                            "operation_count": len(operations),
                        },
                    )
                )

            # Create individual CRUD workflows
            for crud_type, crud_nodes in _group_by_crud_type(group_nodes).items():
                if len(crud_nodes) >= 2:
                    operations = [node.operation for node in crud_nodes]
                    dependencies = _build_dependencies_for_nodes(crud_nodes, edges)

                    sequence_type = f"crud_{crud_type}"
                    sequence_name = f"{crud_type.title()} {resource} Operations"

                    sequences.append(
                        OperationSequence(
                            id=str(uuid.uuid4()),
                            name=sequence_name,
                            description=f"{crud_type.title()} operations for {resource}",
                            operations=operations,
                            dependencies=dependencies,
                            sequence_type=sequence_type,
                            priority=2,
                            metadata={
                                "resource": resource,
                                "crud_type": crud_type,
                                "operation_count": len(operations),
                            },
                        )
                    )

        return sequences


class CombinedStrategy(SequenceGenerationStrategy):
    """Combine all strategies to generate diverse sequences."""

    def __init__(self):
        self.strategies = [
            OperationTypeStrategy(),
            HierarchicalStrategy(),
            WorkflowStrategy(),
            CRUDStrategy(),
        ]

    def generate_sequences(
        self, nodes: List[OperationNode], edges: List[DependencyEdge]
    ) -> List[OperationSequence]:
        """Generate sequences using all strategies and merge results."""
        all_sequences = []

        # Generate sequences using each strategy
        for strategy in self.strategies:
            sequences = strategy.generate_sequences(nodes, edges)
            all_sequences.extend(sequences)

        # Remove duplicates and merge similar sequences
        unique_sequences = self._merge_similar_sequences(all_sequences)

        return unique_sequences

    def _merge_similar_sequences(
        self, sequences: List[OperationSequence]
    ) -> List[OperationSequence]:
        """Merge sequences that are too similar."""
        if not sequences:
            return []

        # Group by operation sets
        operation_groups = defaultdict(list)
        for seq in sequences:
            operation_key = tuple(sorted(seq.operations))
            operation_groups[operation_key].append(seq)

        merged_sequences = []
        for operation_key, group_sequences in operation_groups.items():
            if len(group_sequences) == 1:
                merged_sequences.append(group_sequences[0])
            else:
                # Merge similar sequences, keeping the one with highest priority
                best_sequence = max(group_sequences, key=lambda s: s.priority)

                # Update name to indicate it's a merged sequence
                best_sequence.name = f"Merged: {best_sequence.name}"
                best_sequence.description = f"Merged sequence combining multiple strategies: {best_sequence.description}"

                merged_sequences.append(best_sequence)

        return merged_sequences


# Helper methods for all strategies


def _extract_base_resource_path(path: str) -> str:
    """Extract base resource path without parameters."""
    import re

    # Remove path parameters and get the base path
    clean_path = re.sub(r"\{[^}]+\}", "", path)
    # Get path segments up to the first parameter
    segments = clean_path.strip("/").split("/")
    base_segments = []
    for segment in segments:
        if segment:
            base_segments.append(segment)
        else:
            break
    return "/" + "/".join(base_segments) if base_segments else "/"


def _get_hierarchy_depth(path: str) -> int:
    """Get the hierarchy depth of a path."""
    return len([s for s in path.split("/") if s and not s.startswith("{")])


def _extract_resource_name(path: str) -> str:
    """Extract resource name from path."""
    segments = path.split("/")
    for segment in reversed(segments):
        if segment and not segment.startswith("{"):
            return segment
    return ""


def _identify_workflow_patterns(
    nodes: List[OperationNode],
) -> Dict[str, List[OperationNode]]:
    """Identify different workflow patterns in nodes."""
    workflows = defaultdict(list)

    for node in nodes:
        if node.method == "GET":
            if "list" in node.path.lower() or node.path.endswith("/"):
                workflows["read_list"].append(node)
            else:
                workflows["read_detail"].append(node)
        elif node.method == "POST":
            workflows["create"].append(node)
        elif node.method == "PUT":
            workflows["update"].append(node)
        elif node.method == "DELETE":
            workflows["delete"].append(node)
        else:
            workflows["other"].append(node)

    return dict(workflows)


def _identify_crud_operations(nodes: List[OperationNode]) -> List[OperationNode]:
    """Identify CRUD operations from nodes."""
    crud_methods = {"POST", "GET", "PUT", "DELETE"}
    return [node for node in nodes if node.method in crud_methods]


def _group_by_crud_type(nodes: List[OperationNode]) -> Dict[str, List[OperationNode]]:
    """Group nodes by CRUD type."""
    crud_groups = defaultdict(list)

    for node in nodes:
        if node.method == "POST":
            crud_groups["create"].append(node)
        elif node.method == "GET":
            crud_groups["read"].append(node)
        elif node.method == "PUT":
            crud_groups["update"].append(node)
        elif node.method == "DELETE":
            crud_groups["delete"].append(node)

    return dict(crud_groups)


def _build_dependencies_for_nodes(
    nodes: List[OperationNode], edges: List[DependencyEdge]
) -> List[OperationDependency]:
    """Build dependencies for a specific set of nodes."""
    dependencies = []
    node_ids = {node.id for node in nodes}

    for edge in edges:
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids:
            source_op = next(
                (n.operation for n in nodes if n.id == edge.source_node_id), None
            )
            target_op = next(
                (n.operation for n in nodes if n.id == edge.target_node_id), None
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

    return dependencies
