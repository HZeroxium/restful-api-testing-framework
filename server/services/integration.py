"""
Integration service to connect the API server with existing KAT components
Now uses shared_config for unified directory structure
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src directory to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import shared_config for unified directory management
try:
    from shared_config import (
        ensure_service_structure,
        get_data_dir_file,
        get_test_case_generator_working_dir,
        get_test_data_working_dir,
        get_results_dir,
        get_odg_working_dir,
        service_exists
    )
    SHARED_CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import shared_config: {e}")
    SHARED_CONFIG_AVAILABLE = False

try:
    from kat.test_case_generator.test_case_generator import TestCaseGenerator, get_endpoints, get_schemas, read_swagger_data
    from sequence_runner.runner import SequenceRunner
    KAT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: KAT components not available: {e}")
    KAT_AVAILABLE = False


# ServiceDirectoryManager removed - functionality moved to shared_config


class KATIntegrationService:
    """Service to integrate with KAT components"""
    
    def __init__(self, service_id: str, service_name: str, services_base_dir: Path = None):
        self.service_id = service_id
        self.service_name = service_name
        
        if SHARED_CONFIG_AVAILABLE:
            self.service_dir = ensure_service_structure(service_name)
        else:
            # Fallback path
            self.service_dir = services_base_dir / service_name if services_base_dir else Path(service_name)
        
    def setup_service(self, spec_content: str) -> Dict[str, str]:
        """Setup service with KAT-compatible structure"""
        if SHARED_CONFIG_AVAILABLE:
            # Service structure already created by shared_config
            spec_file = self.service_dir / "specs" / "openapi.json"
            with open(spec_file, 'w', encoding='utf-8') as f:
                if isinstance(spec_content, str):
                    f.write(spec_content)
                else:
                    json.dump(spec_content, f, indent=2)
            
            return {
                "spec_path": str(spec_file),
                "working_dir": str(self.service_dir),
                "test_cases_dir": str(self.service_dir / "test_cases"),
                "test_data_dir": str(self.service_dir / "test_data"),
                "results_dir": str(self.service_dir / "results"),
                "odg_dir": str(self.service_dir / "ODG")
            }
        else:
            # Fallback implementation
            self.service_dir.mkdir(exist_ok=True)
            spec_file = self.service_dir / "openapi.json"
            with open(spec_file, 'w', encoding='utf-8') as f:
                if isinstance(spec_content, str):
                    f.write(spec_content)
                else:
                    json.dump(spec_content, f, indent=2)
            return {"spec_path": str(spec_file)}
    
    def get_endpoints_from_spec(self) -> List[Dict[str, Any]]:
        """Extract endpoints from OpenAPI spec using KAT functions"""
        if not KAT_AVAILABLE:
            print("KAT components not available")
            return []
        
        try:
            if SHARED_CONFIG_AVAILABLE:
                spec_file = get_data_dir_file(self.service_name)
            else:
                spec_file = self.service_dir / "openapi.json"
            
            if not os.path.exists(spec_file):
                return []
            
            swagger_spec = read_swagger_data(spec_file)
            endpoints_list = get_endpoints(swagger_spec)
            
            # Convert to detailed endpoint info
            endpoints = []
            for endpoint_str in endpoints_list:
                if '-' in endpoint_str:
                    method, path = endpoint_str.split('-', 1)
                    endpoints.append({
                        "method": method.upper(),
                        "path": path,
                        "endpoint_id": endpoint_str,
                        "operation_id": f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
                    })
            
            return endpoints
            
        except Exception as e:
            print(f"Error extracting endpoints: {e}")
            return []
    
    def get_schemas_from_spec(self) -> Dict[str, Any]:
        """Extract schemas from OpenAPI spec using KAT functions"""
        if not KAT_AVAILABLE:
            return {}
        
        try:
            if SHARED_CONFIG_AVAILABLE:
                spec_file = get_data_dir_file(self.service_name)
            else:
                spec_file = self.service_dir / "openapi.json"
            
            if not os.path.exists(spec_file):
                return {}
            
            swagger_spec = read_swagger_data(spec_file)
            return get_schemas(swagger_spec)
            
        except Exception as e:
            print(f"Error extracting schemas: {e}")
            return {}
    
    def generate_test_cases(self, selected_endpoints: Optional[List[str]] = None, 
                          clear_test_cases: bool = False) -> Dict[str, Any]:
        """Generate test cases using KAT TestCaseGenerator"""
        if not KAT_AVAILABLE:
            raise Exception("KAT components not available")
        
        try:
            # Temporarily patch the working directory to point to our service
            original_working_dir = None
            if hasattr(sys.modules.get('kat.directory_config.directory_config'), 'WORKING_DIRECTORY'):
                import kat.directory_config.directory_config as dc
                original_working_dir = dc.WORKING_DIRECTORY
                # Update to point to our service directory
                dc.WORKING_DIRECTORY = str(self.service_dir)
            
            # Create TestCaseGenerator instance
            generator = TestCaseGenerator(
                service_name=self.service_name,
                collection="default",
                selected_endpoints=selected_endpoints,
                clear_test_cases=clear_test_cases
            )
            
            # Generate test cases
            result = generator.generate_test_cases()
            
            # Restore original working directory
            if original_working_dir and hasattr(sys.modules.get('kat.directory_config.directory_config'), 'WORKING_DIRECTORY'):
                dc.WORKING_DIRECTORY = original_working_dir
            
            # Count generated files  
            if SHARED_CONFIG_AVAILABLE:
                from shared_config import get_test_case_generator_working_dir
                test_cases_dir = Path(get_test_case_generator_working_dir(self.service_name))
            else:
                test_cases_dir = self.service_dir / "test_cases"
            test_case_files = list(test_cases_dir.glob("*.json"))
            
            return {
                "success": True,
                "test_cases_generated": len(test_case_files),
                "generated_files": [str(f) for f in test_case_files],
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_cases_generated": 0,
                "generated_files": []
            }
    
    def generate_test_data(self, endpoints: Optional[List[str]] = None, 
                          regenerate: bool = False) -> Dict[str, Any]:
        """Generate test data using KAT TestDataGenerator"""
        if not KAT_AVAILABLE:
            raise Exception("KAT components not available")
        
        try:
            # Patch working directory similar to test case generation
            original_working_dir = None
            if hasattr(sys.modules.get('kat.directory_config.directory_config'), 'WORKING_DIRECTORY'):
                import kat.directory_config.directory_config as dc
                original_working_dir = dc.WORKING_DIRECTORY
                dc.WORKING_DIRECTORY = str(self.service_dir)
            
            # Create TestCaseGenerator and generate test data
            generator = TestCaseGenerator(
                service_name=self.service_name,
                collection="default",
                regenerate_test_data=regenerate
            )
            
            if endpoints:
                result = generator.generate_test_data_for(endpoints)
            else:
                result = generator.generate_test_data()
            
            # Restore original working directory
            if original_working_dir:
                dc.WORKING_DIRECTORY = original_working_dir
            
            # Count generated files
            if SHARED_CONFIG_AVAILABLE:
                from shared_config import get_test_data_working_dir
                test_data_dir = Path(get_test_data_working_dir(self.service_name))
            else:
                test_data_dir = self.service_dir / "test_data"
            test_data_files = list(test_data_dir.glob("*.csv"))
            
            return {
                "success": True,
                "test_data_generated": len(test_data_files),
                "generated_files": [str(f) for f in test_data_files],
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_data_generated": 0,
                "generated_files": []
            }
    
    def run_tests(self, base_url: str, token: Optional[str] = None,
                   
                  endpoint_filter: Optional[str] = None, out_file_name: Optional[str] = None ) -> Dict[str, Any]:
        """Run tests using SequenceRunner"""
        if not KAT_AVAILABLE:
            raise Exception("KAT components not available")
        
        try:
            # Patch working directory
            original_working_dir = None
            if hasattr(sys.modules.get('kat.directory_config.directory_config'), 'WORKING_DIRECTORY'):
                import kat.directory_config.directory_config as dc
                original_working_dir = dc.WORKING_DIRECTORY
                dc.WORKING_DIRECTORY = str(self.service_dir)
            
            # Create and configure SequenceRunner
            from sequence_runner.runner import SequenceRunner
            runner = SequenceRunner(
                service_name=self.service_name,
                base_url=base_url,
                token=token,
                endpoint=endpoint_filter,
                out_file_name=out_file_name
            )
            
            # Run tests
            out_dir_name = runner.run_all()
            
            # Restore original working directory
            if original_working_dir:
                dc.WORKING_DIRECTORY = original_working_dir
            
            return {
                "success": True,
                "out_dir_name": out_dir_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_single_test_case(self, test_case_id: str, base_url: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Run a single test case by ID using SequenceRunner"""
        if not KAT_AVAILABLE:
            raise Exception("KAT components not available")
        
        try:
            # Patch working directory
            original_working_dir = None
            if hasattr(sys.modules.get('kat.directory_config.directory_config'), 'WORKING_DIRECTORY'):
                import kat.directory_config.directory_config as dc
                original_working_dir = dc.WORKING_DIRECTORY
                dc.WORKING_DIRECTORY = str(self.service_dir)
            
            # Find test case file
            if SHARED_CONFIG_AVAILABLE:
                from shared_config import get_test_case_generator_working_dir
                test_cases_dir = Path(get_test_case_generator_working_dir(self.service_name))
            else:
                test_cases_dir = self.service_dir / "test_cases"
            
            # Look for test case file by ID
            test_case_file = None
            for json_file in test_cases_dir.glob("*.json"):
                if json_file.stem == test_case_id or test_case_id in json_file.name:
                    test_case_file = json_file
                    break
            
            if not test_case_file:
                raise Exception(f"Test case file not found for ID: {test_case_id}")
            
            # Create SequenceRunner and run single test case
            from sequence_runner.runner import SequenceRunner
            runner = SequenceRunner(
                service_name=self.service_name,
                base_url=base_url,
                token=token,
                skip_preload=True,
                out_file_name=test_case_id
            )
            
            # Initialize CSV output for results
            results_file = runner.file.open_csv_output(self.service_name)
            
            # Run specific test case
            is_success = runner.run_test_case(test_case_file)
            
            # Close runner to ensure files are properly written
            runner.close()
            
            # Restore original working directory
            if original_working_dir:
                dc.WORKING_DIRECTORY = original_working_dir
            
            return {
                "success": True,
                "test_passed": is_success,
                "test_case_file": str(test_case_file),
                "results_file": results_file,
                "result": f"Test case {'PASSED' if is_success else 'FAILED'}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_test_case_files(self) -> List[Dict[str, Any]]:
        """Get list of test case files"""
        if SHARED_CONFIG_AVAILABLE:
            test_cases_dir = Path(get_test_case_generator_working_dir(self.service_name).rstrip('/'))
        else:
            test_cases_dir = self.service_dir / "test_cases"
        
        test_cases = []
        for json_file in test_cases_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                test_cases.append({
                    "filename": json_file.name,
                    "path": str(json_file),
                    "id": data.get("id", json_file.stem),
                    "endpoint": data.get("endpoint", ""),
                    "method": data.get("method", ""),
                    "path_pattern": data.get("path", ""),
                    "created_at": json_file.stat().st_mtime
                })
            except Exception:
                continue
        
        return test_cases
    
    def get_test_data_files(self) -> List[Dict[str, Any]]:
        """Get list of test data files"""
        if SHARED_CONFIG_AVAILABLE:
            test_data_dir = Path(get_test_data_working_dir(self.service_name).rstrip('/'))
        else:
            test_data_dir = self.service_dir / "test_data"
        
        test_data_files = []
        for csv_file in test_data_dir.glob("*.csv"):
            test_data_files.append({
                "filename": csv_file.name,
                "path": str(csv_file),
                "size": csv_file.stat().st_size,
                "modified_at": csv_file.stat().st_mtime
            })
        
        return test_data_files
