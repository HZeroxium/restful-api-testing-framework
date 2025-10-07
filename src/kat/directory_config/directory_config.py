"""
KAT Directory Configuration - now uses shared_config for unified database structure
"""

import sys
import os
from pathlib import Path

# Add src to path for shared_config import
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

try:
    from shared_config import (
        get_data_dir_file,
        get_output_dir,
        get_odg_working_dir,
        get_test_case_generator_working_dir,
        get_operation_sequences_file_path,
        get_endpoint_schema_dependencies_file_path,
        get_topolist_file_path,
        get_test_data_working_dir,
        get_results_dir,
        get_logs_dir,
        get_root_dir,
        WORKING_DIRECTORY
    )
except ImportError as e:
    print(f"Warning: Could not import shared_config: {e}")
    print("Falling back to legacy directory structure")
    
    # Fallback to legacy structure if shared_config not available
    WORKING_DIRECTORY = "./KAT_CLONE_TEST_CASES"

    def get_output_dir(service_name, phase):
        return f"{WORKING_DIRECTORY}/{service_name}/{phase}/"

    def get_data_dir_file(service_name):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        return os.path.join(project_root, "Dataset", service_name, "openapi.json")

    def get_odg_working_dir(service_name):
        return f"{WORKING_DIRECTORY}/{service_name}/ODG/"
        
    def get_test_case_generator_working_dir(service_name):
        return f"{WORKING_DIRECTORY}/{service_name}/test_case_generator/"
        
    def get_operation_sequences_file_path(service_name):
        return f"{get_odg_working_dir(service_name)}operation_sequences.json"
        
    def get_endpoint_schema_dependencies_file_path(service_name):
        return f"{get_odg_working_dir(service_name)}endpoint_schema_dependencies.json"
        
    def get_topolist_file_path(service_name):
        return f"{get_odg_working_dir(service_name)}topolist.json"
        
    def get_test_data_working_dir(service_name):
        return f"{WORKING_DIRECTORY}/{service_name}/TestData/"
        
    def get_root_dir():
        return f"{WORKING_DIRECTORY}/"

# Export the functions for backward compatibility
__all__ = [
    'get_data_dir_file',
    'get_output_dir',
    'get_odg_working_dir', 
    'get_test_case_generator_working_dir',
    'get_operation_sequences_file_path',
    'get_endpoint_schema_dependencies_file_path',
    'get_topolist_file_path',
    'get_test_data_working_dir',
    'get_root_dir',
    'WORKING_DIRECTORY'
]