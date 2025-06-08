# llm/base_client.py

from typing import Type

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough

from llm.interface import LLMClient, LLMRequest, LLMResponse, T


class BaseLLMClient(LLMClient[T]):
    """Base implementation of LLM client using LangChain"""

    def __init__(self, model: BaseChatModel):
        self._model = model

    def get_model(self) -> BaseChatModel:
        return self._model

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        """Send a prompt to the LLM and get a raw text response"""
        messages = []

        if request.system_message:
            messages.append(SystemMessage(content=request.system_message))

        messages.append(HumanMessage(content=request.prompt))

        # Configure model parameters
        model_kwargs = {
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.max_tokens > 0:
            model_kwargs["max_tokens"] = request.max_tokens

        # Properly configure the model with parameters before invoking
        configured_model = self._model.with_config(
            config={"model_kwargs": model_kwargs}
        )

        # Invoke the properly configured model
        response = configured_model.invoke(messages)

        return LLMResponse(text=response.content, raw_response=response)

    def send_prompt_with_schema(self, request: LLMRequest, output_schema: Type[T]) -> T:
        """Send a prompt to the LLM and parse the response according to the provided schema"""
        # Create messages
        messages = []

        system_content = request.system_message or ""

        if system_content:
            messages.append(SystemMessagePromptTemplate.from_template(system_content))

        messages.append(HumanMessagePromptTemplate.from_template("{prompt}"))

        chat_prompt = ChatPromptTemplate.from_messages(messages)

        # Configure model parameters
        model_kwargs = {
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.max_tokens > 0:
            model_kwargs["max_tokens"] = request.max_tokens

        # Use with_structured_output feature
        structured_model = self._model.with_structured_output(
            output_schema, include_raw=True
        ).with_config(config={"model_kwargs": model_kwargs})

        # Create the chain
        chain = {"prompt": RunnablePassthrough()} | chat_prompt | structured_model

        # Execute the chain
        result = chain.invoke(request.prompt)

        # Return the parsed Pydantic model directly, rather than the full response dictionary
        if isinstance(result, dict) and "parsed" in result:
            return result["parsed"]

        return result
