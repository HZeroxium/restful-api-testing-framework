# app/api/routers/constraint_router.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from application.services.constraint_service import ConstraintService
from app.api.dto.constraint_dto import (
    ConstraintCreateRequest,
    ConstraintResponse,
    ConstraintListResponse,
    MineConstraintsRequest,
    MineConstraintsResponse,
)
from schemas.tools.constraint_miner import ApiConstraint
from infra.di.container import constraint_service_dependency
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
    service: ConstraintService = constraint_service_dependency,
):
    """Get all constraints, optionally filtered by endpoint_id."""
    logger.info(f"GET /constraints - endpoint_id filter: {endpoint_id or 'none'}")

    try:
        if endpoint_id:
            constraints = await service.get_constraints_by_endpoint_id(endpoint_id)
        else:
            constraints = await service.get_all_constraints()

        logger.debug(f"Retrieved {len(constraints)} constraints")
        return ConstraintListResponse(
            constraints=[ConstraintResponse.from_constraint(c) for c in constraints],
            total=len(constraints),
        )

    except Exception as e:
        logger.exception("Failed to list constraints")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list constraints: {str(e)}",
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
