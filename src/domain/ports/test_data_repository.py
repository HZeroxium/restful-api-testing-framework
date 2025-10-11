# domain/ports/test_data_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional

from schemas.core.test_data import TestData


class TestDataRepositoryInterface(ABC):
    """Interface for test data repository operations."""

    @abstractmethod
    async def create(self, test_data: TestData) -> TestData:
        """Create a new test data item."""
        pass

    @abstractmethod
    async def get_by_id(self, test_data_id: str) -> Optional[TestData]:
        """Get test data by ID."""
        pass

    @abstractmethod
    async def get_by_endpoint_id(self, endpoint_id: str) -> List[TestData]:
        """Get all test data for an endpoint."""
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[TestData]:
        """Get all test data with pagination."""
        pass

    @abstractmethod
    async def update(
        self, test_data_id: str, test_data: TestData
    ) -> Optional[TestData]:
        """Update test data."""
        pass

    @abstractmethod
    async def delete(self, test_data_id: str) -> bool:
        """Delete test data by ID."""
        pass

    @abstractmethod
    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all test data for an endpoint. Returns count of deleted items."""
        pass
