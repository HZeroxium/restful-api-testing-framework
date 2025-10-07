# adapters/repository/json_file_validation_script_repository.py

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from domain.ports.validation_script_repository import (
    ValidationScriptRepositoryInterface,
)
from schemas.tools.test_script_generator import ValidationScript
from common.logger import LoggerFactory, LoggerType, LogLevel
from application.services.validation_script_lookup_service import (
    ValidationScriptLookupService,
)


class JsonFileValidationScriptRepository(ValidationScriptRepositoryInterface):
    """JSON file-based implementation of ValidationScriptRepositoryInterface."""

    def __init__(
        self,
        file_path: str = "data/validation_scripts.json",
        dataset_id: Optional[str] = None,
    ):
        self.dataset_id = dataset_id
        if dataset_id:
            # Dataset-specific storage
            self.file_path = (
                Path("data/datasets") / dataset_id / "validation_scripts.json"
            )
            self.logger = LoggerFactory.get_logger(
                name="repository.validation_script",
                logger_type=LoggerType.STANDARD,
                level=LogLevel.INFO,
            )
            self._ensure_file_exists()
            self._load_scripts()
        else:
            # Global storage - use lookup service to search across all datasets
            self.file_path = Path(file_path)
            self.lookup_service = ValidationScriptLookupService()
            self.logger = LoggerFactory.get_logger(
                name="repository.validation_script",
                logger_type=LoggerType.STANDARD,
                level=LogLevel.INFO,
            )
            self.logger.info(
                f"Initializing JsonFileValidationScriptRepository (global mode) with lookup service"
            )

    def _ensure_file_exists(self):
        """Ensure the JSON file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "scripts": {},
                        "metadata": {"created_at": datetime.now().isoformat()},
                    },
                    f,
                    indent=2,
                )

    def _load_scripts(self):
        """Load validation scripts from JSON file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._scripts = data.get("scripts", {})
        except (json.JSONDecodeError, FileNotFoundError):
            self._scripts = {}

    def _save_scripts(self):
        """Save validation scripts to JSON file."""
        data = {
            "scripts": self._scripts,
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "total_scripts": len(self._scripts),
            },
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _script_to_dict(self, script: ValidationScript) -> Dict[str, Any]:
        """Convert ValidationScript to dictionary."""
        return {
            "id": script.id,
            "endpoint_id": script.endpoint_id,
            "name": script.name,
            "script_type": script.script_type,
            "validation_code": script.validation_code,
            "description": script.description,
            "constraint_id": script.constraint_id,
            "created_at": script.created_at or datetime.now().isoformat(),
            "updated_at": script.updated_at or datetime.now().isoformat(),
        }

    def _dict_to_script(self, data: Dict[str, Any]) -> ValidationScript:
        """Convert dictionary to ValidationScript."""
        return ValidationScript(
            id=data["id"],
            endpoint_id=data.get("endpoint_id"),
            name=data["name"],
            script_type=data["script_type"],
            validation_code=data["validation_code"],
            description=data["description"],
            constraint_id=data.get("constraint_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def create(self, script: ValidationScript) -> ValidationScript:
        """Create a new validation script."""
        if not script.id:
            script.id = str(uuid.uuid4())

        script.created_at = datetime.now().isoformat()
        script.updated_at = script.created_at

        script_dict = self._script_to_dict(script)
        self._scripts[script.id] = script_dict
        self._save_scripts()

        self.logger.info(
            f"Created validation script: {script.id} for endpoint: {script.endpoint_id}"
        )
        return script

    async def get_by_id(self, script_id: str) -> Optional[ValidationScript]:
        """Get validation script by ID."""
        if self.dataset_id:
            # Dataset-specific repository
            script_data = self._scripts.get(script_id)
            if not script_data:
                return None
            return self._dict_to_script(script_data)
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_script_by_id(script_id)

    async def get_by_endpoint_id(self, endpoint_id: str) -> List[ValidationScript]:
        """Get all validation scripts for a specific endpoint."""
        if self.dataset_id:
            # Dataset-specific repository
            scripts = []
            for script_data in self._scripts.values():
                if script_data.get("endpoint_id") == endpoint_id:
                    scripts.append(self._dict_to_script(script_data))

            self.logger.debug(
                f"Retrieved {len(scripts)} validation scripts for endpoint: {endpoint_id}"
            )
            return scripts
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_scripts_by_endpoint_id(endpoint_id)

    async def get_all(self) -> List[ValidationScript]:
        """Get all validation scripts."""
        if self.dataset_id:
            # Dataset-specific repository
            return [self._dict_to_script(data) for data in self._scripts.values()]
        else:
            # Global repository - use lookup service
            all_scripts, _ = await self.lookup_service.get_all_scripts()
            return [
                self.lookup_service._dict_to_script(data)
                for data in all_scripts.values()
            ]

    async def update(
        self, script_id: str, script: ValidationScript
    ) -> Optional[ValidationScript]:
        """Update an existing validation script."""
        if script_id not in self._scripts:
            return None

        # Preserve original creation date
        original_data = self._scripts[script_id]
        script.id = script_id
        script.created_at = original_data.get("created_at")
        script.updated_at = datetime.now().isoformat()

        script_dict = self._script_to_dict(script)
        self._scripts[script_id] = script_dict
        self._save_scripts()

        return script

    async def delete(self, script_id: str) -> bool:
        """Delete a validation script."""
        if script_id in self._scripts:
            del self._scripts[script_id]
            self._save_scripts()
            return True
        return False

    async def delete_by_endpoint_id(self, endpoint_id: str) -> int:
        """Delete all validation scripts for a specific endpoint."""
        to_delete = [
            sid
            for sid, data in self._scripts.items()
            if data.get("endpoint_id") == endpoint_id
        ]

        for sid in to_delete:
            del self._scripts[sid]

        if to_delete:
            self._save_scripts()

        return len(to_delete)

    async def get_by_constraint_id(self, constraint_id: str) -> List[ValidationScript]:
        """Get all validation scripts for a specific constraint."""
        if self.dataset_id:
            # Dataset-specific repository
            scripts = []
            for script_data in self._scripts.values():
                if script_data.get("constraint_id") == constraint_id:
                    scripts.append(self._dict_to_script(script_data))
            return scripts
        else:
            # Global repository - use lookup service
            return await self.lookup_service.get_scripts_by_constraint_id(constraint_id)
