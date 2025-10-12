# utils/code_script_utils.py

"""
Utilities for handling validation script execution and preparation.
This module provides functions to prepare validation scripts for execution
by wrapping function definitions with execution code.
"""

from typing import Dict, Any, Optional
import re
from pydantic import BaseModel

from common.logger import LoggerFactory, LoggerType, LogLevel

# Initialize logger
logger = LoggerFactory.get_logger(
    name="utils.code_script_utils", logger_type=LoggerType.STANDARD, level=LogLevel.INFO
)


def prepare_validation_script(validation_code: str) -> str:
    """
    Prepare a validation script for execution by wrapping it with code that executes
    the validation function with proper parameters.

    Args:
        validation_code: The validation function code as string
        request_data: The request data to pass to the validation function
        response_data: The response data to pass to the validation function

    Returns:
        A string containing the complete executable code
    """
    logger.debug(f"Preparing validation script for execution")

    # Extract function name from the validation code
    function_name = extract_function_name(validation_code)

    if not function_name:
        logger.warning("Could not extract function name from validation code")
        # Use a default function name if extraction fails
        function_name = "validate"

    # Build the complete executable code
    executable_code = f"""
# Original validation function
{validation_code}

# Execute the validation function with request and response data
try:
    # Execute the function with request and response data
    _result = {function_name}(request, response)
except Exception as e:
    # Return False if there's an error in execution
    _result = False
    print(f"Error executing validation function: {{e}}")

# Return the result explicitly 
print(_result)
"""

    logger.debug(f"Prepared validation script with function name: {function_name}")
    return executable_code


def extract_function_name(code: str) -> Optional[str]:
    """
    Extract the function name from a Python function definition.

    Args:
        code: The Python code containing a function definition

    Returns:
        The function name if found, None otherwise
    """
    # Regular expression to match function definition
    # This matches "def function_name(" pattern
    func_pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("

    # Try to find a match
    match = re.search(func_pattern, code)

    if match:
        return match.group(1)
    return None


def normalize_validation_script(script_code: str) -> str:
    """
    Normalize validation script to use correct response schema.

    Converts common incorrect patterns to correct ones:
    - response.data → response.get('body')
    - response['data'] → response.get('body')
    - response.status_code → response.get('status_code')
    - response['status_code'] → response.get('status_code')
    - response.headers → response.get('headers')
    - response['headers'] → response.get('headers')

    Args:
        script_code: The validation script code to normalize

    Returns:
        Normalized script code with correct response schema access patterns
    """
    logger.debug("Normalizing validation script for correct response schema")

    # Pattern 1: response.data (attribute access)
    script_code = re.sub(r"\bresponse\.data\b", "response.get('body')", script_code)

    # Pattern 2: response['data'] (bracket notation)
    script_code = re.sub(r"response\['data'\]", "response.get('body')", script_code)
    script_code = re.sub(r'response\["data"\]', "response.get('body')", script_code)

    # Pattern 3: response.status_code (attribute)
    script_code = re.sub(
        r"\bresponse\.status_code\b", "response.get('status_code')", script_code
    )

    # Pattern 4: response['status_code'] (bracket)
    script_code = re.sub(
        r"response\['status_code'\]", "response.get('status_code')", script_code
    )

    # Pattern 5: response.headers (attribute)
    script_code = re.sub(
        r"\bresponse\.headers\b", "response.get('headers')", script_code
    )

    # Pattern 6: response['headers'] (bracket)
    script_code = re.sub(
        r"response\['headers'\]", "response.get('headers')", script_code
    )

    logger.debug("Validation script normalization completed")
    return script_code


class ValidationResult(BaseModel):
    """Model for validation result data."""

    success: bool
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
