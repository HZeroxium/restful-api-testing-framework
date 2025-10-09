"""
Router for aggregator endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dto.aggregator_dto import ConstraintsScriptsAggregatorResponse
from infra.di.container import aggregator_service_dependency
from application.services.aggregator_service import AggregatorService

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
