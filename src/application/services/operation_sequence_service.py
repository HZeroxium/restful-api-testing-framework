# application/services/operation_sequence_service.py

from typing import List, Optional, Tuple, Dict, Any
import uuid

from domain.ports.operation_sequence_repository import (
    OperationSequenceRepositoryInterface,
)
from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.tools.operation_sequencer import (
    OperationSequence,
    DependencyGraph,
    OperationNode,
    DependencyEdge,
)
from tools.llm.operation_sequencer import OperationSequencerTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class OperationSequenceService:
    """Service for managing operation sequences."""

    def __init__(
        self,
        sequence_repository: OperationSequenceRepositoryInterface,
        endpoint_repository: EndpointRepositoryInterface,
        verbose: bool = False,
    ):
        self.sequence_repository = sequence_repository
        self.endpoint_repository = endpoint_repository
        self.verbose = verbose

        # Initialize logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name="service.operation_sequence",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize the sequencer tool
        self.sequencer_tool = OperationSequencerTool(verbose=verbose)

    async def generate_sequences_for_dataset(
        self, dataset_id: str, override_existing: bool = True
    ) -> Dict[str, Any]:
        """Generate operation sequences for all endpoints in a dataset."""
        self.logger.info(f"Generating operation sequences for dataset: {dataset_id}")

        # Import here to avoid circular dependency
        from adapters.repository.json_file_operation_sequence_repository import (
            JsonFileOperationSequenceRepository,
        )

        # Create dataset-specific repository
        dataset_repo = JsonFileOperationSequenceRepository(
            dataset_id=dataset_id, verbose=self.verbose
        )

        # Get all endpoints for dataset
        endpoints, total = await self.endpoint_repository.get_by_dataset_id(dataset_id)

        if not endpoints:
            error_msg = f"No endpoints found for dataset {dataset_id}"
            self.logger.warning(error_msg)
            return {"error": error_msg}

        self.logger.info(f"Found {len(endpoints)} endpoints in dataset {dataset_id}")

        # Delete existing sequences if override
        if override_existing:
            deleted_count = await dataset_repo.delete_by_dataset_id(dataset_id)
            self.logger.info(
                f"Deleted {deleted_count} existing sequences for dataset {dataset_id}"
            )

        # Generate sequences using tool
        from schemas.tools.operation_sequencer import OperationSequencerInput

        tool_input = OperationSequencerInput(
            endpoints=endpoints,
            collection_name=f"Dataset {dataset_id}",
            include_data_mapping=True,
        )

        self.logger.info("Starting sequence generation with hybrid approach...")
        output = await self.sequencer_tool.execute(tool_input)

        # Save sequences to dataset-specific repository
        saved_sequences = []
        for sequence in output.sequences:
            # Add dataset_id metadata
            if not sequence.metadata:
                sequence.metadata = {}
            sequence.metadata["dataset_id"] = dataset_id

            saved_seq = await dataset_repo.create(sequence)
            saved_sequences.append(saved_seq)

        self.logger.info(
            f"Successfully generated and saved {len(saved_sequences)} sequences for dataset {dataset_id}"
        )

        return {
            "dataset_id": dataset_id,
            "total_endpoints": len(endpoints),
            "sequences_generated": len(saved_sequences),
            "analysis_method": output.analysis_method,
            "graph": output.graph.model_dump() if output.graph else None,
            "result": output.result,
        }

    async def get_sequences_by_dataset_id(
        self, dataset_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get sequences for a dataset."""
        # Import here to avoid circular dependency
        from adapters.repository.json_file_operation_sequence_repository import (
            JsonFileOperationSequenceRepository,
        )

        # Create dataset-specific repository
        dataset_repo = JsonFileOperationSequenceRepository(
            dataset_id=dataset_id, verbose=self.verbose
        )

        sequences, total = await dataset_repo.get_by_dataset_id(
            dataset_id, limit, offset
        )
        self.logger.debug(
            f"Retrieved {len(sequences)} sequences for dataset {dataset_id}"
        )
        return sequences, total

    async def get_sequence_by_id(self, sequence_id: str) -> Optional[OperationSequence]:
        """Get a specific sequence by searching across all datasets."""
        # Import here to avoid circular dependency
        from adapters.repository.json_file_operation_sequence_repository import (
            JsonFileOperationSequenceRepository,
        )
        import os
        from pathlib import Path

        # First try the global repository
        sequence = await self.sequence_repository.get_by_id(sequence_id)
        if sequence:
            self.logger.debug(
                f"Retrieved sequence from global repo: {sequence.name} (ID: {sequence_id})"
            )
            return sequence

        # If not found, search in dataset-specific repositories
        datasets_dir = Path("data/datasets")
        if datasets_dir.exists():
            for dataset_dir in datasets_dir.iterdir():
                if dataset_dir.is_dir():
                    dataset_id = dataset_dir.name
                    try:
                        dataset_repo = JsonFileOperationSequenceRepository(
                            dataset_id=dataset_id, verbose=self.verbose
                        )
                        sequence = await dataset_repo.get_by_id(sequence_id)
                        if sequence:
                            self.logger.debug(
                                f"Retrieved sequence from dataset {dataset_id}: {sequence.name} (ID: {sequence_id})"
                            )
                            return sequence
                    except Exception as e:
                        self.logger.debug(
                            f"Error searching dataset {dataset_id}: {str(e)}"
                        )
                        continue

        self.logger.debug(f"Sequence not found: {sequence_id}")
        return None

    async def delete_sequences_by_dataset_id(self, dataset_id: str) -> int:
        """Delete all sequences for a dataset."""
        # Import here to avoid circular dependency
        from adapters.repository.json_file_operation_sequence_repository import (
            JsonFileOperationSequenceRepository,
        )

        # Create dataset-specific repository
        dataset_repo = JsonFileOperationSequenceRepository(
            dataset_id=dataset_id, verbose=self.verbose
        )

        deleted_count = await dataset_repo.delete_by_dataset_id(dataset_id)
        self.logger.info(f"Deleted {deleted_count} sequences for dataset {dataset_id}")
        return deleted_count

    async def delete_sequence(self, sequence_id: str) -> bool:
        """Delete a specific sequence."""
        success = await self.sequence_repository.delete(sequence_id)
        if success:
            self.logger.info(f"Deleted sequence: {sequence_id}")
        else:
            self.logger.warning(f"Failed to delete sequence: {sequence_id}")
        return success

    async def update_sequence(
        self, sequence_id: str, sequence: OperationSequence
    ) -> Optional[OperationSequence]:
        """Update a specific sequence."""
        updated_sequence = await self.sequence_repository.update(sequence_id, sequence)
        if updated_sequence:
            self.logger.info(f"Updated sequence: {sequence.name} (ID: {sequence_id})")
        else:
            self.logger.warning(f"Failed to update sequence: {sequence_id}")
        return updated_sequence

    def build_graph_from_sequences(
        self, sequences: List[OperationSequence]
    ) -> DependencyGraph:
        """Build dependency graph from stored sequences."""
        self.logger.debug(f"Building graph from {len(sequences)} sequences")

        # Extract unique operations and build nodes
        operations = set()
        for sequence in sequences:
            operations.update(sequence.operations)

        # Create nodes for each unique operation
        nodes = []
        operation_to_node_id = {}

        for operation in operations:
            node_id = str(uuid.uuid4())
            operation_to_node_id[operation] = node_id

            # Extract method and path from operation string
            parts = operation.split(" ", 1)
            method = parts[0] if len(parts) > 0 else "UNKNOWN"
            path = parts[1] if len(parts) > 1 else ""

            nodes.append(
                OperationNode(
                    id=node_id,
                    operation=operation,
                    method=method,
                    path=path,
                    endpoint_id=None,  # We don't have endpoint_id in stored sequences
                    metadata={"from_sequence": True},
                )
            )

        # Build edges from sequence dependencies
        edges = []
        for sequence in sequences:
            for dependency in sequence.dependencies:
                source_node_id = operation_to_node_id.get(dependency.source_operation)
                target_node_id = operation_to_node_id.get(dependency.target_operation)

                if source_node_id and target_node_id:
                    edges.append(
                        DependencyEdge(
                            id=str(uuid.uuid4()),
                            source_node_id=source_node_id,
                            target_node_id=target_node_id,
                            dependency_type="workflow",
                            reason=dependency.reason,
                            data_mapping=dependency.data_mapping,
                            confidence=0.9,  # Stored sequences have high confidence
                        )
                    )

        # Add metadata
        metadata = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_sequences": len(sequences),
            "generated_from_stored": True,
            "sequences_by_type": self._get_sequences_by_type(sequences),
        }

        return DependencyGraph(nodes=nodes, edges=edges, metadata=metadata)

    def _get_sequences_by_type(
        self, sequences: List[OperationSequence]
    ) -> Dict[str, int]:
        """Get count of sequences by type."""
        type_counts = {}
        for sequence in sequences:
            seq_type = sequence.sequence_type
            type_counts[seq_type] = type_counts.get(seq_type, 0) + 1
        return type_counts

    async def get_sequences_by_type(
        self, sequence_type: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get sequences filtered by type."""
        all_sequences, total = await self.sequence_repository.get_all(
            limit=1000, offset=0
        )  # Get all to filter

        filtered_sequences = [
            seq for seq in all_sequences if seq.sequence_type == sequence_type
        ]

        # Apply pagination
        total_filtered = len(filtered_sequences)
        paginated_sequences = filtered_sequences[offset : offset + limit]

        self.logger.debug(
            f"Retrieved {len(paginated_sequences)} sequences of type '{sequence_type}'"
        )
        return paginated_sequences, total_filtered

    async def get_sequence_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about sequences."""
        all_sequences, total = await self.sequence_repository.get_all(
            limit=1000, offset=0
        )

        stats = {
            "total_sequences": total,
            "sequences_by_type": self._get_sequences_by_type(all_sequences),
            "sequences_with_dependencies": len(
                [seq for seq in all_sequences if seq.dependencies]
            ),
            "average_operations_per_sequence": (
                sum(len(seq.operations) for seq in all_sequences) / len(all_sequences)
                if all_sequences
                else 0
            ),
            "sequences_by_priority": self._get_sequences_by_priority(all_sequences),
        }

        return stats

    def _get_sequences_by_priority(
        self, sequences: List[OperationSequence]
    ) -> Dict[int, int]:
        """Get count of sequences by priority."""
        priority_counts = {}
        for sequence in sequences:
            priority = sequence.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return priority_counts

    async def validate_sequence(self, sequence: OperationSequence) -> Dict[str, Any]:
        """Validate a sequence for completeness and correctness."""
        validation_results = {"is_valid": True, "errors": [], "warnings": []}

        # Check required fields
        if not sequence.name:
            validation_results["errors"].append("Sequence name is required")
            validation_results["is_valid"] = False

        if not sequence.operations:
            validation_results["errors"].append(
                "Sequence must have at least one operation"
            )
            validation_results["is_valid"] = False

        # Check for duplicate operations
        if len(sequence.operations) != len(set(sequence.operations)):
            validation_results["warnings"].append(
                "Sequence contains duplicate operations"
            )

        # Check dependency consistency
        for dependency in sequence.dependencies:
            if dependency.source_operation not in sequence.operations:
                validation_results["errors"].append(
                    f"Dependency source operation '{dependency.source_operation}' not found in sequence operations"
                )
                validation_results["is_valid"] = False

            if dependency.target_operation not in sequence.operations:
                validation_results["errors"].append(
                    f"Dependency target operation '{dependency.target_operation}' not found in sequence operations"
                )
                validation_results["is_valid"] = False

        return validation_results
