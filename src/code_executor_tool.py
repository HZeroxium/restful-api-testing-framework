# /src/code_executor_tool.py

import asyncio
import os
import json
from datetime import datetime

from tools import CodeExecutorTool


async def load_and_execute_from_file(
    tool, script_path, context_path=None, timeout=None
):
    """Load code from file and execute it with optional context from JSON file"""
    # Load the script content
    with open(script_path, "r") as f:
        code = f.read()

    # Prepare execution input
    execution_input = {"code": code}

    # Load context variables if provided
    if context_path and os.path.exists(context_path):
        with open(context_path, "r") as f:
            context_variables = json.load(f)
        execution_input["context_variables"] = context_variables

    # Set timeout if provided
    if timeout:
        execution_input["timeout"] = timeout

    # Execute with tool
    return await tool.execute(execution_input)


async def main():
    # build a timestamped directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "code_executor", ts)
    os.makedirs(out_dir, exist_ok=True)

    # Create base directory for scripts if it doesn't exist
    scripts_dir = os.path.join("data", "scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    # Create an instance of the CodeExecutorTool
    tool = CodeExecutorTool(
        verbose=True,
        cache_enabled=False,
        restricted_modules=["os", "sys"],
    )

    # ===== APPROACH 1: Direct examples from code variables =====
    examples = {
        # Simple function example
        "sum_function": {
            "code": """
def add_numbers(a, b):
    return a + b
""",
            "context_variables": {"a": 5, "b": 10},
        },
        # Example with calculation
        "sum_1_10": {
            "code": "total = sum(range(1,11))\n_result = total",
        },
        # Example that will cause an error
        "divide_zero": {
            "code": "x = 1/0\n_result = x",
        },
        # Function with validation logic
        "validate_test_data": {
            "code": """
def validate_test_data(test_data):
    # simple schema: must have "id" (int) and "name" (str)
    if not isinstance(test_data, dict):
        return False
    return isinstance(test_data.get("id"), int) and isinstance(test_data.get("name"), str)
""",
            "context_variables": {"test_data": {"id": 123, "name": "Alice"}},
        },
        # Same validation function with invalid data
        "validate_test_data_invalid": {
            "code": """
def validate_test_data(test_data):
    if not isinstance(test_data, dict):
        return False
    return isinstance(test_data.get("id"), int) and isinstance(test_data.get("name"), str)
""",
            "context_variables": {"test_data": {"id": "not-an-int"}},
        },
        # Multiple parameters function example
        "validate_req_res": {
            "code": """
def validate_req_res(req, res):
    # must be GET, 200 OK, response body has "data" list
    if req.get("method") != "GET":
        return False
    if res.get("status_code") != 200:
        return False
    body = res.get("body") or {}
    return isinstance(body.get("data"), list)
""",
            "context_variables": {
                "req": {
                    "path": "/items",
                    "method": "GET",
                    "headers": {"Accept": "application/json"},
                },
                "res": {
                    "status_code": 200,
                    "body": {"data": [1, 2, 3]},
                    "headers": {"Content-Type": "application/json"},
                },
            },
        },
        # Test for restricted modules
        "restricted_module": {
            "code": """
def get_current_dir():
    import os  # This should be restricted
    return os.getcwd()
""",
        },
        # Test for timeout handling
        "timeout_test": {
            "code": """
import time

def long_running_task():
    print("Starting long process...")
    time.sleep(5)  # This should time out with default timeout of 3
    print("Finished!")
    return "Done"
""",
            "timeout": 3,
        },
        # Multiple functions - should execute the first one
        "multiple_functions": {
            "code": """
def first_function():
    return "Result from first function"
    
def second_function():
    return "Result from second function"
"""
        },
        # Function that returns complex object
        "complex_result": {
            "code": """
def generate_data():
    return {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ],
        "total": 2,
        "page": 1
    }
"""
        },
    }

    # Run direct examples
    print("\n=== Running examples directly from code variables ===\n")
    for name, example in examples.items():
        print(f"\nExecuting example: {name}")

        # Execute with tool
        result = await tool.execute(example)

        # Save result to file
        filename = f"direct_{name}.json"
        with open(os.path.join(out_dir, filename), "w") as f:
            json.dump(result.model_dump(), f, indent=2)

        # Print brief result summary
        print(f"Success: {result.success}")
        print(f"Result: {result.result}")
        if not result.success:
            print(f"Error: {result.error}")
        print(f"Wrote {filename}")

    # ===== APPROACH 2: Load examples from files =====
    # Define file-based examples to run
    file_examples = [
        {"name": "sum_function", "context": True},
        {"name": "sum_1_10", "context": False},
        {"name": "divide_zero", "context": False},
        {"name": "validate_test_data", "context": True},
        {"name": "validate_test_data_invalid", "context": True},
        {"name": "validate_req_res", "context": True},
        {"name": "restricted_module", "context": False},
        {"name": "timeout_test", "context": False, "timeout": 3},
        {"name": "multiple_functions", "context": False},
        {"name": "complex_result", "context": False},
    ]

    print("\n=== Running examples loaded from files ===\n")
    for example in file_examples:
        name = example["name"]
        print(f"\nExecuting file example: {name}")

        script_path = os.path.join(scripts_dir, f"{name}.py")
        context_path = (
            os.path.join(scripts_dir, f"{name}_context.json")
            if example.get("context")
            else None
        )
        timeout = example.get("timeout")

        # Load and execute from file
        result = await load_and_execute_from_file(
            tool, script_path, context_path, timeout
        )

        # Save result to file
        filename = f"file_{name}.json"
        with open(os.path.join(out_dir, filename), "w") as f:
            json.dump(result.model_dump(), f, indent=2)

        # Print brief result summary
        print(f"Success: {result.success}")
        print(f"Result: {result.result}")
        if not result.success:
            print(f"Error: {result.error}")
        print(f"Wrote {filename}")


if __name__ == "__main__":
    asyncio.run(main())
