# schemas/core/base_agent.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    """Base schema for agent inputs."""

    query: str = Field(..., description="The query or instruction for the agent")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context for the agent"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional parameters for the agent"
    )


class AgentOutput(BaseModel):
    """Base schema for agent outputs."""

    response: str = Field(..., description="The agent's response")
    reasoning: Optional[str] = Field(
        default=None, description="The agent's reasoning process"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Details of tools called during execution"
    )
    artifacts: Optional[Dict[str, Any]] = Field(
        default=None, description="Any artifacts produced during execution"
    )


class AgentState(BaseModel):
    """Represents the internal state of an agent during execution."""

    input: Optional[AgentInput] = None
    output: Optional[AgentOutput] = None
    action_history: List[Dict[str, Any]] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)

    def clear(self) -> None:
        """Clear the state for a new run."""
        self.input = None
        self.output = None
        self.action_history = []
        # We keep memory across runs by default
