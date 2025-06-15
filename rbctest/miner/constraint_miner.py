"""
Main constraint miner that orchestrates the extraction process.
"""

from typing import Dict, List, Tuple
import json
import os

from schemas.constraint import (
    ConstraintExtractionResult,
    MiningConfiguration,
    MiningProgress,
)
from schemas.openapi import OpenAPIParserOutput
from miner.core.input_parameter_extractor import InputParameterExtractor
from miner.core.response_property_extractor import ResponsePropertyExtractor
from miner.core.request_response_mapper import RequestResponseMapper
from oas_parser.operations import extract_operations
from oas_parser.schema import SchemaProcessor


class ConstraintMiner:
    """Main constraint mining orchestrator."""

    def __init__(self, config: MiningConfiguration):
        self.config = config
        self.input_extractor = InputParameterExtractor()
        self.response_extractor = ResponsePropertyExtractor()
        self.request_response_mapper = RequestResponseMapper()
        self.progress = MiningProgress(total_operations=0)

    def mine_constraints(
        self, parser_output: OpenAPIParserOutput
    ) -> ConstraintExtractionResult:
        """
        Mine all types of constraints from the OpenAPI specification.

        Args:
            parser_output: Parsed OpenAPI specification

        Returns:
            Complete constraint extraction results
        """
        service_name = parser_output.raw_spec.get("info", {}).get(
            "title", "Unknown Service"
        )

        # Initialize result
        result = ConstraintExtractionResult(service_name=service_name)

        # Load cache if enabled
        if self.config.save_and_load:
            self._load_caches(service_name)

        # Update progress
        operations = list(parser_output.simplified_endpoints.keys())
        if self.config.selected_operations:
            operations = [
                op for op in operations if op in self.config.selected_operations
            ]

        self.progress.total_operations = len(operations)

        # Extract input parameter constraints
        print("Extracting input parameter constraints...")
        result.input_parameter_constraints = self.input_extractor.extract_constraints(
            parser_output.simplified_endpoints,
            parser_output.raw_spec,
            self.config.selected_operations,
        )

        # Extract response property constraints
        print("Extracting response property constraints...")
        response_schemas = self._get_response_schemas(parser_output.raw_spec)
        simplified_schemas = self._get_simplified_schemas(parser_output.raw_spec)

        result.response_property_constraints = (
            self.response_extractor.extract_constraints(
                simplified_schemas, response_schemas, self.config.selected_schemas
            )
        )

        # Create request-response mappings
        print("Creating request-response mappings...")
        operation_schemas = self._get_operation_response_schemas(parser_output.raw_spec)

        result.request_response_mappings = self.request_response_mapper.create_mappings(
            result.input_parameter_constraints, simplified_schemas, operation_schemas
        )

        # Save cache if enabled
        if self.config.save_and_load:
            self._save_caches(service_name)

        return result

    def _get_response_schemas(self, spec: Dict) -> List[str]:
        """Get all response schemas from the specification."""
        response_schemas = []
        operations = extract_operations(spec)
        schema_processor = SchemaProcessor(spec)

        for operation in operations:
            _, relevant_schemas = schema_processor.get_relevant_schemas_of_operation(
                operation
            )
            response_schemas.extend(relevant_schemas)

        return list(set(response_schemas))

    def _get_simplified_schemas(self, spec: Dict) -> Dict[str, Dict[str, str]]:
        """Get simplified schemas from the specification."""
        schema_processor = SchemaProcessor(spec)
        return schema_processor.get_simplified_schema()

    def _get_operation_response_schemas(
        self, spec: Dict
    ) -> Dict[str, Tuple[List[str], List[str]]]:
        """Get response schemas for each operation."""
        schema_processor = SchemaProcessor(spec)
        operations = extract_operations(spec)
        operation_schemas = {}

        for operation in operations:
            main_schemas, all_schemas = (
                schema_processor.get_relevant_schemas_of_operation(operation)
            )
            operation_schemas[operation] = (main_schemas, all_schemas)

        return operation_schemas

    def _load_caches(self, service_name: str) -> None:
        """Load caches from previous runs."""
        cache_dir = os.path.join(self.config.experiment_folder, service_name)

        # Load input parameter cache
        input_cache_path = os.path.join(cache_dir, "input_parameters_checked.json")
        if os.path.exists(input_cache_path):
            with open(input_cache_path, "r") as f:
                self.input_extractor.load_validation_cache(json.load(f))

        # Load response property cache
        response_cache_path = os.path.join(
            cache_dir, "response_properties_checked.json"
        )
        if os.path.exists(response_cache_path):
            with open(response_cache_path, "r") as f:
                self.response_extractor.load_validation_cache(json.load(f))

        # Load mapping cache
        mapping_cache_path = os.path.join(cache_dir, "mappings_checked.json")
        if os.path.exists(mapping_cache_path):
            with open(mapping_cache_path, "r") as f:
                self.request_response_mapper.load_mapping_cache(json.load(f))

    def _save_caches(self, service_name: str) -> None:
        """Save caches for future runs."""
        cache_dir = os.path.join(self.config.experiment_folder, service_name)
        os.makedirs(cache_dir, exist_ok=True)

        # Save input parameter cache
        input_cache_path = os.path.join(cache_dir, "input_parameters_checked.json")
        with open(input_cache_path, "w") as f:
            json.dump(self.input_extractor.get_validation_cache_data(), f, indent=2)

        # Save response property cache
        response_cache_path = os.path.join(
            cache_dir, "response_properties_checked.json"
        )
        with open(response_cache_path, "w") as f:
            json.dump(self.response_extractor.get_validation_cache_data(), f, indent=2)

        # Save mapping cache
        mapping_cache_path = os.path.join(cache_dir, "mappings_checked.json")
        with open(mapping_cache_path, "w") as f:
            json.dump(
                self.request_response_mapper.get_mapping_cache_data(), f, indent=2
            )
