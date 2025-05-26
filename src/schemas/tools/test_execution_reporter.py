# schemas/tools/test_execution_reporter.py

from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class ValidationResult(BaseModel):
    """Result of a single validation script."""

    script_id: str
    script_name: str
    status: TestStatus
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TestCaseResult(BaseModel):
    """Result of a single test case."""

    test_case_id: str
    test_case_name: str
    status: TestStatus
    elapsed_time: float
    request: Dict[str, Any]
    response: Dict[str, Any]
    validation_results: List[ValidationResult]
    message: Optional[str] = None


class TestExecutionReporterInput(BaseModel):
    """Input for TestExecutionReporterTool."""

    api_name: str
    api_version: str
    endpoint_name: str
    endpoint_path: str
    endpoint_method: str
    test_case_results: List[TestCaseResult]
    started_at: datetime
    finished_at: datetime


class TestSummary(BaseModel):
    """Summary statistics for test results."""

    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    success_rate: float  # percentage


class TestReport(BaseModel):
    """Complete test report."""

    api_name: str
    api_version: str
    endpoint_name: str
    endpoint_path: str
    endpoint_method: str
    summary: TestSummary
    test_case_results: List[TestCaseResult]
    started_at: datetime
    finished_at: datetime
    total_time: float


class TestExecutionReporterOutput(BaseModel):
    """Output from TestExecutionReporterTool."""

    report: TestReport
    report_path: Optional[str] = None  # If saved to file
