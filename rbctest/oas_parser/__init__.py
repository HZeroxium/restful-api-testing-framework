"""
OpenAPI Parser module for parsing and processing OpenAPI specifications.

This module has been refactored to consolidate functionality into fewer files:
- parser.py: Main OpenAPI parser implementation
- schema.py: Schema processing utilities
- operations.py: Operation processing utilities
- loaders.py: Spec loading utilities
- helpers.py: Shared utility functions

The following files have been deprecated and their functionality moved:
- schema_parser.py -> schema.py
- response_utils.py -> operations.py
- param_utils.py -> operations.py
- openapi_simplifier.py -> operations.py
- operation_utils.py -> operations.py
"""

# Re-export the main classes and functions
from .parser import OpenAPIParser
from .schema import SchemaProcessor
from .operations import OperationProcessor, extract_operations, is_success_status_code
from .loaders import load_openapi, load_spec_from_url, get_ref
from .helpers import find_object_with_key, extract_ref_values

# For backwards compatibility
# These imports ensure that code importing from the old files will still work
import warnings


# Set up migration warning
def _warn_migration(old_file, new_file):
    warnings.warn(
        f"Importing from {old_file} is deprecated and will be removed in a future version. "
        f"Import from rbctest.oas_parser.{new_file} instead.",
        DeprecationWarning,
        stacklevel=2,
    )


# Create migration helpers for deprecated files
class _SchemaMigration:
    def __getattr__(self, name):
        _warn_migration("schema_parser", "schema")
        from .schema import SchemaProcessor

        schema_processor = SchemaProcessor({})  # Empty spec for compatibility
        return getattr(schema_processor, name)


class _OperationMigration:
    def __getattr__(self, name):
        _warn_migration("operation_utils", "operations")
        from .operations import (
            extract_operations,
            is_success_status_code,
            contains_required_parameters,
        )

        if name == "extract_operations":
            return extract_operations
        if name == "is_success_status_code":
            return is_success_status_code
        if name == "contains_required_parameters":
            return contains_required_parameters
        raise AttributeError(f"module 'operation_utils' has no attribute '{name}'")


class _ResponseMigration:
    def __getattr__(self, name):
        _warn_migration("response_utils", "operations")
        if name == "get_response_body_name_and_type":
            from .operations import OperationProcessor

            op = OperationProcessor({})  # Empty spec for compatibility
            return op.get_response_body_name_and_type
        if name == "get_main_response_schemas_of_operation":
            from .operations import OperationProcessor

            op = OperationProcessor({})
            return op.get_main_response_schemas_of_operation
        if name == "get_relevent_response_schemas_of_operation":
            from .operations import OperationProcessor

            op = OperationProcessor({})
            return op.get_relevant_schemas_of_operation
        raise AttributeError(f"module 'response_utils' has no attribute '{name}'")


class _SimplifierMigration:
    def __getattr__(self, name):
        _warn_migration("openapi_simplifier", "operations")
        if name == "simplify_openapi":
            from .operations import OperationProcessor

            op = OperationProcessor({})
            return op.simplify_openapi
        raise AttributeError(f"module 'openapi_simplifier' has no attribute '{name}'")


# Create migration modules
schema_parser = _SchemaMigration()
operation_utils = _OperationMigration()
response_utils = _ResponseMigration()
openapi_simplifier = _SimplifierMigration()
