"""
Example usage of the constraint mining framework.
"""

import os
import json

from miner.constraint_miner import ConstraintMiner
from schemas.constraint import MiningConfiguration, ConstraintExtractionResult
from oas_parser.parser import OpenAPIParser
from schemas.openapi import OpenAPIParserInput, SpecSourceType
from utils.convert_to_excel_annotation_file import (
    convert_json_to_excel_response_property_constraints,
)


def save_results(results: ConstraintExtractionResult, output_dir: str) -> None:
    """Save constraint extraction results to files."""
    os.makedirs(output_dir, exist_ok=True)

    # Save input parameter constraints
    input_file = os.path.join(output_dir, "input_parameter_constraints.json")
    with open(input_file, "w") as f:
        json.dump(results.input_parameter_constraints, f, indent=2)

    # Save response property constraints
    response_file = os.path.join(output_dir, "response_property_constraints.json")
    with open(response_file, "w") as f:
        json.dump(results.response_property_constraints, f, indent=2)

    # Save request-response mappings
    mapping_file = os.path.join(output_dir, "request_response_mappings.json")
    with open(mapping_file, "w") as f:
        json.dump(results.request_response_mappings, f, indent=2)

    print(f"Results saved to {output_dir}")


def mine_single_service(
    service_name: str,
    openapi_path: str,
    experiment_folder: str = "experiment_results",
    selected_operations: list = None,
    selected_schemas: list = None,
) -> ConstraintExtractionResult:
    """
    Mine constraints for a single REST service.

    Args:
        service_name: Name of the service
        openapi_path: Path to OpenAPI specification
        experiment_folder: Folder for experiment results
        selected_operations: Optional list of operations to process
        selected_schemas: Optional list of schemas to process

    Returns:
        Constraint extraction results
    """
    print(f"\n{'='*60}")
    print(f"Mining constraints for: {service_name}")
    print(f"OpenAPI spec: {openapi_path}")
    print(f"{'='*60}")

    # Configure mining
    config = MiningConfiguration(
        save_and_load=True,
        experiment_folder=experiment_folder,
        selected_operations=selected_operations,
        selected_schemas=selected_schemas,
    )

    # Initialize parser and miner
    parser = OpenAPIParser(verbose=True)
    miner = ConstraintMiner(config)

    # Parse OpenAPI specification
    parser_input = OpenAPIParserInput(
        spec_source=openapi_path, source_type=SpecSourceType.FILE
    )
    parser_output = parser.parse(parser_input)

    # Mine constraints
    results = miner.mine_constraints(parser_output)

    # Save results
    output_dir = os.path.join(experiment_folder, results.service_name)
    save_results(results, output_dir)

    # Convert to Excel if needed
    try:
        response_json = os.path.join(output_dir, "response_property_constraints.json")
        response_excel = os.path.join(output_dir, "response_property_constraints.xlsx")
        convert_json_to_excel_response_property_constraints(
            response_json, openapi_path, response_excel
        )
        print(f"Excel file created: {response_excel}")
    except Exception as e:
        print(f"Warning: Could not create Excel file: {e}")

    return results


def mine_multiple_services():
    """Example of mining constraints for multiple services."""

    # Configuration
    experiment_folder = "experiment_results"

    # List of services to process
    services = [
        {
            "name": "Canada Holidays",
            "openapi_path": "example/Canada Holidays/openapi.json",
        },
        {"name": "Petstore", "openapi_path": "example/Petstore/openapi.json"},
    ]

    # Process each service
    all_results = {}

    for service in services:
        try:
            results = mine_single_service(
                service["name"], service["openapi_path"], experiment_folder
            )
            all_results[service["name"]] = results

            # Print summary
            print(f"\nSummary for {service['name']}:")
            print(
                f"  - Operations with input constraints: {len(results.input_parameter_constraints)}"
            )
            print(
                f"  - Schemas with property constraints: {len(results.response_property_constraints)}"
            )
            print(
                f"  - Request-response mappings: {len(results.request_response_mappings)}"
            )

        except Exception as e:
            print(f"Error processing {service['name']}: {e}")
            continue

    # Save combined summary
    summary_file = os.path.join(experiment_folder, "mining_summary.json")
    summary = {
        "total_services": len(services),
        "successful_services": len(all_results),
        "services": {
            name: {
                "input_constraints": len(result.input_parameter_constraints),
                "response_constraints": len(result.response_property_constraints),
                "mappings": len(result.request_response_mappings),
            }
            for name, result in all_results.items()
        },
    }

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nMining complete! Summary saved to {summary_file}")
    return all_results


def mine_with_specific_selections():
    """Example of mining with specific operation and schema selections."""

    # For services with many operations, you might want to focus on specific ones
    selected_operations = ["get-/holidays", "get-/provinces"]

    selected_schemas = ["Holiday", "Province"]

    results = mine_single_service(
        "Canada Holidays (Filtered)",
        "example/Canada Holidays/openapi.json",
        "experiment_filtered",
        selected_operations=selected_operations,
        selected_schemas=selected_schemas,
    )

    return results


def analyze_results(results: ConstraintExtractionResult):
    """Analyze and display constraint extraction results."""

    print(f"\n{'='*60}")
    print(f"ANALYSIS: {results.service_name}")
    print(f"{'='*60}")

    # Analyze input parameters
    total_input_constraints = 0
    for operation, locations in results.input_parameter_constraints.items():
        for location, params in locations.items():
            total_input_constraints += len(params)

    print(f"\nInput Parameter Constraints:")
    print(f"  - Total operations: {len(results.input_parameter_constraints)}")
    print(f"  - Total parameters with constraints: {total_input_constraints}")

    # Analyze response properties
    total_response_constraints = 0
    for schema, properties in results.response_property_constraints.items():
        total_response_constraints += len(properties)

    print(f"\nResponse Property Constraints:")
    print(f"  - Total schemas: {len(results.response_property_constraints)}")
    print(f"  - Total properties with constraints: {total_response_constraints}")

    # Analyze mappings
    total_mappings = 0
    for schema, properties in results.request_response_mappings.items():
        for prop, mappings in properties.items():
            total_mappings += len(mappings)

    print(f"\nRequest-Response Mappings:")
    print(
        f"  - Total mapped properties: {sum(len(props) for props in results.request_response_mappings.values())}"
    )
    print(f"  - Total individual mappings: {total_mappings}")

    # Show examples
    if results.response_property_constraints:
        print(f"\nExample Response Property Constraints:")
        for schema_name, properties in list(
            results.response_property_constraints.items()
        )[:2]:
            print(f"  Schema: {schema_name}")
            for prop_name, constraint in list(properties.items())[:3]:
                print(f"    - {prop_name}: {constraint[:100]}...")

    if results.request_response_mappings:
        print(f"\nExample Request-Response Mappings:")
        for schema, properties in list(results.request_response_mappings.items())[:2]:
            print(f"  Schema: {schema}")
            for prop, mappings in list(properties.items())[:2]:
                print(f"    - {prop} <- {len(mappings)} parameter(s)")
                for mapping in mappings[:2]:
                    print(f"      * {mapping[0]} ({mapping[1]}.{mapping[2]})")


def main():
    """Main example function."""

    print("Constraint Mining Framework - Example Usage")
    print("==========================================")

    # Example 1: Mine a single service
    print("\n1. Mining single service...")
    results = mine_single_service(
        "Canada Holidays", "data/RBCTest_dataset/Canada Holidays/openapi.json"
    )
    analyze_results(results)

    # # Example 2: Mine with selections
    # print("\n2. Mining with specific selections...")
    # filtered_results = mine_with_specific_selections()
    # analyze_results(filtered_results)

    # # Example 3: Mine multiple services
    # print("\n3. Mining multiple services...")
    # all_results = mine_multiple_services()

    # print("\n" + "=" * 60)
    # print("EXAMPLES COMPLETE")
    # print("=" * 60)
    # print("Check the 'experiment_results' folder for detailed outputs.")
    # print("Each service has its own subdirectory with:")
    # print("  - input_parameter_constraints.json")
    # print("  - response_property_constraints.json")
    # print("  - request_response_mappings.json")
    # print("  - response_property_constraints.xlsx (if available)")


if __name__ == "__main__":
    main()
