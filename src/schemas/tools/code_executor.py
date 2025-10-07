# schemas/tools/code_executor.py

from typing import Any, Dict, Optional
from pydantic import Field, field_validator

from schemas.core import ToolInput, ToolOutput


class CodeExecutorInput(ToolInput):
    """Input schema for the Python Script Executor tool."""

    code: str = Field(..., description="Python code to execute")
    context_variables: Optional[Dict[str, Any]] = Field(
        default=None, description="Variables to be available in the execution context"
    )
    timeout: Optional[float] = Field(
        default=None, description="Maximum execution time in seconds"
    )


class CodeExecutorOutput(ToolOutput):
    """Output schema for the Python Script Executor tool."""

    success: bool = Field(..., description="Whether the execution was successful")
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    stdout: Optional[str] = Field(
        default="", description="Standard output from code execution"
    )
    stderr: Optional[str] = Field(
        default="", description="Standard error from code execution"
    )
    execution_time: float = Field(
        ..., description="Time taken to execute the code in seconds"
    )
    validated_code: str = Field(
        ..., description="The validated and potentially modified code that was executed"
    )

    @field_validator("error")
    def error_required_on_failure(cls, v, info):
        """Ensure error is provided when success is False."""
        # Access success from info.data in Pydantic v2
        if info.data.get("success") is False and v is None:
            raise ValueError("Error message must be provided when success is False")
        return v
