"""
Debug script to test verification logic step by step.
"""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import asyncio
import json


async def test_verification_logic():
    """Test verification logic step by step."""

    # Test 1: Check if we can load validation scripts
    print("=== Test 1: Loading Validation Scripts ===")

    try:
        from application.services.validation_script_service import (
            ValidationScriptService,
        )
        from application.services.endpoint_service import EndpointService
        from adapters.repository.json_file_validation_script_repository import (
            JsonFileValidationScriptRepository,
        )
        from adapters.repository.json_file_endpoint_repository import (
            JsonFileEndpointRepository,
        )

        # Create services
        endpoint_repo = JsonFileEndpointRepository()
        script_repo = JsonFileValidationScriptRepository()

        endpoint_service = EndpointService(endpoint_repo)
        script_service = ValidationScriptService(script_repo, None, endpoint_repo)

        # Get endpoint by name
        endpoint = await endpoint_service.get_endpoint_by_name("get_brands")
        print(f"Found endpoint: {endpoint.name} (ID: {endpoint.id})")

        # Get validation scripts
        scripts = await script_service.get_scripts_by_endpoint_id(endpoint.id)
        print(f"Found {len(scripts)} validation scripts")

        for script in scripts:
            print(f"  - {script.name} (type: {script.script_type})")

        # Filter scripts by type
        request_scripts = [
            s for s in scripts if s.script_type in ["request_param", "request_body"]
        ]
        response_scripts = [
            s
            for s in scripts
            if s.script_type in ["response_property", "request_response"]
        ]

        print(f"Request scripts: {len(request_scripts)}")
        print(f"Response scripts: {len(response_scripts)}")

    except Exception as e:
        print(f"Error in Test 1: {e}")
        import traceback

        traceback.print_exc()

    print("\n=== Test 2: Test Script Execution ===")

    try:
        from tools.core.code_executor import CodeExecutorTool
        from utils.code_script_utils import prepare_validation_script
        from schemas.tools.code_executor import CodeExecutorInput

        # Get a sample script
        if scripts:
            sample_script = scripts[0]
            print(f"Testing script: {sample_script.name}")
            print(f"Script code: {sample_script.validation_code}")

            # Prepare script
            prepared_script = prepare_validation_script(sample_script.validation_code)
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
                    "body": [{"id": "1", "name": "Samsung"}],
                    "headers": {"Content-Type": "application/json"},
                },
            }

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
            print(f"Execution time: {result.execution_time}")

    except Exception as e:
        print(f"Error in Test 2: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_verification_logic())
