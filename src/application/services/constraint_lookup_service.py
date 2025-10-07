# application/services/constraint_lookup_service.py

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from schemas.tools.constraint_miner import ApiConstraint, ConstraintType
from common.logger import LoggerFactory, LoggerType, LogLevel


class ConstraintLookupService:
    """Service for looking up constraints across all datasets."""

    def __init__(self, datasets_base_path: str = "data/datasets"):
        self.datasets_base_path = Path(datasets_base_path)
        self.logger = LoggerFactory.get_logger(
            name="service.constraint_lookup",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    def _load_constraints_from_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Load all constraints from a specific dataset."""
        constraints_file = self.datasets_base_path / dataset_id / "constraints.json"

        if not constraints_file.exists():
            return {}

        try:
            with open(constraints_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("constraints", {})
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Could not load constraints from dataset {dataset_id}: {e}"
            )
            return {}

    def _dict_to_constraint(self, data: Dict[str, Any]) -> ApiConstraint:
        """Convert dictionary to ApiConstraint."""
        return ApiConstraint(
            id=data["id"],
            endpoint_id=data.get("endpoint_id"),
            type=(
                ConstraintType(data["type"])
                if isinstance(data["type"], str)
                else data["type"]
            ),
            description=data["description"],
            severity=data.get("severity", "info"),
            source=data["source"],
            details=data.get("details", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def get_constraint_by_id(self, constraint_id: str) -> Optional[ApiConstraint]:
        """Get constraint by ID across all datasets."""
        self.logger.debug(f"Looking up constraint by ID: {constraint_id}")

        if not self.datasets_base_path.exists():
            return None

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            constraints = self._load_constraints_from_dataset(dataset_id)

            if constraint_id in constraints:
                constraint_data = constraints[constraint_id]
                self.logger.debug(
                    f"Found constraint {constraint_id} in dataset {dataset_id}"
                )
                return self._dict_to_constraint(constraint_data)

        self.logger.debug(f"Constraint {constraint_id} not found in any dataset")
        return None

    async def get_all_constraints(self) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Get all constraints across all datasets.

        Returns:
            Tuple of (constraints_dict, dataset_mapping) where dataset_mapping maps constraint_id to dataset_id
        """
        all_constraints = {}
        dataset_mapping = {}

        if not self.datasets_base_path.exists():
            return all_constraints, dataset_mapping

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            constraints = self._load_constraints_from_dataset(dataset_id)

            for constraint_id, constraint_data in constraints.items():
                all_constraints[constraint_id] = constraint_data
                dataset_mapping[constraint_id] = dataset_id

        self.logger.debug(
            f"Loaded {len(all_constraints)} constraints from {len(dataset_mapping)} datasets"
        )
        return all_constraints, dataset_mapping

    async def get_constraints_by_endpoint_id(
        self, endpoint_id: str
    ) -> List[ApiConstraint]:
        """Get all constraints for a specific endpoint across all datasets."""
        results = []

        if not self.datasets_base_path.exists():
            return results

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            constraints = self._load_constraints_from_dataset(dataset_dir.name)

            for constraint_data in constraints.values():
                if constraint_data.get("endpoint_id") == endpoint_id:
                    results.append(self._dict_to_constraint(constraint_data))

        return results

    async def get_constraints_by_dataset_id(
        self, dataset_id: str
    ) -> List[ApiConstraint]:
        """Get all constraints for a specific dataset."""
        constraints = self._load_constraints_from_dataset(dataset_id)

        result = []
        for constraint_data in constraints.values():
            result.append(self._dict_to_constraint(constraint_data))

        return result
