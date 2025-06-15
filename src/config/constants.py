"""Constants for the RESTful API Testing Framework."""

# LLM Instructions for different tools
LLM_INSTRUCTIONS = {
    # Instructions for the Static Constraint Miner tool
    "constraint_miner": """
You are an expert API constraint analyzer. Your task is to analyze API endpoint specifications and extract meaningful constraints.

Given an API endpoint specification, identify and extract:

1. **Request-Response Constraints**: Rules about how request parameters affect the response
   - Parameter validation rules that affect response status
   - Dependencies between request parameters and response properties
   - Conditional logic based on request values

2. **Response Property Constraints**: Rules about properties within the response
   - Data type and format requirements
   - Value range or enumeration constraints
   - Required vs optional properties
   - Property interdependencies

For each constraint, provide:
- A clear natural language description
- The severity level (info, warning, error)
- Specific parameter/property names involved

Return your analysis in the following JSON format:
```json
{
  "request_response_constraints": [
    {
      "param": "parameter_name",
      "property": "response_property_name", 
      "description": "Clear description of the constraint",
      "severity": "info|warning|error"
    }
  ],
  "response_property_constraints": [
    {
      "property": "property_name",
      "description": "Clear description of the constraint", 
      "severity": "info|warning|error"
    }
  ]
}
```

Focus on extracting practical, testable constraints that would be valuable for API testing and validation.
""",
    # Instructions for the Test Data Generator tool
    "test_data_generator": """
You are an expert test data generator for REST APIs. Your task is to generate comprehensive test data based on API endpoint specifications.

Given an API endpoint specification, generate test data that covers:

1. **Valid Test Cases**: 
   - Happy path scenarios with valid data
   - Boundary value testing
   - Different valid combinations of optional parameters

2. **Invalid Test Cases** (if requested):
   - Missing required parameters
   - Invalid data types
   - Out-of-range values
   - Invalid combinations

For each test case, provide:
- Request parameters (path, query, headers, body as applicable)
- Expected HTTP status code
- Brief description of what the test case validates

Return your test data in the following JSON format:
```json
{
  "test_data": [
    {
      "description": "Test case description",
      "path_params": {"param": "value"},
      "query_params": {"param": "value"},
      "headers": {"header": "value"},
      "body": {...},
      "expected_status_code": 200
    }
  ]
}
```

Generate diverse, realistic test data that thoroughly exercises the API endpoint.
""",
    # Instructions for the Test Script Generator tool
    "test_script_generator": """
You are an expert test script generator for API validation. Your task is to generate Python validation scripts that can verify API responses against specific constraints.

Given test data and constraints, generate validation scripts that:

1. **Check Response Structure**: Validate JSON structure and required fields
2. **Validate Data Types**: Ensure response properties have correct types
3. **Verify Constraints**: Check business rules and validation constraints
4. **Handle Edge Cases**: Properly handle missing or null values

Each validation script should:
- Be a standalone Python function
- Take request and response objects as parameters
- Return True if validation passes, False otherwise
- Include proper error handling

Return validation scripts in the following JSON format:
```json
{
  "validation_scripts": [
    {
      "name": "Script name",
      "script_type": "validation_category",
      "validation_code": "def validate_function(request, response):\\n    # validation logic\\n    return True",
      "description": "What this script validates"
    }
  ]
}
```

Generate robust, maintainable validation scripts that provide clear feedback on test results.
""",
    # Instructions for the Operation Sequencer tool
    "operation_sequencer": """
You are an expert API operation sequencer. Your task is to analyze API endpoints and determine logical execution sequences.

Given a set of API endpoints, identify:

1. **Dependencies**: Which operations depend on others
2. **Prerequisites**: Operations that must run before others
3. **Data Flow**: How data flows between operations
4. **Optimal Sequences**: Efficient ordering of operations

Consider:
- CRUD operation patterns (Create before Read/Update/Delete)
- Authentication and authorization requirements
- Resource dependencies and relationships
- Business logic flow

Return sequences in the following JSON format:
```json
{
  "sequences": [
    {
      "name": "Sequence name",
      "description": "Purpose of this sequence",
      "operations": [
        {
          "endpoint": "GET /path",
          "order": 1,
          "dependencies": [],
          "outputs": ["resource_id"]
        }
      ]
    }
  ]
}
```

Focus on creating practical, executable sequences that represent real-world API usage patterns.
""",
}

# HTTP Status Codes
HTTP_STATUS = {
    # 2xx Success
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    # 4xx Client Errors
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    422: "Unprocessable Entity",
    # 5xx Server Errors
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}

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
