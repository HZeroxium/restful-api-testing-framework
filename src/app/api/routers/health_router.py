# app/api/routers/health_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import os
from pathlib import Path
from datetime import datetime

from application.services.dataset_service import DatasetService
from application.services.endpoint_service import EndpointService
from application.services.constraint_service import ConstraintService
from application.services.validation_script_service import ValidationScriptService
from application.services.test_data_service import TestDataService
from application.services.test_execution_service import TestExecutionService
from infra.di.container import (
    dataset_service_dependency,
    endpoint_service_dependency,
    constraint_service_dependency,
    validation_script_service_dependency,
    test_data_service_dependency,
    test_execution_service_dependency,
)

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Check if the API server is running.",
)
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "RESTful API Testing Framework",
        "version": "1.0.0",
    }


@router.get(
    "/services",
    status_code=status.HTTP_200_OK,
    summary="Check service health",
    description="Check the health of all services and their dependencies.",
)
async def check_services_health(
    dataset_service: DatasetService = dataset_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
    constraint_service: ConstraintService = constraint_service_dependency,
    validation_script_service: ValidationScriptService = validation_script_service_dependency,
    test_data_service: TestDataService = test_data_service_dependency,
    test_execution_service: TestExecutionService = test_execution_service_dependency,
) -> Dict[str, Any]:
    """Check the health of all services."""
    services_status = {}
    overall_healthy = True

    # Check Dataset Service
    try:
        datasets = await dataset_service.get_all_datasets()
        services_status["dataset_service"] = {
            "status": "healthy",
            "datasets_count": len(datasets),
            "error": None,
        }
    except Exception as e:
        services_status["dataset_service"] = {
            "status": "unhealthy",
            "datasets_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check Endpoint Service
    try:
        # Try to get all endpoints (this will test the lookup service)
        endpoints = await endpoint_service.get_all_endpoints()
        services_status["endpoint_service"] = {
            "status": "healthy",
            "endpoints_count": len(endpoints),
            "error": None,
        }
    except Exception as e:
        services_status["endpoint_service"] = {
            "status": "unhealthy",
            "endpoints_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check Constraint Service
    try:
        # Try to get constraints for a known endpoint if available
        if endpoints:
            test_endpoint = endpoints[0]
            constraints = await constraint_service.get_constraints_by_endpoint_name(
                test_endpoint.name
            )
            services_status["constraint_service"] = {
                "status": "healthy",
                "test_endpoint": test_endpoint.name,
                "constraints_count": len(constraints),
                "error": None,
            }
        else:
            services_status["constraint_service"] = {
                "status": "healthy",
                "test_endpoint": None,
                "constraints_count": 0,
                "error": None,
            }
    except Exception as e:
        services_status["constraint_service"] = {
            "status": "unhealthy",
            "test_endpoint": None,
            "constraints_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check Validation Script Service
    try:
        if endpoints:
            test_endpoint = endpoints[0]
            scripts = (
                await validation_script_service.get_validation_scripts_by_endpoint_name(
                    test_endpoint.name
                )
            )
            services_status["validation_script_service"] = {
                "status": "healthy",
                "test_endpoint": test_endpoint.name,
                "scripts_count": len(scripts),
                "error": None,
            }
        else:
            services_status["validation_script_service"] = {
                "status": "healthy",
                "test_endpoint": None,
                "scripts_count": 0,
                "error": None,
            }
    except Exception as e:
        services_status["validation_script_service"] = {
            "status": "unhealthy",
            "test_endpoint": None,
            "scripts_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check Test Data Service
    try:
        if endpoints:
            test_endpoint = endpoints[0]
            test_data = await test_data_service.get_test_data_by_endpoint_id(
                test_endpoint.id
            )
            services_status["test_data_service"] = {
                "status": "healthy",
                "test_endpoint": test_endpoint.name,
                "test_data_count": len(test_data),
                "error": None,
            }
        else:
            services_status["test_data_service"] = {
                "status": "healthy",
                "test_endpoint": None,
                "test_data_count": 0,
                "error": None,
            }
    except Exception as e:
        services_status["test_data_service"] = {
            "status": "unhealthy",
            "test_endpoint": None,
            "test_data_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check Test Execution Service
    try:
        if endpoints:
            test_endpoint = endpoints[0]
            executions = await test_execution_service.get_execution_history(
                test_endpoint.id, limit=1
            )
            services_status["test_execution_service"] = {
                "status": "healthy",
                "test_endpoint": test_endpoint.name,
                "executions_count": len(executions),
                "error": None,
            }
        else:
            services_status["test_execution_service"] = {
                "status": "healthy",
                "test_endpoint": None,
                "executions_count": 0,
                "error": None,
            }
    except Exception as e:
        services_status["test_execution_service"] = {
            "status": "unhealthy",
            "test_endpoint": None,
            "executions_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
        "overall_healthy": overall_healthy,
    }


@router.get(
    "/storage",
    status_code=status.HTTP_200_OK,
    summary="Check storage health",
    description="Check the health of file storage and data directories.",
)
async def check_storage_health() -> Dict[str, Any]:
    """Check the health of file storage."""
    storage_status = {}
    overall_healthy = True

    # Check datasets directory
    datasets_path = Path(
        "D:\\Projects\\Desktop\\restful-api-testing-framework\\data\\datasets"
    )
    try:
        if datasets_path.exists():
            dataset_dirs = [d for d in datasets_path.iterdir() if d.is_dir()]
            storage_status["datasets_directory"] = {
                "status": "healthy",
                "path": str(datasets_path),
                "exists": True,
                "dataset_count": len(dataset_dirs),
                "error": None,
            }
        else:
            storage_status["datasets_directory"] = {
                "status": "warning",
                "path": str(datasets_path),
                "exists": False,
                "dataset_count": 0,
                "error": "Directory does not exist",
            }
    except Exception as e:
        storage_status["datasets_directory"] = {
            "status": "unhealthy",
            "path": str(datasets_path),
            "exists": False,
            "dataset_count": 0,
            "error": str(e),
        }
        overall_healthy = False

    # Check individual dataset directories
    if datasets_path.exists():
        dataset_details = []
        for dataset_dir in datasets_path.iterdir():
            if dataset_dir.is_dir():
                dataset_info = {
                    "dataset_id": dataset_dir.name,
                    "files": [],
                    "file_count": 0,
                }

                try:
                    for file_path in dataset_dir.iterdir():
                        if file_path.is_file():
                            dataset_info["files"].append(
                                {
                                    "name": file_path.name,
                                    "size": file_path.stat().st_size,
                                    "modified": datetime.fromtimestamp(
                                        file_path.stat().st_mtime
                                    ).isoformat(),
                                }
                            )
                            dataset_info["file_count"] += 1
                except Exception as e:
                    dataset_info["error"] = str(e)

                dataset_details.append(dataset_info)

        storage_status["dataset_details"] = dataset_details

    # Check global storage files
    global_files = [
        "data/endpoints.json",
        "data/constraints.json",
        "data/validation_scripts.json",
        "data/test_data.json",
        "data/executions.json",
    ]

    global_storage_status = {}
    for file_path in global_files:
        full_path = (
            Path("D:\\Projects\\Desktop\\restful-api-testing-framework") / file_path
        )
        try:
            if full_path.exists():
                file_stat = full_path.stat()
                global_storage_status[file_path] = {
                    "status": "healthy",
                    "exists": True,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "error": None,
                }
            else:
                global_storage_status[file_path] = {
                    "status": "warning",
                    "exists": False,
                    "size": 0,
                    "modified": None,
                    "error": "File does not exist",
                }
        except Exception as e:
            global_storage_status[file_path] = {
                "status": "unhealthy",
                "exists": False,
                "size": 0,
                "modified": None,
                "error": str(e),
            }
            overall_healthy = False

    storage_status["global_files"] = global_storage_status

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "storage": storage_status,
        "overall_healthy": overall_healthy,
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if the service is ready to accept requests.",
)
async def readiness_check(
    dataset_service: DatasetService = dataset_service_dependency,
    endpoint_service: EndpointService = endpoint_service_dependency,
) -> Dict[str, Any]:
    """Check if the service is ready to accept requests."""
    try:
        # Check if we can access datasets
        datasets = await dataset_service.get_all_datasets()

        # Check if we can access endpoints
        endpoints = await endpoint_service.get_all_endpoints()

        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "datasets_accessible": True,
            "endpoints_accessible": True,
            "datasets_count": len(datasets),
            "endpoints_count": len(endpoints),
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat(),
            "datasets_accessible": False,
            "endpoints_accessible": False,
            "datasets_count": 0,
            "endpoints_count": 0,
            "error": str(e),
        }


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if the service is alive and responding.",
)
async def liveness_check() -> Dict[str, Any]:
    """Check if the service is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "unknown",  # Could be enhanced with actual uptime tracking
    }
