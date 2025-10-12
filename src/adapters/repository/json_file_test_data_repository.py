# adapters/repository/json_file_test_data_repository.py

import json
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from domain.ports.test_data_repository import TestDataRepositoryInterface
from schemas.core.test_data import TestData
from common.logger import LoggerFactory, LoggerType, LogLevel


class JsonFileTestDataRepository(TestDataRepositoryInterface):
    """JSON file-based implementation of test data repository."""

    def __init__(self, dataset_id: Optional[str] = None, verbose: bool = False):
        """
        Initialize the repository.

        Args:
            dataset_id: If provided, operates on dataset-specific file.
                       If None, operates on global repository (searches all datasets).
            verbose: Enable verbose logging
        """
        self.dataset_id = dataset_id
        self.logger = LoggerFactory.get_logger(
            name=f"repository.test_data",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        )

        if self.dataset_id:
            # Dataset-specific repository
            self._test_data_file = Path(
                f"D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets\\{dataset_id}\\test_data.json"
            )
            self._test_data_file.parent.mkdir(parents=True, exist_ok=True)
            self._test_data = self._load_test_data()
        else:
            # Global repository (no file, uses lookup service)
            self._test_data = {}

    def _load_test_data(self) -> dict:
        """Load test data from JSON file."""
        if not self._test_data_file.exists():
            return {}

        try:
            with open(self._test_data_file, "r") as f:
                data = json.load(f)
                return data.get("test_data", {})
        except Exception as e:
            self.logger.error(
                f"Failed to load test data from {self._test_data_file}: {e}"
            )
            return {}

    def _save_test_data(self) -> None:
        """Save test data to JSON file."""
        try:
            data = {
                "test_data": self._test_data,
                "metadata": {
                    "total_count": len(self._test_data),
                    "last_updated": str(uuid.uuid4()),  # Simple timestamp placeholder
                },
            }

            with open(self._test_data_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(
                f"Saved {len(self._test_data)} test data items to {self._test_data_file}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to save test data to {self._test_data_file}: {e}"
            )

    async def create(self, test_data: TestData) -> TestData:
        """Create a new test data item."""
        if not test_data.id:
            test_data.id = str(uuid.uuid4())

        self._test_data[test_data.id] = test_data.model_dump()

        if self.dataset_id:
            self._save_test_data()

        self.logger.info(
            f"Created test data: {test_data.id} for endpoint: {test_data.endpoint_id}"
        )
        return test_data

    async def get_by_id(self, test_data_id: str) -> Optional[TestData]:
        """Get test data by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            test_data_dict = self._test_data.get(test_data_id)
            if test_data_dict:
                return TestData(**test_data_dict)
            return None
        else:
            # Global repository - search all datasets
            datasets_base_path = Path("data/datasets")
            if not datasets_base_path.exists():
                return None

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                test_data_file = dataset_dir / "test_data.json"
                if not test_data_file.exists():
                    continue

                with open(test_data_file, "r") as f:
                    data = json.load(f)

                test_data_dict = data.get("test_data", {}).get(test_data_id)
                if test_data_dict:
                    return TestData(**test_data_dict)

            return None

    async def get_by_endpoint_id(
        self, endpoint_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[TestData], int]:
        """Get all test data for an endpoint with pagination."""
        if self.dataset_id:
            # Dataset-specific repository
            test_data_items = []
            for test_data_dict in self._test_data.values():
                if test_data_dict.get("endpoint_id") == endpoint_id:
                    test_data_items.append(TestData(**test_data_dict))

            # Calculate total count before pagination
            total_count = len(test_data_items)

            # Apply pagination
            paginated_items = test_data_items[offset : offset + limit]

            return paginated_items, total_count
        else:
            # Global repository - search all datasets
            test_data_items = []
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return [], 0

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                test_data_file = dataset_dir / "test_data.json"
                if not test_data_file.exists():
                    continue

                with open(test_data_file, "r") as f:
                    data = json.load(f)

                for test_data_dict in data.get("test_data", {}).values():
                    if test_data_dict.get("endpoint_id") == endpoint_id:
                        test_data_items.append(TestData(**test_data_dict))

            # Calculate total count before pagination
            total_count = len(test_data_items)

            # Apply pagination
            paginated_items = test_data_items[offset : offset + limit]

            return paginated_items, total_count

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> Tuple[List[TestData], int]:
        """Get all test data with pagination."""
        if self.dataset_id:
            # Dataset-specific repository
            all_data = [
                TestData(**test_data_dict)
                for test_data_dict in self._test_data.values()
            ]
        else:
            # Global repository - search all datasets
            all_data = []
            datasets_base_path = Path("data/datasets")

            if datasets_base_path.exists():
                for dataset_dir in datasets_base_path.iterdir():
                    if not dataset_dir.is_dir():
                        continue

                    test_data_file = dataset_dir / "test_data.json"
                    if not test_data_file.exists():
                        continue

                    with open(test_data_file, "r") as f:
                        data = json.load(f)

                    for test_data_dict in data.get("test_data", {}).values():
                        all_data.append(TestData(**test_data_dict))

        # Calculate total count before pagination
        total_count = len(all_data)

        # Apply pagination
        paginated_data = all_data[offset : offset + limit]

        return paginated_data, total_count

    async def update(
        self, test_data_id: str, test_data: TestData
    ) -> Optional[TestData]:
        """Update test data."""
        if self.dataset_id:
            # Dataset-specific repository
            if test_data_id in self._test_data:
                test_data.id = test_data_id  # Ensure ID consistency
                self._test_data[test_data_id] = test_data.model_dump()
                self._save_test_data()
                self.logger.info(f"Updated test data: {test_data_id}")
                return test_data
            return None
        else:
            # Global repository - update in appropriate dataset file
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return None

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                test_data_file = dataset_dir / "test_data.json"
                if not test_data_file.exists():
                    continue

                with open(test_data_file, "r") as f:
                    data = json.load(f)

                if test_data_id in data.get("test_data", {}):
                    test_data.id = test_data_id  # Ensure ID consistency
                    data["test_data"][test_data_id] = test_data.model_dump()

                    with open(test_data_file, "w") as f:
                        json.dump(data, f, indent=2)

                    self.logger.info(f"Updated test data: {test_data_id}")
                    return test_data

            return None

    async def delete(self, test_data_id: str) -> bool:
        """Delete test data by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            if test_data_id in self._test_data:
                del self._test_data[test_data_id]
                self._save_test_data()
                self.logger.info(f"Deleted test data: {test_data_id}")
                return True
            return False
        else:
            # Global repository - delete from appropriate dataset file
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return False

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                test_data_file = dataset_dir / "test_data.json"
                if not test_data_file.exists():
                    continue

                with open(test_data_file, "r") as f:
                    data = json.load(f)

                if test_data_id in data.get("test_data", {}):
                    del data["test_data"][test_data_id]

                    with open(test_data_file, "w") as f:
                        json.dump(data, f, indent=2)

                    self.logger.info(f"Deleted test data: {test_data_id}")
                    return True

            return False

    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all test data for an endpoint. Returns count of deleted items."""
        if self.dataset_id:
            # Dataset-specific repository
            to_delete = [
                tid
                for tid, data in self._test_data.items()
                if data.get("endpoint_id") == endpoint_id
            ]

            for tid in to_delete:
                del self._test_data[tid]

            if to_delete:
                self._save_test_data()

            return len(to_delete)
        else:
            # Global repository - need to delete from all datasets
            deleted_count = 0
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return 0

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                # Load test data for this dataset
                test_data_file = dataset_dir / "test_data.json"
                if not test_data_file.exists():
                    continue

                with open(test_data_file, "r") as f:
                    data = json.load(f)

                test_data = data.get("test_data", {})
                to_delete = [
                    tid
                    for tid, test_data_dict in test_data.items()
                    if test_data_dict.get("endpoint_id") == endpoint_id
                ]

                # Delete test data
                for tid in to_delete:
                    del test_data[tid]
                    deleted_count += 1

                # Save updated test data
                if to_delete:
                    data["test_data"] = test_data
                    with open(test_data_file, "w") as f:
                        json.dump(data, f, indent=2)

            return deleted_count
