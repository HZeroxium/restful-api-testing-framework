"""Service for managing test collections."""

from typing import List, Optional

from schemas.test_collection import TestCollectionModel
from core.repositories.file_repository import FileTestCollectionRepository
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestCollectionService:
    """Service for managing test collections."""

    def __init__(self, data_dir: str = "data/collections"):
        """Initialize the service.

        Args:
            data_dir: Directory to store the collections
        """
        # Initialize custom logger
        self.logger = LoggerFactory.get_logger(
            name="test-collection-service",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

        self.repository = FileTestCollectionRepository(
            directory=data_dir, model_class=TestCollectionModel
        )

    async def get_all_collections(self) -> List[TestCollectionModel]:
        """Get all test collections."""
        collections = await self.repository.get_all()
        self.logger.debug(f"Retrieved {len(collections)} test collections")
        return collections

    async def get_collection_by_id(
        self, collection_id: str
    ) -> Optional[TestCollectionModel]:
        """Get a test collection by ID."""
        collection = await self.repository.get_by_id(collection_id)
        if collection:
            self.logger.debug(
                f"Found collection with ID {collection_id}: {collection.name}"
            )
        else:
            self.logger.warning(f"Collection with ID {collection_id} not found")
        return collection

    async def get_collection_by_name(self, name: str) -> Optional[TestCollectionModel]:
        """Get a test collection by name."""
        collection = await self.repository.get_by_name(name)
        if collection:
            self.logger.debug(f"Found collection with name '{name}': {collection.id}")
        else:
            self.logger.warning(f"Collection with name '{name}' not found")
        return collection

    async def create_collection(
        self, collection: TestCollectionModel
    ) -> TestCollectionModel:
        """Create a new test collection."""
        created_collection = await self.repository.create(collection)
        self.logger.info(
            f"Created test collection '{created_collection.name}' with ID {created_collection.id}"
        )
        return created_collection

    async def update_collection(
        self, collection_id: str, collection: TestCollectionModel
    ) -> TestCollectionModel:
        """Update an existing test collection."""
        updated_collection = await self.repository.update(collection_id, collection)
        self.logger.info(
            f"Updated test collection '{updated_collection.name}' with ID {collection_id}"
        )
        return updated_collection

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a test collection."""
        result = await self.repository.delete(collection_id)
        if result:
            self.logger.info(f"Deleted test collection with ID {collection_id}")
        else:
            self.logger.warning(
                f"Failed to delete test collection with ID {collection_id}"
            )
        return result
