# application/services/endpoint_lookup_service.py

import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from schemas.tools.openapi_parser import EndpointInfo, AuthType
from common.logger import LoggerFactory, LoggerType, LogLevel


class EndpointLookupService:
    """Service for looking up endpoints across all datasets."""

    def __init__(self, datasets_base_path: str = "data/datasets"):
        self.datasets_base_path = Path(datasets_base_path)
        self.logger = LoggerFactory.get_logger(
            name="service.endpoint_lookup",
            logger_type=LoggerType.STANDARD,
            level=LogLevel.INFO,
        )

    def _load_endpoints_from_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Load all endpoints from a specific dataset."""
        endpoints_file = self.datasets_base_path / dataset_id / "endpoints.json"

        if not endpoints_file.exists():
            return {}

        try:
            with open(endpoints_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("endpoints", {})
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Could not load endpoints from dataset {dataset_id}: {e}"
            )
            return {}

    def _dict_to_endpoint(self, data: Dict[str, Any]) -> EndpointInfo:
        """Convert dictionary to EndpointInfo."""
        endpoint_data = {
            "name": data["name"],
            "description": data.get("description"),
            "path": data["path"],
            "method": data["method"],
            "tags": data.get("tags", []),
            "auth_required": data.get("auth_required", False),
            "auth_type": AuthType(data["auth_type"]) if data.get("auth_type") else None,
            "input_schema": data.get("input_schema", {}),
            "output_schema": data.get("output_schema", {}),
        }

        endpoint = EndpointInfo(**endpoint_data)
        endpoint.id = data.get("id")
        endpoint.dataset_id = data.get("dataset_id")
        endpoint.created_at = data.get("created_at")
        endpoint.updated_at = data.get("updated_at")

        return endpoint

    async def get_endpoint_by_id(self, endpoint_id: str) -> Optional[EndpointInfo]:
        """Get endpoint by ID across all datasets."""
        self.logger.debug(f"Looking up endpoint by ID: {endpoint_id}")

        # Get all dataset IDs
        if not self.datasets_base_path.exists():
            return None

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            endpoints = self._load_endpoints_from_dataset(dataset_id)

            if endpoint_id in endpoints:
                endpoint_data = endpoints[endpoint_id]
                self.logger.debug(
                    f"Found endpoint {endpoint_id} in dataset {dataset_id}"
                )
                return self._dict_to_endpoint(endpoint_data)

        self.logger.debug(f"Endpoint {endpoint_id} not found in any dataset")
        return None

    async def get_endpoint_by_name(self, name: str) -> Optional[EndpointInfo]:
        """Get endpoint by name across all datasets."""
        self.logger.debug(f"Looking up endpoint by name: {name}")

        # Get all dataset IDs
        if not self.datasets_base_path.exists():
            return None

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            endpoints = self._load_endpoints_from_dataset(dataset_id)

            for endpoint_data in endpoints.values():
                if endpoint_data.get("name") == name:
                    self.logger.debug(
                        f"Found endpoint '{name}' in dataset {dataset_id}"
                    )
                    return self._dict_to_endpoint(endpoint_data)

        self.logger.debug(f"Endpoint '{name}' not found in any dataset")
        return None

    async def get_all_endpoints(self) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Get all endpoints across all datasets.

        Returns:
            Tuple of (endpoints_dict, dataset_mapping) where dataset_mapping maps endpoint_id to dataset_id
        """
        all_endpoints = {}
        dataset_mapping = {}

        if not self.datasets_base_path.exists():
            return all_endpoints, dataset_mapping

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            endpoints = self._load_endpoints_from_dataset(dataset_id)

            for endpoint_id, endpoint_data in endpoints.items():
                all_endpoints[endpoint_id] = endpoint_data
                dataset_mapping[endpoint_id] = dataset_id

        self.logger.debug(
            f"Loaded {len(all_endpoints)} endpoints from {len(dataset_mapping)} datasets"
        )
        return all_endpoints, dataset_mapping

    async def get_endpoints_by_dataset_id(self, dataset_id: str) -> List[EndpointInfo]:
        """Get all endpoints for a specific dataset."""
        endpoints = self._load_endpoints_from_dataset(dataset_id)

        result = []
        for endpoint_data in endpoints.values():
            result.append(self._dict_to_endpoint(endpoint_data))

        return result

    async def search_endpoints_by_tag(self, tag: str) -> List[EndpointInfo]:
        """Search endpoints by tag across all datasets."""
        results = []

        if not self.datasets_base_path.exists():
            return results

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            endpoints = self._load_endpoints_from_dataset(dataset_dir.name)

            for endpoint_data in endpoints.values():
                if tag in endpoint_data.get("tags", []):
                    results.append(self._dict_to_endpoint(endpoint_data))

        return results

    async def search_endpoints_by_path(self, path_pattern: str) -> List[EndpointInfo]:
        """Search endpoints by path pattern across all datasets."""
        results = []

        if not self.datasets_base_path.exists():
            return results

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            endpoints = self._load_endpoints_from_dataset(dataset_dir.name)

            for endpoint_data in endpoints.values():
                if path_pattern.lower() in endpoint_data["path"].lower():
                    results.append(self._dict_to_endpoint(endpoint_data))

        return results

    async def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get statistics across all endpoints in all datasets."""
        all_endpoints, _ = await self.get_all_endpoints()

        total_endpoints = len(all_endpoints)
        method_counts = {}
        auth_counts = {}
        tag_counts = {}

        for endpoint_data in all_endpoints.values():
            # Method counts
            method = endpoint_data["method"]
            method_counts[method] = method_counts.get(method, 0) + 1

            # Auth type counts
            auth_type = endpoint_data.get("auth_type", "none")
            auth_counts[auth_type] = auth_counts.get(auth_type, 0) + 1

            # Tag counts
            for tag in endpoint_data.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_endpoints": total_endpoints,
            "method_distribution": method_counts,
            "auth_type_distribution": auth_counts,
            "tag_distribution": tag_counts,
            "last_updated": "now",  # Could be improved with actual timestamp
        }
