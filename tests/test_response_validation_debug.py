"""
Debug script to test response validation specifically.
"""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import asyncio


async def test_response_validation():
    """Test response validation with debug info."""

    try:
        from tools.core.code_executor import CodeExecutorTool
        from utils.code_script_utils import prepare_validation_script
        from schemas.tools.code_executor import CodeExecutorInput

        # Test the specific response validation script
        script_code = """def validate_response_body_is_array(request, response):
    \"\"\"Validate that the response body is an array. - Reference: placeholder_id\"\"\"
    try:
        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {})
        print(f"DEBUG: response type: {type(response)}")
        print(f"DEBUG: response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        print(f"DEBUG: body type: {type(body)}")
        print(f"DEBUG: body value: {body}")
        print(f"DEBUG: status_code: {response.get('status_code')}")
        if response.status_code == 200:
            return isinstance(body, list)
        return True # Only validate for 200 status
    except Exception as e:
        print(f"DEBUG: Error: {e}")
        return False"""

        # Prepare script
        prepared_script = prepare_validation_script(script_code)
        print(f"Prepared script:\n{prepared_script}")

        # Create test context
        test_context = {
            "request": {
                "params": {"general": "electronics"},
                "headers": {"Content-Type": "application/json"},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"Content-Type": "application/json"},
                "body": [
                    {
                        "id": "1",
                        "name": "Samsung",
                        "slug": "samsung",
                    },
                    {
                        "id": "2",
                        "name": "Apple",
                        "slug": "apple",
                    },
                ],
            },
        }

        print(f"Test context: {test_context}")

        # Execute script
        code_executor = CodeExecutorTool()
        script_input = CodeExecutorInput(
            code=prepared_script, context_variables=test_context, timeout=30
        )

        result = await code_executor.execute(script_input)
        print(f"Execution result: {result.success}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        print(f"Error: {result.error}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_response_validation())
