# schemas/tools/test_executor.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .test_suite_generator import TestSuite


class ValidationScriptResult(BaseModel):
    """Result of a single validation script execution."""

    script_id: str = Field(..., description="ID of the validation script")
    script_name: str = Field(..., description="Name of the validation script")
    passed: bool = Field(..., description="Whether the script passed")
    result: Optional[str] = Field(None, description="Script output/result")
    error: Optional[str] = Field(None, description="Error message if script failed")
    description: Optional[str] = Field(None, description="Script description")
    execution_success: bool = Field(
        True, description="Whether script executed successfully"
    )
    execution_time: Optional[float] = Field(
        None, description="Script execution time in seconds"
    )


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
    save_results: bool = Field(
        default=True, description="Whether to save execution results to files"
    )
    output_directory: Optional[str] = Field(
        default=None,
        description="Directory to save results (default: test_reports/{timestamp})",
    )
    comprehensive_report_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Comprehensive report data from test generation pipeline",
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
    validation_results: List[ValidationScriptResult] = Field(default_factory=list)
    request_details: Dict[str, Any] = Field(default_factory=dict)
    execution_timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    expected_status_code: Optional[int] = Field(
        None, description="Expected status code"
    )
    status_code_passed: Optional[bool] = Field(
        None, description="Whether status code matched expectation"
    )
    validation_passed: Optional[bool] = Field(
        None, description="Whether all validations passed"
    )


class TestSuiteExecutionResult(BaseModel):
    """Result of executing a test suite."""

    test_suite_id: str
    test_suite_name: str
    endpoint_path: Optional[str] = Field(
        None, description="Endpoint path for this test suite"
    )
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time: float
    test_case_results: List[TestCaseExecutionResult]
    execution_timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    total_validation_scripts: int = Field(
        0, description="Total number of validation scripts executed"
    )
    passed_validation_scripts: int = Field(
        0, description="Number of validation scripts that passed"
    )
    failed_validation_scripts: int = Field(
        0, description="Number of validation scripts that failed"
    )


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
    execution_timestamp: datetime = Field(default_factory=datetime.now)
    output_directory: Optional[str] = Field(
        None, description="Directory where results were saved"
    )
    saved_files: List[str] = Field(
        default_factory=list, description="List of saved result files"
    )
