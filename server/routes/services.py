"""
Services API routes for managing OpenAPI specifications and services
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from typing import List
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..models import (
    CreateServiceRequest, ServiceSummary, ServiceDetail, UpdateServiceSpecRequest,
    ApiResponse, EndpointInfo, SchemaInfo
)
from ..database import DatabaseManager
from ..services.integration import KATIntegrationService

router = APIRouter()


@router.post("/services", response_model=ApiResponse)
async def create_service(request: Request, service_data: CreateServiceRequest):
    """Create a new service with OpenAPI specification"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        
        # Handle different spec source types
        spec_content = None
        if service_data.swagger_source.type == "upload":
            # Read spec from uploaded file path
            spec_path = service_data.swagger_source.path_or_url
            if not os.path.exists(spec_path):
                raise HTTPException(status_code=400, detail="Spec file not found")
            
            with open(spec_path, 'r', encoding='utf-8') as f:
                spec_content = f.read()
                
        elif service_data.swagger_source.type == "url":
            # TODO: Implement URL fetching
            raise HTTPException(status_code=501, detail="URL spec source not implemented yet")
            
        elif service_data.swagger_source.type == "existing":
            # Use existing file
            spec_path = service_data.swagger_source.path_or_url
            if not os.path.exists(spec_path):
                raise HTTPException(status_code=400, detail="Existing spec file not found")
                
            with open(spec_path, 'r', encoding='utf-8') as f:
                spec_content = f.read()
        
        # Create service in database
        service_id = db_manager.create_service(
            service_name=service_data.service_name,
            spec_content=spec_content,
            spec_source=service_data.swagger_source.path_or_url
        )
        
        # Setup KAT integration  
        integration_service = KATIntegrationService(
            service_id=service_id,
            service_name=service_data.service_name
        )
        
        # Setup KAT-compatible directory structure
        kat_paths = integration_service.setup_service(spec_content)
        
        # Update service with endpoints count
        db_manager.update_service(service_id, {
            "endpoints_count": len(integration_service.get_endpoints_from_spec())
        })
        
        # TODO: If rebuild_odg is True, trigger ODG generation
        if service_data.rebuild_odg:
            # This will be implemented when we integrate with ODG generator
            pass
        
        return ApiResponse(
            success=True,
            message=f"Service '{service_data.service_name}' created successfully",
            data={"service_id": service_id}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create service: {str(e)}")


@router.get("/services", response_model=ApiResponse)
async def list_services(request: Request):
    """List all registered services"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        services_data = db_manager.get_all_services()
        
        services = [
            ServiceSummary(
                id=service["id"],
                name=service["name"],
                status=service["status"],
                endpoints_count=service.get("endpoints_count", 0),
                test_cases_count=service.get("test_cases_count", 0),
                test_data_count=service.get("test_data_count", 0),
                created_at=service["created_at"],
                updated_at=service["updated_at"]
            )
            for service in services_data
        ]
        
        return ApiResponse(
            success=True,
            message="Services retrieved successfully",
            data=services
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve services: {str(e)}")


@router.get("/services/{service_id}", response_model=ApiResponse)
async def get_service(request: Request, service_id: str):
    """Get detailed information about a specific service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_detail = ServiceDetail(
            id=service_data["id"],
            name=service_data["name"],
            status=service_data["status"],
            endpoints_count=service_data.get("endpoints_count", 0),
            test_cases_count=service_data.get("test_cases_count", 0),
            test_data_count=service_data.get("test_data_count", 0),
            created_at=service_data["created_at"],
            updated_at=service_data["updated_at"],
            spec_path=service_data["spec_path"],
            spec_source=service_data["spec_source"],
            working_dir=service_data["working_dir"]
        )
        
        return ApiResponse(
            success=True,
            message="Service details retrieved successfully",
            data=service_detail
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve service: {str(e)}")


@router.put("/services/{service_id}/spec", response_model=ApiResponse)
async def update_service_spec(request: Request, service_id: str, spec_data: UpdateServiceSpecRequest):
    """Update OpenAPI specification for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Update spec file
        spec_path = service_data["spec_path"]
        with open(spec_path, 'w', encoding='utf-8') as f:
            if isinstance(spec_data.spec_content, str):
                # Validate JSON
                json.loads(spec_data.spec_content)
                f.write(spec_data.spec_content)
            else:
                json.dump(spec_data.spec_content, f, indent=2)
        
        # Update database
        db_manager.update_service(service_id, {
            "updated_at": db_manager.load_data()["services"][service_id]["updated_at"]
        })
        
        # TODO: If rebuild_odg is True, trigger ODG regeneration
        if spec_data.rebuild_odg:
            pass
        
        return ApiResponse(
            success=True,
            message="Service specification updated successfully"
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON specification")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update specification: {str(e)}")


@router.delete("/services/{service_id}", response_model=ApiResponse)
async def delete_service(request: Request, service_id: str):
    """Delete a service and all its associated data"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        
        if not db_manager.get_service(service_id):
            raise HTTPException(status_code=404, detail="Service not found")
        
        success = db_manager.delete_service(service_id)
        
        if success:
            return ApiResponse(
                success=True,
                message="Service deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete service")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete service: {str(e)}")

@router.delete("/services/by-name/{service_name}", response_model=ApiResponse)
async def delete_service(request: Request, service_name: str):
    """Delete a service and all its associated data"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        
        # Find service by name
        services = db_manager.get_all_services()
        service = next((s for s in services if s["name"] == service_name), None)
        
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        success = db_manager.delete_service_by_name(service_name)
        
        if success:
            return ApiResponse(
                success=True,
                message="Service deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete service")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete service: {str(e)}")
@router.get("/services/{service_id}/endpoints", response_model=ApiResponse)
async def get_service_endpoints(request: Request, service_id: str):
    """Get list of endpoints for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Use KAT integration to extract endpoints
        integration_service = KATIntegrationService(
            service_id=service_id,
            service_name=service_data["name"]
        )
        
        endpoints_data = integration_service.get_endpoints_from_spec()
        
        endpoints = [
            EndpointInfo(
                method=endpoint["method"],
                path=endpoint["path"],
                operation_id=endpoint["operation_id"],
                summary=f"{endpoint['method']} {endpoint['path']}"
            )
            for endpoint in endpoints_data
        ]
        
        return ApiResponse(
            success=True,
            message="Endpoints retrieved successfully",
            data=endpoints
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve endpoints: {str(e)}")


@router.get("/services/{service_id}/schemas", response_model=ApiResponse)
async def get_service_schemas(request: Request, service_id: str):
    """Get schemas from OpenAPI specification"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Use KAT integration to extract schemas
        integration_service = KATIntegrationService(
            service_id=service_id,
            service_name=service_data["name"]
        )
        
        schemas_data = integration_service.get_schemas_from_spec()
        
        schemas = [
            SchemaInfo(
                name=name,
                type=schema.get("type", "object"),
                properties=schema.get("properties", {})
            )
            for name, schema in schemas_data.items()
        ]
        
        return ApiResponse(
            success=True,
            message="Schemas retrieved successfully",
            data=schemas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve schemas: {str(e)}")


@router.post("/services/upload-spec", response_model=ApiResponse)
async def upload_spec_file(file: UploadFile = File(...)):
    """Upload OpenAPI specification file"""
    try:
        if not file.filename.endswith(('.json', '.yaml', '.yml')):
            raise HTTPException(status_code=400, detail="Only JSON and YAML files are supported")
        
        # Save uploaded file temporarily
        project_root = Path(__file__).parent.parent.parent
        uploads_dir = project_root / "server" / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        file_path = uploads_dir / file.filename
        
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Validate the file content
        if file.filename.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)  # Validate JSON
        
        return ApiResponse(
            success=True,
            message="Specification file uploaded successfully",
            data={"file_path": str(file_path)}
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
