"""
Test Cases API routes for managing test case generation and CRUD operations
"""

from fastapi import APIRouter, Request, HTTPException
from typing import List
import json
import os
import csv
from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..models import (
    GenerateTestCasesRequest, GenerateAllRequest, ApiResponse, 
    TestCaseInfo, UpdateTestCaseRequest
)
from ..database import DatabaseManager
from ..services.integration import KATIntegrationService

router = APIRouter()


@router.post("/services/{service_id}/generate/test-cases", response_model=ApiResponse)
async def generate_test_cases(request: Request, service_id: str, generate_request: GenerateTestCasesRequest):
    """Generate test cases for specified endpoints"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # TODO: Integrate with TestCaseGenerator
        # For now, simulate test case generation
        
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        
        # Clear existing test cases if requested
        if generate_request.clear_test_cases:
            for file in test_cases_dir.glob("*.json"):
                file.unlink()
        
        # Determine which endpoints to generate test cases for
        endpoints_to_generate = []
        if generate_request.selected_endpoints:
            endpoints_to_generate = generate_request.selected_endpoints
        else:
            # Generate for all endpoints - get them from the service's OpenAPI spec
            try:
                from services.integration import KATIntegrationService
                service = db_manager.get_service(service_id)
                if not service:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Get all endpoints from the OpenAPI spec using KAT integration
                kat_service = KATIntegrationService(service_id, service["name"])
                all_endpoints = kat_service.get_endpoints_from_spec()
                endpoints_to_generate = [f"{ep['method'].lower()}-{ep['path']}" for ep in all_endpoints]
                
                if not endpoints_to_generate:
                    raise HTTPException(status_code=400, detail="No endpoints found in service specification")
                    
            except Exception as e:
                logger.error(f"Failed to get endpoints from service spec: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get service endpoints: {str(e)}")

        # Use KAT integration for proper test case generation
        try:
            from services.integration import KATIntegrationService
            service = db_manager.get_service(service_id)
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
                
            kat_service = KATIntegrationService(service_id, service["name"])
            
            # Use KAT's test case generation method
            logger.info(f"Using KAT to generate test cases for {len(endpoints_to_generate)} endpoints")
            result = kat_service.generate_test_cases(endpoints_to_generate, generate_request.clear_test_cases)
            
            if result.get("success"):
                generated_files = result.get("generated_files", [])
                logger.info(f"KAT successfully generated {result.get('test_cases_generated', 0)} test case files")
            else:
                error_msg = result.get('error', 'Unknown KAT error')
                logger.error(f"KAT test case generation failed: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Test case generation failed: {error_msg}")
                
        except ImportError as ie:
            logger.error(f"KAT components not available: {ie}")
            raise HTTPException(status_code=500, detail="KAT test case generation components not available")
        except Exception as e:
            logger.error(f"KAT test case generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate test cases: {str(e)}")
        
        # Update service test cases count
        test_cases_count = len(list(test_cases_dir.glob("*.json")))
        db_manager.update_service(service_id, {"test_cases_count": test_cases_count})
        
        return ApiResponse(
            success=True,
            message=f"Generated {len(generated_files)} test cases",
            data={"generated_files": generated_files}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test cases: {str(e)}")


@router.post("/services/{service_id}/generate/all", response_model=ApiResponse)
async def generate_all(request: Request, service_id: str, generate_request: GenerateAllRequest):
    """Generate both test cases and test data for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Get all endpoints from the service's OpenAPI spec
        try:
            from services.integration import KATIntegrationService
            service = db_manager.get_service(service_id)
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
            
            # Get all endpoints from the OpenAPI spec using KAT integration
            kat_service = KATIntegrationService(service_id, service["name"])
            all_endpoints = kat_service.get_endpoints_from_spec()
            endpoints_to_generate = [f"{ep['method'].lower()}-{ep['path']}" for ep in all_endpoints]
            
            if not endpoints_to_generate:
                raise HTTPException(status_code=400, detail="No endpoints found in service specification")
                
        except Exception as e:
            logger.error(f"Failed to get endpoints from service spec: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get service endpoints: {str(e)}")
        
        # Use KAT integration to generate both test cases and test data
        try:
            from services.integration import KATIntegrationService
            service = db_manager.get_service(service_id)
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
                
            kat_service = KATIntegrationService(service_id, service["name"])
            
            results = {
                "test_cases_generated": 0,
                "test_data_generated": 0,
                "generated_files": []
            }
            
            # Generate test cases using KAT
            logger.info(f"Using KAT to generate test cases for {len(endpoints_to_generate)} endpoints")
            test_case_result = kat_service.generate_test_cases(endpoints_to_generate, False)
            
            if test_case_result.get("success"):
                results["test_cases_generated"] = test_case_result.get("test_cases_generated", 0)
                results["generated_files"].extend(test_case_result.get("generated_files", []))
                logger.info(f"KAT successfully generated {results['test_cases_generated']} test case files")
            else:
                logger.warning(f"KAT test case generation failed: {test_case_result.get('error')}")
            
            # Generate test data using KAT
            logger.info(f"Using KAT to generate test data for {len(endpoints_to_generate)} endpoints")
            test_data_result = kat_service.generate_test_data(endpoints_to_generate, False)
            
            if test_data_result.get("success"):
                results["test_data_generated"] = test_data_result.get("test_data_generated", 0)
                results["generated_files"].extend(test_data_result.get("generated_files", []))
                logger.info(f"KAT successfully generated {results['test_data_generated']} test data files")
            else:
                logger.warning(f"KAT test data generation failed: {test_data_result.get('error')}")
                
        except ImportError as ie:
            logger.error(f"KAT components not available: {ie}")
            raise HTTPException(status_code=500, detail="KAT generation components not available")
        except Exception as e:
            logger.error(f"KAT generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate test cases and data: {str(e)}")
        
        # Update service counts
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        test_data_dir = service_dir / "test_data"
        test_cases_count = len(list(test_cases_dir.glob("*.json")))
        test_data_count = len(list(test_data_dir.glob("*.csv")))
        db_manager.update_service(service_id, {
            "test_cases_count": test_cases_count,
            "test_data_count": test_data_count
        })
        
        return ApiResponse(
            success=True,
            message=f"Generated {results['test_cases_generated']} test cases and {results['test_data_generated']} test data files",
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate all: {str(e)}")


@router.get("/services/{service_id}/test-cases", response_model=ApiResponse)
async def list_test_cases(request: Request, service_id: str):
    """List all test cases for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        
        test_cases = []
        for test_case_file in test_cases_dir.glob("*.json"):
            try:
                with open(test_case_file, 'r', encoding='utf-8') as f:
                    test_case_data = json.load(f)
                
                test_case = TestCaseInfo(
                    id=test_case_data.get("id", test_case_file.stem),
                    endpoint=test_case_data.get("endpoint", ""),
                    method=test_case_data.get("method", ""),
                    path=test_case_data.get("path", ""),
                    description=test_case_data.get("description"),
                    parameters=test_case_data.get("parameters"),
                    body=test_case_data.get("body"),
                    expected_status=test_case_data.get("expected_status"),
                    created_at=test_case_data.get("created_at", "")
                )
                test_cases.append(test_case)
            except (json.JSONDecodeError, KeyError):
                continue
        
        return ApiResponse(
            success=True,
            message="Test cases retrieved successfully",
            data=test_cases
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test cases: {str(e)}")


@router.get("/services/{service_id}/test-cases/{test_case_id}", response_model=ApiResponse)
async def get_test_case(request: Request, service_id: str, test_case_id: str):
    """Get a specific test case"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        
        # Find test case file
        test_case_file = None
        for file in test_cases_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("id") == test_case_id or file.stem == test_case_id:
                        test_case_file = file
                        break
            except:
                continue
        
        if not test_case_file:
            raise HTTPException(status_code=404, detail="Test case not found")
        
        with open(test_case_file, 'r', encoding='utf-8') as f:
            test_case_data = json.load(f)
        
        return ApiResponse(
            success=True,
            message="Test case retrieved successfully",
            data=test_case_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test case: {str(e)}")


@router.put("/services/{service_id}/test-cases/{test_case_id}", response_model=ApiResponse)
async def update_test_case(request: Request, service_id: str, test_case_id: str, update_data: UpdateTestCaseRequest):
    """Update a specific test case"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        
        # Find test case file
        test_case_file = None
        for file in test_cases_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("id") == test_case_id or file.stem == test_case_id:
                        test_case_file = file
                        break
            except:
                continue
        
        if not test_case_file:
            raise HTTPException(status_code=404, detail="Test case not found")
        
        # Load existing data
        with open(test_case_file, 'r', encoding='utf-8') as f:
            test_case_data = json.load(f)
        
        # Update with new data
        update_dict = update_data.dict(exclude_unset=True)
        test_case_data.update(update_dict)
        test_case_data["updated_at"] = db_manager.load_data()["services"][service_id]["updated_at"]
        
        # Save updated data
        with open(test_case_file, 'w', encoding='utf-8') as f:
            json.dump(test_case_data, f, indent=2)
        
        return ApiResponse(
            success=True,
            message="Test case updated successfully",
            data=test_case_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update test case: {str(e)}")


@router.delete("/services/{service_id}/test-cases/{test_case_id}", response_model=ApiResponse)
async def delete_test_case(request: Request, service_id: str, test_case_id: str):
    """Delete a specific test case"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_cases_dir = service_dir / "test_cases"
        
        # Find and delete test case file
        deleted = False
        for file in test_cases_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("id") == test_case_id or file.stem == test_case_id:
                        file.unlink()
                        deleted = True
                        break
            except:
                continue
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Test case not found")
        
        # Update service test cases count
        test_cases_count = len(list(test_cases_dir.glob("*.json")))
        db_manager.update_service(service_id, {"test_cases_count": test_cases_count})
        
        return ApiResponse(
            success=True,
            message="Test case deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test case: {str(e)}")
