"""Utility functions for working with LLM agents."""

import uuid
import json
import asyncio
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar, List, Union, Callable
from pydantic import BaseModel

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types

from config.settings import settings
from config.constants import LLM_INSTRUCTIONS, DEFAULT_LLM_TIMEOUT

T = TypeVar("T", bound=BaseModel)


class LlmSession:
    """Manages LLM session components and lifecycle."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self.artifact_service = InMemoryArtifactService()
        self.memory_service = InMemoryMemoryService()
        self.session_id = str(uuid.uuid4())
        self.user_id = "system"

        # Initialize session
        self.session_service.create_session(
            app_name=app_name,
            user_id=self.user_id,
            session_id=self.session_id,
            state={},
        )


class LlmExecutor:
    """Handles LLM agent execution with standardized error handling and retries."""

    def __init__(
        self,
        session: LlmSession,
        agent_name: str,
        instruction: str,
        input_schema: Optional[Type] = None,
        output_schema: Optional[Type] = None,
        timeout: float = DEFAULT_LLM_TIMEOUT,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        verbose: bool = False,
    ):
        self.session = session
        self.agent_name = agent_name
        self.instruction = instruction
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verbose = verbose

        # Create the LLM agent
        self.agent = LlmAgent(
            name=agent_name,
            model=settings.llm.LLM_MODEL,
            instruction=instruction,
            input_schema=input_schema,
            output_schema=output_schema,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        # Create runner
        self.runner = Runner(
            app_name=session.app_name,
            agent=self.agent,
            session_service=session.session_service,
            artifact_service=session.artifact_service,
            memory_service=session.memory_service,
        )

    async def execute(
        self, input_data: Union[str, Dict, BaseModel]
    ) -> Optional[Dict[str, Any]]:
        """Execute the LLM agent with retry logic and error handling."""
        # Prepare input
        if isinstance(input_data, BaseModel):
            user_message = input_data.model_dump_json()
        elif isinstance(input_data, dict):
            user_message = json.dumps(input_data)
        else:
            user_message = str(input_data)

        user_input = types.Content(role="user", parts=[types.Part(text=user_message)])

        # Execute with retries
        for retry in range(self.max_retries + 1):
            if retry > 0:
                if self.verbose:
                    print(
                        f"Retry {retry}/{self.max_retries} after waiting {self.retry_delay}s..."
                    )
                await asyncio.sleep(self.retry_delay)

            try:
                if self.verbose:
                    print(f"Running LLM agent: {self.agent_name}")

                start_time = time.time()
                raw_text = await self._get_llm_response(user_input)

                if not raw_text:
                    if self.verbose:
                        print("No response received from LLM")
                    if retry < self.max_retries:
                        continue
                    return None

                # Parse JSON response
                json_data = extract_json_from_text(raw_text)

                if json_data is None:
                    if self.verbose:
                        print(f"Failed to extract JSON from LLM response")
                        print(f"Raw response preview: {raw_text[:200]}...")
                    if retry < self.max_retries:
                        continue
                    return None

                if self.verbose:
                    execution_time = round(time.time() - start_time, 2)
                    print(f"LLM execution completed in {execution_time}s")

                return json_data

            except Exception as e:
                if self.verbose:
                    print(f"Error during LLM processing: {str(e)}")
                if retry < self.max_retries:
                    continue
                return None

        return None

    async def _get_llm_response(self, user_input: types.Content) -> Optional[str]:
        """Get response from LLM with timeout protection."""

        async def get_response():
            try:
                response_parts = []

                # Check if the runner.run returns an async iterator or regular iterator
                runner_result = self.runner.run(
                    session_id=self.session.session_id,
                    user_id=self.session.user_id,
                    new_message=user_input,
                )

                # Handle both async and sync iterators
                if hasattr(runner_result, "__aiter__"):
                    # Async iterator
                    async for event in runner_result:
                        if event.content:
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)
                elif hasattr(runner_result, "__iter__"):
                    # Regular iterator - convert to async
                    import asyncio

                    for event in runner_result:
                        # Yield control to allow other async operations
                        await asyncio.sleep(0)
                        if event.content:
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)
                else:
                    # Direct result
                    if hasattr(runner_result, "content"):
                        for part in runner_result.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_parts.append(part.text)

                return "".join(response_parts) if response_parts else None
            except Exception as e:
                if self.verbose:
                    print(f"Error during LLM generation: {str(e)}")
                return None

        try:
            return await asyncio.wait_for(get_response(), timeout=self.timeout)
        except asyncio.TimeoutError:
            if self.verbose:
                print(f"LLM request timed out after {self.timeout} seconds")
            return None


async def create_and_execute_llm_agent(
    app_name: str,
    agent_name: str,
    instruction: str,
    input_data: Union[str, Dict, BaseModel],
    input_schema: Optional[Type] = None,
    output_schema: Optional[Type] = None,
    timeout: float = DEFAULT_LLM_TIMEOUT,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to create and execute an LLM agent in one call.

    Args:
        app_name: Name of the application
        agent_name: Name of the LLM agent
        instruction: Instruction for the agent
        input_data: Input data for the agent
        input_schema: Optional input schema for validation
        output_schema: Optional output schema for validation
        timeout: Timeout for LLM execution
        max_retries: Maximum number of retries
        retry_delay: Delay between retries
        verbose: Whether to print verbose output

    Returns:
        Parsed JSON response from LLM or None if failed
    """
    try:
        session = LlmSession(app_name)
        executor = LlmExecutor(
            session=session,
            agent_name=agent_name,
            instruction=instruction,
            input_schema=input_schema,
            output_schema=output_schema,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verbose=verbose,
        )

        return await executor.execute(input_data)
    except Exception as e:
        if verbose:
            print(f"Error in create_and_execute_llm_agent: {str(e)}")
        return None


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON content from text that may contain markdown code blocks or other text.

    Args:
        text: The text containing JSON

    Returns:
        Extracted JSON as a dictionary, or None if extraction failed
    """
    if not text:
        return None

    try:
        # Try several methods to extract JSON

        # Method 1: Look for JSON content in markdown code blocks
        if "```json" in text:
            json_parts = text.split("```json")
            if len(json_parts) > 1:
                json_content = json_parts[1].split("```")[0].strip()
                return json.loads(json_content)

        # Method 2: Look for any code blocks
        elif "```" in text:
            json_parts = text.split("```")
            if len(json_parts) > 1:
                for part in json_parts[1::2]:  # Look at all code block parts
                    try:
                        return json.loads(part.strip())
                    except json.JSONDecodeError:
                        continue

        # Method 3: Try to find JSON object using regex
        pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(pattern, text)
        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # Method 4: Try parsing the entire text as JSON
        return json.loads(text)

    except (json.JSONDecodeError, TypeError):
        return None


async def execute_llm_with_structured_output(
    app_name: str,
    agent_name: str,
    instruction: str,
    input_data: Union[str, Dict, BaseModel],
    output_processor: Callable[[Dict[str, Any]], Any],
    input_schema: Optional[Type] = None,
    output_schema: Optional[Type] = None,
    timeout: float = DEFAULT_LLM_TIMEOUT,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    verbose: bool = False,
) -> Any:
    """
    Execute LLM agent and process the output with a custom processor function.

    Args:
        app_name: Name of the application
        agent_name: Name of the LLM agent
        instruction: Instruction for the agent
        input_data: Input data for the agent
        output_processor: Function to process the LLM output
        input_schema: Optional input schema for validation
        output_schema: Optional output schema for validation
        timeout: Timeout for LLM execution
        max_retries: Maximum number of retries
        retry_delay: Delay between retries
        verbose: Whether to print verbose output

    Returns:
        Processed output from the output_processor function
    """
    raw_json = await create_and_execute_llm_agent(
        app_name=app_name,
        agent_name=agent_name,
        instruction=instruction,
        input_data=input_data,
        input_schema=input_schema,
        output_schema=output_schema,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        verbose=verbose,
    )

    if raw_json is None:
        return None

    return output_processor(raw_json)
