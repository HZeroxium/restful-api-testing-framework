"""
Router for aggregator endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.api.dto.aggregator_dto import ConstraintsScriptsAggregatorResponse
from infra.di.container import aggregator_service_dependency
from application.services.aggregator_service import AggregatorService


class FullPipelineRequest(BaseModel):
    """Request for running the full testing pipeline."""

    base_url: str = Field(..., description="Base URL for API calls")
    test_count: int = Field(
        5, description="Number of test data items to generate", ge=1, le=20
    )
    include_invalid: bool = Field(
        True, description="Whether to include invalid test data"
    )
    override_existing: bool = Field(
        True, description="Whether to override existing constraints/scripts"
    )
    use_mock_api: bool = Field(
        False, description="Whether to use mock API calls instead of real HTTP requests"
    )


router = APIRouter(prefix="/aggregator", tags=["aggregator"])


@router.post(
    "/constraints-scripts/{endpoint_name}",
    response_model=ConstraintsScriptsAggregatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Mine constraints and generate validation scripts for an endpoint",
    description="Aggregated endpoint that performs constraint mining followed by validation script generation for the specified endpoint. This combines the functionality of /constraints/mine/by-endpoint-name/{endpoint_name} and /validation-scripts/generate/by-endpoint-name/{endpoint_name} into a single operation.",
)
async def mine_constraints_and_generate_scripts(
    endpoint_name: str,
    service: AggregatorService = aggregator_service_dependency,
):
    """
    Mine constraints and generate validation scripts for an endpoint.

    This endpoint performs the following operations in sequence:
    1. Mine constraints for the specified endpoint
    2. Generate validation scripts based on the mined constraints

    Args:
        endpoint_name: Name of the endpoint to process
        service: AggregatorService instance

    Returns:
        Aggregated response containing both constraint mining and script generation results

    Raises:
        HTTPException: If the endpoint is not found or if there are critical errors
    """
    try:
        result = await service.mine_constraints_and_generate_scripts(endpoint_name)

        # If the endpoint wasn't found, return 404
        if result.endpoint_id == "unknown":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Return the aggregated result
        return result

    except ValueError as e:
        # Handle specific validation errors (like endpoint not found)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during aggregated operations: {str(e)}",
        )


@router.post(
    "/full-pipeline/{endpoint_name}",
    status_code=status.HTTP_200_OK,
    summary="Run complete testing pipeline for an endpoint",
    description="Execute the full testing workflow: mine constraints → generate scripts → generate test data → execute tests → save results.",
)
async def run_full_pipeline(
    endpoint_name: str,
    request: FullPipelineRequest,
    service: AggregatorService = aggregator_service_dependency,
):
    """
    Run the complete testing pipeline for an endpoint.

    This endpoint performs the following operations in sequence:
    1. Mine constraints for the specified endpoint (if not exist or override)
    2. Generate validation scripts based on the mined constraints (if not exist or override)
    3. Generate test data for the endpoint
    4. Execute tests with real API calls
    5. Save execution results and history
    6. Return comprehensive pipeline report

    Args:
        endpoint_name: Name of the endpoint to test
        request: FullPipelineRequest with base_url, test_count, include_invalid, override_existing
        service: AggregatorService instance

    Returns:
        Dictionary with comprehensive pipeline results including all step outcomes

    Raises:
        HTTPException: If the endpoint is not found or if there are critical errors
    """
    try:
        result = await service.run_full_pipeline_for_endpoint(
            endpoint_name=endpoint_name,
            base_url=request.base_url,
            test_count=request.test_count,
            include_invalid=request.include_invalid,
            override_existing=request.override_existing,
            use_mock_api=request.use_mock_api,
        )

        # If the endpoint wasn't found, return 404
        if result.get("endpoint_id") == "unknown" or "Endpoint" in str(
            result.get("error", "")
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        return result

    except ValueError as e:
        # Handle specific validation errors (like endpoint not found)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during full pipeline execution: {str(e)}",
        )
