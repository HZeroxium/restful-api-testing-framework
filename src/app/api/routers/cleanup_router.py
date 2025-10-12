# app/api/routers/cleanup_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from application.services.constraint_service import ConstraintService
from application.services.validation_script_service import ValidationScriptService
from application.services.test_data_service import TestDataService
from application.services.test_execution_service import TestExecutionService
from application.services.endpoint_service import EndpointService
from infra.di.container import (
    constraint_service_dependency,
    validation_script_service_dependency,
    test_data_service_dependency,
    test_execution_service_dependency,
    endpoint_service_dependency,
)

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


@router.delete(
    "/endpoint/{endpoint_name}",
    status_code=status.HTTP_200_OK,
    summary="Delete all artifacts for an endpoint",
    description="Delete all constraints, validation scripts, test data, and execution history for the specified endpoint.",
)
async def cleanup_endpoint_artifacts(
    endpoint_name: str,
    constraint_service: ConstraintService = constraint_service_dependency,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    test_data_service: TestDataService = test_data_service_dependency,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Delete all artifacts (constraints, scripts, test data, executions) for an endpoint."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Delete executions first (as they depend on test data)
        execution_deleted_count = (
            await test_execution_service.delete_executions_by_endpoint_id(endpoint.id)
        )

        # Delete test data
        test_data_deleted_count = (
            await test_data_service.delete_test_data_by_endpoint_id(endpoint.id)
        )

        # Delete validation scripts
        script_deleted_count = (
            await validation_script_service.delete_validation_scripts_by_endpoint_name(
                endpoint_name
            )
        )

        # Delete constraints (this should also delete related validation scripts)
        constraint_deleted_count = (
            await constraint_service.delete_constraints_by_endpoint_name(endpoint_name)
        )

        return {
            "message": f"Successfully cleaned up all artifacts for endpoint '{endpoint_name}'",
            "endpoint_name": endpoint_name,
            "endpoint_id": endpoint.id,
            "deleted_counts": {
                "executions": execution_deleted_count,
                "test_data": test_data_deleted_count,
                "validation_scripts": script_deleted_count,
                "constraints": constraint_deleted_count,
            },
            "total_deleted": (
                execution_deleted_count
                + test_data_deleted_count
                + script_deleted_count
                + constraint_deleted_count
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup endpoint artifacts: {str(e)}",
        )


@router.delete(
    "/endpoint/{endpoint_name}/constraints",
    status_code=status.HTTP_200_OK,
    summary="Delete all constraints for an endpoint",
    description="Delete all constraints and related validation scripts for the specified endpoint.",
)
async def cleanup_endpoint_constraints(
    endpoint_name: str,
    constraint_service: ConstraintService = constraint_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Delete all constraints and related validation scripts for an endpoint."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Delete constraints (this should also delete related validation scripts)
        deleted_count = await constraint_service.delete_constraints_by_endpoint_name(
            endpoint_name
        )

        return {
            "message": f"Successfully deleted {deleted_count} constraint(s) for endpoint '{endpoint_name}'",
            "endpoint_name": endpoint_name,
            "endpoint_id": endpoint.id,
            "deleted_count": deleted_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup endpoint constraints: {str(e)}",
        )


@router.delete(
    "/endpoint/{endpoint_name}/test-data",
    status_code=status.HTTP_200_OK,
    summary="Delete all test data for an endpoint",
    description="Delete all test data for the specified endpoint.",
)
async def cleanup_endpoint_test_data(
    endpoint_name: str,
    test_data_service: TestDataService = test_data_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Delete all test data for an endpoint."""
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
            "message": f"Successfully deleted {deleted_count} test data item(s) for endpoint '{endpoint_name}'",
            "endpoint_name": endpoint_name,
            "endpoint_id": endpoint.id,
            "deleted_count": deleted_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup endpoint test data: {str(e)}",
        )


@router.delete(
    "/endpoint/{endpoint_name}/executions",
    status_code=status.HTTP_200_OK,
    summary="Delete all execution history for an endpoint",
    description="Delete all execution history for the specified endpoint.",
)
async def cleanup_endpoint_executions(
    endpoint_name: str,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Delete all execution history for an endpoint."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Delete executions
        deleted_count = await test_execution_service.delete_executions_by_endpoint_id(
            endpoint.id
        )

        return {
            "message": f"Successfully deleted {deleted_count} execution(s) for endpoint '{endpoint_name}'",
            "endpoint_name": endpoint_name,
            "endpoint_id": endpoint.id,
            "deleted_count": deleted_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup endpoint executions: {str(e)}",
        )
