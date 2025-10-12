# adapters/repository/json_file_constraint_repository.py

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from domain.ports.constraint_repository import ConstraintRepositoryInterface
from schemas.tools.constraint_miner import ApiConstraint, ConstraintType
from common.logger import LoggerFactory, LoggerType, LogLevel
from application.services.constraint_lookup_service import ConstraintLookupService
from utils.pagination_utils import paginate_list


class JsonFileConstraintRepository(ConstraintRepositoryInterface):
    """JSON file-based implementation of ConstraintRepositoryInterface."""

    def __init__(
        self, file_path: str = "data/constraints.json", dataset_id: Optional[str] = None
    ):
        self.dataset_id = dataset_id
        if dataset_id:
            # Dataset-specific storage
            self.file_path = (
                Path(
                    "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets"
                )
                / dataset_id
                / "constraints.json"
            )
            self.logger = LoggerFactory.get_logger(
                name="repository.constraint",
                logger_type=LoggerType.STANDARD,
                level=LogLevel.INFO,
            )

            self.logger.info(
                f"Initializing JsonFileConstraintRepository with file: {self.file_path}"
            )
            self._ensure_file_exists()
            self._load_constraints()
            self.logger.info(
                f"Loaded {len(self._constraints)} constraints from storage"
            )
        else:
            # Global storage - use lookup service to search across all datasets
            self.file_path = Path(file_path)
            self.lookup_service = ConstraintLookupService(
                "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets"
            )
            self.logger = LoggerFactory.get_logger(
                name="repository.constraint",
                logger_type=LoggerType.STANDARD,
                level=LogLevel.INFO,
            )
            self.logger.info(
                f"Initializing JsonFileConstraintRepository (global mode) with lookup service"
            )

    def _ensure_file_exists(self):
        """Ensure the JSON file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "constraints": {},
                        "metadata": {"created_at": datetime.now().isoformat()},
                    },
                    f,
                    indent=2,
                )

    def _load_constraints(self):
        """Load constraints from JSON file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._constraints = data.get("constraints", {})
            self.logger.debug(
                f"Successfully loaded {len(self._constraints)} constraints"
            )
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Could not load constraints file: {e}. Starting with empty constraints."
            )
            self._constraints = {}

    def _save_constraints(self):
        """Save constraints to JSON file."""
        data = {
            "constraints": self._constraints,
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "total_constraints": len(self._constraints),
            },
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _constraint_to_dict(self, constraint: ApiConstraint) -> Dict[str, Any]:
        """Convert ApiConstraint to dictionary."""
        return {
            "id": constraint.id,
            "endpoint_id": constraint.endpoint_id,
            "type": (
                constraint.type.value
                if isinstance(constraint.type, ConstraintType)
                else constraint.type
            ),
            "description": constraint.description,
            "severity": constraint.severity,
            "source": constraint.source,
            "details": constraint.details,
            "created_at": constraint.created_at or datetime.now().isoformat(),
            "updated_at": constraint.updated_at or datetime.now().isoformat(),
        }

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

    async def create(self, constraint: ApiConstraint) -> ApiConstraint:
        """Create a new constraint."""
        if self.dataset_id:
            # Dataset-specific repository
            if not constraint.id:
                constraint.id = str(uuid.uuid4())

            constraint.created_at = datetime.now().isoformat()
            constraint.updated_at = constraint.created_at

            constraint_dict = self._constraint_to_dict(constraint)
            self._constraints[constraint.id] = constraint_dict
            self._save_constraints()

            self.logger.info(
                f"Created constraint: {constraint.id} for endpoint: {constraint.endpoint_id}"
            )
            return constraint
        else:
            # Global repository - this shouldn't be called for global mode
            # Constraints should be created in dataset-specific repositories
            raise NotImplementedError(
                "Cannot create constraints in global repository mode. Use dataset-specific repository."
            )

    async def get_by_id(self, constraint_id: str) -> Optional[ApiConstraint]:
        """Get constraint by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            constraint_data = self._constraints.get(constraint_id)
            if not constraint_data:
                return None
            return self._dict_to_constraint(constraint_data)
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_constraint_by_id(constraint_id)

    async def get_by_endpoint_id(
        self, endpoint_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ApiConstraint], int]:
        """Get all constraints for a specific endpoint with pagination."""
        if self.dataset_id:
            # Dataset-specific repository
            constraints = []
            for constraint_data in self._constraints.values():
                if constraint_data.get("endpoint_id") == endpoint_id:
                    constraints.append(self._dict_to_constraint(constraint_data))

            # Apply pagination
            paginated_constraints, total_count = paginate_list(
                constraints, offset, limit
            )

            self.logger.debug(
                f"Retrieved {len(paginated_constraints)} constraints for endpoint: {endpoint_id} (total: {total_count})"
            )
            return paginated_constraints, total_count
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_constraints_by_endpoint_id(
                endpoint_id, limit, offset
            )

    async def get_all(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ApiConstraint], int]:
        """Get all constraints with pagination."""
        if self.dataset_id:
            # Dataset-specific repository
            all_constraints = [
                self._dict_to_constraint(data) for data in self._constraints.values()
            ]
            # Apply pagination
            return paginate_list(all_constraints, offset, limit)
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_all_constraints(limit, offset)

    async def update(
        self, constraint_id: str, constraint: ApiConstraint
    ) -> Optional[ApiConstraint]:
        """Update an existing constraint."""
        if constraint_id not in self._constraints:
            return None

        # Preserve original creation date
        original_data = self._constraints[constraint_id]
        constraint.id = constraint_id
        constraint.created_at = original_data.get("created_at")
        constraint.updated_at = datetime.now().isoformat()

        constraint_dict = self._constraint_to_dict(constraint)
        self._constraints[constraint_id] = constraint_dict
        self._save_constraints()

        return constraint

    async def delete(self, constraint_id: str) -> bool:
        """Delete a constraint."""
        if constraint_id in self._constraints:
            del self._constraints[constraint_id]
            self._save_constraints()
            self.logger.info(f"Deleted constraint: {constraint_id}")
            return True
        self.logger.warning(f"Constraint not found for deletion: {constraint_id}")
        return False

    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all constraints for a specific endpoint."""
        if self.dataset_id:
            # Dataset-specific repository
            to_delete = [
                cid
                for cid, data in self._constraints.items()
                if data.get("endpoint_id") == endpoint_id
            ]

            for cid in to_delete:
                del self._constraints[cid]

            if to_delete:
                self._save_constraints()

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

                # Load constraints for this dataset
                constraints_file = dataset_dir / "constraints.json"
                if not constraints_file.exists():
                    continue

                with open(constraints_file, "r") as f:
                    data = json.load(f)

                constraints = data.get("constraints", {})
                to_delete = [
                    cid
                    for cid, constraint_data in constraints.items()
                    if constraint_data.get("endpoint_id") == endpoint_id
                ]

                # Delete constraints
                for cid in to_delete:
                    del constraints[cid]
                    deleted_count += 1

                # Save updated constraints
                if to_delete:
                    data["constraints"] = constraints
                    with open(constraints_file, "w") as f:
                        json.dump(data, f, indent=2)

            return deleted_count
