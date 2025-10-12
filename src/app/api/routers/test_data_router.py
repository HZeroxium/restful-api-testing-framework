# app/api/routers/test_data_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from app.api.dto.test_data_dto import (
    GenerateTestDataRequest,
    GenerateTestDataResponse,
    TestDataResponse,
    TestDataListResponse,
    UpdateTestDataRequest,
)
from application.services.test_data_service import TestDataService
from application.services.endpoint_service import EndpointService
from infra.di.container import test_data_service_dependency, endpoint_service_dependency
from schemas.tools.test_data_generator import TestData
from schemas.core.pagination import PaginationParams
from utils.pagination_utils import calculate_pagination_metadata

router = APIRouter(prefix="/test-data", tags=["test-data"])


def convert_test_data_to_response(test_data: TestData) -> TestDataResponse:
    """Convert TestData to TestDataResponse, handling datetime conversion."""
    test_data_dict = test_data.model_dump()
    # Convert string timestamps to datetime objects for the response
    test_data_dict["created_at"] = datetime.fromisoformat(test_data_dict["created_at"])
    test_data_dict["updated_at"] = datetime.fromisoformat(test_data_dict["updated_at"])
    return TestDataResponse(**test_data_dict)


@router.post(
    "/generate/by-endpoint-name/{endpoint_name}",
    response_model=GenerateTestDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate test data for an endpoint",
    description="Generate test data for the specified endpoint using the test data generator tool.",
)
async def generate_test_data_by_endpoint_name(
    endpoint_name: str,
    request: GenerateTestDataRequest,
    test_data_service: TestDataService = test_data_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Generate test data for an endpoint by name."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Get count of existing test data before deletion
        existing_test_data = await test_data_service.get_test_data_by_endpoint_id(
            endpoint.id
        )
        deleted_count = len(existing_test_data) if request.override_existing else 0

        # Validate dataset_id exists
        if not endpoint.dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Endpoint '{endpoint_name}' does not have a dataset_id. Cannot generate test data without dataset context.",
            )

        # Convert endpoint to dict for the generator
        endpoint_dict = {
            "id": endpoint.id,
            "name": endpoint.name,
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "input_schema": endpoint.input_schema,
            "output_schema": endpoint.output_schema,
            "tags": endpoint.tags,
            "auth_required": endpoint.auth_required,
            "auth_type": endpoint.auth_type,
            "dataset_id": endpoint.dataset_id,
        }

        # Generate test data
        generator_output = await test_data_service.generate_test_data_for_endpoint(
            endpoint_id=endpoint.id,
            endpoint_info=endpoint_dict,
            count=request.count,
            include_invalid=request.include_invalid_data,
            override_existing=request.override_existing,
        )

        # Convert to response format
        test_data_responses = [
            convert_test_data_to_response(test_data)
            for test_data in generator_output.test_data_collection
        ]

        return GenerateTestDataResponse(
            endpoint_id=endpoint.id,
            endpoint_name=endpoint_name,
            test_data_items=test_data_responses,
            total_count=len(test_data_responses),
            valid_count=sum(1 for item in test_data_responses if item.is_valid),
            invalid_count=sum(1 for item in test_data_responses if not item.is_valid),
            generation_success=True,
            deleted_existing_count=deleted_count,
            execution_timestamp=(
                test_data_responses[0].created_at.isoformat()
                if test_data_responses
                else ""
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test data: {str(e)}",
        )


@router.get(
    "/by-endpoint-name/{endpoint_name}",
    response_model=TestDataListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get test data for an endpoint by name",
    description="Retrieve all test data items for the specified endpoint.",
)
async def get_test_data_by_endpoint_name(
    endpoint_name: str,
    test_data_service: TestDataService = test_data_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Get test data for an endpoint by name."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Get test data
        test_data_items, total_count = (
            await test_data_service.get_test_data_by_endpoint_id(
                endpoint.id, limit=1000, offset=0
            )
        )

        # Convert to response format
        test_data_responses = [
            convert_test_data_to_response(test_data) for test_data in test_data_items
        ]

        return TestDataListResponse(
            test_data_items=test_data_responses,
            total_count=total_count,
            valid_count=sum(1 for item in test_data_responses if item.is_valid),
            invalid_count=sum(1 for item in test_data_responses if not item.is_valid),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test data: {str(e)}",
        )


@router.get(
    "/by-endpoint-id/{endpoint_id}",
    response_model=TestDataListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get test data for an endpoint by ID",
    description="Retrieve all test data items for the specified endpoint ID.",
)
async def get_test_data_by_endpoint_id(
    endpoint_id: str,
    pagination: PaginationParams = Depends(),
    test_data_service: TestDataService = test_data_service_dependency,
):
    """Get test data for an endpoint by ID."""
    try:
        # Get test data
        test_data_items, total_count = (
            await test_data_service.get_test_data_by_endpoint_id(
                endpoint_id, limit=pagination.limit, offset=pagination.offset
            )
        )

        # Convert to response format
        test_data_responses = [
            convert_test_data_to_response(test_data) for test_data in test_data_items
        ]

        # Calculate pagination metadata
        pagination_metadata = calculate_pagination_metadata(
            offset=pagination.offset, limit=pagination.limit, total_items=total_count
        )

        return TestDataListResponse(
            test_data_items=test_data_responses,
            total_count=total_count,
            valid_count=sum(1 for item in test_data_responses if item.is_valid),
            invalid_count=sum(1 for item in test_data_responses if not item.is_valid),
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test data: {str(e)}",
        )


@router.get(
    "/",
    response_model=TestDataListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all test data",
    description="Retrieve all test data items across all endpoints.",
)
async def get_all_test_data(
    pagination: PaginationParams = Depends(),
    test_data_service: TestDataService = test_data_service_dependency,
):
    """Get all test data with pagination."""
    try:
        # Get all test data
        all_test_data_items, total_count = await test_data_service.get_all_test_data(
            limit=pagination.limit, offset=pagination.offset
        )

        # Convert to response format
        test_data_responses = [
            TestDataResponse(**test_data.model_dump())
            for test_data in all_test_data_items
        ]

        print(f"Test data responses: {test_data_responses}")

        # Calculate pagination metadata
        pagination_metadata = calculate_pagination_metadata(
            offset=pagination.offset, limit=pagination.limit, total_items=total_count
        )

        return TestDataListResponse(
            test_data_items=test_data_responses,
            total_count=total_count,
            valid_count=sum(1 for item in test_data_responses if item.is_valid),
            invalid_count=sum(1 for item in test_data_responses if not item.is_valid),
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve all test data: {str(e)}",
        )


@router.get(
    "/{test_data_id}",
    response_model=TestDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific test data item",
    description="Retrieve a specific test data item by its ID.",
)
async def get_test_data_by_id(
    test_data_id: str,
    test_data_service: TestDataService = test_data_service_dependency,
):
    """Get specific test data item by ID."""
    try:
        test_data = await test_data_service.get_test_data_by_id(test_data_id)
        if not test_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test data with ID '{test_data_id}' not found",
            )

        return TestDataResponse(**test_data.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test data: {str(e)}",
        )


@router.delete(
    "/by-endpoint-name/{endpoint_name}",
    status_code=status.HTTP_200_OK,
    summary="Delete all test data for an endpoint by name",
    description="Delete all test data items for the specified endpoint.",
)
async def delete_test_data_by_endpoint_name(
    endpoint_name: str,
    test_data_service: TestDataService = test_data_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Delete all test data for an endpoint by name."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Delete test data
        deleted_count = await test_data_service.delete_test_data_by_endpoint_id(
            endpoint.id
        )

        return {
            "message": f"Deleted {deleted_count} test data items for endpoint '{endpoint_name}'",
            "deleted_count": deleted_count,
            "endpoint_id": endpoint.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete test data: {str(e)}",
        )


@router.put(
    "/{test_data_id}",
    response_model=TestDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Update test data item",
    description="Update a specific test data item.",
)
async def update_test_data(
    test_data_id: str,
    request: UpdateTestDataRequest,
    test_data_service: TestDataService = test_data_service_dependency,
):
    """Update test data item."""
    try:
        # Get existing test data
        existing_test_data = await test_data_service.get_test_data_by_id(test_data_id)
        if not existing_test_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test data with ID '{test_data_id}' not found",
            )

        # Update fields that are provided
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(existing_test_data, field):
                setattr(existing_test_data, field, value)

        # Save updated test data
        updated_test_data = await test_data_service.update_test_data(
            test_data_id, existing_test_data
        )
        if not updated_test_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update test data",
            )

        return TestDataResponse(**updated_test_data.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update test data: {str(e)}",
        )
