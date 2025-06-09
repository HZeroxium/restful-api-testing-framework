# schemas/core/base_tool.py

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base schema for tool inputs."""

    # Base fields that all tool inputs should have
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata for the tool execution"
    )


class ToolOutput(BaseModel):
    """Base schema for tool outputs."""

    # Base fields that all tool outputs should have
    success: bool = Field(
        default=True, description="Whether the tool execution was successful"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Time taken for execution in seconds"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata from the tool execution"
    )
