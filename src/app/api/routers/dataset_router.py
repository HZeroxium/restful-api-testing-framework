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


class UploadSpecRequest(BaseModel):
    """Request body for uploading OpenAPI spec."""

    spec_content: str = Field(
        ..., description="OpenAPI specification content (JSON or YAML)"
    )
    is_yaml: bool = Field(False, description="Whether the spec is in YAML format")


class UploadSpecResponse(BaseModel):
    """Response for spec upload."""

    dataset_id: str
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


@router.post("/{dataset_id}/upload-spec", response_model=UploadSpecResponse)
async def upload_spec(
    dataset_id: str,
    request: UploadSpecRequest,
    service: DatasetService = dataset_service_dependency,
):
    """Upload and parse an OpenAPI specification for a dataset."""
    logger.info(f"POST /datasets/{dataset_id}/upload-spec")

    try:
        result = await service.upload_and_parse_spec(
            dataset_id=dataset_id,
            spec_content=request.spec_content,
            is_yaml=request.is_yaml,
        )
        logger.info(
            f"Successfully uploaded spec for dataset {dataset_id}: {result['endpoints_count']} endpoints"
        )
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/upload-spec-file")
async def upload_spec_file(
    dataset_id: str,
    file: UploadFile = File(...),
    service: DatasetService = dataset_service_dependency,
):
    """Upload an OpenAPI specification file for a dataset."""
    logger.info(
        f"POST /datasets/{dataset_id}/upload-spec-file - filename: {file.filename}"
    )

    try:
        # Read file content
        content = await file.read()
        spec_content = content.decode("utf-8")

        # Determine if YAML based on file extension
        is_yaml = file.filename and (
            file.filename.endswith(".yaml") or file.filename.endswith(".yml")
        )

        result = await service.upload_and_parse_spec(
            dataset_id=dataset_id,
            spec_content=spec_content,
            is_yaml=is_yaml,
        )

        logger.info(
            f"Successfully uploaded spec file for dataset {dataset_id}: {result['endpoints_count']} endpoints"
        )
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload spec file: {e}")
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
