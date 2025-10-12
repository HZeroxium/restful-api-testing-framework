# app/api/routers/batch_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from application.services.aggregator_service import AggregatorService
from application.services.constraint_service import ConstraintService
from application.services.validation_script_service import ValidationScriptService
from application.services.endpoint_service import EndpointService
from infra.di.container import (
    aggregator_service_dependency,
    constraint_service_dependency,
    validation_script_service_dependency,
    endpoint_service_dependency,
)

router = APIRouter(prefix="/batch", tags=["batch"])


# DTOs
class BatchConstraintMiningRequest(BaseModel):
    """Request for batch constraint mining."""

    endpoint_names: List[str] = Field(
        ..., description="List of endpoint names to mine constraints for"
    )
    base_url: str = Field(..., description="Base URL for the API")
    use_mock_api: bool = Field(False, description="Whether to use mock API calls")


class BatchValidationScriptGenerationRequest(BaseModel):
    """Request for batch validation script generation."""

    endpoint_names: List[str] = Field(
        ..., description="List of endpoint names to generate scripts for"
    )
    base_url: str = Field(..., description="Base URL for the API")
    use_mock_api: bool = Field(False, description="Whether to use mock API calls")


class BatchFullPipelineRequest(BaseModel):
    """Request for batch full pipeline execution."""

    endpoint_names: List[str] = Field(
        ..., description="List of endpoint names to run full pipeline for"
    )
    base_url: str = Field(..., description="Base URL for the API")
    use_mock_api: bool = Field(False, description="Whether to use mock API calls")


class BatchResult(BaseModel):
    """Result for a single endpoint in batch operation."""

    endpoint_name: str
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: float
    details: Dict[str, Any] = {}


class BatchResponse(BaseModel):
    """Response for batch operations."""

    total_endpoints: int
    successful_endpoints: int
    failed_endpoints: int
    success_rate: float
    total_execution_time_ms: float
    results: List[BatchResult]


@router.post(
    "/constraints/mine",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch mine constraints for multiple endpoints",
    description="Mine constraints for multiple endpoints in parallel.",
)
async def batch_mine_constraints(
    request: BatchConstraintMiningRequest,
    constraint_service: ConstraintService = constraint_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> BatchResponse:
    """Batch mine constraints for multiple endpoints."""
    import asyncio
    import time

    start_time = time.time()
    results = []

    # Validate all endpoints exist
    for endpoint_name in request.endpoint_names:
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            results.append(
                BatchResult(
                    endpoint_name=endpoint_name,
                    success=False,
                    error_message=f"Endpoint '{endpoint_name}' not found",
                    execution_time_ms=0.0,
                )
            )

    if any(not result.success for result in results):
        # Some endpoints not found, return early
        total_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BatchResponse(
            total_endpoints=len(request.endpoint_names),
            successful_endpoints=successful,
            failed_endpoints=failed,
            success_rate=(
                successful / len(request.endpoint_names)
                if request.endpoint_names
                else 0.0
            ),
            total_execution_time_ms=total_time,
            results=results,
        )

    # All endpoints exist, proceed with mining
    async def mine_constraints_for_endpoint(endpoint_name: str) -> BatchResult:
        endpoint_start_time = time.time()
        try:
            # Get endpoint by name to get the ID
            endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
            if not endpoint:
                execution_time = (time.time() - endpoint_start_time) * 1000
                return BatchResult(
                    endpoint_name=endpoint_name,
                    success=False,
                    error_message=f"Endpoint '{endpoint_name}' not found",
                    execution_time_ms=execution_time,
                )

            result = await constraint_service.mine_constraints_for_endpoint(
                endpoint_id=endpoint.id,
                override_existing=True,
            )

            execution_time = (time.time() - endpoint_start_time) * 1000

            return BatchResult(
                endpoint_name=endpoint_name,
                success=True,
                execution_time_ms=execution_time,
                details={
                    "constraints_mined": len(result.constraints),
                    "execution_time_ms": execution_time,
                },
            )
        except Exception as e:
            execution_time = (time.time() - endpoint_start_time) * 1000
            return BatchResult(
                endpoint_name=endpoint_name,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    # Execute in parallel
    tasks = [mine_constraints_for_endpoint(name) for name in request.endpoint_names]
    results = await asyncio.gather(*tasks)

    total_time = (time.time() - start_time) * 1000
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return BatchResponse(
        total_endpoints=len(request.endpoint_names),
        successful_endpoints=successful,
        failed_endpoints=failed,
        success_rate=(
            successful / len(request.endpoint_names) if request.endpoint_names else 0.0
        ),
        total_execution_time_ms=total_time,
        results=results,
    )


@router.post(
    "/validation-scripts/generate",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch generate validation scripts for multiple endpoints",
    description="Generate validation scripts for multiple endpoints in parallel.",
)
async def batch_generate_validation_scripts(
    request: BatchValidationScriptGenerationRequest,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> BatchResponse:
    """Batch generate validation scripts for multiple endpoints."""
    import asyncio
    import time

    start_time = time.time()
    results = []

    # Validate all endpoints exist
    for endpoint_name in request.endpoint_names:
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            results.append(
                BatchResult(
                    endpoint_name=endpoint_name,
                    success=False,
                    error_message=f"Endpoint '{endpoint_name}' not found",
                    execution_time_ms=0.0,
                )
            )

    if any(not result.success for result in results):
        # Some endpoints not found, return early
        total_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BatchResponse(
            total_endpoints=len(request.endpoint_names),
            successful_endpoints=successful,
            failed_endpoints=failed,
            success_rate=(
                successful / len(request.endpoint_names)
                if request.endpoint_names
                else 0.0
            ),
            total_execution_time_ms=total_time,
            results=results,
        )

    # All endpoints exist, proceed with generation
    async def generate_scripts_for_endpoint(endpoint_name: str) -> BatchResult:
        endpoint_start_time = time.time()
        try:
            # Get endpoint by name to get the ID
            endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
            if not endpoint:
                execution_time = (time.time() - endpoint_start_time) * 1000
                return BatchResult(
                    endpoint_name=endpoint_name,
                    success=False,
                    error_message=f"Endpoint '{endpoint_name}' not found",
                    execution_time_ms=execution_time,
                )

            result = await validation_script_service.generate_scripts_for_endpoint(
                endpoint_id=endpoint.id,
                override_existing=True,
            )

            execution_time = (time.time() - endpoint_start_time) * 1000

            return BatchResult(
                endpoint_name=endpoint_name,
                success=True,
                execution_time_ms=execution_time,
                details={
                    "scripts_generated": len(result.scripts),
                    "execution_time_ms": execution_time,
                },
            )
        except Exception as e:
            execution_time = (time.time() - endpoint_start_time) * 1000
            return BatchResult(
                endpoint_name=endpoint_name,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    # Execute in parallel
    tasks = [generate_scripts_for_endpoint(name) for name in request.endpoint_names]
    results = await asyncio.gather(*tasks)

    total_time = (time.time() - start_time) * 1000
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return BatchResponse(
        total_endpoints=len(request.endpoint_names),
        successful_endpoints=successful,
        failed_endpoints=failed,
        success_rate=(
            successful / len(request.endpoint_names) if request.endpoint_names else 0.0
        ),
        total_execution_time_ms=total_time,
        results=results,
    )


@router.post(
    "/full-pipeline",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch run full pipeline for multiple endpoints",
    description="Run the complete testing pipeline (mine → generate → test → execute → report) for multiple endpoints in parallel.",
)
async def batch_run_full_pipeline(
    request: BatchFullPipelineRequest,
    aggregator_service: AggregatorService = aggregator_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> BatchResponse:
    """Batch run full pipeline for multiple endpoints."""
    import asyncio
    import time

    start_time = time.time()
    results = []

    # Validate all endpoints exist
    for endpoint_name in request.endpoint_names:
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            results.append(
                BatchResult(
                    endpoint_name=endpoint_name,
                    success=False,
                    error_message=f"Endpoint '{endpoint_name}' not found",
                    execution_time_ms=0.0,
                )
            )

    if any(not result.success for result in results):
        # Some endpoints not found, return early
        total_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BatchResponse(
            total_endpoints=len(request.endpoint_names),
            successful_endpoints=successful,
            failed_endpoints=failed,
            success_rate=(
                successful / len(request.endpoint_names)
                if request.endpoint_names
                else 0.0
            ),
            total_execution_time_ms=total_time,
            results=results,
        )

    # All endpoints exist, proceed with full pipeline
    async def run_full_pipeline_for_endpoint(endpoint_name: str) -> BatchResult:
        endpoint_start_time = time.time()
        try:
            result = await aggregator_service.run_full_pipeline_for_endpoint(
                endpoint_name=endpoint_name,
                base_url=request.base_url,
                use_mock_api=request.use_mock_api,
            )

            execution_time = (time.time() - endpoint_start_time) * 1000

            return BatchResult(
                endpoint_name=endpoint_name,
                success=result.overall_success,
                execution_time_ms=execution_time,
                details={
                    "constraints_mined": result.constraints_mined,
                    "scripts_generated": result.scripts_generated,
                    "test_data_generated": result.test_data_generated,
                    "tests_executed": result.tests_executed,
                    "execution_id": result.execution_id,
                    "overall_success": result.overall_success,
                },
            )
        except Exception as e:
            execution_time = (time.time() - endpoint_start_time) * 1000
            return BatchResult(
                endpoint_name=endpoint_name,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    # Execute in parallel
    tasks = [run_full_pipeline_for_endpoint(name) for name in request.endpoint_names]
    results = await asyncio.gather(*tasks)

    total_time = (time.time() - start_time) * 1000
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return BatchResponse(
        total_endpoints=len(request.endpoint_names),
        successful_endpoints=successful,
        failed_endpoints=failed,
        success_rate=(
            successful / len(request.endpoint_names) if request.endpoint_names else 0.0
        ),
        total_execution_time_ms=total_time,
        results=results,
    )


@router.get(
    "/endpoints/available",
    status_code=status.HTTP_200_OK,
    summary="Get available endpoints for batch operations",
    description="Get a list of all available endpoints that can be used in batch operations.",
)
async def get_available_endpoints_for_batch(
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Get available endpoints for batch operations."""
    try:
        endpoints = await endpoint_service.get_all_endpoints()

        endpoint_list = []
        for endpoint in endpoints:
            endpoint_list.append(
                {
                    "name": endpoint.name,
                    "id": endpoint.id,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "dataset_id": endpoint.dataset_id,
                    "description": endpoint.description,
                }
            )

        return {
            "total_endpoints": len(endpoints),
            "endpoints": endpoint_list,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve available endpoints: {str(e)}",
        )
