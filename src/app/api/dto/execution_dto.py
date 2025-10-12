# app/api/dto/execution_dto.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from schemas.core.pagination import PaginationMetadata

from schemas.core.execution_history import ExecutionStatus


class ExecuteTestRequest(BaseModel):
    """Request for executing tests."""

    base_url: str = Field(..., description="Base URL for API calls")
    test_data_ids: Optional[List[str]] = Field(
        None, description="Optional list of specific test data IDs to use"
    )
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=300)
    headers: Optional[Dict[str, str]] = Field(
        None, description="Additional headers to include in requests"
    )


class TestCaseExecutionResultResponse(BaseModel):
    """Response for a single test case execution result."""

    test_data_id: str = Field(..., description="ID of the test data used")
    test_data_name: str = Field(..., description="Name of the test data")
    request_sent: Dict[str, Any] = Field(..., description="Request that was sent")
    response_received: Dict[str, Any] = Field(
        ..., description="Response that was received"
    )
    execution_status: ExecutionStatus = Field(
        ..., description="Status of the execution"
    )
    validation_results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Validation script results"
    )
    execution_time_ms: float = Field(0.0, description="Execution time in milliseconds")
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    passed: bool = Field(False, description="Whether the test case passed")


class ExecuteTestResponse(BaseModel):
    """Response for test execution."""

    execution_id: str = Field(..., description="ID of the execution")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
    base_url: str = Field(..., description="Base URL used for testing")
    overall_status: ExecutionStatus = Field(..., description="Overall execution status")
    total_tests: int = Field(0, description="Total number of test cases executed")
    passed_tests: int = Field(0, description="Number of test cases that passed")
    failed_tests: int = Field(0, description="Number of test cases that failed")
    success_rate: float = Field(0.0, description="Success rate (0.0 to 1.0)")
    total_execution_time_ms: float = Field(
        0.0, description="Total execution time in milliseconds"
    )
    started_at: datetime = Field(..., description="When execution started")
    completed_at: Optional[datetime] = Field(
        None, description="When execution completed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    execution_results: List[TestCaseExecutionResultResponse] = Field(
        default_factory=list, description="Individual test case results"
    )


class ExecutionHistoryResponse(BaseModel):
    """Response for execution history item."""

    id: str = Field(..., description="ID of the execution")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
    base_url: str = Field(..., description="Base URL used for testing")
    overall_status: ExecutionStatus = Field(..., description="Overall execution status")
    total_tests: int = Field(0, description="Total number of test cases")
    passed_tests: int = Field(0, description="Number of passed test cases")
    failed_tests: int = Field(0, description="Number of failed test cases")
    success_rate: float = Field(0.0, description="Success rate")
    total_execution_time_ms: float = Field(
        0.0, description="Total execution time in milliseconds"
    )
    started_at: datetime = Field(..., description="When execution started")
    completed_at: Optional[datetime] = Field(
        None, description="When execution completed"
    )
    test_data_used: List[str] = Field(
        default_factory=list, description="IDs of test data items used"
    )


class ExecutionHistoryListResponse(BaseModel):
    """Response for execution history list."""

    executions: List[ExecutionHistoryResponse] = Field(
        default_factory=list, description="List of executions"
    )
    pagination: PaginationMetadata


class ExecutionDetailResponse(BaseModel):
    """Response for detailed execution information."""

    id: str = Field(..., description="ID of the execution")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
    base_url: str = Field(..., description="Base URL used for testing")
    overall_status: ExecutionStatus = Field(..., description="Overall execution status")
    total_tests: int = Field(0, description="Total number of test cases")
    passed_tests: int = Field(0, description="Number of passed test cases")
    failed_tests: int = Field(0, description="Number of failed test cases")
    success_rate: float = Field(0.0, description="Success rate")
    total_execution_time_ms: float = Field(
        0.0, description="Total execution time in milliseconds"
    )
    started_at: datetime = Field(..., description="When execution started")
    completed_at: Optional[datetime] = Field(
        None, description="When execution completed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    test_data_used: List[str] = Field(
        default_factory=list, description="IDs of test data items used"
    )
    execution_results: List[TestCaseExecutionResultResponse] = Field(
        default_factory=list, description="Individual test case results"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )
