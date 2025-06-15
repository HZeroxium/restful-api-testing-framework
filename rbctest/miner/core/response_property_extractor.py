"""
Response property constraint extractor.
"""

from typing import Dict, List, Optional

from schemas.constraint import (
    ResponsePropertyConstraint,
    ConstraintStatus,
    ConstraintValidationItem,
)
from utils.constraint_utils import (
    extract_description_from_field,
    extract_data_type_from_field,
    has_description,
    extract_llm_answer,
)
from config.prompts.constraint_extraction import (
    DESCRIPTION_OBSERVATION_PROMPT,
    CONSTRAINT_CONFIRMATION,
)
from utils.gptcall import call_llm


class ResponsePropertyExtractor:
    """Extracts constraints from response properties."""

    def __init__(self):
        self.validation_cache: List[ConstraintValidationItem] = []

    def load_validation_cache(self, cache_data: List[Dict]) -> None:
        """Load validation cache from previous runs."""
        self.validation_cache = [
            ConstraintValidationItem(
                identifier=item[0], status=ConstraintStatus(item[1])
            )
            for item in cache_data
        ]

    def find_cached_validation(
        self, constraint: ResponsePropertyConstraint
    ) -> Optional[ConstraintValidationItem]:
        """Find cached validation result for a property constraint."""
        identifier = [
            constraint.property_name,
            f"{constraint.data_type} (description: {constraint.description})",
        ]

        for validation in self.validation_cache:
            if validation.identifier == identifier:
                return validation

        return None

    def extract_constraints(
        self,
        simplified_schemas: Dict[str, Dict[str, str]],
        response_schemas: List[str],
        selected_schemas: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Extract response property constraints from schemas.

        Args:
            simplified_schemas: Simplified schema specifications
            response_schemas: List of schemas used in responses
            selected_schemas: Optional list of schemas to process

        Returns:
            Dictionary of response property constraints
        """
        constraints = {}
        schemas_to_process = selected_schemas or response_schemas

        for schema_name in schemas_to_process:
            if schema_name not in simplified_schemas:
                continue

            constraints[schema_name] = {}
            schema_properties = simplified_schemas[schema_name]

            for property_name, property_value in schema_properties.items():
                if not has_description(property_value):
                    continue

                constraint = ResponsePropertyConstraint(
                    schema_name=schema_name,
                    property_name=property_name,
                    data_type=extract_data_type_from_field(property_value),
                    description=extract_description_from_field(property_value) or "",
                )

                # Check cache first
                cached_result = self.find_cached_validation(constraint)
                if cached_result and cached_result.status == ConstraintStatus.VALID:
                    constraints[schema_name][property_name] = constraint.description
                    continue
                elif cached_result and cached_result.status == ConstraintStatus.INVALID:
                    continue

                # Validate constraint with LLM
                if self._validate_property_constraint(constraint):
                    constraints[schema_name][property_name] = constraint.description

                    # Cache result
                    validation_item = ConstraintValidationItem(
                        identifier=[constraint.property_name, property_value],
                        status=ConstraintStatus.VALID,
                    )
                    self.validation_cache.append(validation_item)
                else:
                    validation_item = ConstraintValidationItem(
                        identifier=[constraint.property_name, property_value],
                        status=ConstraintStatus.INVALID,
                    )
                    self.validation_cache.append(validation_item)

        return constraints

    def _validate_property_constraint(
        self, constraint: ResponsePropertyConstraint
    ) -> bool:
        """
        Validate if a property constraint is meaningful using LLM.

        Args:
            constraint: Property constraint to validate

        Returns:
            True if constraint is valid
        """
        try:
            # Generate observation
            observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                attribute=constraint.property_name,
                data_type=constraint.data_type,
                description=constraint.description,
                param_schema="",
            )

            observation_response = call_llm(observation_prompt)

            # Confirm constraint
            confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                attribute=constraint.property_name,
                data_type=constraint.data_type,
                description_observation=observation_response,
                description=constraint.description,
                param_schema="",
            )

            confirmation_response = call_llm(confirmation_prompt)
            confirmation = extract_llm_answer(confirmation_response)

            return confirmation == "yes"

        except Exception as e:
            print(f"Error validating constraint for {constraint.property_name}: {e}")
            return False

    def get_validation_cache_data(self) -> List[List]:
        """Get validation cache data for persistence."""
        return [[item.identifier, item.status.value] for item in self.validation_cache]
