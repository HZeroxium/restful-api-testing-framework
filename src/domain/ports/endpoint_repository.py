# domain/ports/endpoint_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from schemas.tools.openapi_parser import EndpointInfo


class EndpointRepositoryInterface(ABC):
    """Interface for EndpointInfo repository operations."""

    @abstractmethod
    async def create(self, endpoint: EndpointInfo) -> EndpointInfo:
        """Create a new endpoint."""
        pass

    @abstractmethod
    async def get_by_id(self, endpoint_id: str) -> Optional[EndpointInfo]:
        """Get endpoint by ID."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[EndpointInfo]:
        """Get endpoint by name."""
        pass

    @abstractmethod
    async def get_by_path_method(
        self, path: str, method: str
    ) -> Optional[EndpointInfo]:
        """Get endpoint by path and method."""
        pass

    @abstractmethod
    async def get_all(self) -> List[EndpointInfo]:
        """Get all endpoints."""
        pass

    @abstractmethod
    async def update(
        self, endpoint_id: str, endpoint: EndpointInfo
    ) -> Optional[EndpointInfo]:
        """Update an existing endpoint."""
        pass

    @abstractmethod
    async def delete(self, endpoint_id: str) -> bool:
        """Delete an endpoint."""
        pass

    @abstractmethod
    async def search_by_tag(self, tag: str) -> List[EndpointInfo]:
        """Search endpoints by tag."""
        pass

    @abstractmethod
    async def search_by_path(self, path_pattern: str) -> List[EndpointInfo]:
        """Search endpoints by path pattern."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        pass

    @abstractmethod
    async def get_by_dataset_id(self, dataset_id: str) -> List[EndpointInfo]:
        """Get all endpoints for a specific dataset."""
        pass
