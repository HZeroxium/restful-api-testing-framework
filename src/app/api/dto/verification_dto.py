"""
DTOs for verification endpoints.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TestDataItem(BaseModel):
    """Single test data item for verification."""

    request_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Request parameters"
    )
    request_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Request headers"
    )
    request_body: Optional[Union[Dict[str, Any], str]] = Field(
        default=None, description="Request body"
    )
    expected_status_code: Optional[int] = Field(
        default=200, description="Expected HTTP status code"
    )
    # Additional fields for simplified input
    method: Optional[str] = Field(
        default=None,
        description="HTTP method (will be filled from endpoint if not provided)",
    )
    path: Optional[str] = Field(
        default=None,
        description="Request path (will be filled from endpoint if not provided)",
    )
    timeout: Optional[int] = Field(default=30, description="Request timeout in seconds")


class VerifyTestDataRequest(BaseModel):
    """Request for verifying test data."""

    test_data_items: List[TestDataItem] = Field(
        ..., description="List of test data items to verify"
    )
    timeout: Optional[int] = Field(
        default=30, description="Script execution timeout in seconds"
    )


class VerificationResult(BaseModel):
    """Result of a single validation script execution."""

    script_id: str = Field(..., description="ID of the validation script")
    script_type: str = Field(..., description="Type of validation script")
    passed: bool = Field(..., description="Whether the validation passed")
    error_message: Optional[str] = Field(
        default=None, description="Error message if validation failed"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Script execution time in seconds"
    )
    script_output: Optional[str] = Field(default=None, description="Raw script output")


class TestDataVerificationResult(BaseModel):
    """Verification result for a single test data item."""

    test_data_index: int = Field(..., description="Index of the test data item")
    overall_passed: bool = Field(..., description="Whether all validations passed")
    results: List[VerificationResult] = Field(
        default_factory=list, description="Individual script results"
    )
    total_execution_time: Optional[float] = Field(
        default=None, description="Total execution time"
    )


class VerifyTestDataResponse(BaseModel):
    """Response for test data verification."""

    endpoint_name: str = Field(..., description="Name of the endpoint being verified")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    total_test_data_items: int = Field(
        ..., description="Total number of test data items"
    )
    overall_passed: bool = Field(..., description="Whether all validations passed")
    verification_results: List[TestDataVerificationResult] = Field(
        default_factory=list, description="Results for each test data item"
    )
    total_execution_time: Optional[float] = Field(
        default=None, description="Total execution time"
    )


class RequestResponsePair(BaseModel):
    """Request-response pair for verification."""

    request: Dict[str, Any] = Field(
        ..., description="Request details (method, url, headers, params, body)"
    )
    response: Dict[str, Any] = Field(
        ..., description="Response details (status_code, headers, body)"
    )


class SimplifiedRequestResponsePair(BaseModel):
    """Simplified request-response pair for easier input."""

    # Request fields
    method: Optional[str] = Field(
        default=None,
        description="HTTP method (will be filled from endpoint if not provided)",
    )
    path: Optional[str] = Field(
        default=None,
        description="Request path (will be filled from endpoint if not provided)",
    )
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Request parameters"
    )
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Request headers"
    )
    body: Optional[Union[Dict[str, Any], str]] = Field(
        default=None, description="Request body"
    )

    # Response fields
    status_code: Optional[int] = Field(
        default=200, description="Expected response status code"
    )
    response_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Expected response headers"
    )
    response_body: Optional[Union[Dict[str, Any], str]] = Field(
        default=None, description="Expected response body"
    )

    # Additional options
    timeout: Optional[int] = Field(default=30, description="Request timeout in seconds")


class VerifyRequestResponseRequest(BaseModel):
    """Request for verifying request-response pairs."""

    request_response_pairs: List[RequestResponsePair] = Field(
        ..., description="List of request-response pairs to verify"
    )
    timeout: Optional[int] = Field(
        default=30, description="Script execution timeout in seconds"
    )


class VerifySimplifiedRequestResponseRequest(BaseModel):
    """Simplified request for verifying request-response pairs."""

    request_response_pairs: List[SimplifiedRequestResponsePair] = Field(
        ..., description="List of simplified request-response pairs to verify"
    )
    timeout: Optional[int] = Field(
        default=30, description="Script execution timeout in seconds"
    )


class ValidationScriptResult(BaseModel):
    """Result of a validation script execution."""

    script_id: str = Field(..., description="ID of the validation script")
    script_type: str = Field(..., description="Type of validation script")
    passed: bool = Field(..., description="Whether the validation passed")
    error_message: Optional[str] = Field(
        default=None, description="Error message if validation failed"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Script execution time in seconds"
    )
    script_output: Optional[str] = Field(default=None, description="Raw script output")


class RequestResponseVerificationResult(BaseModel):
    """Verification result for a single request-response pair."""

    pair_index: int = Field(..., description="Index of the request-response pair")
    overall_passed: bool = Field(..., description="Whether all validations passed")
    results: List[ValidationScriptResult] = Field(
        default_factory=list, description="Individual script results"
    )
    total_execution_time: Optional[float] = Field(
        default=None, description="Total execution time"
    )


class VerifyRequestResponseResponse(BaseModel):
    """Response for request-response verification."""

    endpoint_name: str = Field(..., description="Name of the endpoint being verified")
    endpoint_id: str = Field(..., description="ID of the endpoint")
    total_pairs: int = Field(..., description="Total number of request-response pairs")
    overall_passed: bool = Field(..., description="Whether all validations passed")
    verification_results: List[RequestResponseVerificationResult] = Field(
        default_factory=list, description="Results for each request-response pair"
    )
    total_execution_time: Optional[float] = Field(
        default=None, description="Total execution time"
    )
