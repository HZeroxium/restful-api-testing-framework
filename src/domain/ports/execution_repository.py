# domain/ports/execution_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional

from schemas.core.execution_history import ExecutionHistory


class ExecutionRepositoryInterface(ABC):
    """Interface for execution history repository operations."""

    @abstractmethod
    async def create(self, execution: ExecutionHistory) -> ExecutionHistory:
        """Create a new execution history record."""
        pass

    @abstractmethod
    async def get_by_id(self, execution_id: str) -> Optional[ExecutionHistory]:
        """Get execution history by ID."""
        pass

    @abstractmethod
    async def get_by_endpoint_id(
        self, endpoint_id: str, limit: int = 10
    ) -> List[ExecutionHistory]:
        """Get execution history for an endpoint with limit."""
        pass

    @abstractmethod
    async def get_all(self, limit: int = 10) -> List[ExecutionHistory]:
        """Get all execution history with limit."""
        pass

    @abstractmethod
    async def update(
        self, execution_id: str, execution: ExecutionHistory
    ) -> Optional[ExecutionHistory]:
        """Update execution history."""
        pass

    @abstractmethod
    async def delete(self, execution_id: str) -> bool:
        """Delete execution history by ID."""
        pass
