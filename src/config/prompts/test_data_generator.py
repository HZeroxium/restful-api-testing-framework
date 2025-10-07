# config/prompts/test_data_generator.py

"""
Prompt templates for Test Data Generation.
"""

TEST_DATA_GENERATION_PROMPT = """
You are an expert API testing engineer. Generate comprehensive test data for the following API endpoint.

**API ENDPOINT INFORMATION:**
- Method: {method}
- Path: {path}
- Description: {description}

**REQUEST PARAMETERS:**
{request_params}

**REQUEST BODY SCHEMA:**
{request_body_schema}

**RESPONSE SCHEMA:**
{response_schema}

**INSTRUCTIONS:**
1. Generate exactly {test_case_count} test cases
2. Include both valid and invalid test data as specified below
3. Each test case must have a unique name and clear description
4. Use realistic data values that would be used in production
5. For invalid test cases, create data that violates the API specification

**TEST DATA REQUIREMENTS:**
- Include valid test data: {include_valid_data}
- Include invalid test data: {include_invalid_data}
- Generate edge cases and boundary conditions
- Use realistic values for strings, numbers, dates, etc.
- Consider authentication requirements if present

**RESPONSE FORMAT:**
Return a JSON array with the following structure for each test case:
{{
  "id": "unique_test_id",
  "name": "descriptive_test_name",
  "description": "detailed_description_of_what_this_test_validates",
  "request_params": {{}}, // Query/path parameters
  "request_headers": {{}}, // HTTP headers
  "request_body": null, // Request body (null if not applicable)
  "expected_status_code": 200, // Expected HTTP status code
  "expected_response_schema": {{}}, // Expected response structure
  "expected_response_contains": [] // List of keys/values expected in response
}}

**IMPORTANT NOTES:**
- For invalid test cases, set expected_status_code to 400, 401, 403, 404, 422, or 500 as appropriate
- Ensure request_params includes all required parameters
- Use null for request_body if the endpoint doesn't accept a body
- Make expected_response_contains specific to help with validation
- Consider various invalid scenarios: missing required fields, invalid data types, out-of-range values, etc.

Generate the test data now:
"""

FALLBACK_TEST_DATA_PROMPT = """
Generate basic test data for API endpoint {method} {path}.

Create {test_case_count} test cases including:
- 1 valid test case with minimal required data
- 1 valid test case with comprehensive data (if applicable)
- Invalid test cases with various error conditions (if include_invalid_data is True)

Return as JSON array with structure:
[{{
  "id": "test_id",
  "name": "test_name", 
  "description": "test_description",
  "request_params": {{}},
  "request_headers": {{}},
  "request_body": null,
  "expected_status_code": 200,
  "expected_response_schema": {{}},
  "expected_response_contains": []
}}]
"""

MISMATCH_DATA_DETECTION_PROMPT = """
You are an expert API testing engineer. Analyze the following test data and identify potential mismatches between the generated test data and the OpenAPI specification.

**API ENDPOINT SPECIFICATION:**
- Method: {method}
- Path: {path}
- Parameters: {parameters}
- Request Body Schema: {request_body_schema}
- Response Schema: {response_schema}

**GENERATED TEST DATA:**
{test_data}

**INSTRUCTIONS:**
1. Compare each test case against the OpenAPI specification
2. Identify test cases that claim to be "valid" but violate the specification
3. Identify test cases that claim to be "invalid" but actually conform to the specification
4. Check for:
   - Missing required parameters
   - Invalid data types
   - Values outside allowed ranges
   - Invalid enum values
   - Schema violations
   - Authentication/authorization issues

**RESPONSE FORMAT:**
Return a JSON object with the following structure:
{{
  "mismatched_test_cases": [
    {{
      "test_id": "test_case_id",
      "issue_type": "claimed_valid_but_invalid" | "claimed_invalid_but_valid",
      "description": "detailed_description_of_the_mismatch",
      "specification_violation": "specific_violation_details",
      "recommended_action": "fix_test_data" | "update_expected_status" | "remove_test_case"
    }}
  ],
  "validation_summary": {{
    "total_test_cases": number,
    "valid_test_cases": number,
    "invalid_test_cases": number,
    "mismatched_test_cases": number
  }}
}}

Analyze the test data now:
"""
