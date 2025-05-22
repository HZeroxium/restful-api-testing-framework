# main.py

from tools import OpenAPIParserTool
from schemas.tools.openapi_parser import SpecSourceType, OpenAPIParserOutput
import json
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()


async def demonstrate_openapi_parser():
    """Demonstrate the OpenAPI Parser Tool."""
    print("\n--- OpenAPI Parser Tool Demo ---\n")

    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the tool
    openapi_tool = OpenAPIParserTool(verbose=True, cache_enabled=False)

    # List of OpenAPI spec files to process
    spec_paths = [
        "data/example/openapi.yaml",
        # "data/RBCTest_dataset/GitLab Repository/openapi.json",
        # "data/RBCTest_dataset/GitLab Project/openapi.json",
        # "data/RBCTest_dataset/GitLab Issues/openapi.json",
        # "data/RBCTest_dataset/GitLab Groups/openapi.json",
        # "data/RBCTest_dataset/GitLab Commit/openapi.json",
        # "data/RBCTest_dataset/GitLab Branch/openapi.json",
        # "data/RBCTest_dataset/StripeClone/openapi.json",
        # "data/RBCTest_dataset/Canada Holidays/openapi.json",
    ]

    # Process each spec file
    for index, spec_path in enumerate(spec_paths):
        print(f"\n===== Processing Spec #{index+1}: {spec_path} =====")

        try:
            # Parse the spec
            result: OpenAPIParserOutput = await openapi_tool.execute(
                {"spec_source": spec_path, "source_type": SpecSourceType.FILE}
            )

            # Generate unique output filename based on directory and file name
            dir_name = os.path.basename(os.path.dirname(spec_path))
            base_filename = os.path.splitext(os.path.basename(spec_path))[0]

            # Create a unique identifier - combine directory name and base filename
            unique_id = (
                f"{dir_name}_{base_filename}"
                if dir_name != "example"
                else base_filename
            )
            output_filename = f"openapi_parsed_{unique_id}.json"
            output_path = os.path.join(output_dir, output_filename)

            # Display basic information
            print(f"API Title: {result.title}")
            print(f"API Version: {result.version}")
            print(f"API Description: {result.description}")
            print(f"Endpoint Count: {result.endpoint_count}")
            print("\nEndpoints (showing up to 5):")
            for endpoint in result.endpoints[
                :5
            ]:  # Show only first 5 endpoints to avoid overwhelming output
                print(f"  {endpoint.method} {endpoint.path}: {endpoint.name}")

            if len(result.endpoints) > 5:
                print(f"  ... and {len(result.endpoints) - 5} more endpoints")

            # Save parsed API spec to output file
            with open(output_path, "w") as f:
                # Convert to dict first to handle serialization
                result_dict = result.model_dump()
                json.dump(result_dict, f, indent=2)
                print(f"\nSaved parsed spec to: {output_path}")

            # Detailed output of one endpoint for inspection if available
            if result.endpoints:
                print("\nSample endpoint information:")
                endpoint = result.endpoints[0]
                print(f"Name: {endpoint.name}")
                print(f"Path: {endpoint.path}")
                print(f"Method: {endpoint.method}")
                print(f"Auth Required: {endpoint.auth_required}")

        except Exception as e:
            print(f"Error processing {spec_path}: {str(e)}")
            # Log the full exception for debugging
            import traceback

            print(f"Full error: {traceback.format_exc()}")


async def main():
    """Run all demonstrations."""
    await demonstrate_openapi_parser()


if __name__ == "__main__":
    asyncio.run(main())
