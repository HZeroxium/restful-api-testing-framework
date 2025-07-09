# config/prompts/__init__.py

"""
Prompt templates for the API Testing Framework.

This module contains all LLM prompt templates organized by their purpose.
"""

from .constraint_miner import *
from .test_data_generator import *
from .test_script_generator import *

__all__ = [
    # Constraint miner prompts
    "REQUEST_PARAM_CONSTRAINT_PROMPT",
    "REQUEST_BODY_CONSTRAINT_PROMPT",
    "RESPONSE_PROPERTY_CONSTRAINT_PROMPT",
    "REQUEST_RESPONSE_CONSTRAINT_PROMPT",
    # Test data generator prompts
    "TEST_DATA_GENERATION_PROMPT",
    # Test script generator prompts
    "REQUEST_PARAM_VALIDATION_PROMPT",
    "REQUEST_BODY_VALIDATION_PROMPT",
    "RESPONSE_PROPERTY_VALIDATION_PROMPT",
    "REQUEST_RESPONSE_VALIDATION_PROMPT",
]
