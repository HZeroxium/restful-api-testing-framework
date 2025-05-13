# core/base_agent.py

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class AgentInput(BaseModel):
    """Base class for agent inputs"""

    pass


class AgentOutput(BaseModel):
    """Base class for agent outputs"""

    pass


class BaseAgent(ABC):
    """Base agent that all other agents will inherit from"""

    @abstractmethod
    def run(self, input_data: AgentInput) -> AgentOutput:
        """Execute the agent's main functionality"""
        pass

    def __call__(self, input_data: AgentInput) -> AgentOutput:
        """Allow the agent to be called like a function"""
        return self.run(input_data)
