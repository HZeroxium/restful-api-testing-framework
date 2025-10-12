# app/api/routers/constraint_router.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.core.pagination import PaginationParams
from utils.pagination_utils import calculate_pagination_metadata
from application.services.constraint_service import ConstraintService
from application.services.endpoint_service import EndpointService
from application.services.validation_script_service import ValidationScriptService
from app.api.dto.constraint_dto import (
    ConstraintCreateRequest,
    ConstraintResponse,
    ConstraintListResponse,
    MineConstraintsRequest,
    MineConstraintsResponse,
)
from schemas.tools.constraint_miner import ApiConstraint
from infra.di.container import (
    constraint_service_dependency,
    endpoint_service_dependency,
    validation_script_service_dependency,
)
from common.logger import LoggerFactory, LoggerType, LogLevel

router = APIRouter(prefix="/constraints", tags=["constraints"])

# Initialize logger for this router
logger = LoggerFactory.get_logger(
    name="router.constraint",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
)


@router.post(
    "/",
    response_model=ConstraintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new constraint",
)
async def create_constraint(
    request: ConstraintCreateRequest,
    service: ConstraintService = constraint_service_dependency,
):
    """Create a new constraint manually."""
    try:
        constraint = ApiConstraint(
            id="",  # Will be generated
            endpoint_id=request.endpoint_id,
            type=request.type,
            description=request.description,
            severity=request.severity,
            source=request.source,
            details=request.details,
        )

        created_constraint = await service.create_constraint(constraint)
        return ConstraintResponse.from_constraint(created_constraint)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create constraint: {str(e)}",
        )


@router.post(
    "/mine",
    response_model=MineConstraintsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mine constraints for an endpoint",
)
async def mine_constraints(
    request: MineConstraintsRequest,
    service: ConstraintService = constraint_service_dependency,
):
    """
    Mine constraints for a specific endpoint using AI.

    This endpoint will:
    1. Fetch the endpoint information
    2. Use StaticConstraintMinerTool to analyze and extract constraints
    3. Save the constraints to the repository
    4. Return all mined constraints
    """
    try:
        miner_output = await service.mine_constraints_for_endpoint(request.endpoint_id)
        return MineConstraintsResponse.from_miner_output(
            miner_output, request.endpoint_id
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mine constraints: {str(e)}",
        )


@router.get(
    "/",
    response_model=ConstraintListResponse,
    summary="Get all constraints or filter by endpoint",
)
async def list_constraints(
    endpoint_id: str = Query(None, description="Filter by endpoint ID"),
    pagination: PaginationParams = Depends(),
    service: ConstraintService = constraint_service_dependency,
):
    """Get all constraints, optionally filtered by endpoint_id."""
    logger.info(f"GET /constraints - endpoint_id filter: {endpoint_id or 'none'}")

    try:
        if endpoint_id:
            constraints, total_count = await service.get_constraints_by_endpoint_id(
                endpoint_id, pagination.limit, pagination.offset
            )
        else:
            constraints, total_count = await service.get_all_constraints(
                pagination.limit, pagination.offset
            )

        logger.debug(f"Retrieved {len(constraints)} constraints")
        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )
        return ConstraintListResponse(
            constraints=[ConstraintResponse.from_constraint(c) for c in constraints],
            pagination=pagination_metadata,
        )

    except Exception as e:
        logger.exception("Failed to list constraints")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list constraints: {str(e)}",
        )


@router.get(
    "/by-endpoint-name/{endpoint_name}",
    response_model=ConstraintListResponse,
    summary="Get constraints by endpoint name",
)
async def get_constraints_by_endpoint_name(
    endpoint_name: str,
    pagination: PaginationParams = Depends(),
    constraint_service: ConstraintService = constraint_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Get constraints for a specific endpoint by endpoint name."""
    logger.info(f"GET /constraints/by-endpoint-name/{endpoint_name}")

    try:
        # First, find the endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with name '{endpoint_name}' not found",
            )

        # Get constraints for the endpoint
        constraints, total_count = (
            await constraint_service.get_constraints_by_endpoint_id(
                endpoint.id, pagination.limit, pagination.offset
            )
        )

        logger.debug(
            f"Retrieved {len(constraints)} constraints for endpoint '{endpoint_name}'"
        )
        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )
        return ConstraintListResponse(
            constraints=[ConstraintResponse.from_constraint(c) for c in constraints],
            pagination=pagination_metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get constraints for endpoint '{endpoint_name}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get constraints for endpoint '{endpoint_name}': {str(e)}",
        )


@router.post(
    "/mine/by-endpoint-name/{endpoint_name}",
    response_model=MineConstraintsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mine constraints by endpoint name",
)
async def mine_constraints_by_endpoint_name(
    endpoint_name: str,
    constraint_service: ConstraintService = constraint_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """
    Mine constraints for a specific endpoint using endpoint name.

    This is a convenience endpoint that:
    1. Finds the endpoint by name
    2. Mines constraints for that endpoint
    3. Returns the mined constraints
    """
    logger.info(f"POST /constraints/mine/by-endpoint-name/{endpoint_name}")

    try:
        # First, find the endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with name '{endpoint_name}' not found",
            )

        # Mine constraints for the endpoint
        miner_output = await constraint_service.mine_constraints_for_endpoint(
            endpoint.id
        )
        return MineConstraintsResponse.from_miner_output(miner_output, endpoint.id)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to mine constraints for endpoint '{endpoint_name}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mine constraints for endpoint '{endpoint_name}': {str(e)}",
        )


@router.get(
    "/by-endpoint-id/{endpoint_id}",
    response_model=ConstraintListResponse,
    summary="Get constraints by endpoint ID",
)
async def get_constraints_by_endpoint_id(
    endpoint_id: str,
    pagination: PaginationParams = Depends(),
    constraint_service: ConstraintService = constraint_service_dependency,
):
    """Get constraints for a specific endpoint by endpoint ID."""
    logger.info(f"GET /constraints/by-endpoint-id/{endpoint_id}")

    try:
        constraints, total_count = (
            await constraint_service.get_constraints_by_endpoint_id(
                endpoint_id, pagination.limit, pagination.offset
            )
        )

        logger.debug(
            f"Retrieved {len(constraints)} constraints for endpoint ID '{endpoint_id}'"
        )
        pagination_metadata = calculate_pagination_metadata(
            pagination.offset, pagination.limit, total_count
        )
        return ConstraintListResponse(
            constraints=[ConstraintResponse.from_constraint(c) for c in constraints],
            pagination=pagination_metadata,
        )

    except Exception as e:
        logger.exception(f"Failed to get constraints for endpoint ID '{endpoint_id}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get constraints for endpoint ID '{endpoint_id}': {str(e)}",
        )


@router.get(
    "/{constraint_id}",
    response_model=ConstraintResponse,
    summary="Get constraint by ID",
)
async def get_constraint(
    constraint_id: str,
    service: ConstraintService = constraint_service_dependency,
):
    """Get a specific constraint by ID."""
    try:
        constraint = await service.get_constraint_by_id(constraint_id)
        if not constraint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Constraint with ID {constraint_id} not found",
            )

        return ConstraintResponse.from_constraint(constraint)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get constraint: {str(e)}",
        )


@router.delete(
    "/by-endpoint-name/{endpoint_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all constraints for an endpoint",
)
async def delete_constraints_by_endpoint_name(
    endpoint_name: str,
    constraint_service: ConstraintService = constraint_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
):
    """
    Delete all constraints for a specific endpoint by endpoint name.
    Also deletes all related validation scripts first.
    """
    logger.info(f"DELETE /constraints/by-endpoint-name/{endpoint_name}")
    try:
        # Find endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # First delete all validation scripts for this endpoint
        deleted_scripts_count = (
            await validation_script_service.delete_scripts_by_endpoint_id(endpoint.id)
        )
        logger.info(
            f"Deleted {deleted_scripts_count} validation scripts for endpoint '{endpoint_name}'"
        )

        # Then delete all constraints for this endpoint
        deleted_constraints_count = (
            await constraint_service.delete_constraints_by_endpoint_id(endpoint.id)
        )
        logger.info(
            f"Deleted {deleted_constraints_count} constraints for endpoint '{endpoint_name}'"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Internal server error during constraints deletion for {endpoint_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during deletion",
        )


@router.delete(
    "/{constraint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a constraint",
)
async def delete_constraint(
    constraint_id: str,
    service: ConstraintService = constraint_service_dependency,
):
    """Delete a specific constraint."""
    try:
        deleted = await service.delete_constraint(constraint_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Constraint with ID {constraint_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete constraint: {str(e)}",
        )
