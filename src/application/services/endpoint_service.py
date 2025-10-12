# application/services/endpoint_service.py

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from domain.ports.endpoint_repository import EndpointRepositoryInterface
from schemas.tools.openapi_parser import (
    EndpointInfo,
    OpenAPIParserInput,
    OpenAPIParserOutput,
)
from tools.core.openapi_parser import OpenAPIParserTool


class EndpointService:
    """Service for managing EndpointInfo operations."""

    def __init__(self, repository: EndpointRepositoryInterface):
        self.repository = repository

    async def create_endpoint(self, endpoint: EndpointInfo) -> EndpointInfo:
        """Create a new endpoint."""
        # Check if endpoint already exists
        existing = await self.repository.get_by_path_method(
            endpoint.path, endpoint.method
        )
        if existing:
            raise ValueError(
                f"Endpoint {endpoint.method} {endpoint.path} already exists"
            )

        return await self.repository.create(endpoint)

    async def get_endpoint_by_id(self, endpoint_id: str) -> Optional[EndpointInfo]:
        """Get endpoint by ID."""
        return await self.repository.get_by_id(endpoint_id)

    async def get_endpoint_by_name(self, name: str) -> Optional[EndpointInfo]:
        """Get endpoint by name."""
        return await self.repository.get_by_name(name)

    async def get_endpoint_by_path_method(
        self, path: str, method: str
    ) -> Optional[EndpointInfo]:
        """Get endpoint by path and method."""
        return await self.repository.get_by_path_method(path, method)

    async def get_all_endpoints(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Get all endpoints with pagination."""
        return await self.repository.get_all(limit, offset)

    async def update_endpoint(
        self, endpoint_id: str, endpoint: EndpointInfo
    ) -> Optional[EndpointInfo]:
        """Update an existing endpoint."""
        # Check if endpoint exists
        existing = await self.repository.get_by_id(endpoint_id)
        if not existing:
            return None

        # Check if new path/method combination conflicts with other endpoints
        if existing.path != endpoint.path or existing.method != endpoint.method:
            conflicting = await self.repository.get_by_path_method(
                endpoint.path, endpoint.method
            )
            if conflicting and conflicting.id != endpoint_id:
                raise ValueError(
                    f"Endpoint {endpoint.method} {endpoint.path} already exists"
                )

        return await self.repository.update(endpoint_id, endpoint)

    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete an endpoint."""
        return await self.repository.delete(endpoint_id)

    async def search_endpoints_by_tag(
        self, tag: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Search endpoints by tag with pagination."""
        return await self.repository.search_by_tag(tag, limit, offset)

    async def search_endpoints_by_path(
        self, path_pattern: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[EndpointInfo], int]:
        """Search endpoints by path pattern with pagination."""
        return await self.repository.search_by_path(path_pattern, limit, offset)

    async def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get endpoint statistics."""
        return await self.repository.get_stats()

    async def parse_openapi_spec(
        self, spec_input: OpenAPIParserInput
    ) -> OpenAPIParserOutput:
        """Parse OpenAPI specification and create endpoints."""
        # Use existing OpenAPIParserTool
        parser_tool = OpenAPIParserTool(verbose=False, cache_enabled=False)

        try:
            # Parse the specification
            parse_result = await parser_tool.execute(spec_input)

            # Save parsed endpoints to repository
            created_endpoints = []
            for endpoint in parse_result.endpoints:
                try:
                    created_endpoint = await self.create_endpoint(endpoint)
                    created_endpoints.append(created_endpoint)
                except ValueError as e:
                    # Endpoint already exists, skip
                    continue

            # Update result with created endpoints info
            parse_result.created_endpoints = len(created_endpoints)
            parse_result.skipped_endpoints = len(parse_result.endpoints) - len(
                created_endpoints
            )

            return parse_result

        except Exception as e:
            raise RuntimeError(f"Failed to parse OpenAPI specification: {str(e)}")

    async def bulk_create_endpoints(
        self, endpoints: List[EndpointInfo]
    ) -> Dict[str, Any]:
        """Bulk create multiple endpoints."""
        results = {"created": [], "skipped": [], "errors": []}

        for endpoint in endpoints:
            try:
                created_endpoint = await self.create_endpoint(endpoint)
                results["created"].append(created_endpoint)
            except ValueError as e:
                # Endpoint already exists
                results["skipped"].append({"endpoint": endpoint, "reason": str(e)})
            except Exception as e:
                # Other errors
                results["errors"].append({"endpoint": endpoint, "error": str(e)})

        return results

    async def export_endpoints(self, format: str = "json") -> Dict[str, Any]:
        """Export all endpoints in specified format."""
        endpoints, total_count = await self.get_all_endpoints()
        stats = await self.get_endpoint_stats()

        return {
            "endpoints": [self._endpoint_to_dict(endpoint) for endpoint in endpoints],
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_count": total_count,
                "stats": stats,
            },
        }

    def _endpoint_to_dict(self, endpoint: EndpointInfo) -> Dict[str, Any]:
        """Convert EndpointInfo to dictionary for export."""
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
            "created_at": getattr(endpoint, "created_at", None),
            "updated_at": getattr(endpoint, "updated_at", None),
        }
