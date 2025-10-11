# application/services/validation_script_lookup_service.py

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from schemas.tools.test_script_generator import ValidationScript
from common.logger import LoggerFactory, LoggerType, LogLevel


class ValidationScriptLookupService:
    """Service for looking up validation scripts across all datasets."""

    def __init__(
        self,
        datasets_base_path: str = "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets",
    ):
        self.datasets_base_path = Path(datasets_base_path)
        self.logger = LoggerFactory.get_logger(
            name="service.validation_script_lookup",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    def _load_scripts_from_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Load all validation scripts from a specific dataset."""
        scripts_file = self.datasets_base_path / dataset_id / "validation_scripts.json"

        if not scripts_file.exists():
            return {}

        try:
            with open(scripts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("scripts", {})
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Could not load validation scripts from dataset {dataset_id}: {e}"
            )
            return {}

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

    async def get_script_by_id(self, script_id: str) -> Optional[ValidationScript]:
        """Get validation script by ID across all datasets."""
        self.logger.debug(f"Looking up validation script by ID: {script_id}")

        if not self.datasets_base_path.exists():
            return None

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            scripts = self._load_scripts_from_dataset(dataset_id)

            if script_id in scripts:
                script_data = scripts[script_id]
                self.logger.debug(
                    f"Found validation script {script_id} in dataset {dataset_id}"
                )
                return self._dict_to_script(script_data)

        self.logger.debug(f"Validation script {script_id} not found in any dataset")
        return None

    async def get_all_scripts(self) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Get all validation scripts across all datasets.

        Returns:
            Tuple of (scripts_dict, dataset_mapping) where dataset_mapping maps script_id to dataset_id
        """
        all_scripts = {}
        dataset_mapping = {}

        if not self.datasets_base_path.exists():
            return all_scripts, dataset_mapping

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            scripts = self._load_scripts_from_dataset(dataset_id)

            for script_id, script_data in scripts.items():
                all_scripts[script_id] = script_data
                dataset_mapping[script_id] = dataset_id

        self.logger.debug(
            f"Loaded {len(all_scripts)} validation scripts from {len(dataset_mapping)} datasets"
        )
        return all_scripts, dataset_mapping

    async def get_scripts_by_endpoint_id(
        self, endpoint_id: str
    ) -> List[ValidationScript]:
        """Get all validation scripts for a specific endpoint across all datasets."""
        results = []

        if not self.datasets_base_path.exists():
            return results

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            scripts = self._load_scripts_from_dataset(dataset_dir.name)

            for script_data in scripts.values():
                if script_data.get("endpoint_id") == endpoint_id:
                    results.append(self._dict_to_script(script_data))

        return results

    async def get_scripts_by_constraint_id(
        self, constraint_id: str
    ) -> List[ValidationScript]:
        """Get all validation scripts for a specific constraint across all datasets."""
        results = []

        if not self.datasets_base_path.exists():
            return results

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            scripts = self._load_scripts_from_dataset(dataset_dir.name)

            for script_data in scripts.values():
                if script_data.get("constraint_id") == constraint_id:
                    results.append(self._dict_to_script(script_data))

        return results

    async def get_scripts_by_dataset_id(
        self, dataset_id: str
    ) -> List[ValidationScript]:
        """Get all validation scripts for a specific dataset."""
        scripts = self._load_scripts_from_dataset(dataset_id)

        result = []
        for script_data in scripts.values():
            result.append(self._dict_to_script(script_data))

        return result
