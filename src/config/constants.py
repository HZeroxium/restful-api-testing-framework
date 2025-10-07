# src/config/constants.py

"""Constants for the RESTful API Testing Framework."""

# Default timeout values (in seconds)
DEFAULT_API_TIMEOUT = 10.0
DEFAULT_LLM_TIMEOUT = 60.0
DEFAULT_CODE_EXECUTION_TIMEOUT = 5.0

# Default retry configuration
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY = 1.0

# File extensions
OPENAPI_FILE_EXTENSIONS = [".json", ".yaml", ".yml"]

# HTTP Status Code Categories
SUCCESS_STATUS_CODES = range(200, 300)
CLIENT_ERROR_STATUS_CODES = range(400, 500)
SERVER_ERROR_STATUS_CODES = range(500, 600)

# Test Data Generation Limits
MAX_TEST_CASES_PER_ENDPOINT = 10
MIN_TEST_CASES_PER_ENDPOINT = 1

# Error Messages
ERROR_MESSAGES = {
    "file_not_found": "The specified file was not found: {file_path}",
    "invalid_file_format": "Invalid file format. Expected: {expected}, Got: {actual}",
    "parsing_error": "Error parsing OpenAPI specification: {error}",
    "llm_timeout": "LLM request timed out after {timeout} seconds",
    "llm_error": "Error during LLM processing: {error}",
    "no_endpoints": "No endpoints found in the OpenAPI specification",
    "invalid_selection": "Invalid endpoint selection: {selection}",
}

# Success Messages
SUCCESS_MESSAGES = {
    "parsing_complete": "OpenAPI specification parsed successfully",
    "constraints_generated": "Constraints generated successfully",
    "test_data_generated": "Test data generated successfully",
    "validation_complete": "Validation completed successfully",
}

# Tool Names
TOOL_NAMES = {
    "openapi_parser": "OpenAPI Parser",
    "constraint_miner": "Static Constraint Miner",
    "test_data_generator": "Test Data Generator",
    "test_script_generator": "Test Script Generator",
    "operation_sequencer": "Operation Sequencer",
}

# Default File Paths
DEFAULT_PATHS = {
    "openapi_spec": "data/toolshop/openapi.json",
    "output_base": "output",
    "config_dir": "config",
}

