"""
Test Data API routes for managing test data generation and validation
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from typing import List, Optional
import json
import os
import csv
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from ..models import GenerateTestDataRequest, ApiResponse
from ..database import DatabaseManager

router = APIRouter()


@router.post("/services/{service_id}/generate/test-data", response_model=ApiResponse)
async def generate_test_data(request: Request, service_id: str, generate_request: GenerateTestDataRequest):
    """Generate test data for specified endpoints using TestCaseGenerator"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_name = service_data["name"]
        logger.info(f"Generating test data for service: {service_name}")
        
        # Import TestCaseGenerator
        try:
            from kat.test_case_generator.test_case_generator import TestCaseGenerator
        except ImportError as e:
            logger.error(f"Failed to import TestCaseGenerator: {e}")
            raise HTTPException(status_code=500, detail="TestCaseGenerator not available")
        
        # Initialize TestCaseGenerator with options
        generator = TestCaseGenerator(
            service_name=service_name,
            collection="Default",
            save_prompts=True,
            regenerate_test_data=generate_request.regenerate,  # Use regenerate option from request
            data_generation_mode="all" if generate_request.mode == "all" else "selected",
            clear_test_cases=False  # Don't clear test cases when generating data
        )
        
        generated_files = []
        
        # Determine which endpoints to generate data for
        if generate_request.mode == "all" or not generate_request.endpoints:
            # Generate for all endpoints
            logger.info("Generating test data for ALL endpoints")
            try:
                # Get all endpoints from the generator
                all_endpoints = generator.get_endpoints()
                if not all_endpoints:
                    raise HTTPException(status_code=400, detail="No endpoints found in service specification")
                
                logger.info(f"Found {len(all_endpoints)} endpoints: {all_endpoints}")
                
                # Generate test data for all endpoints
                result = generator.generate_test_data_for(all_endpoints)
                
                # Collect generated files
                service_dir = Path(service_data["working_dir"])
                test_data_dir = service_dir / "test_data"
                
                # Look for CSV files in multiple locations
                csv_patterns = [
                    test_data_dir.glob("*.csv"),
                    test_data_dir.glob("csv/*.csv"),
                    test_data_dir.glob("**/*.csv")
                ]
                
                found_files = set()
                for pattern in csv_patterns:
                    for csv_file in pattern:
                        if csv_file not in found_files:
                            found_files.add(csv_file)
                            generated_files.append(str(csv_file))
                
                logger.info(f"Generated test data files: {generated_files}")
                
            except Exception as e:
                logger.error(f"Failed to generate test data for all endpoints: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to generate test data: {str(e)}")
        
        else:
            # Generate for selected endpoints
            endpoints = generate_request.endpoints
            logger.info(f"Generating test data for selected endpoints: {endpoints}")
            
            try:
                # Generate test data for specific endpoints
                result = generator.generate_test_data_for(endpoints)
                
                # Collect generated files
                service_dir = Path(service_data["working_dir"])
                test_data_dir = service_dir / "test_data"
                
                # Look for files related to specified endpoints
                for endpoint in endpoints:
                    # Convert endpoint format for file matching
                    endpoint_pattern = endpoint.replace('-', '_').replace('/', '_')
                    
                    csv_patterns = [
                        test_data_dir.glob(f"*{endpoint_pattern}*.csv"),
                        test_data_dir.glob(f"csv/*{endpoint_pattern}*.csv"),
                        test_data_dir.glob(f"**/*{endpoint_pattern}*.csv")
                    ]
                    
                    for pattern in csv_patterns:
                        for csv_file in pattern:
                            generated_files.append(str(csv_file))
                
                logger.info(f"Generated test data files: {generated_files}")
                
            except Exception as e:
                logger.error(f"Failed to generate test data for selected endpoints: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to generate test data: {str(e)}")
        
        # Update service test data count
        service_dir = Path(service_data["working_dir"])
        test_data_dir = service_dir / "test_data"
        test_data_count = len(list(test_data_dir.glob("*.csv"))) + len(list(test_data_dir.glob("csv/*.csv")))
        db_manager.update_service(service_id, {"test_data_count": test_data_count})
        
        return ApiResponse(
            success=True,
            message=f"Generated test data for {len(generated_files)} endpoint(s) using TestCaseGenerator",
            data={
                "generated_files": generated_files,
                "mode": generate_request.mode,
                "regenerate": generate_request.regenerate,
                "endpoints_processed": len(generate_request.endpoints) if generate_request.endpoints else len(generator.get_endpoints())
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_test_data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate test data: {str(e)}")


@router.post("/services/{service_id}/generate/complete", response_model=ApiResponse)
async def generate_complete_test_suite(request: Request, service_id: str, generate_request: GenerateTestDataRequest):
    """Generate both test cases and test data using TestCaseGenerator (like run_generator.py)"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_name = service_data["name"]
        logger.info(f"Generating complete test suite for service: {service_name}")
        
        # Import TestCaseGenerator
        try:
            from kat.test_case_generator.test_case_generator import TestCaseGenerator
        except ImportError as e:
            logger.error(f"Failed to import TestCaseGenerator: {e}")
            raise HTTPException(status_code=500, detail="TestCaseGenerator not available")
        
        # Initialize TestCaseGenerator with full options
        generator = TestCaseGenerator(
            service_name=service_name,
            collection="Default",
            save_prompts=True,
            regenerate_test_data=generate_request.regenerate,
            data_generation_mode="all" if generate_request.mode == "all" else "selected",
            clear_test_cases=False  # Don't clear existing test cases
        )
        
        results = {
            "test_data_generated": 0,
            "test_cases_generated": 0,
            "generated_files": [],
            "endpoints_processed": 0
        }
        
        try:
            # Step 1: Generate test data first (like in run_generator.py)
            logger.info("Step 1: Generating test data...")
            
            if generate_request.mode == "all" or not generate_request.endpoints:
                # Get all endpoints
                all_endpoints = generator.get_endpoints()
                logger.info(f"Generating test data for all {len(all_endpoints)} endpoints")
                generator.generate_test_data_for(all_endpoints)
                results["endpoints_processed"] = len(all_endpoints)
            else:
                # Generate for selected endpoints
                logger.info(f"Generating test data for selected endpoints: {generate_request.endpoints}")
                generator.generate_test_data_for(generate_request.endpoints)
                results["endpoints_processed"] = len(generate_request.endpoints)
            
            # Step 2: Generate test cases (like in run_generator.py)
            logger.info("Step 2: Generating test cases...")
            
            if generate_request.mode == "all" or not generate_request.endpoints:
                # Generate test cases for all endpoints
                generator.generate_test_cases()
            else:
                # Generate test cases for selected endpoints
                generator.generate_test_cases(generate_request.endpoints)
            
            # Step 3: Collect generated files
            service_dir = Path(service_data["working_dir"])
            
            # Count test data files
            test_data_dir = service_dir / "test_data"
            test_data_patterns = [
                test_data_dir.glob("*.csv"),
                test_data_dir.glob("csv/*.csv"),
                test_data_dir.glob("**/*.csv")
            ]
            
            test_data_files = set()
            for pattern in test_data_patterns:
                for csv_file in pattern:
                    if csv_file not in test_data_files:
                        test_data_files.add(csv_file)
                        results["generated_files"].append(str(csv_file))
            
            results["test_data_generated"] = len(test_data_files)
            
            # Count test case files
            test_cases_dir = service_dir / "test_cases"
            test_case_files = list(test_cases_dir.glob("*.json"))
            results["test_cases_generated"] = len(test_case_files)
            
            for json_file in test_case_files:
                results["generated_files"].append(str(json_file))
            
            # Update service counts
            test_data_count = len(test_data_files)
            test_cases_count = len(test_case_files)
            db_manager.update_service(service_id, {
                "test_data_count": test_data_count,
                "test_cases_count": test_cases_count
            })
            
            logger.info(f"✅ Complete generation finished!")
            logger.info(f"Generated {results['test_data_generated']} test data files")
            logger.info(f"Generated {results['test_cases_generated']} test case files")
            
            return ApiResponse(
                success=True,
                message=f"Generated complete test suite: {results['test_cases_generated']} test cases, {results['test_data_generated']} test data files",
                data=results
            )
            
        except Exception as e:
            logger.error(f"Failed during complete test suite generation: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate complete test suite: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_complete_test_suite: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate complete test suite: {str(e)}")


@router.get("/services/{service_id}/test-data", response_model=ApiResponse)
async def list_test_data(request: Request, service_id: str):
    """List all test data files for a service"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_data_dir = service_dir / "test_data"
        
        test_data_files = []
        # Look for CSV files in both test_data and test_data/csv directories
        csv_patterns = [
            test_data_dir.glob("*.csv"),           # Direct in test_data
            test_data_dir.glob("csv/*.csv"),       # In csv subdirectory
            test_data_dir.glob("**/*.csv")         # Recursive search
        ]
        
        found_files = set()
        for pattern in csv_patterns:
            for csv_file in pattern:
                if csv_file not in found_files:
                    found_files.add(csv_file)
        
        # Process each found file
        for csv_file in found_files:
            file_info = {
                "filename": csv_file.name,
                "path": str(csv_file),
                "size": csv_file.stat().st_size,
                "modified_at": csv_file.stat().st_mtime,
                "endpoint": csv_file.stem.replace('_', '-')
            }
            
            # Read first few rows to get column info
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    row_count = sum(1 for _ in reader)
                    file_info["headers"] = headers
                    file_info["row_count"] = row_count
            except:
                file_info["headers"] = []
                file_info["row_count"] = 0
            
            test_data_files.append(file_info)
        
        return ApiResponse(
            success=True,
            message="Test data files retrieved successfully",
            data=test_data_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test data: {str(e)}")


@router.get("/services/{service_id}/test-data/{filename}", response_model=ApiResponse)
async def get_test_data_file(request: Request, service_id: str, filename: str):
    """Get content of a specific test data file"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_data_dir = service_dir / "test_data"
        
        # Look for file in both test_data and test_data/csv directories
        possible_paths = [
            test_data_dir / filename,
            test_data_dir / "csv" / filename
        ]
        
        test_data_file = None
        for path in possible_paths:
            if path.exists():
                test_data_file = path
                break
        
        if not test_data_file:
            raise HTTPException(status_code=404, detail="Test data file not found")
        
        # Read CSV content
        data_rows = []
        with open(test_data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data_rows = list(reader)
        
        file_info = {
            "filename": filename,
            "headers": list(data_rows[0].keys()) if data_rows else [],
            "row_count": len(data_rows),
            "data": data_rows
        }
        
        return ApiResponse(
            success=True,
            message="Test data file retrieved successfully",
            data=file_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test data file: {str(e)}")


@router.post("/services/{service_id}/test-data/validate", response_model=ApiResponse)
async def validate_test_data(request: Request, service_id: str):
    """Validate test data files structure and required columns"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_data_dir = service_dir / "test_data"
        
        validation_results = []
        required_columns = ["expected_status_code", "expected_code"]  # Standard columns
        
        for csv_file in test_data_dir.glob("*.csv"):
            file_result = {
                "filename": csv_file.name,
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames or []
                    
                    # Check for required columns
                    missing_columns = []
                    for col in required_columns:
                        if col not in headers:
                            missing_columns.append(col)
                    
                    if missing_columns:
                        file_result["warnings"].append(f"Missing optional columns: {', '.join(missing_columns)}")
                    
                    # Validate data rows
                    row_count = 0
                    for row_num, row in enumerate(reader, start=2):
                        row_count += 1
                        
                        # Check for empty required fields
                        for col in headers:
                            if col.startswith("expected_") and not row.get(col, "").strip():
                                file_result["errors"].append(f"Row {row_num}: Empty value in '{col}'")
                        
                        # Validate status codes
                        if "expected_status_code" in row:
                            status_code = row["expected_status_code"].strip()
                            if status_code and not status_code.isdigit():
                                file_result["errors"].append(f"Row {row_num}: Invalid status code '{status_code}'")
                    
                    if row_count == 0:
                        file_result["errors"].append("File contains no data rows")
                    
                    file_result["row_count"] = row_count
                    
            except Exception as e:
                file_result["valid"] = False
                file_result["errors"].append(f"Failed to read file: {str(e)}")
            
            if file_result["errors"]:
                file_result["valid"] = False
            
            validation_results.append(file_result)
        
        overall_valid = all(result["valid"] for result in validation_results)
        
        return ApiResponse(
            success=True,
            message=f"Validation completed. {len([r for r in validation_results if r['valid']])} of {len(validation_results)} files are valid",
            data={
                "overall_valid": overall_valid,
                "file_results": validation_results
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate test data: {str(e)}")


@router.delete("/services/{service_id}/test-data/{filename}", response_model=ApiResponse)
async def delete_test_data_file(request: Request, service_id: str, filename: str):
    """Delete a specific test data file"""
    try:
        db_manager: DatabaseManager = request.app.state.db
        service_data = db_manager.get_service(service_id)
        
        if not service_data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        service_dir = Path(service_data["working_dir"])
        test_data_dir = service_dir / "test_data"
        
        # Look for file in both test_data and test_data/csv directories
        possible_paths = [
            test_data_dir / filename,
            test_data_dir / "csv" / filename
        ]
        
        test_data_file = None
        for path in possible_paths:
            if path.exists():
                test_data_file = path
                break
        
        if not test_data_file:
            raise HTTPException(status_code=404, detail="Test data file not found")
        
        test_data_file.unlink()
        
        # Update service test data count
        test_data_count = len(list((service_dir / "test_data").glob("*.csv")))
        db_manager.update_service(service_id, {"test_data_count": test_data_count})
        
        return ApiResponse(
            success=True,
            message="Test data file deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test data file: {str(e)}")
