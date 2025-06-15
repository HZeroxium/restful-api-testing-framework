"""
Request-response parameter mapper.
"""

from typing import Dict, List, Optional, Tuple
import json

from schemas.constraint import (
    ConstraintValidationItem,
    ConstraintStatus,
)
from utils.constraint_utils import (
    extract_description_from_field,
    extract_data_type_from_field,
    filter_schema_by_data_type,
    verify_attribute_in_schema,
    extract_llm_answer,
    extract_corresponding_attribute,
)
from config.prompts.parameter_mapping import (
    PARAMETER_OBSERVATION,
    SCHEMA_OBSERVATION,
    PARAMETER_SCHEMA_MAPPING_PROMPT,
    MAPPING_CONFIRMATION,
)
from utils.gptcall import call_llm


class RequestResponseMapper:
    """Maps request parameters to response properties."""

    def __init__(self):
        self.mapping_cache: List[ConstraintValidationItem] = []

    def load_mapping_cache(self, cache_data: List[List]) -> None:
        """Load mapping cache from previous runs."""
        self.mapping_cache = [
            ConstraintValidationItem(
                identifier=item[0],
                status=(
                    ConstraintStatus(item[1])
                    if len(item) > 1
                    else ConstraintStatus.PENDING
                ),
                validation_details=item[3] if len(item) > 3 else None,
            )
            for item in cache_data
        ]

    def find_cached_mapping(
        self, param_name: str, description: str, schema_name: str
    ) -> Optional[ConstraintValidationItem]:
        """Find cached mapping result."""
        for mapping in self.mapping_cache:
            if (
                len(mapping.identifier) >= 3
                and mapping.identifier[0] == param_name
                and mapping.identifier[1] == description
                and mapping.identifier[2] == schema_name
            ):
                return mapping
        return None

    def create_mappings(
        self,
        input_constraints: Dict[str, Dict[str, Dict[str, str]]],
        simplified_schemas: Dict[str, Dict[str, str]],
        operation_response_schemas: Dict[str, Tuple[List[str], List[str]]],
    ) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        Create mappings between request parameters and response properties.

        Args:
            input_constraints: Input parameter constraints
            simplified_schemas: Simplified schema specifications
            operation_response_schemas: Mapping of operations to their response schemas

        Returns:
            Dictionary of request-response mappings
        """
        mappings = {}

        for operation, constraints in input_constraints.items():
            # Get response schemas for this operation
            main_schemas, _ = operation_response_schemas.get(operation, ([], []))

            for schema_name in main_schemas:
                if schema_name not in simplified_schemas:
                    continue

                schema_spec = simplified_schemas[schema_name]

                for location in ["parameters", "requestBody"]:
                    location_constraints = constraints.get(location, {})

                    for param_name, param_value in location_constraints.items():
                        description = extract_description_from_field(param_value) or ""

                        # Check cache first
                        cached_mapping = self.find_cached_mapping(
                            param_name, description, schema_name
                        )
                        if cached_mapping:
                            if cached_mapping.validation_details:
                                corresponding_attr = cached_mapping.validation_details
                                if schema_name not in mappings:
                                    mappings[schema_name] = {}
                                if corresponding_attr not in mappings[schema_name]:
                                    mappings[schema_name][corresponding_attr] = []
                                mappings[schema_name][corresponding_attr].append(
                                    [operation, location, param_name]
                                )
                            continue

                        # Create new mapping
                        mapping_result = self._create_parameter_mapping(
                            operation,
                            location,
                            param_name,
                            param_value,
                            schema_name,
                            schema_spec,
                        )

                        if mapping_result:
                            corresponding_attr = mapping_result
                            if schema_name not in mappings:
                                mappings[schema_name] = {}
                            if corresponding_attr not in mappings[schema_name]:
                                mappings[schema_name][corresponding_attr] = []
                            mappings[schema_name][corresponding_attr].append(
                                [operation, location, param_name]
                            )

                            # Cache the successful mapping
                            cache_item = ConstraintValidationItem(
                                identifier=[param_name, description, schema_name],
                                status=ConstraintStatus.VALID,
                                validation_details=corresponding_attr,
                            )
                            self.mapping_cache.append(cache_item)
                        else:
                            # Cache the failed mapping
                            cache_item = ConstraintValidationItem(
                                identifier=[param_name, description, schema_name],
                                status=ConstraintStatus.INVALID,
                            )
                            self.mapping_cache.append(cache_item)

        return mappings

    def _create_parameter_mapping(
        self,
        operation: str,
        location: str,
        param_name: str,
        param_value: str,
        schema_name: str,
        schema_spec: Dict[str, str],
    ) -> Optional[str]:
        """
        Create a mapping between a parameter and response property.

        Returns:
            Name of the corresponding response property, or None if no mapping
        """
        try:
            description = extract_description_from_field(param_value) or ""
            data_type = extract_data_type_from_field(param_value)

            # Filter schema by data type
            filtered_schema = filter_schema_by_data_type(schema_spec, data_type)
            if not filtered_schema:
                return None

            method = operation.split("-")[0]
            endpoint = "-".join(operation.split("-")[1:])

            # Generate parameter observation
            param_observation_prompt = PARAMETER_OBSERVATION.format(
                method=method.upper(),
                endpoint=endpoint,
                attribute=param_name,
                description=description,
            )
            param_observation_response = call_llm(param_observation_prompt)

            # Generate schema observation
            schema_observation_prompt = SCHEMA_OBSERVATION.format(
                schema=schema_name, specification=json.dumps(filtered_schema)
            )
            schema_observation_response = call_llm(schema_observation_prompt)

            # Generate mapping
            mapping_prompt = PARAMETER_SCHEMA_MAPPING_PROMPT.format(
                method=method.upper(),
                endpoint=endpoint,
                attribute=param_name,
                description=description,
                parameter_observation=param_observation_response,
                schema=schema_name,
                schema_observation=schema_observation_response,
                attributes=list(filtered_schema.keys()),
            )
            mapping_response = call_llm(mapping_prompt)

            # Check if mapping exists
            answer = extract_llm_answer(mapping_response)
            if "yes" not in answer:
                return None

            # Extract corresponding attribute
            corresponding_attr = extract_corresponding_attribute(mapping_response)
            if not verify_attribute_in_schema(filtered_schema, corresponding_attr):
                return None

            # Confirm mapping
            confirmation_prompt = MAPPING_CONFIRMATION.format(
                method=method.upper(),
                endpoint=endpoint,
                parameter_name=param_name,
                description=description,
                schema=schema_name,
                corresponding_attribute=corresponding_attr,
            )
            confirmation_response = call_llm(confirmation_prompt)
            confirmation_status = extract_llm_answer(confirmation_response)

            if "incorrect" in confirmation_status:
                return None

            return corresponding_attr

        except Exception as e:
            print(f"Error creating mapping for {param_name}: {e}")
            return None

    def get_mapping_cache_data(self) -> List[List]:
        """Get mapping cache data for persistence."""
        return [
            [item.identifier, item.status.value, None, item.validation_details]
            for item in self.mapping_cache
        ]
