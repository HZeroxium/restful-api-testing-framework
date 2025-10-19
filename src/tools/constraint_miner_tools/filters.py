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


def is_trivial_constraint(constraint: ApiConstraint) -> bool:
    """
    Returns True if the constraint is trivial and should be dropped.

    Heuristics:
    - Any pure type/required/format/enum checks on params/properties
    - Basic array/object structure assertions
    - Presence of common fields (id/name/slug) without cross-field logic
    - For request/response property types, if only structure/type is asserted
    """
    try:
        ctype = (
            constraint.type.value
            if hasattr(constraint.type, "value")
            else str(constraint.type)
        )
        ctype = ctype.lower()
        details = getattr(constraint, "details", {}) or {}
        source = str(getattr(constraint, "source", "")).lower()

        # If it's a request_response constraint, it's rarely trivial; keep by default
        if ctype == "request_response":
            return False

        # Drop trivial type/required/structure-only assertions
        if _is_structure_only(details):
            return True

        # Drop obvious field presence requirements without any correlation
        if _is_obvious_field_presence(details):
            return True

        # If description explicitly talks only about "must be string/number/boolean"
        desc = (constraint.description or "").lower()
        if any(
            token in desc for token in ["must be of type", "should be of type", "type "]
        ):
            return True

        # Keep others by default (possible complex rules)
        return False
    except Exception:
        # Be conservative on errors: keep the constraint
        return False
