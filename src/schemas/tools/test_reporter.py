# schemas/tools/test_execution_reporter.py

from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


class TestStatus(str, Enum):
    """Status of a test or validation."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class ValidationResult(BaseModel):
    """Result of a validation script execution."""

    script_id: str
    script_name: str
    status: TestStatus
    message: Optional[str] = None
    validation_code: Optional[str] = None  # Include the validation code
    script_type: Optional[str] = None  # Add script_type field


class TestCaseResult(BaseModel):
    """Result of a test case execution."""

    test_case_id: str
    test_case_name: str
    status: TestStatus
    elapsed_time: float
    request: Dict[str, Any]
    response: Dict[str, Any]
    validation_results: List[ValidationResult]
    message: Optional[str] = None
    test_data: Optional[Dict[str, Any]] = None


class TestSummary(BaseModel):
    """Summary statistics for a test report."""

    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int = 0
    success_rate: float  # percentage


class TestReport(BaseModel):
    """Complete test execution report for an endpoint."""

    id: str
    api_name: str
    api_version: str
    endpoint_name: str
    endpoint_path: str
    endpoint_method: str
    summary: TestSummary
    test_case_results: List[TestCaseResult]
    started_at: datetime
    finished_at: datetime
    total_time: float  # seconds


class TestReporterInput(BaseModel):
    """Input for TestExecutionReporterTool."""

    api_name: str
    api_version: str
    endpoint_name: str
    endpoint_path: str
    endpoint_method: str
    test_case_results: List[TestCaseResult]
    started_at: datetime
    finished_at: datetime


class TestReporterOutput(BaseModel):
    """Output from TestExecutionReporterTool."""

    report: TestReport
