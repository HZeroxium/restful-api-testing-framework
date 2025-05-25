# src/rest_tool_runner.py

import asyncio
import os
import json
from datetime import datetime

# Import OpenAPIToolset from ADK
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import (
    OpenAPIToolset,
)

# Import our new RestApiAgent
from agents import RestApiAgent


async def main():
    """
    1. Create output directory with timestamp (YYYYMMDD_HHMMSS)
    2. Initialize OpenAPIToolset from spec file
    3. Get auto-generated RestApiTool list
    4. Initialize RestApiAgent with these tools
    5. Execute API calls using the agent
    6. Save JSON results for each call
    """
    # 1. Set up output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_out = os.path.join("output", "rest_tool", ts)
    os.makedirs(base_out, exist_ok=True)

    # 2. Initialize OpenAPIToolset
    spec_path = "data/json_place_holder/openapi.yaml"

    # Read the YAML file content
    try:
        with open(spec_path, "r") as f:
            spec_content = f.read()
    except FileNotFoundError:
        print(f"Error: Spec file not found at '{spec_path}'")
        return

    # Create the toolset with the file content
    toolset = OpenAPIToolset(
        spec_str=spec_content,
        spec_str_type="yaml",
    )

    # 3. Get the list of RestApiTools
    rest_tools = toolset.get_tools()
    print(f"Found {len(rest_tools)} REST API tools")

    # Print info about the first tool to help with debugging
    if rest_tools and len(rest_tools) > 0:
        first_tool = rest_tools[0]
        print(f"First tool: {first_tool.name}")
        print(f"Tool type: {type(first_tool)}")
        print(f"Tool methods: {[m for m in dir(first_tool) if not m.startswith('_')]}")
        print(f"Tool endpoint: {first_tool.endpoint}")

    # 4. Initialize the RestApiAgent with these tools
    agent = RestApiAgent(
        model_name="gemini-1.5-flash",
        tools=rest_tools,
        verbose=True,
    )

    # 5. Define the API calls to make
    api_calls = ["GET /posts", "GET /posts/1", "GET /comments", "GET /comments/1"]

    # 6. Execute each call using the agent and save results
    for call in api_calls:
        print(f"\nExecuting: {call}")

        # Format as a command for the agent
        query = f"CALL {call}"

        try:
            # Run the agent with this query
            result = await agent.run({"query": query})

            # Extract file name from the call
            method, path = call.split(" ", 1)
            endpoint_name = path.strip("/").replace("/", "_")
            if not endpoint_name:
                endpoint_name = "root"

            # Save results to JSON file
            out_file = os.path.join(base_out, f"{method.lower()}_{endpoint_name}.json")
            with open(out_file, "w") as f:
                json.dump(result.model_dump(), f, indent=2)
            print(f"Wrote result to {out_file}")

        except Exception as e:
            print(f"Error executing {call}: {str(e)}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
