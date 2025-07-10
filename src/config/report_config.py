# config/report_config.py

"""
Configuration settings for comprehensive reporting system.
This module provides centralized configuration for report generation,
file naming conventions, and output structure.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ReportingConfig:
    """Configuration for comprehensive test reporting."""

    # Base directories
    BASE_OUTPUT_DIR: str = "test_reports"
    LOGS_DIR: str = "logs"
    CACHE_DIR: str = "cache"

    # Timestamp format for report directories
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"

    # Report structure
    CONSTRAINTS_SUBDIR: str = "constraints"
    TEST_DATA_SUBDIR: str = "test_data"
    TEST_EXECUTION_SUBDIR: str = "test_execution"
    VALIDATION_SCRIPTS_SUBDIR: str = "validation_scripts"
    SUMMARY_SUBDIR: str = "summary"

    # File naming conventions
    CONSTRAINTS_FILE: str = "constraints.json"
    CONSTRAINTS_SUMMARY_FILE: str = "constraints_summary.md"
    TEST_DATA_FILE: str = "test_data.json"
    TEST_DATA_SUMMARY_FILE: str = "test_data_summary.md"
    VALIDATION_SCRIPTS_FILE: str = "validation_scripts.json"
    EXECUTION_RESULTS_FILE: str = "execution_results.json"
    EXECUTION_SUMMARY_FILE: str = "execution_summary.md"
    OVERALL_SUMMARY_FILE: str = "overall_summary.json"
    OVERALL_SUMMARY_MD_FILE: str = "overall_summary.md"
    LEGACY_SUMMARY_FILE: str = "legacy_summary.json"

    # Report generation options
    INCLUDE_VERBOSE_DETAILS: bool = True
    SAVE_RAW_DATA: bool = True
    CREATE_HUMAN_READABLE: bool = True
    SAVE_INDIVIDUAL_SCRIPTS: bool = True
    INCLUDE_FAILED_CASES_SEPARATELY: bool = True

    # Performance settings
    MAX_CONCURRENT_REPORTS: int = 5
    REPORT_TIMEOUT_SECONDS: int = 300

    # Content limits
    MAX_RESPONSE_BODY_SIZE: int = 1024 * 1024  # 1MB
    MAX_REQUEST_BODY_SIZE: int = 512 * 1024  # 512KB
    MAX_ERROR_MESSAGE_LENGTH: int = 10000

    # Validation script storage
    INDIVIDUAL_SCRIPTS_SUBDIR: str = "individual_scripts"
    SCRIPT_FILE_EXTENSION: str = ".py"

    # Markdown formatting
    MAX_CODE_BLOCK_LINES: int = 100
    INCLUDE_EXECUTION_TIMES: bool = True
    INCLUDE_STACK_TRACES: bool = False  # For production

    @classmethod
    def create_from_dict(cls, config_dict: Dict[str, Any]) -> "ReportingConfig":
        """Create ReportingConfig from dictionary."""
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key.upper()):
                setattr(config, key.upper(), value)
        return config

    def get_base_output_path(self) -> Path:
        """Get the base output path as a Path object."""
        return Path(self.BASE_OUTPUT_DIR)

    def get_logs_path(self) -> Path:
        """Get the logs directory path as a Path object."""
        return Path(self.LOGS_DIR)

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.get_base_output_path(),
            self.get_logs_path(),
            Path(self.CACHE_DIR),
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_endpoint_safe_name(
        self, method: str, path: str, name: Optional[str] = None
    ) -> str:
        """
        Create a safe filename from endpoint information.

        Args:
            method: HTTP method
            path: Endpoint path
            name: Optional endpoint name

        Returns:
            Safe filename string
        """
        if name:
            safe_name = f"{method.upper()}_{name}"
        else:
            safe_name = f"{method.upper()}_{path}"

        # Remove/replace unsafe characters
        unsafe_chars = '/\\:*?"<>|{}'
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, "_")

        # Remove multiple underscores
        while "__" in safe_name:
            safe_name = safe_name.replace("__", "_")

        # Remove leading/trailing underscores
        safe_name = safe_name.strip("_")

        return safe_name

    def get_report_structure(self, base_dir: str) -> Dict[str, str]:
        """
        Get the complete report directory structure.

        Args:
            base_dir: Base directory for the report

        Returns:
            Dictionary mapping structure names to paths
        """
        base_path = Path(base_dir)

        return {
            "base": str(base_path),
            "constraints": str(base_path / self.CONSTRAINTS_SUBDIR),
            "test_data": str(base_path / self.TEST_DATA_SUBDIR),
            "test_execution": str(base_path / self.TEST_EXECUTION_SUBDIR),
            "validation_scripts": str(base_path / self.VALIDATION_SCRIPTS_SUBDIR),
            "summary": str(base_path / self.SUMMARY_SUBDIR),
        }


# Default configuration instance
DEFAULT_CONFIG = ReportingConfig()


def get_config(custom_config: Optional[Dict[str, Any]] = None) -> ReportingConfig:
    """
    Get reporting configuration, optionally customized.

    Args:
        custom_config: Optional dictionary of custom configuration values

    Returns:
        ReportingConfig instance
    """
    if custom_config:
        return ReportingConfig.create_from_dict(custom_config)
    return DEFAULT_CONFIG


# Magic numbers and strings - centralized constants
class ReportConstants:
    """Centralized constants for reporting system."""

    # Status indicators
    STATUS_PASS = "PASS"
    STATUS_FAIL = "FAIL"
    STATUS_ERROR = "ERROR"
    STATUS_SKIP = "SKIP"

    # Report sections
    SECTION_CONSTRAINTS = "constraints"
    SECTION_TEST_DATA = "test_data"
    SECTION_VALIDATION_SCRIPTS = "validation_scripts"
    SECTION_EXECUTION = "execution"
    SECTION_SUMMARY = "summary"

    # Constraint types
    CONSTRAINT_REQUEST_PARAM = "request_param"
    CONSTRAINT_REQUEST_BODY = "request_body"
    CONSTRAINT_RESPONSE_PROPERTY = "response_property"
    CONSTRAINT_REQUEST_RESPONSE = "request_response"

    # Script types
    SCRIPT_TYPE_REQUEST_PARAM = "request_param"
    SCRIPT_TYPE_REQUEST_BODY = "request_body"
    SCRIPT_TYPE_RESPONSE_PROPERTY = "response_property"
    SCRIPT_TYPE_REQUEST_RESPONSE = "request_response"

    # Validation results
    VALIDATION_PASSED = "passed"
    VALIDATION_FAILED = "failed"
    VALIDATION_ERROR = "error"

    # File encoding
    ENCODING_UTF8 = "utf-8"

    # HTTP status code ranges
    STATUS_SUCCESS_MIN = 200
    STATUS_SUCCESS_MAX = 299
    STATUS_CLIENT_ERROR_MIN = 400
    STATUS_CLIENT_ERROR_MAX = 499
    STATUS_SERVER_ERROR_MIN = 500
    STATUS_SERVER_ERROR_MAX = 599

    # Default values
    DEFAULT_TIMEOUT = 30
    DEFAULT_CONCURRENT_REQUESTS = 10
    DEFAULT_TEST_CASE_COUNT = 2

    # Report quality thresholds
    GOOD_SUCCESS_RATE_THRESHOLD = 90.0
    ACCEPTABLE_SUCCESS_RATE_THRESHOLD = 70.0

    @classmethod
    def is_success_status(cls, status_code: int) -> bool:
        """Check if status code indicates success."""
        return cls.STATUS_SUCCESS_MIN <= status_code <= cls.STATUS_SUCCESS_MAX

    @classmethod
    def is_client_error_status(cls, status_code: int) -> bool:
        """Check if status code indicates client error."""
        return cls.STATUS_CLIENT_ERROR_MIN <= status_code <= cls.STATUS_CLIENT_ERROR_MAX

    @classmethod
    def is_server_error_status(cls, status_code: int) -> bool:
        """Check if status code indicates server error."""
        return cls.STATUS_SERVER_ERROR_MIN <= status_code <= cls.STATUS_SERVER_ERROR_MAX

    @classmethod
    def get_success_rate_quality(cls, success_rate: float) -> str:
        """Get quality assessment for success rate."""
        if success_rate >= cls.GOOD_SUCCESS_RATE_THRESHOLD:
            return "GOOD"
        elif success_rate >= cls.ACCEPTABLE_SUCCESS_RATE_THRESHOLD:
            return "ACCEPTABLE"
        else:
            return "POOR"
