"""
Input parameter constraint extractor.
"""

from typing import Dict, List, Optional

from schemas.constraint import (
    ParameterConstraint,
    ConstraintStatus,
    ParameterLocation,
    ConstraintValidationItem,
)
from utils.constraint_utils import (
    extract_description_from_field,
    extract_data_type_from_field,
    has_description,
)
from config.prompts.constraint_extraction import DESCRIPTION_OBSERVATION_PROMPT
from utils.gptcall import call_llm


class InputParameterExtractor:
    """Extracts constraints from input parameters."""

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
        self, parameter: ParameterConstraint
    ) -> Optional[ConstraintValidationItem]:
        """Find cached validation result for a parameter."""
        identifier = [
            parameter.parameter_name,
            f"{parameter.data_type} (description: {parameter.description})",
        ]

        for validation in self.validation_cache:
            if validation.identifier == identifier:
                return validation

        return None

    def extract_constraints(
        self,
        simplified_operations: Dict[str, Dict],
        operation_specs: Dict[str, Dict],
        selected_operations: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Extract input parameter constraints from operations.

        Args:
            simplified_operations: Simplified operation specifications
            operation_specs: Full operation specifications
            selected_operations: Optional list of operations to process

        Returns:
            Dictionary of input parameter constraints
        """
        constraints = {}
        operations_to_process = selected_operations or list(
            simplified_operations.keys()
        )

        for operation in operations_to_process:
            constraints[operation] = {
                ParameterLocation.PARAMETERS.value: {},
                ParameterLocation.REQUEST_BODY.value: {},
            }

            operation_spec = simplified_operations.get(operation, {})

            for location in [
                ParameterLocation.PARAMETERS,
                ParameterLocation.REQUEST_BODY,
            ]:
                location_spec = operation_spec.get(location.value, {})
                if not location_spec:
                    continue

                for param_name, param_value in location_spec.items():
                    if not has_description(param_value):
                        continue

                    constraint = ParameterConstraint(
                        operation=operation,
                        location=location,
                        parameter_name=param_name,
                        data_type=extract_data_type_from_field(param_value),
                        description=extract_description_from_field(param_value) or "",
                    )

                    # Check cache first
                    cached_result = self.find_cached_validation(constraint)
                    if cached_result and cached_result.status == ConstraintStatus.VALID:
                        constraints[operation][location.value][param_name] = param_value
                        continue
                    elif (
                        cached_result
                        and cached_result.status == ConstraintStatus.INVALID
                    ):
                        continue

                    # Validate constraint
                    if self._validate_parameter_constraint(constraint, operation_specs):
                        constraints[operation][location.value][param_name] = param_value

                        # Cache result
                        validation_item = ConstraintValidationItem(
                            identifier=[constraint.parameter_name, param_value],
                            status=ConstraintStatus.VALID,
                        )
                        self.validation_cache.append(validation_item)
                    else:
                        validation_item = ConstraintValidationItem(
                            identifier=[constraint.parameter_name, param_value],
                            status=ConstraintStatus.INVALID,
                        )
                        self.validation_cache.append(validation_item)

        return constraints

    def _validate_parameter_constraint(
        self, constraint: ParameterConstraint, operation_specs: Dict[str, Dict]
    ) -> bool:
        """
        Validate if a parameter constraint is meaningful.

        Args:
            constraint: Parameter constraint to validate
            operation_specs: Full operation specifications

        Returns:
            True if constraint is valid
        """
        # Get parameter schema if available
        param_schema = self._get_parameter_schema(constraint, operation_specs)

        # For now, we'll accept all parameters with descriptions as having constraints
        # This can be enhanced with LLM validation if needed
        return True

    def _get_parameter_schema(
        self, constraint: ParameterConstraint, operation_specs: Dict[str, Dict]
    ) -> Dict:
        """Get the schema for a parameter from operation specs."""
        operation_path = constraint.operation.split("-", 1)[1]
        operation_method = constraint.operation.split("-")[0]

        full_spec = (
            operation_specs.get("paths", {})
            .get(operation_path, {})
            .get(operation_method, {})
        )
        location_specs = full_spec.get(constraint.location.value, [])

        if isinstance(location_specs, list):
            for spec in location_specs:
                if (
                    isinstance(spec, dict)
                    and spec.get("name") == constraint.parameter_name
                ):
                    return spec.get("schema", {})

        return {}

    def get_validation_cache_data(self) -> List[List]:
        """Get validation cache data for persistence."""
        return [[item.identifier, item.status.value] for item in self.validation_cache]
