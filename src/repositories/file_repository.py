"""File-based repository implementations."""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Generic, TypeVar, Type, Union
import logging

from pydantic import BaseModel

from repositories.interfaces import TestCollectionRepository, TestExecutionRepository


# Type for models that can be stored
T = TypeVar("T", bound=BaseModel)


class FileRepository(Generic[T]):
    """Base file repository implementation."""

    def __init__(self, directory: str, file_prefix: str, model_class: Type[T]):
        """Initialize the file repository.

        Args:
            directory: Directory to store the files
            file_prefix: Prefix for the filenames
            model_class: Class of the model being stored
        """
        self.directory = directory
        self.file_prefix = file_prefix
        self.model_class = model_class
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

    async def _save_to_file(self, filename: str, data: Dict[str, Any]) -> None:
        """Save data to a file."""
        file_path = os.path.join(self.directory, filename)
        async with asyncio.Lock():
            try:
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                self.logger.debug(f"Saved data to {file_path}")
            except Exception as e:
                self.logger.error(f"Error saving to {file_path}: {e}")
                raise

    async def _load_from_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load data from a file."""
        file_path = os.path.join(self.directory, filename)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading from {file_path}: {e}")
            return None

    async def _list_files(self, prefix: str) -> List[str]:
        """List all files with a given prefix."""
        try:
            files = [
                f
                for f in os.listdir(self.directory)
                if f.startswith(prefix) and f.endswith(".json")
            ]
            return files
        except Exception as e:
            self.logger.error(f"Error listing files in {self.directory}: {e}")
            return []


class FileTestCollectionRepository(TestCollectionRepository[T], FileRepository[T]):
    """File-based implementation of TestCollectionRepository."""

    def __init__(self, directory: str, model_class: Type[T]):
        """Initialize the repository."""
        super().__init__(directory, "collection_", model_class)

    async def get_all(self) -> List[T]:
        """Get all test collections."""
        files = await self._list_files(self.file_prefix)
        collections = []

        for file in files:
            data = await self._load_from_file(file)
            if data:
                try:
                    collection = self.model_class(**data)
                    collections.append(collection)
                except Exception as e:
                    self.logger.error(f"Error parsing collection from {file}: {e}")

        return collections

    async def get_by_id(self, id: str) -> Optional[T]:
        """Get a test collection by ID."""
        filename = f"{self.file_prefix}{id}.json"
        data = await self._load_from_file(filename)
        if data:
            try:
                return self.model_class(**data)
            except Exception as e:
                self.logger.error(f"Error parsing collection from {filename}: {e}")
        return None

    async def get_by_name(self, name: str) -> Optional[T]:
        """Get a test collection by name."""
        collections = await self.get_all()
        for collection in collections:
            if collection.name == name:
                return collection
        return None

    async def create(self, item: T) -> T:
        """Create a new test collection."""
        # Generate ID if not present
        data = item.model_dump()
        if "id" not in data or not data["id"]:
            data["id"] = str(uuid.uuid4())

        # Save to file
        filename = f"{self.file_prefix}{data['id']}.json"
        await self._save_to_file(filename, data)

        # Return updated item
        return self.model_class(**data)

    async def update(self, id: str, item: T) -> T:
        """Update an existing test collection."""
        data = item.model_dump()
        data["id"] = id  # Ensure ID is set correctly

        filename = f"{self.file_prefix}{id}.json"
        await self._save_to_file(filename, data)

        return self.model_class(**data)

    async def delete(self, id: str) -> bool:
        """Delete a test collection."""
        filename = f"{self.file_prefix}{id}.json"
        file_path = os.path.join(self.directory, filename)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                self.logger.error(f"Error deleting {file_path}: {e}")
                return False
        return False


class FileTestExecutionRepository(TestExecutionRepository[T], FileRepository[T]):
    """File-based implementation of TestExecutionRepository."""

    def __init__(self, directory: str, model_class: Type[T]):
        """Initialize the repository."""
        super().__init__(directory, "execution_", model_class)

    async def get_all(self) -> List[T]:
        """Get all test executions."""
        files = await self._list_files(self.file_prefix)
        executions = []

        for file in files:
            data = await self._load_from_file(file)
            if data:
                try:
                    execution = self.model_class(**data)
                    executions.append(execution)
                except Exception as e:
                    self.logger.error(f"Error parsing execution from {file}: {e}")

        return executions

    async def get_by_id(self, id: str) -> Optional[T]:
        """Get a test execution by ID."""
        filename = f"{self.file_prefix}{id}.json"
        data = await self._load_from_file(filename)
        if data:
            try:
                return self.model_class(**data)
            except Exception as e:
                self.logger.error(f"Error parsing execution from {filename}: {e}")
        return None

    async def get_by_collection_id(self, collection_id: str) -> List[T]:
        """Get test executions for a specific collection."""
        files = await self._list_files(f"{self.file_prefix}{collection_id}_")
        executions = []

        for file in files:
            data = await self._load_from_file(file)
            if data:
                try:
                    execution = self.model_class(**data)
                    executions.append(execution)
                except Exception as e:
                    self.logger.error(f"Error parsing execution from {file}: {e}")

        return executions

    async def create(self, item: T) -> T:
        """Create a new test execution."""
        # Generate ID if not present
        data = item.model_dump()
        if "id" not in data or not data["id"]:
            data["id"] = str(uuid.uuid4())

        # Save to file
        filename = f"{self.file_prefix}{data['id']}.json"
        await self._save_to_file(filename, data)

        return self.model_class(**data)

    async def create_execution(self, collection_id: str, execution: T) -> T:
        """Create a new test execution for a collection."""
        data = execution.model_dump()

        # Generate execution ID
        execution_id = str(uuid.uuid4())
        data["id"] = execution_id
        data["collection_id"] = collection_id
        data["timestamp"] = datetime.now().isoformat()

        # Save to file with collection ID in the filename
        filename = f"{self.file_prefix}{collection_id}_{execution_id}.json"
        await self._save_to_file(filename, data)

        return self.model_class(**data)

    async def update(self, id: str, item: T) -> T:
        """Update an existing test execution."""
        data = item.model_dump()
        data["id"] = id  # Ensure ID is set correctly

        filename = f"{self.file_prefix}{id}.json"
        await self._save_to_file(filename, data)

        return self.model_class(**data)

    async def delete(self, id: str) -> bool:
        """Delete a test execution."""
        filename = f"{self.file_prefix}{id}.json"
        file_path = os.path.join(self.directory, filename)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                self.logger.error(f"Error deleting {file_path}: {e}")
                return False
        return False
