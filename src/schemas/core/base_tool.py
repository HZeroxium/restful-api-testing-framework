# schemas/core/base_tool.py

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base schema for tool inputs."""

    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the tool execution"
    )


class ToolOutput(BaseModel):
    """Base schema for tool outputs."""

    result: Any = Field(..., description="The result of the tool execution")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the execution"
    )
