# schemas/tools/test_executor.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from schemas.tools.test_case_generator import TestCase
from schemas.tools.test_suite_generator import TestSuite


class TestExecutorInput(BaseModel):
    """Input for TestExecutorTool."""

    test_suites: List[TestSuite] = Field(..., description="Test suites to execute")
    base_url: str = Field(..., description="Base URL for API endpoints")
    timeout: Optional[int] = Field(
        default=30, description="Timeout for HTTP requests in seconds"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Default headers to include in requests"
    )
    parallel_execution: bool = Field(
        default=True, description="Whether to execute tests in parallel"
    )
    max_concurrent_requests: int = Field(
        default=10, description="Maximum number of concurrent requests"
    )


class TestCaseExecutionResult(BaseModel):
    """Result of executing a single test case."""

    test_case_id: str
    test_case_name: str
    passed: bool
    status_code: int
    response_time: float
    response_body: Optional[Any] = None
    response_headers: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    request_details: Dict[str, Any] = Field(default_factory=dict)


class TestSuiteExecutionResult(BaseModel):
    """Result of executing a test suite."""

    test_suite_id: str
    test_suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time: float
    test_case_results: List[TestCaseExecutionResult]


class TestExecutorOutput(BaseModel):
    """Output from TestExecutorTool."""

    execution_summary: Dict[str, Any] = Field(
        ..., description="Summary of test execution"
    )
    test_suite_results: List[TestSuiteExecutionResult] = Field(
        ..., description="Results for each test suite"
    )
    total_execution_time: float = Field(
        ..., description="Total execution time in seconds"
    )
    overall_passed: bool = Field(..., description="Whether all tests passed")
