"""Abstract repository interfaces for the application."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any

# Generic type for repository items
T = TypeVar("T")


class Repository(Generic[T], ABC):
    """Abstract repository interface for CRUD operations."""

    @abstractmethod
    async def get_all(self) -> List[T]:
        """Get all items from the repository."""
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get an item by its ID."""
        pass

    @abstractmethod
    async def create(self, item: T) -> T:
        """Create a new item in the repository."""
        pass

    @abstractmethod
    async def update(self, id: str, item: T) -> T:
        """Update an existing item in the repository."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an item from the repository."""
        pass


class TestCollectionRepository(Repository[T], ABC):
    """Repository interface for TestCollection."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[T]:
        """Get a test collection by name."""
        pass


class TestExecutionRepository(Repository[T], ABC):
    """Repository interface for TestExecution."""

    @abstractmethod
    async def get_by_collection_id(self, collection_id: str) -> List[T]:
        """Get test executions for a specific collection."""
        pass

    @abstractmethod
    async def create_execution(self, collection_id: str, execution: T) -> T:
        """Create a new test execution for a collection."""
        pass
