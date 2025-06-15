"""
Simplified response property miner example using the new constraint mining framework.
"""

import os
import json

from miner.constraint_miner import ConstraintMiner
from schemas.constraint import MiningConfiguration
from oas_parser.parser import OpenAPIParser
from schemas.openapi import OpenAPIParserInput, SpecSourceType
from utils.convert_to_excel_annotation_file import (
    convert_json_to_excel_response_property_constraints,
)


def main():
    experiment_folder = "experiment_our"
    rest_services = ["Canada Holidays"]

    # Optional: Load specific selections for large services
    selected_schemas = None
    selected_operations = None

    # Uncomment and modify for services like StripeClone
    # selected_schemas = [line.strip() for line in open("stripe_selected/selected_schemas.txt").readlines()]
    # selected_operations = [line.strip() for line in open("stripe_selected/selected_operations.txt").readlines()]

    for rest_service in rest_services:
        print("*" * 20)
        print(rest_service)
        print("*" * 20)

        openapi_path = f"example/{rest_service}/openapi.json"

        # Configure mining
        config = MiningConfiguration(
            save_and_load=True,
            experiment_folder=experiment_folder,
            selected_operations=selected_operations,
            selected_schemas=selected_schemas,
        )

        # Initialize components
        parser = OpenAPIParser(verbose=False)
        miner = ConstraintMiner(config)

        # Parse specification
        parser_input = OpenAPIParserInput(
            spec_source=openapi_path, source_type=SpecSourceType.FILE
        )
        parser_output = parser.parse(parser_input)

        service_name = parser_output.raw_spec["info"]["title"]
        os.makedirs(f"{experiment_folder}/{service_name}", exist_ok=True)

        # Mine constraints
        results = miner.mine_constraints(parser_output)

        # Save response property constraints
        outfile = (
            f"{experiment_folder}/{service_name}/response_property_constraints.json"
        )
        with open(outfile, "w") as f:
            json.dump(results.response_property_constraints, f, indent=2)

        # Convert to Excel
        try:
            convert_json_to_excel_response_property_constraints(
                outfile, openapi_path, outfile.replace(".json", ".xlsx")
            )
            print(f"Excel file created: {outfile.replace('.json', '.xlsx')}")
        except Exception as e:
            print(f"Warning: Could not create Excel file: {e}")


if __name__ == "__main__":
    main()
