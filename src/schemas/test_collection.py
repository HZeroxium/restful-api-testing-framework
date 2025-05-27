

"""Models for test collections and executions."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from schemas.tools.test_suite_generator import TestSuite
from schemas.tools.test_execution_reporter import TestReport, TestSummary


class TestCollectionModel(BaseModel):
    """Model for a test collection."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    test_suites: List[TestSuite]
    api_name: Optional[str] = None
    api_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TestExecutionModel(BaseModel):
    """Model for a test execution."""

    id: Optional[str] = None
    collection_id: str
    collection_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    reports: List[TestReport]
    summary: TestSummary  # Contains test counts, success rates, etc.
