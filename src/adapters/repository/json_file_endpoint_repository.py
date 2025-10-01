# adapters/repository/json_file_endpoint_repository.py

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.tools.openapi_parser import EndpointInfo, AuthType


class JsonFileEndpointRepository(EndpointRepositoryInterface):
    """JSON file-based implementation of EndpointRepositoryInterface."""

    def __init__(self, file_path: str = "data/endpoints.json"):
        self.file_path = Path(file_path)
        self._ensure_file_exists()
        self._load_endpoints()

    def _ensure_file_exists(self):
        """Ensure the JSON file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "endpoints": {},
                        "metadata": {"created_at": datetime.now().isoformat()},
                    },
                    f,
                    indent=2,
                )

    def _load_endpoints(self):
        """Load endpoints from JSON file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._endpoints = data.get("endpoints", {})
        except (json.JSONDecodeError, FileNotFoundError):
            self._endpoints = {}

    def _save_endpoints(self):
        """Save endpoints to JSON file."""
        data = {
            "endpoints": self._endpoints,
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "total_endpoints": len(self._endpoints),
            },
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _endpoint_to_dict(self, endpoint: EndpointInfo) -> Dict[str, Any]:
        """Convert EndpointInfo to dictionary."""
        return {
            "id": getattr(endpoint, "id", None),
            "name": endpoint.name,
            "description": endpoint.description,
            "path": endpoint.path,
            "method": endpoint.method,
            "tags": endpoint.tags,
            "auth_required": endpoint.auth_required,
            "auth_type": endpoint.auth_type.value if endpoint.auth_type else None,
            "input_schema": endpoint.input_schema,
            "output_schema": endpoint.output_schema,
            "created_at": getattr(endpoint, "created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
        }

    def _dict_to_endpoint(self, data: Dict[str, Any]) -> EndpointInfo:
        """Convert dictionary to EndpointInfo."""
        # Create endpoint without id first
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
        # Set additional attributes
        endpoint.id = data.get("id")
        endpoint.created_at = data.get("created_at")
        endpoint.updated_at = data.get("updated_at")

        return endpoint

    async def create(self, endpoint: EndpointInfo) -> EndpointInfo:
        """Create a new endpoint."""
        endpoint_id = str(uuid.uuid4())
        endpoint.id = endpoint_id
        endpoint.created_at = datetime.now().isoformat()

        endpoint_dict = self._endpoint_to_dict(endpoint)
        self._endpoints[endpoint_id] = endpoint_dict
        self._save_endpoints()

        return endpoint

    async def get_by_id(self, endpoint_id: str) -> Optional[EndpointInfo]:
        """Get endpoint by ID."""
        endpoint_data = self._endpoints.get(endpoint_id)
        if not endpoint_data:
            return None
        return self._dict_to_endpoint(endpoint_data)

    async def get_by_path_method(
        self, path: str, method: str
    ) -> Optional[EndpointInfo]:
        """Get endpoint by path and method."""
        for endpoint_data in self._endpoints.values():
            if (
                endpoint_data["path"] == path
                and endpoint_data["method"].upper() == method.upper()
            ):
                return self._dict_to_endpoint(endpoint_data)
        return None

    async def get_all(self) -> List[EndpointInfo]:
        """Get all endpoints."""
        return [self._dict_to_endpoint(data) for data in self._endpoints.values()]

    async def update(
        self, endpoint_id: str, endpoint: EndpointInfo
    ) -> Optional[EndpointInfo]:
        """Update an existing endpoint."""
        if endpoint_id not in self._endpoints:
            return None

        # Preserve original creation date
        original_data = self._endpoints[endpoint_id]
        endpoint.id = endpoint_id
        endpoint.created_at = original_data.get("created_at")
        endpoint.updated_at = datetime.now().isoformat()

        endpoint_dict = self._endpoint_to_dict(endpoint)
        self._endpoints[endpoint_id] = endpoint_dict
        self._save_endpoints()

        return endpoint

    async def delete(self, endpoint_id: str) -> bool:
        """Delete an endpoint."""
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            self._save_endpoints()
            return True
        return False

    async def search_by_tag(self, tag: str) -> List[EndpointInfo]:
        """Search endpoints by tag."""
        results = []
        for endpoint_data in self._endpoints.values():
            if tag in endpoint_data.get("tags", []):
                results.append(self._dict_to_endpoint(endpoint_data))
        return results

    async def search_by_path(self, path_pattern: str) -> List[EndpointInfo]:
        """Search endpoints by path pattern."""
        results = []
        for endpoint_data in self._endpoints.values():
            if path_pattern.lower() in endpoint_data["path"].lower():
                results.append(self._dict_to_endpoint(endpoint_data))
        return results

    async def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        total_endpoints = len(self._endpoints)

        # Count by method
        method_counts = {}
        # Count by auth type
        auth_counts = {}
        # Count by tags
        tag_counts = {}

        for endpoint_data in self._endpoints.values():
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
            "last_updated": datetime.now().isoformat(),
        }
