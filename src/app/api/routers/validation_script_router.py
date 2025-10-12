# app/api/routers/validation_script_router.py

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from application.services.validation_script_service import ValidationScriptService
from application.services.endpoint_service import EndpointService
from app.api.dto.validation_script_dto import (
    ValidationScriptCreateRequest,
    ValidationScriptResponse,
    ValidationScriptListResponse,
    GenerateScriptsRequest,
    GenerateScriptsResponse,
)
from schemas.tools.test_script_generator import ValidationScript
from infra.di.container import (
    validation_script_service_dependency,
    endpoint_service_dependency,
)
from common.logger import LoggerFactory, LoggerType, LogLevel
from schemas.core.pagination import PaginationParams
from utils.pagination_utils import calculate_pagination_metadata

router = APIRouter(prefix="/validation-scripts", tags=["validation-scripts"])

# Initialize logger for this router
logger = LoggerFactory.get_logger(
    name="router.validation_script",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
)


@router.post(
    "/",
    response_model=ValidationScriptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new validation script",
)
async def create_validation_script(
    request: ValidationScriptCreateRequest,
    service: ValidationScriptService = validation_script_service_dependency,
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
async def generate_validation_scripts(
    request: GenerateScriptsRequest,
    service: ValidationScriptService = validation_script_service_dependency,
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
    logger.info(
        f"POST /validation-scripts/generate - endpoint_id: {request.endpoint_id}"
    )

    try:
        generator_output = await service.generate_scripts_for_endpoint(
            request.endpoint_id
        )
        logger.info(
            f"Successfully generated {len(generator_output.validation_scripts)} scripts for endpoint: {request.endpoint_id}"
        )
        return GenerateScriptsResponse.from_generator_output(
            generator_output, request.endpoint_id
        )

    except ValueError as e:
        logger.error(f"Endpoint not found: {request.endpoint_id} - {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Failed to generate scripts for endpoint: {request.endpoint_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate validation scripts: {str(e)}",
        )


@router.get(
    "/",
    response_model=ValidationScriptListResponse,
    summary="Get all validation scripts or filter by endpoint",
)
async def list_validation_scripts(
    endpoint_id: str = Query(None, description="Filter by endpoint ID"),
    pagination: PaginationParams = Depends(),
    service: ValidationScriptService = validation_script_service_dependency,
):
    """Get all validation scripts, optionally filtered by endpoint_id."""
    try:
        if endpoint_id:
            scripts, total_count = await service.get_scripts_by_endpoint_id(
                endpoint_id, limit=pagination.limit, offset=pagination.offset
            )
        else:
            scripts, total_count = await service.get_all_scripts(
                limit=pagination.limit, offset=pagination.offset
            )

        # Calculate pagination metadata
        pagination_metadata = calculate_pagination_metadata(
            offset=pagination.offset, limit=pagination.limit, total_items=total_count
        )

        return ValidationScriptListResponse(
            scripts=[ValidationScriptResponse.from_script(s) for s in scripts],
            total=total_count,
            pagination=pagination_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list validation scripts: {str(e)}",
        )


@router.get(
    "/by-endpoint-name/{endpoint_name}",
    response_model=ValidationScriptListResponse,
    summary="Get validation scripts by endpoint name",
)
async def get_validation_scripts_by_endpoint_name(
    endpoint_name: str,
    pagination: PaginationParams = Depends(),
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """Get validation scripts for a specific endpoint by endpoint name."""
    logger.info(f"GET /validation-scripts/by-endpoint-name/{endpoint_name}")

    try:
        # First, find the endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with name '{endpoint_name}' not found",
            )

        # Get validation scripts for the endpoint
        scripts, total_count = (
            await validation_script_service.get_scripts_by_endpoint_id(
                endpoint.id, limit=pagination.limit, offset=pagination.offset
            )
        )

        logger.debug(
            f"Retrieved {len(scripts)} validation scripts for endpoint '{endpoint_name}'"
        )

        # Calculate pagination metadata
        pagination_metadata = calculate_pagination_metadata(
            offset=pagination.offset, limit=pagination.limit, total_items=total_count
        )

        return ValidationScriptListResponse(
            scripts=[ValidationScriptResponse.from_script(s) for s in scripts],
            total=total_count,
            pagination=pagination_metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Failed to get validation scripts for endpoint '{endpoint_name}'"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation scripts for endpoint '{endpoint_name}': {str(e)}",
        )


@router.post(
    "/generate/by-endpoint-name/{endpoint_name}",
    response_model=GenerateScriptsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate validation scripts by endpoint name",
)
async def generate_validation_scripts_by_endpoint_name(
    endpoint_name: str,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """
    Generate validation scripts for a specific endpoint using endpoint name.

    This is a convenience endpoint that:
    1. Finds the endpoint by name
    2. Generates validation scripts for that endpoint
    3. Returns the generated scripts
    """
    logger.info(f"POST /validation-scripts/generate/by-endpoint-name/{endpoint_name}")

    try:
        # First, find the endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint with name '{endpoint_name}' not found",
            )

        # Generate validation scripts for the endpoint
        generator_output = (
            await validation_script_service.generate_scripts_for_endpoint(endpoint.id)
        )
        logger.info(
            f"Successfully generated {len(generator_output.validation_scripts)} scripts for endpoint: {endpoint_name}"
        )
        return GenerateScriptsResponse.from_generator_output(
            generator_output, endpoint.id
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Endpoint not found: {endpoint_name} - {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to generate scripts for endpoint: {endpoint_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate validation scripts for endpoint '{endpoint_name}': {str(e)}",
        )


@router.get(
    "/by-endpoint-id/{endpoint_id}",
    response_model=ValidationScriptListResponse,
    summary="Get validation scripts by endpoint ID",
)
async def get_validation_scripts_by_endpoint_id(
    endpoint_id: str,
    pagination: PaginationParams = Depends(),
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
):
    """Get validation scripts for a specific endpoint by endpoint ID."""
    logger.info(f"GET /validation-scripts/by-endpoint-id/{endpoint_id}")

    try:
        scripts, total_count = (
            await validation_script_service.get_scripts_by_endpoint_id(
                endpoint_id, limit=pagination.limit, offset=pagination.offset
            )
        )

        logger.debug(
            f"Retrieved {len(scripts)} validation scripts for endpoint ID '{endpoint_id}'"
        )

        # Calculate pagination metadata
        pagination_metadata = calculate_pagination_metadata(
            offset=pagination.offset, limit=pagination.limit, total_items=total_count
        )

        return ValidationScriptListResponse(
            scripts=[ValidationScriptResponse.from_script(s) for s in scripts],
            total=total_count,
            pagination=pagination_metadata,
        )

    except Exception as e:
        logger.exception(
            f"Failed to get validation scripts for endpoint ID '{endpoint_id}'"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation scripts for endpoint ID '{endpoint_id}': {str(e)}",
        )


@router.get(
    "/{script_id}",
    response_model=ValidationScriptResponse,
    summary="Get validation script by ID",
)
async def get_validation_script(
    script_id: str,
    service: ValidationScriptService = validation_script_service_dependency,
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
    "/by-endpoint-name/{endpoint_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all validation scripts for an endpoint",
)
async def delete_validation_scripts_by_endpoint_name(
    endpoint_name: str,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """
    Delete all validation scripts for a specific endpoint by endpoint name.
    """
    logger.info(f"DELETE /validation-scripts/by-endpoint-name/{endpoint_name}")
    try:
        # Find endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Delete all validation scripts for this endpoint
        deleted_count = await validation_script_service.delete_scripts_by_endpoint_id(
            endpoint.id
        )
        logger.info(
            f"Deleted {deleted_count} validation scripts for endpoint '{endpoint_name}'"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Internal server error during validation scripts deletion for {endpoint_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during deletion",
        )


@router.delete(
    "/{script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a validation script",
)
async def delete_validation_script(
    script_id: str,
    service: ValidationScriptService = validation_script_service_dependency,
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


@router.post(
    "/to-python-file/{endpoint_name}",
    status_code=status.HTTP_200_OK,
    summary="Export validation scripts to Python file",
)
async def export_validation_scripts_to_python_file(
    endpoint_name: str,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
):
    """
    Export all validation scripts for an endpoint to a Python file.
    """
    logger.info(f"POST /validation-scripts/to-python-file/{endpoint_name}")
    try:
        # Find endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name(endpoint_name)
        if not endpoint:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endpoint '{endpoint_name}' not found",
            )

        # Get all validation scripts for this endpoint
        scripts = await validation_script_service.get_scripts_by_endpoint_id(
            endpoint.id
        )
        if not scripts:
            logger.warning(
                f"No validation scripts found for endpoint '{endpoint_name}'"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No validation scripts found for endpoint '{endpoint_name}'",
            )

        # Create Python file content
        python_content = _generate_python_file_content(endpoint_name, scripts)

        # Save to file
        import os
        from pathlib import Path

        output_dir = Path("data/exports")
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{endpoint_name}_validation_scripts.py"
        file_path = output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(python_content)

        logger.info(f"Exported {len(scripts)} validation scripts to {file_path}")

        return {
            "message": f"Successfully exported {len(scripts)} validation scripts to Python file",
            "endpoint_name": endpoint_name,
            "scripts_count": len(scripts),
            "file_path": str(file_path),
            "filename": filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Internal server error during script export for {endpoint_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during script export",
        )


def _generate_python_file_content(endpoint_name: str, scripts) -> str:
    """Generate Python file content from validation scripts."""

    # Create safe filename
    safe_endpoint_name = endpoint_name.replace("/", "_").replace("-", "_")

    content = f'''"""
Validation Scripts for Endpoint: {endpoint_name}
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Scripts: {len(scripts)}

This file contains all validation scripts for the endpoint '{endpoint_name}'.
Each function represents a validation script that can be used to validate
request parameters, request body, response properties, or request-response correlations.
"""

from typing import Dict, Any, Optional


def validate_endpoint_{safe_endpoint_name}():
    """
    Main validation function for endpoint '{endpoint_name}'.
    Call this function to run all validations for this endpoint.
    """
    print(f"Running validations for endpoint: {endpoint_name}")
    # Add your validation orchestration logic here
    pass


'''

    # Add each validation script
    for i, script in enumerate(scripts, 1):
        content += f"""
# =============================================================================
# Validation Script {i}: {script.name}
# =============================================================================
# Script Type: {script.script_type}
# Description: {script.description}
# Constraint ID: {script.constraint_id or 'N/A'}
# Created: {script.created_at or 'N/A'}
# Updated: {script.updated_at or 'N/A'}
# =============================================================================

{script.validation_code}

"""

    content += f"""
# =============================================================================
# End of Validation Scripts for Endpoint: {endpoint_name}
# Total Scripts: {len(scripts)}
# =============================================================================
"""

    return content
