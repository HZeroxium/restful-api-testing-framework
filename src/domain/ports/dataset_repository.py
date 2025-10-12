# domain/ports/dataset_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from schemas.core.dataset import Dataset


class DatasetRepositoryInterface(ABC):
    """Interface for Dataset repository operations."""

    @abstractmethod
    async def create(self, dataset: Dataset) -> Dataset:
        """Create a new dataset."""
        pass

    @abstractmethod
    async def get_by_id(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Dataset]:
        """Get dataset by name."""
        pass

    @abstractmethod
    async def get_all(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Dataset], int]:
        """Get all datasets with pagination."""
        pass

    @abstractmethod
    async def update(self, dataset_id: str, dataset: Dataset) -> Optional[Dataset]:
        """Update an existing dataset."""
        pass

    @abstractmethod
    async def delete(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        pass
