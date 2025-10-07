# app/api/routers/dataset_router.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from application.services.dataset_service import DatasetService
from schemas.core.dataset import Dataset
from schemas.tools.openapi_parser import EndpointInfo
from common.logger import LoggerFactory, LoggerType, LogLevel


logger = LoggerFactory.get_logger(
    name="router.dataset",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


# DTOs
class CreateDatasetRequest(BaseModel):
    """Request body for creating a dataset."""

    name: str = Field(..., description="Name of the dataset")
    description: Optional[str] = Field(None, description="Description of the dataset")


class CreateDatasetFromFileResponse(BaseModel):
    """Response for creating dataset from file."""

    dataset_id: str
    dataset_name: str
    spec_version: Optional[str]
    base_url: Optional[str]
    endpoints_count: int
    api_title: str


# Dependency injection
from infra.di.container import dataset_service_dependency


@router.post("/", response_model=Dataset, status_code=201)
async def create_dataset(
    request: CreateDatasetRequest,
    service: DatasetService = dataset_service_dependency,
):
    """Create a new dataset."""
    logger.info(f"POST /datasets - name: {request.name}")

    try:
        dataset = await service.create_dataset(
            name=request.name,
            description=request.description,
        )
        logger.info(f"Successfully created dataset: {dataset.id}")
        return dataset
    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-spec", response_model=CreateDatasetFromFileResponse)
async def create_dataset_from_file(
    file: UploadFile = File(
        ..., description="OpenAPI specification file (JSON or YAML)"
    ),
    dataset_name: Optional[str] = Form(
        None, description="Optional custom name for the dataset"
    ),
    service: DatasetService = dataset_service_dependency,
):
    """Create a new dataset from uploaded OpenAPI specification file."""
    logger.info(f"POST /datasets/upload-spec - filename: {file.filename}")

    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Check if file is valid OpenAPI spec
        valid_extensions = [".json", ".yaml", ".yml"]
        if not any(file.filename.lower().endswith(ext) for ext in valid_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Supported formats: {', '.join(valid_extensions)}",
            )

        # Read file content
        file_content = await file.read()

        # Create dataset from file
        result = await service.create_dataset_from_file(
            file_content=file_content,
            filename=file.filename,
            dataset_name=dataset_name,
        )

        logger.info(
            f"Successfully created dataset {result['dataset_id']} from {file.filename}: {result['endpoints_count']} endpoints"
        )
        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create dataset from file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Dataset])
async def get_all_datasets(
    service: DatasetService = dataset_service_dependency,
):
    """Get all datasets."""
    logger.info("GET /datasets")

    try:
        datasets = await service.get_all_datasets()
        logger.info(f"Retrieved {len(datasets)} datasets")
        return datasets
    except Exception as e:
        logger.error(f"Failed to retrieve datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: str,
    service: DatasetService = dataset_service_dependency,
):
    """Get a dataset by ID."""
    logger.info(f"GET /datasets/{dataset_id}")

    try:
        dataset = await service.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/endpoints", response_model=List[EndpointInfo])
async def get_dataset_endpoints(
    dataset_id: str,
    service: DatasetService = dataset_service_dependency,
):
    """Get all endpoints for a dataset."""
    logger.info(f"GET /datasets/{dataset_id}/endpoints")

    try:
        endpoints = await service.get_dataset_endpoints(dataset_id)
        logger.info(f"Retrieved {len(endpoints)} endpoints for dataset {dataset_id}")
        return endpoints
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to retrieve endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: str,
    service: DatasetService = dataset_service_dependency,
):
    """Delete a dataset and all its associated data."""
    logger.info(f"DELETE /datasets/{dataset_id}")

    try:
        success = await service.delete_dataset(dataset_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dataset not found")
        logger.info(f"Successfully deleted dataset: {dataset_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
