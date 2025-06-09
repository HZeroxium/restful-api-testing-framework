"""
Example usage of the OpenAPI Parser.
"""

import json
import os
from datetime import datetime

from oas_parser.parser import OpenAPIParser
from schemas.openapi import OpenAPIParserInput, SpecSourceType


def save_output_to_file(output_dict, file_path):
    """Save parser output to a JSON file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save to file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2)

    print(f"Output saved to {file_path}")


def create_output_dir(base_dir="rbctest_output"):
    """Create a timestamped output directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, "openapi_parser", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def main():
    """Run example OpenAPI parser usage."""
    # Create output directory
    output_dir = create_output_dir()
    print(f"Output directory: {output_dir}")

    # Initialize parser
    parser = OpenAPIParser(verbose=True)

    # Define examples to parse
    examples = [
        {
            "name": "toolshop_api",
            "input": OpenAPIParserInput(
                spec_source="data/toolshop/openapi.json",
                source_type=SpecSourceType.FILE,
            ),
        },
        {
            "name": "gitlab_repository_api",
            "input": OpenAPIParserInput(
                spec_source="data/RBCTest_dataset/GitLab Repository/openapi.json",
                source_type=SpecSourceType.FILE,
                filter_tags=["repository"],
            ),
        },
        # Add more examples as needed
    ]

    # Process each example
    for example in examples:
        name = example["name"]
        input_params = example["input"]

        print(f"\n--- Processing {name} ---")

        try:
            # Parse the OpenAPI spec
            result = parser.parse(input_params)

            # Print summary information
            print(f"API: {result.title} v{result.version}")
            print(
                f"Description: {result.description[:100]}..."
                if result.description and len(result.description) > 100
                else f"Description: {result.description}"
            )
            print(f"Servers: {', '.join(result.servers)}")
            # print(f"Total endpoints: {result.endpoint_count}")

            # Show a sample of endpoints
            if result.endpoints:
                print("\nSample endpoints:")
                for endpoint in result.endpoints[:3]:  # Show up to 3 endpoints
                    print(f"  {endpoint.method} {endpoint.path} - {endpoint.summary}")

            # Save output to file
            output_file = os.path.join(output_dir, f"{name}.json")
            save_output_to_file(result.model_dump(by_alias=True), output_file)

        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
