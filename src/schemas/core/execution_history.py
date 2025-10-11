# schemas/core/execution_history.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestCaseExecutionResult(BaseModel):
    """Result of a single test case execution."""

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


class ExecutionHistory(BaseModel):
    """Complete execution history record."""

    id: str = Field(..., description="Unique identifier for execution")
    endpoint_id: str = Field(..., description="ID of the endpoint that was tested")
    endpoint_name: str = Field(..., description="Name of the endpoint that was tested")
    base_url: str = Field(..., description="Base URL used for testing")
    test_data_used: List[str] = Field(
        default_factory=list, description="IDs of test data items used"
    )
    execution_results: List[TestCaseExecutionResult] = Field(
        default_factory=list, description="Results of test case executions"
    )
    overall_status: ExecutionStatus = Field(
        ExecutionStatus.PENDING, description="Overall execution status"
    )
    total_tests: int = Field(0, description="Total number of test cases executed")
    passed_tests: int = Field(0, description="Number of test cases that passed")
    failed_tests: int = Field(0, description="Number of test cases that failed")
    success_rate: float = Field(0.0, description="Success rate (0.0 to 1.0)")
    total_execution_time_ms: float = Field(
        0.0, description="Total execution time in milliseconds"
    )
    started_at: datetime = Field(
        default_factory=datetime.now, description="When execution started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When execution completed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )


class ExecutionSummary(BaseModel):
    """Summary of execution results."""

    execution_id: str = Field(..., description="ID of the execution")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    endpoint_name: str = Field(..., description="Name of the endpoint")
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
