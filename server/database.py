"""
Database manager for storing service metadata and configurations
Uses JSON file as simple database for storing service information
Now integrated with shared_config for unified directory structure
"""

import json
import os
import uuid
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import shutil

# Add src to path for shared_config import
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from shared_config import (
        get_database_base_dir,
        ensure_service_structure,
        register_service,
        list_services,
        service_exists
    )
    SHARED_CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import shared_config: {e}")
    SHARED_CONFIG_AVAILABLE = False


class DatabaseManager:
    """Manages the JSON database file for services metadata"""
    
    def __init__(self, db_path: str = None):
        if SHARED_CONFIG_AVAILABLE:
            # Use shared_config database structure
            database_dir = get_database_base_dir()
            self.db_path = database_dir / "server_metadata.json"
            self.services_dir = database_dir
        else:
            # Fallback to server-specific structure
            if db_path is None:
                project_root = Path(__file__).parent.parent
                self.db_path = project_root / "server" / "database.json"
            else:
                self.db_path = Path(db_path)
            
            self.services_dir = self.db_path.parent / "services_data"
            self.services_dir.mkdir(exist_ok=True)
    
    def initialize_database(self):
        """Initialize database file if it doesn't exist"""
        if not self.db_path.exists():
            initial_data = {
                "services": {},
                "runs": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
            }
            self.save_data(initial_data)
    
    def load_data(self) -> Dict[str, Any]:
        """Load data from JSON database"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.initialize_database()
            return self.load_data()
    
    def save_data(self, data: Dict[str, Any]):
        """Save data to JSON database"""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_service_working_dir(self, service_name: str) -> Path:
        """Get working directory for a service"""
        if SHARED_CONFIG_AVAILABLE:
            # Use shared_config to ensure service structure
            return ensure_service_structure(service_name)
        else:
            # Fallback to server-specific structure
            service_dir = self.services_dir / service_name
            service_dir.mkdir(exist_ok=True)
            
            # Create subdirectories compatible with KAT structure
            (service_dir / "specs").mkdir(exist_ok=True)
            (service_dir / "test_cases").mkdir(exist_ok=True)
            (service_dir / "test_data").mkdir(exist_ok=True)
            (service_dir / "results").mkdir(exist_ok=True)
            (service_dir / "logs").mkdir(exist_ok=True)
            (service_dir / "ODG").mkdir(exist_ok=True)
            
            return service_dir
    
    # Service CRUD operations
    def create_service(self, service_name: str, spec_content: str, spec_source: str) -> str:
        """Create a new service entry"""
        data = self.load_data()

        service_id = str(uuid.uuid4())
        
        if SHARED_CONFIG_AVAILABLE:
            # Use shared_config to register service (service_name as ID)
            service_dir_str = register_service(service_name, spec_content, {
                "service_id": service_id,
                "spec_source": spec_source,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            })
            service_dir = Path(service_dir_str)
            spec_path = service_dir / "specs" / "openapi.json"
        else:
            # Fallback to server-specific structure
            service_dir = self.get_service_working_dir(service_name)
            
            # Save spec file in specs directory
            spec_path = service_dir / "specs" / "openapi.json"
            with open(spec_path, 'w', encoding='utf-8') as f:
                if isinstance(spec_content, str):
                    try:
                        # Validate JSON
                        json.loads(spec_content)
                        f.write(spec_content)
                    except json.JSONDecodeError:
                        raise ValueError("Invalid JSON spec content")
                else:
                    json.dump(spec_content, f, indent=2)
        
        service_data = {
            "id": service_id,
            "name": service_name,
            "spec_path": str(spec_path),
            "spec_source": spec_source,
            "working_dir": str(service_dir),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
            "endpoints_count": 0,
            "test_cases_count": 0,
            "test_data_count": 0
        }
        
        data["services"][service_id] = service_data
        self.save_data(data)
        
        return service_id
    
    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service by ID or name"""
        if SHARED_CONFIG_AVAILABLE:
            # First try to get all services and find by ID or name
            all_services = self.get_all_services()
            for service in all_services:
                if service.get("id") == service_id or service.get("name") == service_id:
                    return service
            return None
        else:
            # Fallback to server metadata only
            data = self.load_data()
            return data["services"].get(service_id)
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get all services"""
        if SHARED_CONFIG_AVAILABLE:
            # Use shared_config to discover services in database folder
            services_from_shared = list_services()
            data = self.load_data()
            
            # Merge with server metadata
            all_services = []
            for service_info in services_from_shared:
                service_name = service_info["name"]
                service_data = None
                
                # Find in server metadata first
                for srv_id, srv_data in data["services"].items():
                    if srv_data.get("name") == service_name:
                        service_data = srv_data
                        break
                
                # If not found in metadata, create default entry
                if not service_data:
                    spec_file = service_info["spec_file"]
                    service_data = {
                        "id": service_name,  # Use service_name as ID for consistency
                        "name": service_name,
                        "spec_path": spec_file,
                        "spec_source": "existing",
                        "working_dir": service_info["path"],
                        "created_at": "unknown",
                        "updated_at": "unknown",
                        "status": "active",
                        "endpoints_count": 0,
                        "test_cases_count": 0,
                        "test_data_count": 0
                    }
                    
                    # Count actual files
                    import os
                    from pathlib import Path
                    service_path = Path(service_info["path"])
                    
                    # Count endpoints from spec file
                    try:
                        import json
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)
                            endpoints_count = 0
                            for path, methods in spec_data.get('paths', {}).items():
                                for method in methods:
                                    if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                                        endpoints_count += 1
                            service_data["endpoints_count"] = endpoints_count
                    except:
                        service_data["endpoints_count"] = 0
                    
                    # Count test cases
                    test_cases_dir = service_path / "test_cases"
                    if test_cases_dir.exists():
                        service_data["test_cases_count"] = len(list(test_cases_dir.glob("*.json")))
                    
                    # Count test data files
                    test_data_dir = service_path / "test_data"
                    if test_data_dir.exists():
                        service_data["test_data_count"] = len(list(test_data_dir.glob("**/*.csv")))
                
                all_services.append(service_data)
            
            return all_services
        else:
            # Fallback to server metadata only
            data = self.load_data()
            return list(data["services"].values())
    
    def update_service(self, service_id: str, updates: Dict[str, Any]) -> bool:
        """Update service data"""
        data = self.load_data()
        if service_id not in data["services"]:
            return False
        
        data["services"][service_id].update(updates)
        data["services"][service_id]["updated_at"] = datetime.now().isoformat()
        self.save_data(data)
        return True
    
    def delete_service(self, service_id: str) -> bool:
        """Delete service and its data"""
        data = self.load_data()
        for srv in data["services"].values():
            print(f"Checking service with name: {srv['name']}")
        if service_id not in data["services"]:
            print(f"Service ID {service_id} not found in database.")
            return False
        
        # Remove service directory
        service_dir = Path(data["services"][service_id]["working_dir"])
        if service_dir.exists():
            shutil.rmtree(service_dir)
        
        # Remove from database
        del data["services"][service_id]
        self.save_data(data)
        return True

    def delete_service_by_name(self, service_name: str) -> bool:
        """Delete service by name"""
        data = self.load_data()
        service_id = None
        for srv_id, srv_data in data["services"].items():
            if srv_data.get("name") == service_name:
                service_id = srv_id
                break
        
        if not service_id:
            print(f"Service with name {service_name} not found.")
            return False
        
        return self.delete_service(service_id)
    # Run CRUD operations
    def create_run(self, service_id: str, run_config: Dict[str, Any]) -> str:
        """Create a new test run entry"""
        data = self.load_data()
        
        run_id = str(uuid.uuid4())
        run_data = {
            "id": run_id,
            "service_id": service_id,
            "config": run_config,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0
            },
            "artifacts": []
        }
        
        data["runs"][run_id] = run_data
        self.save_data(data)
        
        return run_id
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run by ID"""
        data = self.load_data()
        return data["runs"].get(run_id)
    
    def get_service_runs(self, service_id: str) -> List[Dict[str, Any]]:
        """Get all runs for a service"""
        data = self.load_data()
        return [run for run in data["runs"].values() if run["service_id"] == service_id]
    
    def update_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        """Update run data"""
        data = self.load_data()
        if run_id not in data["runs"]:
            return False
        
        data["runs"][run_id].update(updates)
        self.save_data(data)
        return True
    
    def update_run_status(self, run_id: str, status: str, results: Dict[str, Any] = None):
        """Update run status and results"""
        updates = {"status": status}
        
        if status == "running":
            updates["started_at"] = datetime.now().isoformat()
        elif status in ["completed", "failed"]:
            updates["completed_at"] = datetime.now().isoformat()
            if results:
                updates["results"] = results
        
        self.update_run(run_id, updates)
