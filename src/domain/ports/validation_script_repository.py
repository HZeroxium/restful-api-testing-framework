# domain/ports/validation_script_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from schemas.tools.test_script_generator import ValidationScript


class ValidationScriptRepositoryInterface(ABC):
    """Interface for ValidationScript repository operations."""

    @abstractmethod
    async def create(self, script: ValidationScript) -> ValidationScript:
        """Create a new validation script."""
        pass

    @abstractmethod
    async def get_by_id(self, script_id: str) -> Optional[ValidationScript]:
        """Get validation script by ID."""
        pass

    @abstractmethod
    async def get_by_endpoint_id(self, endpoint_id: str) -> List[ValidationScript]:
        """Get all validation scripts for a specific endpoint."""
        pass

    @abstractmethod
    async def get_all(self) -> List[ValidationScript]:
        """Get all validation scripts."""
        pass

    @abstractmethod
    async def update(
        self, script_id: str, script: ValidationScript
    ) -> Optional[ValidationScript]:
        """Update an existing validation script."""
        pass

    @abstractmethod
    async def delete(self, script_id: str) -> bool:
        """Delete a validation script."""
        pass

    @abstractmethod
    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all validation scripts for a specific endpoint. Returns count of deleted items."""
        pass
