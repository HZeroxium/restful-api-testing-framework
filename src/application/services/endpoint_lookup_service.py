# application/services/endpoint_lookup_service.py

import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from schemas.tools.openapi_parser import EndpointInfo, AuthType
from common.logger import LoggerFactory, LoggerType, LogLevel
from utils.pagination_utils import paginate_list


class EndpointLookupService:
    """Service for looking up endpoints across all datasets."""

    def __init__(
        self,
        datasets_base_path: str = "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets",
    ):
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

    async def get_all_endpoints(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Get all endpoints across all datasets with pagination."""
        all_endpoints = []

        if not self.datasets_base_path.exists():
            return paginate_list(all_endpoints, offset, limit)

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_id = dataset_dir.name
            endpoints = self._load_endpoints_from_dataset(dataset_id)

            for endpoint_data in endpoints.values():
                all_endpoints.append(self._dict_to_endpoint(endpoint_data))

        self.logger.debug(f"Loaded {len(all_endpoints)} endpoints from datasets")
        return paginate_list(all_endpoints, offset, limit)

    async def get_endpoints_by_dataset_id(self, dataset_id: str) -> List[EndpointInfo]:
        """Get all endpoints for a specific dataset."""
        endpoints = self._load_endpoints_from_dataset(dataset_id)

        result = []
        for endpoint_data in endpoints.values():
            result.append(self._dict_to_endpoint(endpoint_data))

        return result

    async def search_endpoints_by_tag(
        self, tag: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Search endpoints by tag across all datasets with pagination."""
        results = []

        if not self.datasets_base_path.exists():
            return paginate_list(results, offset, limit)

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            endpoints = self._load_endpoints_from_dataset(dataset_dir.name)

            for endpoint_data in endpoints.values():
                if tag in endpoint_data.get("tags", []):
                    results.append(self._dict_to_endpoint(endpoint_data))

        return paginate_list(results, offset, limit)

    async def search_endpoints_by_path(
        self, path_pattern: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Search endpoints by path pattern across all datasets with pagination."""
        results = []

        if not self.datasets_base_path.exists():
            return paginate_list(results, offset, limit)

        for dataset_dir in self.datasets_base_path.iterdir():
            if not dataset_dir.is_dir():
                continue

            endpoints = self._load_endpoints_from_dataset(dataset_dir.name)

            for endpoint_data in endpoints.values():
                if path_pattern.lower() in endpoint_data["path"].lower():
                    results.append(self._dict_to_endpoint(endpoint_data))

        return paginate_list(results, offset, limit)

    async def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get statistics across all endpoints in all datasets."""
        all_endpoints, _ = await self.get_all_endpoints()

        total_endpoints = len(all_endpoints)
        method_counts = {}
        auth_counts = {}
        tag_counts = {}

        for endpoint in all_endpoints:
            # Method counts
            method = endpoint.method
            method_counts[method] = method_counts.get(method, 0) + 1

            # Auth type counts
            auth_type = endpoint.auth_type.value if endpoint.auth_type else "none"
            auth_counts[auth_type] = auth_counts.get(auth_type, 0) + 1

            # Tag counts
            for tag in endpoint.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_endpoints": total_endpoints,
            "method_distribution": method_counts,
            "auth_type_distribution": auth_counts,
            "tag_distribution": tag_counts,
            "last_updated": "now",  # Could be improved with actual timestamp
        }
