# src/openapi_parser_tool.py

import asyncio
import os
import json
from datetime import datetime

from tools import OpenAPIParserTool
from schemas.tools.openapi_parser import (
    SpecSourceType,
    OpenAPIParserInput,
    OpenAPIParserOutput,
)


async def main():
    """Run OpenAPI Parser Tool examples."""
    # Create timestamped output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "openapi_parser", ts)
    os.makedirs(out_dir, exist_ok=True)

    # Initialize the tool
    tool = OpenAPIParserTool(verbose=True, cache_enabled=False)

    # Define examples dictionary mapping names to input parameters
    examples = {
        "example_api": {
            "spec_source": "data/example/openapi.yaml",
            "source_type": SpecSourceType.FILE,
        },
        "toolshop_api": {
            "spec_source": "data/toolshop/openapi.json",
            "source_type": SpecSourceType.FILE,
        },
        # Uncomment for additional examples
        # "gitlab_repo_api": {
        #     "spec_source": "data/RBCTest_dataset/GitLab Repository/openapi.json",
        #     "source_type": SpecSourceType.FILE,
        # },
        # "gitlab_project_api": {
        #     "spec_source": "data/RBCTest_dataset/GitLab Project/openapi.json",
        #     "source_type": SpecSourceType.FILE
        # },
        # "gitlab_issues_api": {
        #     "spec_source": "data/RBCTest_dataset/GitLab Issues/openapi.json",
        #     "source_type": SpecSourceType.FILE,
        #     "filter_tags": ["issues"]
        # },
    }

    # Process each example
    for name, params in examples.items():
        print(f"\n--- Processing: {name} ---")
        try:
            # Create input object and execute
            input_data = OpenAPIParserInput(**params)
            result: OpenAPIParserOutput = await tool.execute(input_data)

            # Brief output summary
            print(f"API: {result.title} v{result.version}")
            print(f"Endpoints: {result.endpoint_count}")

            # Save result to JSON file
            output_path = os.path.join(out_dir, f"{name}.json")
            with open(output_path, "w") as f:
                json.dump(result.model_dump(), f, indent=2)
                print(f"Wrote {output_path}")

        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
