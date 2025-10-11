# adapters/repository/json_file_execution_repository.py

import json
import uuid
from pathlib import Path
from typing import List, Optional

from domain.ports.execution_repository import ExecutionRepositoryInterface
from schemas.core.execution_history import ExecutionHistory
from common.logger import LoggerFactory, LoggerType, LogLevel


class JsonFileExecutionRepository(ExecutionRepositoryInterface):
    """JSON file-based implementation of execution repository."""

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
            name=f"repository.execution",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.DEBUG if verbose else LogLevel.INFO,
        )

        if self.dataset_id:
            # Dataset-specific repository
            self._execution_file = Path(
                f"D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets\\{dataset_id}\\executions.json"
            )
            self._execution_file.parent.mkdir(parents=True, exist_ok=True)
            self._executions = self._load_executions()
        else:
            # Global repository (no file, uses lookup service)
            self._executions = {}

    def _load_executions(self) -> dict:
        """Load executions from JSON file."""
        if not self._execution_file.exists():
            return {}

        try:
            with open(self._execution_file, "r") as f:
                data = json.load(f)
                return data.get("executions", {})
        except Exception as e:
            self.logger.error(
                f"Failed to load executions from {self._execution_file}: {e}"
            )
            return {}

    def _save_executions(self) -> None:
        """Save executions to JSON file."""
        try:
            data = {
                "executions": self._executions,
                "metadata": {
                    "total_count": len(self._executions),
                    "last_updated": str(uuid.uuid4()),  # Simple timestamp placeholder
                },
            }

            with open(self._execution_file, "w") as f:
                json.dump(
                    data, f, indent=2, default=str
                )  # default=str for datetime serialization

            self.logger.debug(
                f"Saved {len(self._executions)} executions to {self._execution_file}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to save executions to {self._execution_file}: {e}"
            )

    async def create(self, execution: ExecutionHistory) -> ExecutionHistory:
        """Create a new execution history record."""
        if not execution.id:
            execution.id = str(uuid.uuid4())

        self._executions[execution.id] = execution.model_dump()

        if self.dataset_id:
            self._save_executions()

        self.logger.info(
            f"Created execution history: {execution.id} for endpoint: {execution.endpoint_id}"
        )
        return execution

    async def get_by_id(self, execution_id: str) -> Optional[ExecutionHistory]:
        """Get execution history by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            execution_dict = self._executions.get(execution_id)
            if execution_dict:
                return ExecutionHistory(**execution_dict)
            return None
        else:
            # Global repository - search all datasets
            datasets_base_path = Path("data/datasets")
            if not datasets_base_path.exists():
                return None

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                execution_file = dataset_dir / "executions.json"
                if not execution_file.exists():
                    continue

                with open(execution_file, "r") as f:
                    data = json.load(f)

                execution_dict = data.get("executions", {}).get(execution_id)
                if execution_dict:
                    return ExecutionHistory(**execution_dict)

            return None

    async def get_by_endpoint_id(
        self, endpoint_id: str, limit: int = 10
    ) -> List[ExecutionHistory]:
        """Get execution history for an endpoint with limit."""
        if self.dataset_id:
            # Dataset-specific repository
            executions = []
            for execution_dict in self._executions.values():
                if execution_dict.get("endpoint_id") == endpoint_id:
                    executions.append(ExecutionHistory(**execution_dict))

            # Sort by started_at descending and limit
            executions.sort(key=lambda x: x.started_at, reverse=True)
            return executions[:limit]
        else:
            # Global repository - search all datasets
            executions = []
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return executions

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                execution_file = dataset_dir / "executions.json"
                if not execution_file.exists():
                    continue

                with open(execution_file, "r") as f:
                    data = json.load(f)

                for execution_dict in data.get("executions", {}).values():
                    if execution_dict.get("endpoint_id") == endpoint_id:
                        executions.append(ExecutionHistory(**execution_dict))

            # Sort by started_at descending and limit
            executions.sort(key=lambda x: x.started_at, reverse=True)
            return executions[:limit]

    async def get_all(self, limit: int = 10) -> List[ExecutionHistory]:
        """Get all execution history with limit."""
        if self.dataset_id:
            # Dataset-specific repository
            executions = [
                ExecutionHistory(**execution_dict)
                for execution_dict in self._executions.values()
            ]

            # Sort by started_at descending and limit
            executions.sort(key=lambda x: x.started_at, reverse=True)
            return executions[:limit]
        else:
            # Global repository - search all datasets
            executions = []
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return executions

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                execution_file = dataset_dir / "executions.json"
                if not execution_file.exists():
                    continue

                with open(execution_file, "r") as f:
                    data = json.load(f)

                for execution_dict in data.get("executions", {}).values():
                    executions.append(ExecutionHistory(**execution_dict))

            # Sort by started_at descending and limit
            executions.sort(key=lambda x: x.started_at, reverse=True)
            return executions[:limit]

    async def update(
        self, execution_id: str, execution: ExecutionHistory
    ) -> Optional[ExecutionHistory]:
        """Update execution history."""
        if self.dataset_id:
            # Dataset-specific repository
            if execution_id in self._executions:
                execution.id = execution_id  # Ensure ID consistency
                self._executions[execution_id] = execution.model_dump()
                self._save_executions()
                self.logger.info(f"Updated execution history: {execution_id}")
                return execution
            return None
        else:
            # Global repository - update in appropriate dataset file
            datasets_base_path = Path("data/datasets")

            if not datasets_base_path.exists():
                return None

            for dataset_dir in datasets_base_path.iterdir():
                if not dataset_dir.is_dir():
                    continue

                execution_file = dataset_dir / "executions.json"
                if not execution_file.exists():
                    continue

                with open(execution_file, "r") as f:
                    data = json.load(f)

                if execution_id in data.get("executions", {}):
                    execution.id = execution_id  # Ensure ID consistency
                    data["executions"][execution_id] = execution.model_dump()

                    with open(execution_file, "w") as f:
                        json.dump(data, f, indent=2, default=str)

                    self.logger.info(f"Updated execution history: {execution_id}")
                    return execution

            return None

    async def delete(self, execution_id: str) -> bool:
        """Delete execution history by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            if execution_id in self._executions:
                del self._executions[execution_id]
                self._save_executions()
                self.logger.info(f"Deleted execution history: {execution_id}")
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

                execution_file = dataset_dir / "executions.json"
                if not execution_file.exists():
                    continue

                with open(execution_file, "r") as f:
                    data = json.load(f)

                if execution_id in data.get("executions", {}):
                    del data["executions"][execution_id]

                    with open(execution_file, "w") as f:
                        json.dump(data, f, indent=2, default=str)

                    self.logger.info(f"Deleted execution history: {execution_id}")
                    return True

            return False
