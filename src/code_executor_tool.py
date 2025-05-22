# /src/code_executor_tool.py

import asyncio
import os
import json
from datetime import datetime

from tools import CodeExecutorTool


async def main():
    # build a timestamped directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "code_executor", ts)
    os.makedirs(out_dir, exist_ok=True)

    tool = CodeExecutorTool(
        verbose=True,
        cache_enabled=False,
        config={"restricted_modules": ["os", "sys"], "app_name": "code_exec_demo"},
    )

    examples = {
        "sum_1_10": "total = sum(range(1,11))\n_result = total",
        "divide_zero": "x = 1/0\n_result = x",
        # --- validate_test_data: valid case ---
        "validate_test_data_valid": {
            "code": """
def validate_test_data(test_data):
    # simple schema: must have "id" (int) and "name" (str)
    if not isinstance(test_data, dict):
        return False
    return isinstance(test_data.get("id"), int) and isinstance(test_data.get("name"), str)

# execute validation
is_valid = validate_test_data(test_data)
print(f"Test data valid? {is_valid}")
_result = is_valid
""",
            "context_variables": {"test_data": {"id": 123, "name": "Alice"}},
        },
        # --- validate_test_data: invalid case ---
        "validate_test_data_invalid": {
            "code": """
def validate_test_data(test_data):
    if not isinstance(test_data, dict):
        return False
    return isinstance(test_data.get("id"), int) and isinstance(test_data.get("name"), str)

is_valid = validate_test_data(test_data)
print(f"Test data valid? {is_valid}")
_result = is_valid
""",
            "context_variables": {
                # missing "name", or wrong type
                "test_data": {"id": "not-an-int"}
            },
        },
        # --- validate_request_response_constraint: valid case ---
        "validate_req_res_valid": {
            "code": """
def validate_req_res(req, res):
    # must be GET, 200 OK, response body has "data" list
    if req.get("method") != "GET":
        return False
    if res.get("status_code") != 200:
        return False
    body = res.get("body") or {}
    return isinstance(body.get("data"), list)

passed = validate_req_res(req, res)
print(f"Constraint passed? {passed}")
_result = passed
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
        # --- validate_request_response_constraint: invalid case ---
        "validate_req_res_invalid": {
            "code": """
def validate_req_res(req, res):
    if req.get("method") != "GET":
        return False
    if res.get("status_code") != 200:
        return False
    body = res.get("body") or {}
    return isinstance(body.get("data"), list)

passed = validate_req_res(req, res)
print(f"Constraint passed? {passed}")
_result = passed
""",
            "context_variables": {
                "req": {
                    "path": "/items",
                    "method": "POST",  # wrong method
                    "headers": {"Accept": "application/json"},
                },
                "res": {
                    "status_code": 201,  # wrong status
                    "body": {"message": "Created"},
                    "headers": {"Content-Type": "application/json"},
                },
            },
        },
    }

    for name, code in examples.items():
        # Handle both string and dictionary inputs properly
        if isinstance(code, str):
            # Simple string case
            input_data = {"code": code}
        else:
            # Dictionary case with code and context variables
            input_data = code  # Pass the dictionary directly

        result = await tool.execute(input_data)
        filename = f"{name}.json"
        with open(os.path.join(out_dir, filename), "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    asyncio.run(main())
