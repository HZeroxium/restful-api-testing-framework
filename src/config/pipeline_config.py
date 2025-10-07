# config/pipeline_config.py

"""
Configuration settings for the API Testing Pipeline.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the main testing pipeline."""

    # Test execution settings
    DEFAULT_TEST_CASE_COUNT: int = 2
    MIN_TEST_CASE_COUNT: int = 1
    MAX_TEST_CASE_COUNT: int = 10

    # Data generation settings
    INCLUDE_VALID_DATA: bool = True
    INCLUDE_INVALID_DATA: bool = True
    INCLUDE_MISMATCH_DATA: bool = False

    # Constraint mining settings
    ENABLE_CONSTRAINT_CACHING: bool = True
    CONSTRAINT_MINING_TIMEOUT: int = 60  # seconds

    # Script generation settings
    ENABLE_SCRIPT_CACHING: bool = True
    SCRIPT_GENERATION_TIMEOUT: int = 30  # seconds

    # Test execution settings
    DEFAULT_REQUEST_TIMEOUT: int = 30  # seconds
    MAX_CONCURRENT_REQUESTS: int = 10
    ENABLE_PARALLEL_EXECUTION: bool = True

    # Validation settings
    VALIDATION_SCRIPT_TIMEOUT: int = 10  # seconds
    ENABLE_STRICT_VALIDATION: bool = True

    # Output settings
    OUTPUT_BASE_PATH: str = "output"
    ENABLE_DETAILED_REPORTS: bool = True
    SAVE_INTERMEDIATE_RESULTS: bool = True

    # Status code mappings for invalid data
    INVALID_DATA_STATUS_CODES: List[int] = [400, 401, 403, 404, 422, 500]

    # Error handling
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 1

    # Logging settings
    ENABLE_VERBOSE_LOGGING: bool = False
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


@dataclass
class ConstraintMiningConfig:
    """Configuration for constraint mining operations."""

    # Constraint types to mine
    ENABLED_CONSTRAINT_TYPES: List[str] = None

    # LLM settings
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000

    # Chunking settings for large responses
    RESPONSE_CHUNK_THRESHOLD: int = 20
    MAX_RESPONSE_CHUNK_SIZE: int = 15

    # Fallback settings
    ENABLE_FALLBACK_CONSTRAINTS: bool = True
    FALLBACK_CONSTRAINT_SEVERITY: str = "warning"

    def __post_init__(self):
        if self.ENABLED_CONSTRAINT_TYPES is None:
            self.ENABLED_CONSTRAINT_TYPES = [
                "REQUEST_PARAM",
                "REQUEST_BODY",
                "RESPONSE_PROPERTY",
                "REQUEST_RESPONSE",
            ]


@dataclass
class ScriptGenerationConfig:
    """Configuration for validation script generation."""

    # Script types to generate
    ENABLED_SCRIPT_TYPES: List[str] = None

    # LLM settings
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1500

    # Script execution settings
    SCRIPT_TIMEOUT: int = 10  # seconds
    ENABLE_SCRIPT_CACHING: bool = True

    # Validation settings
    STANDARDIZE_FUNCTION_SIGNATURE: bool = True
    REQUIRED_FUNCTION_PARAMS: List[str] = None

    # Fallback settings
    ENABLE_FALLBACK_SCRIPTS: bool = True
    FALLBACK_SCRIPT_BEHAVIOR: str = "pass"  # "pass", "fail", "skip"

    def __post_init__(self):
        if self.ENABLED_SCRIPT_TYPES is None:
            self.ENABLED_SCRIPT_TYPES = [
                "REQUEST_PARAM",
                "REQUEST_BODY",
                "RESPONSE_PROPERTY",
                "REQUEST_RESPONSE",
            ]

        if self.REQUIRED_FUNCTION_PARAMS is None:
            self.REQUIRED_FUNCTION_PARAMS = ["request", "response"]


@dataclass
class TestDataConfig:
    """Configuration for test data generation and verification."""

    # Data generation settings
    GENERATE_VALID_DATA: bool = True
    GENERATE_INVALID_DATA: bool = True
    GENERATE_EDGE_CASES: bool = True

    # Data verification settings
    ENABLE_DATA_VERIFICATION: bool = True
    STRICT_VERIFICATION: bool = True
    FILTER_MISMATCHED_DATA: bool = True

    # LLM settings for data generation
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.3  # Higher temperature for more diverse data
    LLM_MAX_TOKENS: int = 1500

    # Realistic data settings
    USE_REALISTIC_VALUES: bool = True
    REALISTIC_DATA_PATTERNS: Dict[str, Any] = None

    def __post_init__(self):
        if self.REALISTIC_DATA_PATTERNS is None:
            self.REALISTIC_DATA_PATTERNS = {
                "email": ["user@example.com", "test@domain.org", "admin@company.net"],
                "phone": ["+1-555-123-4567", "+44-20-7123-4567", "+33-1-42-34-56-78"],
                "country": ["US", "UK", "FR", "DE", "JP", "CA"],
                "currency": ["USD", "EUR", "GBP", "JPY", "CAD"],
                "date_format": "%Y-%m-%d",
                "datetime_format": "%Y-%m-%dT%H:%M:%S.%fZ",
            }


# Global configuration instances
PIPELINE_CONFIG = PipelineConfig()
CONSTRAINT_MINING_CONFIG = ConstraintMiningConfig()
SCRIPT_GENERATION_CONFIG = ScriptGenerationConfig()
TEST_DATA_CONFIG = TestDataConfig()


def get_config(config_type: str) -> Any:
    """Get configuration by type."""
    config_map = {
        "pipeline": PIPELINE_CONFIG,
        "constraint_mining": CONSTRAINT_MINING_CONFIG,
        "script_generation": SCRIPT_GENERATION_CONFIG,
        "test_data": TEST_DATA_CONFIG,
    }

    return config_map.get(config_type.lower())


def update_config(config_type: str, **kwargs) -> None:
    """Update configuration settings."""
    config = get_config(config_type)
    if config:
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(
                    f"Configuration key '{key}' not found in {config_type} config"
                )
    else:
        raise ValueError(f"Configuration type '{config_type}' not found")
