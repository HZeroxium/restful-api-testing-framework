"""Utility functions for working with LLM agents."""

import uuid
import json
import asyncio
import re
from typing import Any, Dict, Optional, Type, TypeVar, List, Union
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


async def run_llm_agent(
    input_data: Any,
    output_schema: Type[T],
    instruction_key: str,
    app_name: str = "llm_agent",
    timeout: float = DEFAULT_LLM_TIMEOUT,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Run an LLM agent with the specified parameters and return the parsed response.

    Args:
        input_data: The input data for the LLM (will be converted to JSON)
        output_schema: The Pydantic schema for the expected output
        instruction_key: Key for the instruction in LLM_INSTRUCTIONS
        app_name: Name of the application (used for the session)
        timeout: Timeout in seconds
        verbose: Whether to print verbose output

    Returns:
        Parsed JSON response from the LLM, or None if an error occurred
    """
    # Set up session services
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()

    # Create a unique session ID
    session_id = str(uuid.uuid4())
    user_id = "system"

    # Initialize session
    session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    # Get the instruction from constants
    instruction = LLM_INSTRUCTIONS.get(instruction_key, "")
    if not instruction:
        if verbose:
            print(f"Warning: No instruction found for key '{instruction_key}'")

    # Create the LLM agent
    llm_agent = LlmAgent(
        name=f"llm_{app_name}",
        model=settings.llm.LLM_MODEL,
        instruction=instruction,
        input_schema=(
            type(input_data) if hasattr(input_data, "__annotations__") else None
        ),
        output_schema=output_schema,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )

    # Create a runner
    runner = Runner(
        app_name=app_name,
        agent=llm_agent,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
    )

    # Convert input to JSON if it's a Pydantic model
    input_json = (
        input_data.model_dump() if hasattr(input_data, "model_dump") else input_data
    )

    # Prepare input for the LLM
    user_input = types.Content(
        role="user", parts=[types.Part(text=json.dumps(input_json))]
    )

    # Run the agent with timeout protection
    try:
        # Define an async function to get the LLM response
        async def get_llm_response():
            for event in runner.run(
                session_id=session_id,
                user_id=user_id,
                new_message=user_input,
            ):
                if event.content:
                    return "".join(part.text for part in event.content.parts)
            return None

        # Execute with timeout
        if verbose:
            print(f"Running LLM agent with timeout of {timeout} seconds...")

        raw_text = await asyncio.wait_for(get_llm_response(), timeout=timeout)

        if not raw_text:
            if verbose:
                print("No response received from LLM")
            return None

        # Extract JSON from the response text
        json_data = extract_json_from_text(raw_text)
        if json_data is None and verbose:
            print(f"Failed to extract JSON from LLM response: {raw_text[:100]}...")

        return json_data

    except asyncio.TimeoutError:
        if verbose:
            print(f"LLM request timed out after {timeout} seconds")
        return None

    except Exception as e:
        if verbose:
            print(f"Error during LLM processing: {str(e)}")
        return None


async def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON content from text that may contain markdown code blocks or other text.

    Args:
        text: The text containing JSON

    Returns:
        Extracted JSON as a dictionary, or None if extraction failed
    """
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
                json_content = json_parts[1].strip()
                return json.loads(json_content)

        # Method 3: Try to find JSON object using regex
        pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(pattern, text)
        if matches:
            return json.loads(matches[0])

        # Method 4: Try parsing the entire text as JSON
        return json.loads(text)

    except json.JSONDecodeError:
        return None


async def get_llm_completion(
    prompt: str,
    output_schema: Optional[Type[BaseModel]] = None,
    app_name: str = "llm_completion",
    timeout: float = DEFAULT_LLM_TIMEOUT,
    verbose: bool = False,
) -> str:
    """
    Get a simple text completion from the LLM without parsing JSON.

    Args:
        prompt: The prompt text for the LLM
        output_schema: Optional schema for structured output
        app_name: Name of the application
        timeout: Timeout in seconds
        verbose: Whether to print verbose output

    Returns:
        Raw text response from the LLM
    """
    # Set up session services
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()

    # Create a unique session ID
    session_id = str(uuid.uuid4())
    user_id = "system"

    # Initialize session
    session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    # Create the LLM agent for simple text completion
    llm_agent = LlmAgent(
        name=f"llm_{app_name}",
        model=settings.llm.LLM_MODEL,
        output_schema=output_schema,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )

    # Create a runner
    runner = Runner(
        app_name=app_name,
        agent=llm_agent,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
    )

    # Prepare input for the LLM
    user_input = types.Content(role="user", parts=[types.Part(text=prompt)])

    try:
        # Define an async function to get the LLM response
        async def get_llm_response():
            result = ""
            for event in runner.run(
                session_id=session_id,
                user_id=user_id,
                new_message=user_input,
            ):
                if event.content:
                    result = "".join(part.text for part in event.content.parts)
            return result

        # Execute with timeout
        raw_text = await asyncio.wait_for(get_llm_response(), timeout=timeout)
        return raw_text

    except asyncio.TimeoutError:
        if verbose:
            print(f"LLM request timed out after {timeout} seconds")
        return ""

    except Exception as e:
        if verbose:
            print(f"Error during LLM processing: {str(e)}")
        return ""


async def run_llm_with_schema(
    input_data: Any,
    output_schema: Type[T],
    instruction_key: str,
    app_name: str = "llm_agent",
    timeout: float = DEFAULT_LLM_TIMEOUT,
    verbose: bool = False,
    retry_count: int = 1,
) -> Optional[Union[T, Dict[str, Any]]]:
    """
    Run an LLM agent and return a parsed response matching the provided schema.
    This function extends run_llm_agent by attempting to parse the result into the schema.

    Args:
        input_data: The input data for the LLM
        output_schema: The Pydantic schema for the expected output
        instruction_key: Key for the instruction in LLM_INSTRUCTIONS
        app_name: Name of the application (used for the session)
        timeout: Timeout in seconds
        verbose: Whether to print verbose output
        retry_count: Number of times to retry on parsing failure

    Returns:
        Parsed schema instance, raw dict response, or None if failed
    """
    for attempt in range(retry_count):
        if attempt > 0 and verbose:
            print(f"Retrying LLM request (attempt {attempt+1}/{retry_count})")

        json_response = await run_llm_agent(
            input_data=input_data,
            output_schema=output_schema,
            instruction_key=instruction_key,
            app_name=app_name,
            timeout=timeout,
            verbose=verbose,
        )

        if not json_response:
            if verbose and attempt < retry_count - 1:
                print("Empty response, retrying...")
            continue

        try:
            # Try to parse the response into the schema
            parsed_result = output_schema.model_validate(json_response)
            return parsed_result
        except Exception as e:
            if verbose:
                print(f"Failed to parse LLM response into schema: {str(e)}")
                if attempt < retry_count - 1:
                    print("Retrying with different prompt...")

    # Return the raw JSON response if schema parsing failed
    return json_response
