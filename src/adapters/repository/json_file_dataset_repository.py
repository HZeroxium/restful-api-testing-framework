# adapters/repository/json_file_dataset_repository.py

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from domain.ports.dataset_repository import DatasetRepositoryInterface
from schemas.core.dataset import Dataset
from common.logger import LoggerFactory, LoggerType, LogLevel


class JsonFileDatasetRepository(DatasetRepositoryInterface):
    """JSON file-based implementation of DatasetRepositoryInterface."""

    def __init__(self, base_path: Optional[str] = None):
        # Use default if base_path is None
        if base_path is None:
            base_path = (
                "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets"
            )

        self.base_path = Path(base_path)
        self.index_file = self.base_path / "index.json"
        self.logger = LoggerFactory.get_logger(
            name="repository.dataset",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

        self.logger.info(f"Initializing JsonFileDatasetRepository at: {base_path}")
        self._ensure_directories()
        self._load_index()
        self.logger.info(f"Loaded {len(self._datasets)} datasets from storage")

    def _ensure_directories(self):
        """Ensure base directory and index file exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "datasets": {},
                        "metadata": {"created_at": datetime.now().isoformat()},
                    },
                    f,
                    indent=2,
                )

    def _load_index(self):
        """Load datasets index from JSON file."""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._datasets = data.get("datasets", {})
            self.logger.debug(f"Successfully loaded {len(self._datasets)} datasets")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Could not load index file: {e}. Starting with empty index."
            )
            self._datasets = {}

    def _save_index(self):
        """Save datasets index to JSON file."""
        data = {
            "datasets": self._datasets,
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "total_datasets": len(self._datasets),
            },
        }
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_dataset_dir(self, dataset_id: str) -> Path:
        """Get directory path for a specific dataset."""
        return self.base_path / dataset_id

    def _dataset_to_dict(self, dataset: Dataset) -> Dict[str, Any]:
        """Convert Dataset to dictionary."""
        return {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "spec_file_path": dataset.spec_file_path,
            "version": dataset.version,
            "base_url": dataset.base_url,
            "created_at": dataset.created_at or datetime.now().isoformat(),
            "updated_at": dataset.updated_at or datetime.now().isoformat(),
        }

    def _dict_to_dataset(self, data: Dict[str, Any]) -> Dataset:
        """Convert dictionary to Dataset."""
        return Dataset(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            spec_file_path=data.get("spec_file_path"),
            version=data.get("version"),
            base_url=data.get("base_url"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def create(self, dataset: Dataset) -> Dataset:
        """Create a new dataset."""
        if not dataset.id:
            dataset.id = str(uuid.uuid4())

        dataset.created_at = datetime.now().isoformat()
        dataset.updated_at = dataset.created_at

        # Create dataset directory structure
        dataset_dir = self._get_dataset_dir(dataset.id)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Initialize empty data files
        for file_name in [
            "endpoints.json",
            "constraints.json",
            "validation_scripts.json",
        ]:
            file_path = dataset_dir / file_name
            with open(file_path, "w", encoding="utf-8") as f:
                entity_key = file_name.replace(".json", "")
                json.dump(
                    {
                        entity_key: {},
                        "metadata": {"created_at": datetime.now().isoformat()},
                    },
                    f,
                    indent=2,
                )

        # Save dataset metadata to index
        dataset_dict = self._dataset_to_dict(dataset)
        self._datasets[dataset.id] = dataset_dict
        self._save_index()

        self.logger.info(f"Created dataset: {dataset.id} - {dataset.name}")
        return dataset

    async def get_by_id(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID."""
        dataset_data = self._datasets.get(dataset_id)
        if not dataset_data:
            self.logger.debug(f"Dataset not found: {dataset_id}")
            return None
        return self._dict_to_dataset(dataset_data)

    async def get_by_name(self, name: str) -> Optional[Dataset]:
        """Get dataset by name."""
        for dataset_data in self._datasets.values():
            if dataset_data["name"] == name:
                return self._dict_to_dataset(dataset_data)
        return None

    async def get_all(self) -> List[Dataset]:
        """Get all datasets."""
        datasets = [self._dict_to_dataset(data) for data in self._datasets.values()]
        self.logger.debug(f"Retrieved {len(datasets)} datasets")
        return datasets

    async def update(self, dataset_id: str, dataset: Dataset) -> Optional[Dataset]:
        """Update an existing dataset."""
        if dataset_id not in self._datasets:
            self.logger.warning(f"Cannot update non-existent dataset: {dataset_id}")
            return None

        # Preserve original creation date and ID
        original_data = self._datasets[dataset_id]
        dataset.id = dataset_id
        dataset.created_at = original_data.get("created_at")
        dataset.updated_at = datetime.now().isoformat()

        dataset_dict = self._dataset_to_dict(dataset)
        self._datasets[dataset_id] = dataset_dict
        self._save_index()

        self.logger.info(f"Updated dataset: {dataset_id}")
        return dataset

    async def delete(self, dataset_id: str) -> bool:
        """Delete a dataset and its associated data."""
        if dataset_id not in self._datasets:
            self.logger.warning(f"Cannot delete non-existent dataset: {dataset_id}")
            return False

        # Delete dataset directory and all its contents
        dataset_dir = self._get_dataset_dir(dataset_id)
        if dataset_dir.exists():
            import shutil

            shutil.rmtree(dataset_dir)

        # Remove from index
        del self._datasets[dataset_id]
        self._save_index()

        self.logger.info(f"Deleted dataset: {dataset_id}")
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return {
            "total_datasets": len(self._datasets),
            "datasets": [
                {"id": d["id"], "name": d["name"], "created_at": d.get("created_at")}
                for d in self._datasets.values()
            ],
        }
