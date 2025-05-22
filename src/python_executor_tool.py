# /src/python_executor_tool.py

import asyncio
import os
import json
from dotenv import load_dotenv

# Import our custom tools
from tools import PythonScriptExecutorTool


load_dotenv()


async def demonstrate_python_executor():
    """Demonstrate the Python Script Executor Tool."""
    print("\n--- Python Script Executor Tool Demo ---\n")

    # Create output directory if it doesn't exist
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output"
    )
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the tool
    python_tool = PythonScriptExecutorTool(
        verbose=True,
        cache_enabled=False,
        config={
            "restricted_modules": [
                "os",
                "subprocess",
                "sys",
            ]  # Define restricted modules
        },
    )

    # Example 1: Basic calculation
    code1 = """
# Calculate sum from 1 to 10
total = 0
for i in range(1, 11):
    total += i
_result = total
"""

    print("Example 1: Computing sum from 1 to 10")
    result1 = await python_tool.execute({"code": code1})
    print(f"Result: {result1.result}")
    print(f"Success: {result1.success}")
    print(f"Execution time: {result1.execution_time:.4f}s")

    # Save result to output file
    with open(os.path.join(output_dir, "python_example1_result.json"), "w") as f:
        json.dump(result1.model_dump(), f, indent=2)

    # Example 2: Generate Fibonacci sequence
    code2 = """
# Generate first 10 Fibonacci numbers
def fibonacci(n):
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    return sequence

_result = fibonacci(10)
"""

    print("\nExample 2: Generating Fibonacci sequence")
    result2 = await python_tool.execute({"code": code2, "timeout": 5})
    print(f"Result: {result2.result}")

    # Save result to output file
    with open(os.path.join(output_dir, "python_example2_result.json"), "w") as f:
        json.dump(result2.model_dump(), f, indent=2)

    # Example 3: Error handling
    code3 = """
# This will cause an error
x = 10 / 0
"""

    print("\nExample 3: Error handling")
    result3 = await python_tool.execute({"code": code3})
    print(f"Success: {result3.success}")
    print(f"Error: {result3.error}")

    # Save result to output file
    with open(os.path.join(output_dir, "python_example3_result.json"), "w") as f:
        json.dump(result3.model_dump(), f, indent=2)

    # Example 4: Using context variables
    code4 = """
# Use provided variables
result = x + y
print(f"Sum of {x} and {y} is {result}")
_result = result
"""

    print("\nExample 4: Using context variables")
    result4 = await python_tool.execute(
        {"code": code4, "context_variables": {"x": 5, "y": 7}}
    )
    print(f"Result: {result4.result}")
    print(f"Stdout: {result4.stdout}")

    # Save result to output file
    with open(os.path.join(output_dir, "python_example4_result.json"), "w") as f:
        json.dump(result4.model_dump(), f, indent=2)


async def main():
    """Run all demonstrations."""
    await demonstrate_python_executor()
    # await demonstrate_openapi_parser()


if __name__ == "__main__":
    asyncio.run(main())
