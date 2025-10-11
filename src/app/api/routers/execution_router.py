# app/api/routers/execution_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.api.dto.execution_dto import (
    ExecuteTestRequest,
    ExecuteTestResponse,
    ExecutionHistoryResponse,
    ExecutionHistoryListResponse,
    ExecutionDetailResponse,
    TestCaseExecutionResultResponse,
)
from application.services.test_execution_service import TestExecutionService
from application.services.endpoint_service import EndpointService
from infra.di.container import (
    test_execution_service_dependency,
    endpoint_service_dependency,
)
from schemas.core.execution_history import ExecutionHistory, TestCaseExecutionResult

router = APIRouter(prefix="/execute", tags=["execution"])


@router.post(
    "/by-endpoint-name/{endpoint_name}",
    response_model=ExecuteTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute tests for an endpoint by name",
    description="Execute all test data for the specified endpoint.",
)
async def execute_tests_by_endpoint_name(
    endpoint_name: str,
    request: ExecuteTestRequest,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Execute tests for an endpoint by name."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Execute tests
        execution = await test_execution_service.execute_test_for_endpoint(
            endpoint_id=endpoint.id,
            endpoint_name=endpoint_name,
            base_url=request.base_url,
            test_data_ids=request.test_data_ids,
            timeout=request.timeout,
        )

        # Convert execution results to response format
        execution_results = [
            TestCaseExecutionResultResponse(**result.model_dump())
            for result in execution.execution_results
        ]

        return ExecuteTestResponse(
            execution_id=execution.id,
            endpoint_id=execution.endpoint_id,
            endpoint_name=execution.endpoint_name,
            base_url=execution.base_url,
            overall_status=execution.overall_status,
            total_tests=execution.total_tests,
            passed_tests=execution.passed_tests,
            failed_tests=execution.failed_tests,
            success_rate=execution.success_rate,
            total_execution_time_ms=execution.total_execution_time_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error_message=execution.error_message,
            execution_results=execution_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tests: {str(e)}",
        )


@router.post(
    "/by-endpoint-id/{endpoint_id}",
    response_model=ExecuteTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute tests for an endpoint by ID",
    description="Execute all test data for the specified endpoint ID.",
)
async def execute_tests_by_endpoint_id(
    endpoint_id: str,
    request: ExecuteTestRequest,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Execute tests for an endpoint by ID."""
    try:
        # Get endpoint by ID to get the name
        endpoint = await endpoint_service.get_endpoint_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with ID '{endpoint_id}' not found",
            )

        # Execute tests
        execution = await test_execution_service.execute_test_for_endpoint(
            endpoint_id=endpoint_id,
            endpoint_name=endpoint.name,
            base_url=request.base_url,
            test_data_ids=request.test_data_ids,
            timeout=request.timeout,
        )

        # Convert execution results to response format
        execution_results = [
            TestCaseExecutionResultResponse(**result.model_dump())
            for result in execution.execution_results
        ]

        return ExecuteTestResponse(
            execution_id=execution.id,
            endpoint_id=execution.endpoint_id,
            endpoint_name=execution.endpoint_name,
            base_url=execution.base_url,
            overall_status=execution.overall_status,
            total_tests=execution.total_tests,
            passed_tests=execution.passed_tests,
            failed_tests=execution.failed_tests,
            success_rate=execution.success_rate,
            total_execution_time_ms=execution.total_execution_time_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error_message=execution.error_message,
            execution_results=execution_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tests: {str(e)}",
        )


@router.get(
    "/history/",
    response_model=ExecutionHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all execution history",
    description="Retrieve execution history across all endpoints.",
)
async def get_all_execution_history(
    limit: int = 50,
    offset: int = 0,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
):
    """Get all execution history with pagination."""
    try:
        # Get all execution history
        all_executions = await test_execution_service.get_all_execution_history(
            limit=limit, offset=offset
        )

        # Convert to response format
        execution_responses = [
            ExecutionHistoryResponse(**execution.model_dump())
            for execution in all_executions
        ]

        return ExecutionHistoryListResponse(
            executions=execution_responses, total_count=len(execution_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve all execution history: {str(e)}",
        )


@router.get(
    "/history/by-endpoint-name/{endpoint_name}",
    response_model=ExecutionHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get execution history for an endpoint by name",
    description="Retrieve execution history for the specified endpoint.",
)
async def get_execution_history_by_endpoint_name(
    endpoint_name: str,
    limit: int = 10,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Get execution history for an endpoint by name."""
    try:
        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Get execution history
        executions = await test_execution_service.get_execution_history(
            endpoint.id, limit
        )

        # Convert to response format
        execution_responses = [
            ExecutionHistoryResponse(**execution.model_dump())
            for execution in executions
        ]

        return ExecutionHistoryListResponse(
            executions=execution_responses, total_count=len(execution_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve execution history: {str(e)}",
        )


@router.get(
    "/history/by-endpoint-id/{endpoint_id}",
    response_model=ExecutionHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get execution history for an endpoint by ID",
    description="Retrieve execution history for the specified endpoint ID.",
)
async def get_execution_history_by_endpoint_id(
    endpoint_id: str,
    limit: int = 10,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
):
    """Get execution history for an endpoint by ID."""
    try:
        # Get execution history
        executions = await test_execution_service.get_execution_history(
            endpoint_id, limit
        )

        # Convert to response format
        execution_responses = [
            ExecutionHistoryResponse(**execution.model_dump())
            for execution in executions
        ]

        return ExecutionHistoryListResponse(
            executions=execution_responses, total_count=len(execution_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve execution history: {str(e)}",
        )


@router.get(
    "/history/{execution_id}",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific execution details",
    description="Retrieve detailed information about a specific execution.",
)
async def get_execution_details(
    execution_id: str,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
):
    """Get specific execution details by ID."""
    try:
        execution = await test_execution_service.get_execution_by_id(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution with ID '{execution_id}' not found",
            )

        # Convert execution results to response format
        execution_results = [
            TestCaseExecutionResultResponse(**result.model_dump())
            for result in execution.execution_results
        ]

        return ExecutionDetailResponse(
            id=execution.id,
            endpoint_id=execution.endpoint_id,
            endpoint_name=execution.endpoint_name,
            base_url=execution.base_url,
            overall_status=execution.overall_status,
            total_tests=execution.total_tests,
            passed_tests=execution.passed_tests,
            failed_tests=execution.failed_tests,
            success_rate=execution.success_rate,
            total_execution_time_ms=execution.total_execution_time_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error_message=execution.error_message,
            test_data_used=execution.test_data_used,
            execution_results=execution_results,
            metadata=execution.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve execution details: {str(e)}",
        )


@router.delete(
    "/history/{execution_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete execution record",
    description="Delete a specific execution record.",
)
async def delete_execution(
    execution_id: str,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
):
    """Delete execution record by ID."""
    try:
        success = await test_execution_service.delete_execution(execution_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution with ID '{execution_id}' not found",
            )

        return {
            "message": f"Execution {execution_id} deleted successfully",
            "execution_id": execution_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete execution: {str(e)}",
        )
