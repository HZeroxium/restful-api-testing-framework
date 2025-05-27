"""Service for managing test collections."""

import logging
from typing import List, Optional

from schemas.test_collection import TestCollectionModel
from core.repositories.file_repository import FileTestCollectionRepository


class TestCollectionService:
    """Service for managing test collections."""

    def __init__(self, data_dir: str = "data/collections"):
        """Initialize the service.

        Args:
            data_dir: Directory to store the collections
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.repository = FileTestCollectionRepository(
            directory=data_dir, model_class=TestCollectionModel
        )

    async def get_all_collections(self) -> List[TestCollectionModel]:
        """Get all test collections."""
        return await self.repository.get_all()

    async def get_collection_by_id(
        self, collection_id: str
    ) -> Optional[TestCollectionModel]:
        """Get a test collection by ID."""
        return await self.repository.get_by_id(collection_id)

    async def get_collection_by_name(self, name: str) -> Optional[TestCollectionModel]:
        """Get a test collection by name."""
        return await self.repository.get_by_name(name)

    async def create_collection(
        self, collection: TestCollectionModel
    ) -> TestCollectionModel:
        """Create a new test collection."""
        return await self.repository.create(collection)

    async def update_collection(
        self, collection_id: str, collection: TestCollectionModel
    ) -> TestCollectionModel:
        """Update an existing test collection."""
        return await self.repository.update(collection_id, collection)

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a test collection."""
        return await self.repository.delete(collection_id)
