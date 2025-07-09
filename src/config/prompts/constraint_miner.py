# config/prompts/constraint_miner.py

"""Prompt templates for constraint mining operations."""

REQUEST_PARAM_CONSTRAINT_PROMPT = """
You are an expert API security and validation analyst. Your task is to analyze OpenAPI endpoint information and identify constraints related to request parameters.

Given the endpoint information below, identify and extract constraints that apply to request parameters (query, path, header parameters).

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces to avoid template conflicts.

Focus on:
1. Required vs optional parameters
2. Data type validation constraints
3. Format constraints (email, date, UUID, etc.)
4. Value range constraints (min/max values)
5. Enumeration constraints (allowed values)
6. Pattern constraints (regex validation)
7. Length constraints for strings
8. Security-related parameter constraints

For each constraint found, provide:
- parameter_name: The exact name of the parameter
- parameter_type: The location (query, path, header)
- description: Clear description of the constraint
- constraint_type: Type of constraint (required, format, range, enum, pattern, etc.)
- severity: "error" for validation failures, "warning" for recommendations, "info" for best practices
- validation_rule: Identifier for the validation rule
- details: Additional constraint-specific information

Return your analysis in the specified JSON format with a "constraints" array.

Endpoint Information:
{endpoint_data}

Your task is to identify constraints on request parameters such as:
- Required parameters
- Data type validation (string, integer, boolean, etc.)
- Format constraints (email, URL, date, etc.)
- Value range constraints (min/max values)
- Enum constraints (allowed values)
- Pattern constraints (regex patterns)

Return your analysis as a JSON object with this structure:
{{
  "constraints": [
    {{
      "parameter_name": "string",
      "parameter_type": "query|path|header",
      "description": "Human readable constraint description",
      "constraint_type": "required|type|format|range|enum|pattern",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "allowed_values": ["value1", "value2"] (optional),
      "min_value": 0 (optional),
      "max_value": 100 (optional),
      "pattern": "regex_pattern" (optional),
      "expected_type": "string|integer|boolean|number" (optional)
    }}
  ]
}}

Focus on practical, testable constraints that would be important for API validation.
"""

REQUEST_BODY_CONSTRAINT_PROMPT = """
You are an expert API security and validation analyst. Your task is to analyze OpenAPI endpoint information and identify constraints related to request body content.

Given the endpoint information below, identify and extract constraints that apply to request body fields and structure.

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces to avoid template conflicts.

Focus on:
1. Required vs optional fields in request body
2. Data type validation for body fields
3. Format constraints (email, date, nested objects, etc.)
4. Value constraints (min/max, length limits)
5. Schema validation constraints
6. Content-Type requirements
7. Structure validation constraints
8. Security-related body constraints

For each constraint found, provide:
- field_path: Path to the field in request body (e.g., "user.email", "items[].name")
- description: Clear description of the constraint
- constraint_type: Type of constraint (required, format, structure, etc.)
- severity: "error" for validation failures, "warning" for recommendations, "info" for best practices
- validation_rule: Identifier for the validation rule
- details: Additional constraint-specific information

Return your analysis in the specified JSON format with a "constraints" array.

Endpoint Information:
{endpoint_data}
"""

RESPONSE_PROPERTY_CONSTRAINT_PROMPT = """
You are an expert RESTful API testing specialist with over 20 years of experience at Big Tech companies. Your task is to analyze the provided OpenAPI spec for an endpoint (endpoint_data) and extract only the critical response‐body constraints needed for test case generation.

Important:
- Use **only** information present in endpoint_data. Do **not** invent any details.
- **Skip** basic type checks (string, integer, boolean) that the server already enforces.
- **Ignore** headers and HTTP status code validations.

Focus exclusively on payload constraints that impact testing:
1. **Required fields** and their presence in the response body  
2. **Object/array structure** (nested schemas, required items, polymorphism via oneOf/anyOf)  
3. **Format constraints** (date formats, regex patterns, enum values)  
4. **Numeric and string limits** (minimum, maximum, minLength, maxLength)  
5. **Cross‐field consistency** or conditional requirements  
6. **Example‐driven constraints** if defined in the spec

For each constraint found, provide a JSON entry with:
- **property_path**: JSON pointer to the field (e.g., data.items[0].id)  
- **description**: Clear human‐readable description of the constraint  
- **constraint_type**: one of `required`, `structure`, `format`, `limit`, `consistency`  
- **severity**: `error`|`warning`|`info`  
- **validation_rule**: Spec keyword (e.g., `required`, `pattern`, `enum`, `minLength`)  
- **details**: Additional parameters (e.g., allowed enum values, numeric bounds, regex)

Return your analysis as a JSON object in this exact template:
{{
  "constraints": [
    {{
      "property_path": "path.to.property",
      "description": "Human‐readable constraint description",
      "constraint_type": "required|structure|format|limit|consistency",
      "applies_to_status": [200, 201, 400, ...],
      "severity": "error|warning|info", 
      "validation_rule": "rule_identifier",
      "details": {{}}
    }}
  ]
}}

Endpoint Information:
{endpoint_data}
"""


REQUEST_RESPONSE_CONSTRAINT_PROMPT = """
You are an expert API design analyst specializing in request-response correlations. Your task is to analyze OpenAPI endpoint information and identify constraints that define relationships between request inputs and response outputs.

Given the endpoint information below, identify and extract constraints that show how request parameters/body influence the response.

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces to avoid template conflicts.

Focus on:
1. Request parameter values affecting response content
2. Request headers influencing response format/content
3. Query parameters controlling response filtering/pagination
4. Request body affecting response status codes
5. Authentication/authorization affecting response access
6. Request validation errors and corresponding error responses
7. Conditional response behavior based on request input
8. State-changing operations and their response patterns

For each constraint found, provide:
- request_element: Name of the request parameter/field that influences response
- request_location: Where the request element is located (query, path, body, header)
- response_element: What part of the response is affected (property, status, header)
- description: Clear description of the correlation constraint
- constraint_type: Type of correlation (filtering, validation, state_change, etc.)
- severity: "error" for critical correlations, "warning" for important patterns, "info" for informational
- validation_rule: Identifier for the correlation rule
- details: Additional correlation-specific information

Return your analysis in the specified JSON format with a "constraints" array.

Endpoint Information:
{endpoint_data}

Your task is to identify correlations between request parameters/body and response properties such as:
- Filter parameters affecting response content
- Pagination parameters affecting response structure
- Sort parameters affecting response order
- Request parameters reflected in response
- Conditional response behavior based on request

Return your analysis as a JSON object with this structure:
{{
  "constraints": [
    {{
      "request_element": "parameter_or_field_name",
      "request_location": "query|path|body|header",
      "response_element": "response_property_or_status",
      "description": "Human readable constraint description",
      "constraint_type": "filter|pagination|sort|reflection|conditional",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "condition": "when this constraint applies" (optional)
    }}
  ]
}}

Focus on practical, testable correlations that would be important for API validation.
"""
