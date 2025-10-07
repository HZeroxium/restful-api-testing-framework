# File: config/prompts/test_script_generator.py

"""Prompt templates for test script generation operations."""

REQUEST_PARAM_SCRIPT_PROMPT = """
You are an expert Python test script generator specializing in API request parameter validation. Your task is to generate Python validation scripts that can verify API request parameters against specific constraints.

**IMPORTANT**: You MUST generate exactly ONE validation script for EACH constraint provided. Do not combine multiple constraints into a single script.

Given the endpoint information and request parameter constraints below, generate validation scripts that:

1. **Parameter Presence Validation**: Check if required parameters are present
2. **Data Type Validation**: Ensure parameters have correct data types
3. **Format Validation**: Validate parameter formats (email, UUID, date, etc.)
4. **Range Validation**: Check min/max values for numeric parameters
5. **Enum Validation**: Verify parameters match allowed values
6. **Pattern Validation**: Validate against regex patterns

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces.

Each validation script should:
- Be a standalone Python function taking (request, response) parameters
- Return True if validation passes, False otherwise
- Include proper error handling with try-catch blocks
- Have descriptive function names and docstrings
- Handle edge cases like missing or null values
- Be specific to ONE constraint only

**EXAMPLE MAPPING**:
If you have these constraints:
1. Constraint: "The parameter 'by_brand' must be a string"
2. Constraint: "The parameter 'page' must be an integer"

You MUST generate exactly 2 scripts:

{{{{
  "validation_scripts": [
    {{{{
      "name": "Validate by_brand parameter type",
      "script_type": "request_param",
      "validation_code": "def validate_by_brand_type(request, response):\\n    \\"\\"\\"Validate that by_brand parameter is a string\\"\\"\\"\\n    try:\\n        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})\\n        if 'by_brand' in params:\\n            return isinstance(params['by_brand'], str)\\n        return True  # Optional parameter\\n    except Exception as e:\\n        return False",
      "description": "Validates that by_brand parameter is a string type"
    }},
    {{{{
      "name": "Validate page parameter type",
      "script_type": "request_param",
      "validation_code": "def validate_page_type(request, response):\\n    \\"\\"\\"Validate that page parameter is an integer\\"\\"\\"\\n    try:\\n        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})\\n        if 'page' in params:\\n            return isinstance(params['page'], int)\\n        return True  # Optional parameter\\n    except Exception as e:\\n        return False",
      "description": "Validates that page parameter is an integer type"
    }}
  ]
}}}}

Endpoint Information:
{endpoint_data}

Request Parameter Constraints:
{constraints_data}

**MANDATORY REQUIREMENTS**:
1. Generate exactly {constraint_count} validation scripts (one per constraint)
2. Each script must validate ONE specific constraint
3. Use the constraint description and details to create targeted validation logic
4. Include the constraint ID reference in script comments
5. Scripts should work with any test data that follows the endpoint schema

Generate validation scripts in this JSON format:

{{{{
  "validation_scripts": [
    {{{{
      "name": "Descriptive script name specific to the constraint",
      "script_type": "request_param",
      "validation_code": "def validate_specific_constraint(request, response):\\n    \\"\\"\\"Validate specific parameter constraint - Reference: constraint_id\\"\\"\\"\\n    try:\\n        # constraint-specific validation logic\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Clear description of what specific constraint this script validates"
    }}
  ]
}}}}

REMEMBER: You must generate exactly {constraint_count} scripts, one for each constraint provided.
"""

REQUEST_BODY_SCRIPT_PROMPT = """
You are an expert Python test script generator specializing in API request body validation. Your task is to generate Python validation scripts that can verify API request bodies against specific constraints.

**IMPORTANT**: You MUST generate exactly ONE validation script for EACH constraint provided. Do not combine multiple constraints into a single script.

Given the endpoint information and request body constraints below, generate validation scripts that:

1. **Required Field Validation**: Check if required fields are present in request body
2. **Data Type Validation**: Ensure body fields have correct data types
3. **Format Validation**: Validate field formats (email, date, nested objects, etc.)
4. **Structure Validation**: Verify request body structure and schema compliance
5. **Content-Type Validation**: Check Content-Type headers for request body
6. **Field Dependencies**: Validate interdependencies between fields

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces.

Each validation script should:
- Be a standalone Python function taking (request, response) parameters
- Return True if validation passes, False otherwise
- Include proper error handling with try-catch blocks
- Have descriptive function names and docstrings
- Handle nested object validation and array validation
- Be specific to ONE constraint only

**EXAMPLE MAPPING**:
If you have these constraints:
1. Constraint: "The 'name' field must be a string"
2. Constraint: "The 'email' field must be a valid email format"

You MUST generate exactly 2 scripts:

{{{{
  "validation_scripts": [
    {{{{
      "name": "Validate name field type",
      "script_type": "request_body",
      "validation_code": "def validate_name_field_type(request, response):\\n    \\"\\"\\"Validate that name field is a string\\"\\"\\"\\n    try:\\n        body = getattr(request, 'json', {{}}) if hasattr(request, 'json') else request.get('json', {{}})\\n        if 'name' in body:\\n            return isinstance(body['name'], str)\\n        return True  # Optional field\\n    except Exception as e:\\n        return False",
      "description": "Validates that name field is a string type"
    }},
    {{{{
      "name": "Validate email field format",
      "script_type": "request_body",
      "validation_code": "def validate_email_field_format(request, response):\\n    \\"\\"\\"Validate that email field has valid email format\\"\\"\\"\\n    try:\\n        import re\\n        body = getattr(request, 'json', {{}}) if hasattr(request, 'json') else request.get('json', {{}})\\n        if 'email' in body:\\n            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{{2,}}$'\\n            return re.match(email_pattern, str(body['email'])) is not None\\n        return True  # Optional field\\n    except Exception as e:\\n        return False",
      "description": "Validates that email field has valid email format"
    }}
  ]
}}}}

Endpoint Information:
{endpoint_data}

Request Body Constraints:
{constraints_data}

**MANDATORY REQUIREMENTS**:
1. Generate exactly {constraint_count} validation scripts (one per constraint)
2. Each script must validate ONE specific constraint
3. Use the constraint description and details to create targeted validation logic
4. Include the constraint ID reference in script comments
5. Scripts should work with any test data that follows the endpoint schema

Generate validation scripts in this JSON format:

{{{{
  "validation_scripts": [
    {{{{
      "name": "Descriptive script name specific to the constraint",
      "script_type": "request_body",
      "validation_code": "def validate_specific_body_constraint(request, response):\\n    \\"\\"\\"Validate specific body field constraint - Reference: constraint_id\\"\\"\\"\\n    try:\\n        # constraint-specific validation logic\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Clear description of what specific constraint this script validates"
    }}
  ]
}}}}

REMEMBER: You must generate exactly {constraint_count} scripts, one for each constraint provided.
"""

RESPONSE_PROPERTY_SCRIPT_PROMPT = """
You are an expert Python test script generator specializing in API response property validation. Your task is to generate Python validation scripts that can verify API response properties against specific constraints.

**IMPORTANT**: You MUST generate exactly ONE validation script for EACH constraint provided. Do not combine multiple constraints into a single script.

Given the endpoint information and response property constraints below, generate validation scripts that:

1. **Response Structure Validation**: Check response JSON structure and required properties
2. **Data Type Validation**: Ensure response properties have correct data types
3. **Format Validation**: Validate property formats (dates, IDs, enums, etc.)
4. **Status Code Validation**: Verify response status codes match constraints
5. **Header Validation**: Check response headers (Content-Type, caching, etc.)
6. **Property Dependencies**: Validate interdependencies between response properties

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces.

Each validation script should:
- Be a standalone Python function taking (request, response) parameters
- Return True if validation passes, False otherwise
- Include proper error handling with try-catch blocks
- Have descriptive function names and docstrings
- Handle different response formats and status codes
- Be specific to ONE constraint only

**EXAMPLE MAPPING**:
If you have these constraints:
1. Constraint: "The 'current_page' property must be an integer"
2. Constraint: "The 'data' property must be an array"

You MUST generate exactly 2 scripts:

{{{{
  "validation_scripts": [
    {{{{
      "name": "Validate current_page property type",
      "script_type": "response_property",
      "validation_code": "def validate_current_page_type(request, response):\\n    \\"\\"\\"Validate that current_page property is an integer\\"\\"\\"\\n    try:\\n        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})\\n        if isinstance(body, dict) and 'current_page' in body:\\n            return isinstance(body['current_page'], int)\\n        return True  # Property may not exist in all responses\\n    except Exception as e:\\n        return False",
      "description": "Validates that current_page property is an integer type"
    }},
    {{{{
      "name": "Validate data property type",
      "script_type": "response_property",
      "validation_code": "def validate_data_property_type(request, response):\\n    \\"\\"\\"Validate that data property is an array\\"\\"\\"\\n    try:\\n        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})\\n        if isinstance(body, dict) and 'data' in body:\\n            return isinstance(body['data'], list)\\n        return True  # Property may not exist in all responses\\n    except Exception as e:\\n        return False",
      "description": "Validates that data property is an array type"
    }}
  ]
}}}}

Endpoint Information:
{endpoint_data}

Response Property Constraints:
{constraints_data}

**MANDATORY REQUIREMENTS**:
1. Generate exactly {constraint_count} validation scripts (one per constraint)
2. Each script must validate ONE specific constraint
3. Use the constraint description and details to create targeted validation logic
4. Include the constraint ID reference in script comments
5. Scripts should work with any test data that follows the endpoint schema

Generate validation scripts in this JSON format:
{{{{
  "validation_scripts": [
    {{{{
      "name": "Descriptive script name specific to the constraint",
      "script_type": "response_property",
      "validation_code": "def validate_specific_response_constraint(request, response):\\n    \\"\\"\\"Validate specific response property constraint - Reference: constraint_id\\"\\"\\"\\n    try:\\n        # constraint-specific validation logic\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Clear description of what specific constraint this script validates"
    }}
  ]
}}}}

REMEMBER: You must generate exactly {constraint_count} scripts, one for each constraint provided.
"""  # noqa: E501

REQUEST_RESPONSE_SCRIPT_PROMPT = """
You are an expert Python test script generator specializing in API request-response correlation validation. Your task is to generate Python validation scripts that can verify correlations between request inputs and response outputs.

**IMPORTANT**: You MUST generate exactly ONE validation script for EACH constraint provided. Do not combine multiple constraints into a single script.

Given the endpoint information and request-response correlation constraints below, generate validation scripts that:

1. **Parameter-Response Correlation**: Verify request parameters affect response content correctly
2. **Filter Validation**: Check that filter parameters properly filter response data
3. **Pagination Validation**: Validate pagination parameters affect response structure
4. **Sort Validation**: Verify sort parameters correctly order response data
5. **State Change Validation**: Check state-changing operations produce expected responses
6. **Conditional Response Validation**: Verify conditional response behavior based on request input

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces.

Each validation script should:
- Be a standalone Python function taking (request, response) parameters
- Return True if validation passes, False otherwise
- Include proper error handling with try-catch blocks
- Have descriptive function names and docstrings
- Compare request input with response output to verify correlations
- Be specific to ONE constraint only

**EXAMPLE MAPPING**:
If you have these constraints:
1. Constraint: "The 'by_brand' parameter filters returned products by brand ID"
2. Constraint: "The 'page' parameter determines which page of products is returned"

You MUST generate exactly 2 scripts:
{{{{
  "validation_scripts": [
    {{{{
      "name": "Validate by_brand filter correlation",
      "script_type": "request_response",
      "validation_code": "def validate_by_brand_filter(request, response):\\n    \\"\\"\\"Validate that by_brand parameter filters products correctly\\"\\"\\"\\n    try:\\n        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})\\n        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})\\n        \\n        if 'by_brand' in params and isinstance(body, dict) and 'data' in body:\\n            brand_id = params['by_brand']\\n            products = body['data']\\n            if isinstance(products, list):\\n                for product in products:\\n                    if isinstance(product, dict) and 'brand' in product:\\n                        if product['brand'].get('id') != brand_id:\\n                            return False\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Validates that by_brand parameter correctly filters products by brand ID"
    }},
    {{{{
      "name": "Validate page pagination correlation",
      "script_type": "request_response",
      "validation_code": "def validate_page_pagination(request, response):\\n    \\"\\"\\"Validate that page parameter affects pagination correctly\\"\\"\\"\\n    try:\\n        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})\\n        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})\\n        \\n        if 'page' in params and isinstance(body, dict) and 'current_page' in body:\\n            requested_page = int(params['page'])\\n            current_page = body['current_page']\\n            return requested_page == current_page\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Validates that page parameter correctly determines current page in response"
    }}
  ]
}}}}

Endpoint Information:
{endpoint_data}

Request-Response Correlation Constraints:
{constraints_data}

**MANDATORY REQUIREMENTS**:
1. Generate exactly {constraint_count} validation scripts (one per constraint)
2. Each script must validate ONE specific constraint
3. Use the constraint description and details to create targeted validation logic
4. Include the constraint ID reference in script comments
5. Scripts should work with any test data that follows the endpoint schema

Generate validation scripts in this JSON format:
{{{{
  "validation_scripts": [
    {{{{
      "name": "Descriptive script name specific to the constraint",
      "script_type": "request_response",
      "validation_code": "def validate_specific_correlation_constraint(request, response):\\n    \\"\\"\\"Validate specific request-response correlation - Reference: constraint_id\\"\\"\\"\\n    try:\\n        # constraint-specific validation logic comparing request and response\\n        return True\\n    except Exception as e:\\n        return False",
      "description": "Clear description of what specific correlation this script validates"
    }}
  ]
}}}}

REMEMBER: You must generate exactly {constraint_count} scripts, one for each constraint provided.
"""
