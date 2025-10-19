"""
Helper utilities for filtering trivial constraints from miner outputs.

We aggressively drop trivial/type/required/shape-only constraints and keep
only complex behavioral or cross-field/correlation rules.
"""

from typing import Any

from schemas.tools.constraint_miner import ApiConstraint


_TRIVIAL_TYPES = {
    "type",
    "format",
    "required",
    "enum",
}

_STRUCTURE_HINTS = {
    "array",
    "object",
    "items",
    "properties",
}

_TRIVIAL_FIELD_NAMES = {"id", "name", "slug"}


def _is_structure_only(details: dict[str, Any]) -> bool:
    if not isinstance(details, dict):
        return False
    rule = str(details.get("validation_rule", "")).lower()
    ctype = str(details.get("constraint_type", "")).lower()
    data_type = str(details.get("data_type", "")).lower()

    if rule in _TRIVIAL_TYPES or ctype in _TRIVIAL_TYPES:
        return True

    if any(h in rule for h in _STRUCTURE_HINTS):
        return True
    if any(h in ctype for h in _STRUCTURE_HINTS):
        return True
    if any(h in data_type for h in _STRUCTURE_HINTS):
        return True

    return False


def _is_obvious_field_presence(details: dict[str, Any]) -> bool:
    path = str(details.get("property_path", "")).lower()
    # Accept patterns like data[*].id, items[0].name, etc.
    for fname in _TRIVIAL_FIELD_NAMES:
        if f".{fname}" in path or path.endswith(fname):
            return True
    return False


def is_trivial_schema_constraint(constraint: ApiConstraint) -> bool:
    """
    Returns True if the constraint is a trivial schema/type constraint.

    Focuses on excluding basic datatype, structure, and format constraints
    that are already enforced by API frameworks.
    """
    try:
        ctype = (
            constraint.type.value
            if hasattr(constraint.type, "value")
            else str(constraint.type)
        )
        ctype = ctype.lower()
        details = getattr(constraint, "details", {}) or {}
        desc = (constraint.description or "").lower()

        # Always keep request_response constraints - they contain logical relationships
        if ctype == "request_response":
            return False

        # Drop basic type/format/required/structure constraints
        if _is_structure_only(details):
            return True

        # Drop obvious field presence without cross-field logic
        if _is_obvious_field_presence(details):
            return True

        # Drop pure datatype assertions
        if any(
            token in desc
            for token in [
                "must be of type",
                "should be of type",
                "type ",
                "must be string",
                "must be number",
                "must be boolean",
                "must be array",
                "must be object",
            ]
        ):
            return True

        # Drop response schema structure constraints
        if ctype in ["response_property"] and any(
            token in desc
            for token in [
                "response body must be",
                "response must contain",
                "must have property",
                "array of",
                "object representing",
                "must have an",
            ]
        ):
            return True

        return False
    except Exception:
        return False


def is_trivial_type_constraint(constraint: ApiConstraint) -> bool:
    """
    Returns True if the constraint is a trivial type constraint.

    Focuses on excluding basic parameter type constraints that are
    already enforced by OpenAPI spec validation.
    """
    try:
        ctype = (
            constraint.type.value
            if hasattr(constraint.type, "value")
            else str(constraint.type)
        )
        ctype = ctype.lower()
        details = getattr(constraint, "details", {}) or {}
        desc = (constraint.description or "").lower()

        # Keep request_response constraints
        if ctype == "request_response":
            return False

        # Drop basic parameter type constraints
        if ctype in ["request_param", "request_body"]:
            if any(
                token in desc
                for token in [
                    "must be of type",
                    "parameter must be",
                    "should be of type",
                    "must be string",
                    "must be number",
                    "must be boolean",
                ]
            ):
                return True

        # Drop trivial enum constraints without business logic
        if "enum" in details.get("constraint_type", "").lower():
            if not any(
                token in desc
                for token in ["depending on", "based on", "when", "if", "conditional"]
            ):
                return True

        return False
    except Exception:
        return False


def is_trivial_constraint(constraint: ApiConstraint) -> bool:
    """
    Returns True if the constraint is trivial and should be dropped.

    Enhanced to focus on logical constraints only, excluding:
    - Basic datatype/structure constraints
    - Trivial type/format/required checks
    - Response schema structure assertions
    - Parameter type constraints without business logic
    """
    try:
        # Apply both schema and type triviality checks
        if is_trivial_schema_constraint(constraint):
            return True

        if is_trivial_type_constraint(constraint):
            return True

        # Keep complex logical constraints
        return False
    except Exception:
        # Be conservative on errors: keep the constraint
        return False
