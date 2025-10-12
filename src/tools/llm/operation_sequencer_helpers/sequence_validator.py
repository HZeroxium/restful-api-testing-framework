"""
Sequence validation logic for operation sequencing.
Validates generated sequences for consistency and correctness.
"""

from typing import List, Tuple, Set, Dict, Any
from schemas.tools.operation_sequencer import OperationSequence, OperationDependency


class SequenceValidator:
    """Validate generated sequences."""

    def validate_sequence(
        self, sequence: OperationSequence
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single sequence.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Check minimum operations
        if len(sequence.operations) < 2:
            errors.append("Sequence must have at least 2 operations")

        # Check for duplicate operations within sequence
        if len(sequence.operations) != len(set(sequence.operations)):
            errors.append("Sequence contains duplicate operations")

        # Check dependency consistency
        dependency_errors, dependency_warnings = self._validate_dependencies(sequence)
        errors.extend(dependency_errors)
        warnings.extend(dependency_warnings)

        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(sequence)
        if circular_deps:
            errors.append(f"Sequence contains circular dependencies: {circular_deps}")

        # Check operation references in dependencies
        op_ref_errors = self._validate_dependency_operation_references(sequence)
        errors.extend(op_ref_errors)

        # Validate metadata
        metadata_warnings = self._validate_metadata(sequence)
        warnings.extend(metadata_warnings)

        return len(errors) == 0, errors, warnings

    def validate_sequences(self, sequences: List[OperationSequence]) -> Dict[str, Any]:
        """
        Validate multiple sequences.

        Returns:
            Dictionary with validation results
        """
        results = {
            "total_sequences": len(sequences),
            "valid_sequences": 0,
            "invalid_sequences": 0,
            "sequence_details": [],
            "overall_errors": [],
            "overall_warnings": [],
        }

        for i, sequence in enumerate(sequences):
            is_valid, errors, warnings = self.validate_sequence(sequence)

            sequence_result = {
                "sequence_id": sequence.id,
                "sequence_name": sequence.name,
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "operation_count": len(sequence.operations),
                "dependency_count": len(sequence.dependencies),
            }

            results["sequence_details"].append(sequence_result)

            if is_valid:
                results["valid_sequences"] += 1
            else:
                results["invalid_sequences"] += 1

            results["overall_errors"].extend(errors)
            results["overall_warnings"].extend(warnings)

        # Remove duplicate errors/warnings
        results["overall_errors"] = list(set(results["overall_errors"]))
        results["overall_warnings"] = list(set(results["overall_warnings"]))

        return results

    def _validate_dependencies(
        self, sequence: OperationSequence
    ) -> Tuple[List[str], List[str]]:
        """Validate dependencies within a sequence."""
        errors = []
        warnings = []

        for dependency in sequence.dependencies:
            # Check if source and target operations exist in the sequence
            if dependency.source_operation not in sequence.operations:
                errors.append(
                    f"Dependency references non-existent source operation: {dependency.source_operation}"
                )

            if dependency.target_operation not in sequence.operations:
                errors.append(
                    f"Dependency references non-existent target operation: {dependency.target_operation}"
                )

            # Check if source comes before target in sequence
            try:
                source_index = sequence.operations.index(dependency.source_operation)
                target_index = sequence.operations.index(dependency.target_operation)

                if source_index >= target_index:
                    warnings.append(
                        f"Dependency {dependency.source_operation} -> {dependency.target_operation} may have incorrect ordering"
                    )
            except ValueError:
                # This error is already caught above
                pass

            # Validate data mapping
            if dependency.data_mapping:
                for param, mapping in dependency.data_mapping.items():
                    if not param or not mapping:
                        warnings.append(
                            f"Empty parameter or mapping in dependency: {param} -> {mapping}"
                        )

            # Check reason is not empty
            if not dependency.reason or dependency.reason.strip() == "":
                warnings.append(
                    f"Empty dependency reason for {dependency.source_operation} -> {dependency.target_operation}"
                )

        return errors, warnings

    def _detect_circular_dependencies(self, sequence: OperationSequence) -> List[str]:
        """Detect circular dependencies in a sequence."""
        # Build adjacency list
        graph = {}
        for operation in sequence.operations:
            graph[operation] = []

        for dependency in sequence.dependencies:
            if (
                dependency.source_operation in graph
                and dependency.target_operation in graph
            ):
                graph[dependency.source_operation].append(dependency.target_operation)

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(" -> ".join(cycle))
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if dfs(neighbor, path + [node]):
                    return True

            rec_stack.remove(node)
            return False

        for operation in sequence.operations:
            if operation not in visited:
                dfs(operation, [])

        return cycles

    def _validate_dependency_operation_references(
        self, sequence: OperationSequence
    ) -> List[str]:
        """Validate that all dependency operation references are valid."""
        errors = []
        operation_set = set(sequence.operations)

        for dependency in sequence.dependencies:
            if dependency.source_operation not in operation_set:
                errors.append(
                    f"Dependency source operation '{dependency.source_operation}' not found in sequence operations"
                )

            if dependency.target_operation not in operation_set:
                errors.append(
                    f"Dependency target operation '{dependency.target_operation}' not found in sequence operations"
                )

        return errors

    def _validate_metadata(self, sequence: OperationSequence) -> List[str]:
        """Validate sequence metadata."""
        warnings = []

        # Check if metadata is present
        if not sequence.metadata:
            warnings.append("Sequence has no metadata")
            return warnings

        # Check for required metadata fields based on sequence type
        if sequence.sequence_type:
            if sequence.sequence_type.startswith("crud"):
                if "resource" not in sequence.metadata:
                    warnings.append("CRUD sequence missing 'resource' in metadata")

            elif sequence.sequence_type.startswith("hierarchical"):
                if "base_path" not in sequence.metadata:
                    warnings.append(
                        "Hierarchical sequence missing 'base_path' in metadata"
                    )

            elif sequence.sequence_type.startswith("workflow"):
                if "workflow_type" not in sequence.metadata:
                    warnings.append(
                        "Workflow sequence missing 'workflow_type' in metadata"
                    )

        # Check operation count consistency
        if "operation_count" in sequence.metadata:
            expected_count = sequence.metadata["operation_count"]
            actual_count = len(sequence.operations)
            if expected_count != actual_count:
                warnings.append(
                    f"Metadata operation_count ({expected_count}) doesn't match actual count ({actual_count})"
                )

        return warnings

    def validate_sequence_overlap(
        self, sequences: List[OperationSequence]
    ) -> Dict[str, Any]:
        """Validate operation overlap between sequences."""
        if len(sequences) <= 1:
            return {"overlap_ratio": 0.0, "sequence_pairs": []}

        overlap_info = {
            "overlap_ratio": 0.0,
            "sequence_pairs": [],
            "total_operations": 0,
            "unique_operations": set(),
        }

        all_operations = []
        sequence_operations = {}

        # Collect all operations
        for seq in sequences:
            seq_ops = set(seq.operations)
            sequence_operations[seq.id] = seq_ops
            all_operations.extend(seq.operations)
            overlap_info["unique_operations"].update(seq.operations)

        overlap_info["total_operations"] = len(all_operations)

        # Calculate overlap between sequence pairs
        sequence_list = list(sequences)
        for i in range(len(sequence_list)):
            for j in range(i + 1, len(sequence_list)):
                seq1 = sequence_list[i]
                seq2 = sequence_list[j]

                ops1 = sequence_operations[seq1.id]
                ops2 = sequence_operations[seq2.id]

                intersection = ops1.intersection(ops2)
                union = ops1.union(ops2)

                if union:
                    overlap_ratio = len(intersection) / len(union)

                    overlap_info["sequence_pairs"].append(
                        {
                            "sequence1_id": seq1.id,
                            "sequence1_name": seq1.name,
                            "sequence2_id": seq2.id,
                            "sequence2_name": seq2.name,
                            "overlap_ratio": overlap_ratio,
                            "common_operations": list(intersection),
                            "total_operations": len(union),
                        }
                    )

        # Calculate overall overlap ratio
        if all_operations:
            overlap_info["overlap_ratio"] = (
                len(all_operations) - len(overlap_info["unique_operations"])
            ) / len(all_operations)

        return overlap_info

    def validate_sequence_diversity(
        self, sequences: List[OperationSequence]
    ) -> Dict[str, Any]:
        """Validate sequence diversity and types."""
        if not sequences:
            return {"type_diversity": 0, "type_counts": {}, "diversity_score": 0.0}

        type_counts = {}
        priority_counts = {}

        for seq in sequences:
            # Count by type
            seq_type = seq.sequence_type or "unknown"
            type_counts[seq_type] = type_counts.get(seq_type, 0) + 1

            # Count by priority
            priority_counts[seq.priority] = priority_counts.get(seq.priority, 0) + 1

        # Calculate diversity metrics
        total_sequences = len(sequences)
        unique_types = len(type_counts)
        type_diversity = unique_types / total_sequences if total_sequences > 0 else 0

        # Calculate diversity score (0-1, higher is better)
        # Based on how evenly distributed the types are
        if unique_types <= 1:
            diversity_score = 0.0
        else:
            # Use entropy to measure diversity
            entropy = 0
            for count in type_counts.values():
                p = count / total_sequences
                if p > 0:
                    entropy -= p * (
                        p.bit_length() - 1
                    )  # Simplified entropy calculation

            max_entropy = (unique_types.bit_length() - 1) if unique_types > 0 else 0
            diversity_score = entropy / max_entropy if max_entropy > 0 else 0

        return {
            "type_diversity": type_diversity,
            "type_counts": type_counts,
            "priority_counts": priority_counts,
            "diversity_score": diversity_score,
            "unique_types": unique_types,
            "total_sequences": total_sequences,
        }
