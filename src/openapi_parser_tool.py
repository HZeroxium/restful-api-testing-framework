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
from common.logger import LoggerFactory, LoggerType, LogLevel


async def main():
    """Run OpenAPI Parser Tool examples."""
    # Initialize logger for the demo
    logger = LoggerFactory.get_logger(
        name="openapi-parser-demo",
        logger_type=LoggerType.STANDARD,
        level=LogLevel.INFO,
    )

    # Create timestamped output directory
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "openapi_parser", ts)
    os.makedirs(out_dir, exist_ok=True)

    logger.info(f"Starting OpenAPI Parser Tool demo")
    logger.add_context(output_directory=out_dir, timestamp=ts)

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

    logger.info(f"Processing {len(examples)} OpenAPI specifications")

    # Process each example
    for name, params in examples.items():
        logger.info(f"Processing example: {name}")
        logger.add_context(
            example_name=name, spec_source=params.get("spec_source", "unknown")
        )

        try:
            # Create input object and execute
            input_data = OpenAPIParserInput(**params)
            result: OpenAPIParserOutput = await tool.execute(input_data)

            # Brief output summary
            logger.info(
                f"Successfully parsed API: {result.title} v{result.version} with {result.endpoint_count} endpoints"
            )

            # Save result to JSON file
            output_path = os.path.join(out_dir, f"{name}.json")
            with open(output_path, "w") as f:
                json.dump(result.model_dump(), f, indent=2)

            logger.debug(f"Results saved to: {output_path}")

        except Exception as e:
            logger.error(f"Error processing {name}: {str(e)}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")

    logger.info("OpenAPI Parser Tool demo completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
