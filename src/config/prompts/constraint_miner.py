# config/prompts/constraint_miner.py

"""Prompt templates for constraint mining operations."""

from config.constraint_mining_config import LLMPromptConfig


REQUEST_PARAM_CONSTRAINT_PROMPT = f"""
You are an expert API security and validation analyst with over 20 years of experience at Big Tech companies. Your task is to analyze OpenAPI endpoint information and identify **HIDDEN LOGICAL CONSTRAINTS** related to request parameters.

{LLMPromptConfig.CRITICAL_INSTRUCTION_PREFIX}

CRITICAL: Focus ONLY on complex, hidden, logical constraints that impact behavior. 
SKIP ALL trivial constraints already enforced by frameworks:
- Basic type checks (string, number, boolean)
- Format validations (email, date, uuid)
- Required field checks
- Enum value lists without business logic
- Array/object structure assertions

Important:
- Use **only** information present in endpoint_data. Do **not** invent any details.
- Extract constraints **solely** from the provided OpenAPI specification data.
- **Strictly skip** trivial constraints already enforced by frameworks/spec: type/format/required/enum/shape.
- Prefer complex, hidden, or conditional constraints that impact behavior.

Given the endpoint information below, identify and extract constraints that apply to request parameters (query, path, header parameters).

{LLMPromptConfig.PATH_PARAMETER_NOTE}

PRIORITIZE these constraint types:
1. **Cross-parameter dependencies**: "If parameter A is provided, then parameter B is required"
2. **Conditional logic**: "When X=true, parameter Y must be in range [1-100]"
3. **Business rules**: "Sort parameter affects pagination behavior"
4. **Security constraints**: "Admin users can override certain parameter limits"
5. **Temporal/ordering rules**: "Created_at must be before updated_at"
6. **Correlation constraints**: "Filter parameters affect response structure"

For each constraint found, provide:
- parameter_name: The exact name of the parameter
- parameter_type: The location (query, path, header)
- description: Clear description of the constraint
- constraint_type: Type of constraint (required, format, range, enum, pattern, etc.)
- severity: "error" for validation failures, "warning" for recommendations, "info" for best practices
- validation_rule: Identifier for the validation rule
- details: Additional constraint-specific information

Return your analysis as a JSON object with this structure:
{{{{
  "constraints": [
    {{{{
      "parameter_name": "string",
      "parameter_type": "query|path|header",
      "description": "Human readable constraint description",
      "constraint_type": "conditional|dependency|business_rule|correlation",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "allowed_values": ["value1", "value2"] (optional),
      "min_value": 0 (optional),
      "max_value": 100 (optional),
      "pattern": "regex_pattern" (optional),
      "rationale": "Business reason for this constraint",
      "confidence": 0.8,
      "condition": "when this applies" (optional),
      "dependencies": ["other_param"] (optional)
    }}}}
  ]
}}}}

Focus on practical, testable constraints that would be important for API validation.

Endpoint Information:
{{endpoint_data}}
"""

REQUEST_BODY_CONSTRAINT_PROMPT = f"""
You are an expert API security and validation analyst with over 20 years of experience at Big Tech companies. Your task is to analyze OpenAPI endpoint information and identify **HIDDEN LOGICAL CONSTRAINTS** related to request body content.

{LLMPromptConfig.CRITICAL_INSTRUCTION_PREFIX}

CRITICAL: Focus ONLY on complex, hidden, logical constraints that impact behavior. 
SKIP ALL trivial constraints already enforced by frameworks:
- Basic type checks (string, number, boolean)
- Format validations (email, date, uuid)
- Required field checks
- Enum value lists without business logic
- Array/object structure assertions

Important:
- Use **only** information present in endpoint_data. Do **not** invent any details.
- Extract constraints **solely** from the provided OpenAPI specification data.
- **Strictly skip** trivial constraints already enforced by frameworks/spec: type/format/required/enum/shape.
- Prefer complex, hidden, or conditional constraints that impact behavior.

Given the endpoint information below, identify and extract constraints that apply to request body fields and structure.

{LLMPromptConfig.PATH_PARAMETER_NOTE}

PRIORITIZE these constraint types:
1. **Cross-field dependencies**: "If field A is provided, then field B is required"
2. **Conditional business rules**: "When status=active, certain fields become mandatory"
3. **Data consistency rules**: "Start date must be before end date"
4. **Security constraints**: "Admin users can modify certain protected fields"
5. **State-dependent validation**: "Fields behave differently based on user role"
6. **Complex business logic**: "Pricing rules based on multiple field combinations"

For each constraint found, provide:
- field_path: Path to the field in request body (e.g., "user.email", "items[].name")
- description: Clear description of the constraint
- constraint_type: Type of constraint (required, format, structure, etc.)
- severity: "error" for validation failures, "warning" for recommendations, "info" for best practices
- validation_rule: Identifier for the validation rule
- details: Additional constraint-specific information

Return your analysis as a JSON object with this structure:
{{{{
  "constraints": [
    {{{{
      "field_path": "path.to.field",
      "description": "Human readable constraint description",
      "constraint_type": "conditional|dependency|business_rule|consistency",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "required": true|false (optional),
      "data_type": "string|integer|boolean|number|object|array" (optional),
      "format": "email|date|uuid|etc" (optional),
      "min_length": 0 (optional),
      "rationale": "Business reason for this constraint",
      "confidence": 0.8,
      "condition": "when this applies" (optional),
      "dependencies": ["other_field"] (optional)
    }}}}
  ]
}}}}

Focus on practical, testable constraints that would be important for API validation.

Endpoint Information:
{{endpoint_data}}
"""

RESPONSE_PROPERTY_CONSTRAINT_PROMPT = f"""
You are an expert RESTful API testing specialist with over 20 years of experience at Big Tech companies. Your task is to analyze the provided OpenAPI spec for an endpoint (endpoint_data) and extract only **HIDDEN LOGICAL CONSTRAINTS** needed for test case generation.

{LLMPromptConfig.CRITICAL_INSTRUCTION_PREFIX}

CRITICAL: Focus ONLY on complex, hidden, logical constraints that impact behavior. 
SKIP ALL trivial constraints already enforced by frameworks:
- Basic type checks (string, number, boolean)
- Format validations (email, date, uuid)
- Required field checks
- Enum value lists without business logic
- Array/object structure assertions

Important:
- Use **only** information present in endpoint_data. Do **not** invent any details.
- Extract constraints **solely** from the provided OpenAPI specification data.
- **Strictly skip** trivial constraints already enforced by frameworks/spec: type/format/required/enum/shape.
  Prefer complex, hidden, or conditional constraints that impact behavior.

PRIORITIZE these constraint types:
1. **Cross-field consistency**: "If field A is present, field B must have a specific value"
2. **Conditional response structure**: "Response structure changes based on request parameters"
3. **Business logic constraints**: "Status field determines which other fields are present"
4. **Data integrity rules**: "Related fields must maintain consistency"
5. **Security-driven constraints**: "Certain fields only appear for authorized users"
6. **State-dependent responses**: "Response varies based on resource state"

For each constraint found, provide a JSON entry with:
- **property_path**: JSON pointer to the field (e.g., data.items[0].id)  
- **description**: Clear human‐readable description of the constraint  
- **constraint_type**: one of `required`, `structure`, `format`, `limit`, `consistency`  
- **severity**: `error`|`warning`|`info`  
- **validation_rule**: Spec keyword (e.g., `required`, `pattern`, `enum`, `minLength`)  
- **details**: Additional parameters (e.g., allowed enum values, numeric bounds, regex)

Return your analysis as a JSON object in this exact template:
{{{{
  "constraints": [
    {{{{
      "property_path": "path.to.property",
      "description": "Human‐readable constraint description",
      "constraint_type": "conditional|dependency|business_rule|consistency",
      "applies_to_status": [200, 201, 400, ...],
      "severity": "error|warning|info", 
      "validation_rule": "rule_identifier",
      "rationale": "Business reason for this constraint",
      "confidence": 0.8,
      "condition": "when this applies" (optional),
      "dependencies": ["other_field"] (optional),
      "details": {{}}
    }}}}
  ]
}}}}

Endpoint Information:
{{endpoint_data}}
"""


REQUEST_RESPONSE_CONSTRAINT_PROMPT = f"""
You are an expert API design analyst with over 20 years of experience at Big Tech companies specializing in request-response correlations. Your task is to analyze OpenAPI endpoint information and identify **HIDDEN LOGICAL CONSTRAINTS** that define relationships between request inputs and response outputs.

{LLMPromptConfig.CRITICAL_INSTRUCTION_PREFIX}

CRITICAL: Focus ONLY on complex, hidden, logical constraints that impact behavior. 
SKIP ALL trivial constraints already enforced by frameworks:
- Basic type checks (string, number, boolean)
- Format validations (email, date, uuid)
- Required field checks
- Enum value lists without business logic
- Array/object structure assertions

Important:
- Use **only** information present in endpoint_data. Do **not** invent any details.
- Extract constraints **solely** from the provided OpenAPI specification data.
- **Skip** basic type checks that are already enforced by the API framework.

Given the endpoint information below, identify and extract constraints that show how request parameters/body influence the response.

{LLMPromptConfig.PATH_PARAMETER_NOTE}

PRIORITIZE these constraint types:
1. **Request-response correlations**: "Filter parameters affect response content structure"
2. **Conditional response behavior**: "Response format changes based on request parameters"
3. **Business logic constraints**: "Certain request combinations trigger specific response patterns"
4. **Security-driven responses**: "Authentication level affects response data visibility"
5. **State-dependent behavior**: "Response varies based on resource state and request context"
6. **Cross-parameter dependencies**: "Multiple request parameters must work together"
7. **Temporal constraints**: "Request timing affects response behavior"
8. **Data consistency rules**: "Request data must maintain consistency with response data"

For each constraint found, provide:
- request_element: Name of the request parameter/field that influences response
- request_location: Where the request element is located (query, path, body, header)
- response_element: What part of the response is affected (property, status, header)
- description: Clear description of the correlation constraint
- constraint_type: Type of correlation (correlation, conditional, dependency, business_rule)
- severity: "error" for critical correlations, "warning" for important patterns, "info" for informational
- validation_rule: Identifier for the correlation rule
- rationale: Business reason for this constraint
- confidence: 0.0-1.0 confidence in this constraint
- condition: When this constraint applies (optional)
- dependencies: Other parameters this depends on (optional)
- details: Additional correlation-specific information

Return your analysis as a JSON object with this structure:
{{{{
  "constraints": [
    {{{{
      "request_element": "parameter_or_field_name",
      "request_location": "query|path|body|header",
      "response_element": "response_property_or_status",
      "description": "Human readable constraint description",
      "constraint_type": "filter|pagination|sort|reflection|conditional",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "condition": "when this constraint applies" (optional)
    }}}}
  ]
}}}}

Focus on practical, testable correlations that would be important for API validation.

Endpoint Information:
{{endpoint_data}}

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
      "constraint_type": "correlation|conditional|dependency|business_rule",
      "severity": "error|warning|info",
      "validation_rule": "rule_identifier",
      "rationale": "Business reason for this constraint",
      "confidence": 0.8,
      "condition": "when this constraint applies" (optional),
      "dependencies": ["other_param"] (optional)
    }}
  ]
}}

Focus on practical, testable correlations that would be important for API validation.
"""
