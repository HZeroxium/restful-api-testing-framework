"""
Simplified request-response miner example using the new constraint mining framework.
"""

import os
import json

from miner.constraint_miner import ConstraintMiner
from schemas.constraint import MiningConfiguration
from oas_parser.parser import OpenAPIParser
from schemas.openapi import OpenAPIParserInput, SpecSourceType


def main():
    experiment_folder = "experiment_our"
    rest_services = ["Canada Holidays"]  # Add your service names here

    for rest_service in rest_services:
        print("\n" + "*" * 20)
        print(rest_service)
        print("*" * 20)

        openapi_path = f"data/RBCTest_dataset/{rest_service}/openapi.json"

        # Configure mining
        config = MiningConfiguration(
            save_and_load=True, experiment_folder=experiment_folder
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

        # Mine all constraints
        results = miner.mine_constraints(parser_output)

        # Save results
        input_file = f"{experiment_folder}/{service_name}/input_parameter.json"
        with open(input_file, "w") as f:
            json.dump(results.input_parameter_constraints, f, indent=2)

        mapping_file = (
            f"{experiment_folder}/{service_name}/request_response_constraints.json"
        )
        with open(mapping_file, "w") as f:
            json.dump(results.request_response_mappings, f, indent=2)

        print("Request Response Constraints Have Been Exported")


if __name__ == "__main__":
    main()
