# llm/interface.py

from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar, Generic
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel

T = TypeVar("T", bound=BaseModel)


class LLMRequest(BaseModel):
    """Request model for LLM calls"""

    prompt: str = Field(..., description="The prompt to send to the LLM")
    system_message: Optional[str] = Field(
        default="", description="Optional system message to set context"
    )
    temperature: float = Field(
        default=0.2, description="Sampling temperature, between 0 and 1"
    )
    top_p: float = Field(default=0.9, description="Nucleus sampling parameter")
    max_tokens: int = Field(
        default=-1, description="Maximum tokens to generate, -1 for no limit"
    )


class LLMResponse(BaseModel):
    """Generic response from LLM"""

    text: str = Field(..., description="The text response from the LLM")
    raw_response: Optional[Any] = Field(
        default=None, description="The raw response object"
    )


class LLMClient(Generic[T], ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        """Send a prompt to the LLM and get a text response"""
        pass

    @abstractmethod
    def send_prompt_with_schema(self, request: LLMRequest, output_schema: Type[T]) -> T:
        """Send a prompt to the LLM and parse the response according to the provided schema"""
        pass

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Get the underlying LangChain chat model"""
        pass
