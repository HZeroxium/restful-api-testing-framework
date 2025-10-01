# app/api/routers/validation_script_router.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from dependency_injector.wiring import inject, Provide

from application.services.validation_script_service import ValidationScriptService
from app.api.dto.validation_script_dto import (
    ValidationScriptCreateRequest,
    ValidationScriptResponse,
    ValidationScriptListResponse,
    GenerateScriptsRequest,
    GenerateScriptsResponse,
)
from schemas.tools.test_script_generator import ValidationScript
from infra.di.container import Container

router = APIRouter(prefix="/validation-scripts", tags=["validation-scripts"])


@router.post(
    "/",
    response_model=ValidationScriptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new validation script",
)
@inject
async def create_validation_script(
    request: ValidationScriptCreateRequest,
    service: ValidationScriptService = Depends(
        Provide[Container.validation_script_service]
    ),
):
    """Create a new validation script manually."""
    try:
        script = ValidationScript(
            id="",  # Will be generated
            endpoint_id=request.endpoint_id,
            name=request.name,
            script_type=request.script_type,
            validation_code=request.validation_code,
            description=request.description,
            constraint_id=request.constraint_id,
        )

        created_script = await service.create_script(script)
        return ValidationScriptResponse.from_script(created_script)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create validation script: {str(e)}",
        )


@router.post(
    "/generate",
    response_model=GenerateScriptsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate validation scripts for an endpoint",
)
@inject
async def generate_validation_scripts(
    request: GenerateScriptsRequest,
    service: ValidationScriptService = Depends(
        Provide[Container.validation_script_service]
    ),
):
    """
    Generate validation scripts for a specific endpoint using AI.

    This endpoint will:
    1. Fetch the endpoint information
    2. Fetch existing constraints for the endpoint
    3. Use TestScriptGeneratorTool to generate validation scripts
    4. Save the scripts to the repository
    5. Return all generated scripts
    """
    try:
        generator_output = await service.generate_scripts_for_endpoint(
            request.endpoint_id
        )
        return GenerateScriptsResponse.from_generator_output(
            generator_output, request.endpoint_id
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate validation scripts: {str(e)}",
        )


@router.get(
    "/",
    response_model=ValidationScriptListResponse,
    summary="Get all validation scripts or filter by endpoint",
)
@inject
async def list_validation_scripts(
    endpoint_id: str = Query(None, description="Filter by endpoint ID"),
    service: ValidationScriptService = Depends(
        Provide[Container.validation_script_service]
    ),
):
    """Get all validation scripts, optionally filtered by endpoint_id."""
    try:
        if endpoint_id:
            scripts = await service.get_scripts_by_endpoint_id(endpoint_id)
        else:
            scripts = await service.get_all_scripts()

        return ValidationScriptListResponse(
            scripts=[ValidationScriptResponse.from_script(s) for s in scripts],
            total=len(scripts),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list validation scripts: {str(e)}",
        )


@router.get(
    "/{script_id}",
    response_model=ValidationScriptResponse,
    summary="Get validation script by ID",
)
@inject
async def get_validation_script(
    script_id: str,
    service: ValidationScriptService = Depends(
        Provide[Container.validation_script_service]
    ),
):
    """Get a specific validation script by ID."""
    try:
        script = await service.get_script_by_id(script_id)
        if not script:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation script with ID {script_id} not found",
            )

        return ValidationScriptResponse.from_script(script)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation script: {str(e)}",
        )


@router.delete(
    "/{script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a validation script",
)
@inject
async def delete_validation_script(
    script_id: str,
    service: ValidationScriptService = Depends(
        Provide[Container.validation_script_service]
    ),
):
    """Delete a specific validation script."""
    try:
        deleted = await service.delete_script(script_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation script with ID {script_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete validation script: {str(e)}",
        )
