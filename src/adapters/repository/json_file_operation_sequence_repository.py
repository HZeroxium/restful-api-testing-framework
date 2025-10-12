# adapters/repository/json_file_operation_sequence_repository.py

import json
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from domain.ports.operation_sequence_repository import (
    OperationSequenceRepositoryInterface,
)
from schemas.tools.operation_sequencer import OperationSequence
from common.logger import LoggerFactory, LoggerType, LogLevel


class JsonFileOperationSequenceRepository(OperationSequenceRepositoryInterface):
    """JSON file-based repository for operation sequences."""

    def __init__(self, dataset_id: Optional[str] = None, verbose: bool = False):
        self.dataset_id = dataset_id
        self.verbose = verbose

        # Set up file path
        if dataset_id:
            self.file_path = Path(
                f"data/datasets/{dataset_id}/operation_sequences.json"
            )
        else:
            self.file_path = Path("data/operation_sequences.json")

        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"repository.operation_sequence.{dataset_id or 'global'}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Load existing sequences
        self._sequences: Dict[str, OperationSequence] = self._load_sequences()
        self.logger.info(
            f"Loaded {len(self._sequences)} operation sequences from {self.file_path}"
        )

    def _load_sequences(self) -> Dict[str, OperationSequence]:
        """Load sequences from JSON file."""
        if not self.file_path.exists():
            self.logger.debug(
                f"File {self.file_path} does not exist, starting with empty sequences"
            )
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            sequences = {}
            for seq_data in data.get("sequences", []):
                try:
                    sequence = OperationSequence(**seq_data)
                    sequences[sequence.id] = sequence
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load sequence {seq_data.get('id', 'unknown')}: {str(e)}"
                    )

            self.logger.info(f"Successfully loaded {len(sequences)} sequences")
            return sequences

        except Exception as e:
            self.logger.error(
                f"Failed to load sequences from {self.file_path}: {str(e)}"
            )
            return {}

    def _save_sequences(self) -> None:
        """Save sequences to JSON file."""
        try:
            data = {
                "sequences": [seq.model_dump() for seq in self._sequences.values()],
                "metadata": {
                    "total_sequences": len(self._sequences),
                    "dataset_id": self.dataset_id,
                    "last_updated": str(uuid.uuid4()),  # Simple timestamp replacement
                },
            }

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(
                f"Saved {len(self._sequences)} sequences to {self.file_path}"
            )

        except Exception as e:
            self.logger.error(f"Failed to save sequences to {self.file_path}: {str(e)}")
            raise

    async def create(self, sequence: OperationSequence) -> OperationSequence:
        """Create a new operation sequence."""
        # Generate ID if not provided
        if not sequence.id:
            sequence.id = str(uuid.uuid4())

        # Add to in-memory storage
        self._sequences[sequence.id] = sequence

        # Save to disk
        self._save_sequences()

        self.logger.info(
            f"Created operation sequence: {sequence.name} (ID: {sequence.id})"
        )
        return sequence

    async def get_by_id(self, sequence_id: str) -> Optional[OperationSequence]:
        """Get operation sequence by ID."""
        sequence = self._sequences.get(sequence_id)
        if sequence:
            self.logger.debug(
                f"Retrieved sequence: {sequence.name} (ID: {sequence_id})"
            )
        else:
            self.logger.debug(f"Sequence not found: {sequence_id}")
        return sequence

    async def get_by_dataset_id(
        self, dataset_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get all operation sequences for a dataset with pagination."""
        # Filter sequences by dataset_id in metadata
        filtered_sequences = []
        for sequence in self._sequences.values():
            if sequence.metadata and sequence.metadata.get("dataset_id") == dataset_id:
                filtered_sequences.append(sequence)

        # Apply pagination
        total = len(filtered_sequences)
        paginated_sequences = filtered_sequences[offset : offset + limit]

        self.logger.debug(
            f"Retrieved {len(paginated_sequences)} sequences for dataset {dataset_id} (offset: {offset}, limit: {limit}, total: {total})"
        )
        return paginated_sequences, total

    async def get_all(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get all operation sequences with pagination."""
        sequences = list(self._sequences.values())

        # Apply pagination
        total = len(sequences)
        paginated_sequences = sequences[offset : offset + limit]

        self.logger.debug(
            f"Retrieved {len(paginated_sequences)} sequences (offset: {offset}, limit: {limit}, total: {total})"
        )
        return paginated_sequences, total

    async def update(
        self, sequence_id: str, sequence: OperationSequence
    ) -> Optional[OperationSequence]:
        """Update an existing operation sequence."""
        if sequence_id not in self._sequences:
            self.logger.warning(f"Sequence not found for update: {sequence_id}")
            return None

        # Update the sequence
        sequence.id = sequence_id  # Ensure ID consistency
        self._sequences[sequence_id] = sequence

        # Save to disk
        self._save_sequences()

        self.logger.info(
            f"Updated operation sequence: {sequence.name} (ID: {sequence_id})"
        )
        return sequence

    async def delete(self, sequence_id: str) -> bool:
        """Delete an operation sequence."""
        if sequence_id not in self._sequences:
            self.logger.warning(f"Sequence not found for deletion: {sequence_id}")
            return False

        sequence = self._sequences.pop(sequence_id)

        # Save to disk
        self._save_sequences()

        self.logger.info(
            f"Deleted operation sequence: {sequence.name} (ID: {sequence_id})"
        )
        return True

    async def delete_by_dataset_id(self, dataset_id: str) -> int:
        """Delete all operation sequences for a dataset. Returns count of deleted items."""
        sequences_to_delete = []

        # Find sequences for this dataset
        for seq_id, sequence in self._sequences.items():
            if sequence.metadata and sequence.metadata.get("dataset_id") == dataset_id:
                sequences_to_delete.append(seq_id)

        # Delete sequences
        deleted_count = 0
        for seq_id in sequences_to_delete:
            if seq_id in self._sequences:
                del self._sequences[seq_id]
                deleted_count += 1

        # Save to disk if any deletions occurred
        if deleted_count > 0:
            self._save_sequences()
            self.logger.info(
                f"Deleted {deleted_count} sequences for dataset {dataset_id}"
            )
        else:
            self.logger.debug(f"No sequences found for dataset {dataset_id}")

        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return {
            "total_sequences": len(self._sequences),
            "dataset_id": self.dataset_id,
            "file_path": str(self.file_path),
            "sequences_by_type": self._get_sequences_by_type(),
        }

    def _get_sequences_by_type(self) -> Dict[str, int]:
        """Get count of sequences by type."""
        type_counts = {}
        for sequence in self._sequences.values():
            seq_type = sequence.sequence_type
            type_counts[seq_type] = type_counts.get(seq_type, 0) + 1
        return type_counts
