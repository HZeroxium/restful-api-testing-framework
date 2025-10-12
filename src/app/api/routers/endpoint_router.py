# app/api/routers/endpoint_router.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.core.pagination import PaginationParams
from utils.pagination_utils import calculate_pagination_metadata
from application.services.endpoint_service import EndpointService
from schemas.tools.openapi_parser import EndpointInfo, AuthType
from app.api.dto.endpoint_dto import (
    EndpointCreateRequest,
    EndpointUpdateRequest,
    EndpointResponse,
    EndpointListResponse,
    ParseSpecRequest,
    ParseSpecResponse,
    EndpointStatsResponse,
    SearchEndpointsRequest,
    ErrorResponse,
)
from infra.di.container import endpoint_service_dependency

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.post("/", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    request: EndpointCreateRequest,
    service: EndpointService = endpoint_service_dependency,
):
    """Create a new endpoint."""
    try:
        # Convert request to EndpointInfo
        endpoint = EndpointInfo(
            name=request.name,
            description=request.description,
            path=request.path,
            method=request.method,
            tags=request.tags,
            auth_required=request.auth_required,
            auth_type=request.auth_type,
            input_schema=request.input_schema,
            output_schema=request.output_schema,
        )

        created_endpoint = await service.create_endpoint(endpoint)
        return EndpointResponse.from_endpoint_info(created_endpoint)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create endpoint: {str(e)}",
        )


@router.get("/", response_model=EndpointListResponse)
async def list_endpoints(
    pagination: PaginationParams = Depends(),
    service: EndpointService = endpoint_service_dependency,
):
    """Get all endpoints with pagination."""
    try:
        endpoints, total_count = await service.get_all_endpoints(
            pagination.limit, pagination.offset
        )

        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )

        return EndpointListResponse(
            endpoints=[EndpointResponse.from_endpoint_info(ep) for ep in endpoints],
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list endpoints: {str(e)}",
        )


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    service: EndpointService = endpoint_service_dependency,
):
    """Get endpoint by ID."""
    try:
        endpoint = await service.get_endpoint_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with ID {endpoint_id} not found",
            )

        return EndpointResponse.from_endpoint_info(endpoint)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint: {str(e)}",
        )


@router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    request: EndpointUpdateRequest,
    service: EndpointService = endpoint_service_dependency,
):
    """Update an existing endpoint."""
    try:
        # Get existing endpoint
        existing_endpoint = await service.get_endpoint_by_id(endpoint_id)
        if not existing_endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with ID {endpoint_id} not found",
            )

        # Update fields that are provided
        update_data = request.model_dump(exclude_unset=True)

        # Create updated endpoint
        updated_endpoint = EndpointInfo(
            name=update_data.get("name", existing_endpoint.name),
            description=update_data.get("description", existing_endpoint.description),
            path=update_data.get("path", existing_endpoint.path),
            method=update_data.get("method", existing_endpoint.method),
            tags=update_data.get("tags", existing_endpoint.tags),
            auth_required=update_data.get(
                "auth_required", existing_endpoint.auth_required
            ),
            auth_type=update_data.get("auth_type", existing_endpoint.auth_type),
            input_schema=update_data.get(
                "input_schema", existing_endpoint.input_schema
            ),
            output_schema=update_data.get(
                "output_schema", existing_endpoint.output_schema
            ),
        )

        result = await service.update_endpoint(endpoint_id, updated_endpoint)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with ID {endpoint_id} not found",
            )

        return EndpointResponse.from_endpoint_info(result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update endpoint: {str(e)}",
        )


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    service: EndpointService = endpoint_service_dependency,
):
    """Delete an endpoint."""
    try:
        success = await service.delete_endpoint(endpoint_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with ID {endpoint_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete endpoint: {str(e)}",
        )


@router.get("/search/tag/{tag}", response_model=EndpointListResponse)
async def search_by_tag(
    tag: str,
    pagination: PaginationParams = Depends(),
    service: EndpointService = endpoint_service_dependency,
):
    """Search endpoints by tag."""
    try:
        endpoints, total_count = await service.search_endpoints_by_tag(
            tag, pagination.limit, pagination.offset
        )
        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )
        return EndpointListResponse(
            endpoints=[EndpointResponse.from_endpoint_info(ep) for ep in endpoints],
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search endpoints by tag: {str(e)}",
        )


@router.get("/search/path", response_model=EndpointListResponse)
async def search_by_path(
    pattern: str = Query(..., description="Path pattern to search"),
    pagination: PaginationParams = Depends(),
    service: EndpointService = endpoint_service_dependency,
):
    """Search endpoints by path pattern."""
    try:
        endpoints, total_count = await service.search_endpoints_by_path(
            pattern, pagination.limit, pagination.offset
        )
        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )
        return EndpointListResponse(
            endpoints=[EndpointResponse.from_endpoint_info(ep) for ep in endpoints],
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search endpoints by path: {str(e)}",
        )


@router.get("/stats", response_model=EndpointStatsResponse)
async def get_endpoint_stats(
    service: EndpointService = endpoint_service_dependency,
):
    """Get endpoint statistics."""
    try:
        stats = await service.get_endpoint_stats()
        return EndpointStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint stats: {str(e)}",
        )


@router.post("/parse-spec", response_model=ParseSpecResponse)
async def parse_openapi_spec(
    request: ParseSpecRequest,
    service: EndpointService = endpoint_service_dependency,
):
    """Parse OpenAPI specification and create endpoints."""
    try:
        # Convert request to OpenAPIParserInput
        from schemas.tools.openapi_parser import OpenAPIParserInput

        parser_input = OpenAPIParserInput(
            spec_source=request.spec_source,
            source_type=request.source_type,
            filter_tags=request.filter_tags,
            filter_paths=request.filter_paths,
            filter_methods=request.filter_methods,
        )

        # Parse specification
        result = await service.parse_openapi_spec(parser_input)

        return ParseSpecResponse(
            success=True,
            message=f"Successfully parsed OpenAPI specification. Created {result.created_endpoints} endpoints, skipped {result.skipped_endpoints} duplicates.",
            api_title=result.title,
            api_version=result.version,
            total_endpoints=result.endpoint_count,
            created_endpoints=getattr(result, "created_endpoints", 0),
            skipped_endpoints=getattr(result, "skipped_endpoints", 0),
            endpoints=[
                EndpointResponse.from_endpoint_info(ep) for ep in result.endpoints[:10]
            ],  # Limit to first 10
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse OpenAPI specification: {str(e)}",
        )


@router.get("/export/json")
async def export_endpoints(
    service: EndpointService = endpoint_service_dependency,
):
    """Export all endpoints as JSON."""
    try:
        export_data = await service.export_endpoints("json")
        return export_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export endpoints: {str(e)}",
        )


@router.get(
    "/by-endpoint-name/{endpoint_name}",
    response_model=EndpointResponse,
    summary="Get endpoint by name",
)
async def get_endpoint_by_name(
    endpoint_name: str,
    service: EndpointService = endpoint_service_dependency,
):
    """Get a specific endpoint by name."""
    try:
        endpoint = await service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with name '{endpoint_name}' not found",
            )

        return EndpointResponse.from_endpoint_info(endpoint)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint by name: {str(e)}",
        )
