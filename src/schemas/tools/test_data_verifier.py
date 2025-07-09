# schemas/tools/test_data_verifier.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from schemas.tools.test_data_generator import TestData
from schemas.tools.test_script_generator import ValidationScript


class TestDataVerifierInput(BaseModel):
    """Input for TestDataVerifierTool."""

    test_data_collection: List[TestData] = Field(
        ..., description="Test data to verify against constraints"
    )
    verification_scripts: List[ValidationScript] = Field(
        ..., description="Pre-generated verification scripts to use"
    )
    timeout: Optional[int] = Field(
        default=30, description="Timeout for script execution in seconds"
    )


class VerificationResult(BaseModel):
    """Result of verifying a single test data item."""

    test_data_id: str
    is_valid: bool
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    constraint_violations: List[str] = Field(default_factory=list)


class TestDataVerifierOutput(BaseModel):
    """Output from TestDataVerifierTool."""

    verified_test_data: List[TestData] = Field(
        ..., description="Test data that passed verification"
    )
    verification_results: List[VerificationResult] = Field(
        ..., description="Detailed verification results for each test data"
    )
    filtered_count: int = Field(
        ..., description="Number of test data items filtered out"
    )
