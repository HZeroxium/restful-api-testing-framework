"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class SpecSourceType(str, Enum):
    UPLOAD = "upload"
    URL = "url"
    EXISTING = "existing"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"


# Service Models
class SpecSource(BaseModel):
    type: SpecSourceType
    path_or_url: str


class CreateServiceRequest(BaseModel):
    service_name: str = Field(..., description="Name of the service")
    swagger_source: SpecSource = Field(..., description="Source of the OpenAPI spec")
    rebuild_odg: Optional[bool] = Field(default=True, description="Whether to rebuild ODG")


class ServiceSummary(BaseModel):
    id: str
    name: str
    status: str
    endpoints_count: int
    test_cases_count: int
    test_data_count: int
    created_at: str
    updated_at: str


class ServiceDetail(ServiceSummary):
    spec_path: str
    spec_source: str
    working_dir: str


class UpdateServiceSpecRequest(BaseModel):
    spec_content: Union[str, Dict[str, Any]]
    rebuild_odg: Optional[bool] = Field(default=True)


# Test Case Models
class GenerateTestCasesRequest(BaseModel):
    selected_endpoints: Optional[List[str]] = Field(default=None, description="List of endpoints to generate test cases for")
    clear_test_cases: Optional[bool] = Field(default=False, description="Whether to clear existing test cases")


class GenerateTestDataRequest(BaseModel):
    endpoints: Optional[List[str]] = Field(default=None, description="List of endpoints to generate test data for")
    mode: Optional[str] = Field(default="all", description="Generation mode: 'all' or 'selected'")
    regenerate: Optional[bool] = Field(default=False, description="Whether to regenerate existing data")


class GenerateAllRequest(BaseModel):
    selected_endpoints: Optional[List[str]] = Field(default=None)
    clear_test_cases: Optional[bool] = Field(default=False)
    regenerate_test_data: Optional[bool] = Field(default=False)


# Test Run Models
class CreateRunRequest(BaseModel):
    base_url: str = Field(..., description="Base URL of the API to test")
    token: Optional[str] = Field(default=None, description="Authentication token")
    endpoint_filter: Optional[str] = Field(default=None, description="Filter to run specific endpoints")
    test_case_filter: Optional[List[str]] = Field(default=None, description="Specific test case IDs to run")


class RunResults(BaseModel):
    total: int
    passed: int
    failed: int
    success_rate: float


class RunArtifact(BaseModel):
    name: str
    path: str
    url: str
    size: Optional[int] = None
    created_at: str


class RunSummary(BaseModel):
    id: str
    service_id: str
    status: RunStatus
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    results: RunResults
    config: Dict[str, Any]


class RunDetail(RunSummary):
    artifacts: List[RunArtifact]
    logs: Optional[List[str]] = None


# Response Models
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class EndpointInfo(BaseModel):
    method: str
    path: str
    operation_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None


class SchemaInfo(BaseModel):
    name: str
    type: str
    properties: Optional[Dict[str, Any]] = None


# Health Models
class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str


class ConfigInfo(BaseModel):
    database_path: str
    services_directory: str
    working_directories: Dict[str, str]


# Test Case Models
class TestCaseInfo(BaseModel):
    id: str
    endpoint: str
    method: str
    path: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    expected_status: Optional[int] = None
    created_at: str


class UpdateTestCaseRequest(BaseModel):
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    expected_status: Optional[int] = None


# Dry Run Models
class DryRunRequest(BaseModel):
    endpoint: str = Field(..., description="Endpoint in format 'method-path'")
    base_url: str = Field(..., description="Base URL for the API")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Additional headers")


class DryRunResponse(BaseModel):
    url: str
    method: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[str]] = None
