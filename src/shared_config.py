"""
Shared configuration for KAT, SequenceRunner and Server
Unified directory structure for all components
"""

import os
from pathlib import Path
import json

# Unified database directory structure
DATABASE_BASE_DIR = Path(__file__).parent.parent / "database"

def get_database_base_dir() -> Path:
    """Get the base database directory"""
    DATABASE_BASE_DIR.mkdir(exist_ok=True)
    return DATABASE_BASE_DIR

def get_service_base_dir(service_name: str) -> Path:
    """Get base directory for a service"""
    service_dir = get_database_base_dir() / service_name
    service_dir.mkdir(exist_ok=True)
    return service_dir
def ensure_service_structure(service_name: str) -> Path:
    """Ensure complete service directory structure exists"""
    service_dir = get_service_base_dir(service_name)
    
    # Create all required subdirectories
    subdirs = [
        "specs",           # OpenAPI specifications
        "test_cases",      # Generated test cases JSON files
        "test_data",       # Test data CSV files  
        "results",         # Test execution results
        "logs",            # Execution logs
        "ODG",             # Operation Dependency Graph files
    ]
    
    for subdir in subdirs:
        (service_dir / subdir).mkdir(exist_ok=True)
    
    return service_dir

# KAT Integration Functions
def get_spec_file(service_name: str) -> str:
    """Get OpenAPI spec file path"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "specs" / "openapi.json")
def get_output_dir(service_name: str, phase: str) -> str:
    """Get output directory for a specific phase"""
    service_dir = ensure_service_structure(service_name)
    phase_dir = service_dir / phase
    phase_dir.mkdir(exist_ok=True)
    return str(phase_dir) + "/"

def get_odg_working_dir(service_name: str) -> str:
    """Get ODG working directory"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "ODG") + "/"

def get_test_case_generator_working_dir(service_name: str) -> str:
    """Get test case generator working directory"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "test_cases") + "/"

def get_operation_sequences_file_path(service_name: str) -> str:
    """Get operation sequences file path"""
    return get_odg_working_dir(service_name) + "operation_sequences.json"

def get_endpoint_schema_dependencies_file_path(service_name: str) -> str:
    """Get endpoint schema dependencies file path"""
    return get_odg_working_dir(service_name) + "endpoint_schema_dependencies.json"
def get_endpoints_belong_to_schemas_file_path(service_name: str) -> str:
    """Get endpoints belong to schemas file path"""
    return get_odg_working_dir(service_name) + "endpoints_belong_to_schemas.json"
def get_topolist_file_path(service_name: str) -> str:
    """Get topolist file path"""
    return get_odg_working_dir(service_name) + "topolist.json"

def get_test_data_working_dir(service_name: str) -> str:
    """Get test data working directory"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "test_data") + "/"

def get_results_dir(service_name: str) -> str:
    """Get results directory"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "results") + "/"

def get_logs_dir(service_name: str) -> str:
    """Get logs directory"""
    service_dir = ensure_service_structure(service_name)
    return str(service_dir / "logs") + "/"

def get_root_dir() -> str:
    """Get root database directory"""
    return str(get_database_base_dir()) + "/"
def get_cache_dir(service_name: str) -> str:
    """Get cache directory for a service"""
    service_dir = ensure_service_structure(service_name)
    cache_dir = service_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    return str(cache_dir) + "/"
# Service Registry Functions
def register_service(service_name: str, spec_content: str, metadata: dict = None) -> str:
    """Register a service with spec content"""
    service_dir = ensure_service_structure(service_name)
    
    # Save spec file
    spec_file = service_dir / "specs" / "openapi.json"
    with open(spec_file, 'w', encoding='utf-8') as f:
        if isinstance(spec_content, str):
            f.write(spec_content)
        else:
            json.dump(spec_content, f, indent=2)
    
    # Save metadata
    if metadata:
        metadata_file = service_dir / "service_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    return str(service_dir)

def list_services() -> list:
    """List all registered services"""
    db_dir = get_database_base_dir()
    services = []
    
    for item in db_dir.iterdir():
        if item.is_dir():
            spec_file = item / "specs" / "openapi.json"
            if spec_file.exists():
                services.append({
                    "name": item.name,
                    "path": str(item),
                    "spec_file": str(spec_file)
                })
    
    return services

def service_exists(service_name: str) -> bool:
    """Check if service exists"""
    service_dir = get_service_base_dir(service_name)
    spec_file = service_dir / "specs" / "openapi.json"
    return spec_file.exists()

# Legacy compatibility - for KAT components that expect WORKING_DIRECTORY
WORKING_DIRECTORY = str(get_database_base_dir())

# Export functions that KAT expects
__all__ = [
    'get_spec_file',
    'get_output_dir', 
    'get_odg_working_dir',
    'get_test_case_generator_working_dir',
    'get_operation_sequences_file_path',
    'get_endpoint_schema_dependencies_file_path',
    'get_topolist_file_path',
    'get_test_data_working_dir',
    'get_results_dir',
    'get_logs_dir',
    'get_root_dir',
    'register_service',
    'list_services',
    'service_exists',
    'ensure_service_structure',
    'WORKING_DIRECTORY',
    'get_endpoints_belong_to_schemas_file_path',
]