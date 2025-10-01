# domain/ports/constraint_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from schemas.tools.constraint_miner import ApiConstraint


class ConstraintRepositoryInterface(ABC):
    """Interface for ApiConstraint repository operations."""

    @abstractmethod
    async def create(self, constraint: ApiConstraint) -> ApiConstraint:
        """Create a new constraint."""
        pass

    @abstractmethod
    async def get_by_id(self, constraint_id: str) -> Optional[ApiConstraint]:
        """Get constraint by ID."""
        pass

    @abstractmethod
    async def get_by_endpoint_id(self, endpoint_id: str) -> List[ApiConstraint]:
        """Get all constraints for a specific endpoint."""
        pass

    @abstractmethod
    async def get_all(self) -> List[ApiConstraint]:
        """Get all constraints."""
        pass

    @abstractmethod
    async def update(
        self, constraint_id: str, constraint: ApiConstraint
    ) -> Optional[ApiConstraint]:
        """Update an existing constraint."""
        pass

    @abstractmethod
    async def delete(self, constraint_id: str) -> bool:
        """Delete a constraint."""
        pass

    @abstractmethod
    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all constraints for a specific endpoint. Returns count of deleted items."""
        pass
