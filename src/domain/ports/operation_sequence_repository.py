# domain/ports/operation_sequence_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from schemas.tools.operation_sequencer import OperationSequence


class OperationSequenceRepositoryInterface(ABC):
    """Interface for operation sequence repository operations."""

    @abstractmethod
    async def create(self, sequence: OperationSequence) -> OperationSequence:
        """Create a new operation sequence."""
        pass

    @abstractmethod
    async def get_by_id(self, sequence_id: str) -> Optional[OperationSequence]:
        """Get operation sequence by ID."""
        pass

    @abstractmethod
    async def get_by_dataset_id(
        self, dataset_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get all operation sequences for a dataset with pagination."""
        pass

    @abstractmethod
    async def get_all(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[OperationSequence], int]:
        """Get all operation sequences with pagination."""
        pass

    @abstractmethod
    async def update(
        self, sequence_id: str, sequence: OperationSequence
    ) -> Optional[OperationSequence]:
        """Update an existing operation sequence."""
        pass

    @abstractmethod
    async def delete(self, sequence_id: str) -> bool:
        """Delete an operation sequence."""
        pass

    @abstractmethod
    async def delete_by_dataset_id(self, dataset_id: str) -> int:
        """Delete all operation sequences for a dataset. Returns count of deleted items."""
        pass
