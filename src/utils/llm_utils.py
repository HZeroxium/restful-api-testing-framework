# utils/llm_utils.py

"""LLM utilities for the testing framework."""
import asyncio
import json
import os
import re
import time
import uuid
from typing import Any, Dict, Optional, Type, TypeVar, Union, Callable
from pydantic import BaseModel
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types

from config.settings import settings
from config.constants import LLM_INSTRUCTIONS, DEFAULT_LLM_TIMEOUT
from common.logger import LoggerFactory, LoggerType, LogLevel

T = TypeVar("T", bound=BaseModel)


# Initialize specialized loggers for LLM operations
def _get_llm_loggers():
    """Get specialized loggers for LLM operations with file outputs."""
    # Ensure logs/llm directory exists
    logs_dir = Path("logs/llm")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Request logger - logs all LLM requests
    # Console: INFO and above, File: DEBUG and above
    request_logger = LoggerFactory.create_logger(
        name="llm.requests",
        logger_type=LoggerType.STANDARD,
        console_level=LogLevel.INFO,
        file_level=LogLevel.DEBUG,
        log_file=str(logs_dir / "requests.log"),
        use_colors=False,
    )

    # Response logger - logs all LLM responses
    # Console: INFO and above, File: DEBUG and above
    response_logger = LoggerFactory.create_logger(
        name="llm.responses",
        logger_type=LoggerType.STANDARD,
        console_level=LogLevel.INFO,
        file_level=LogLevel.DEBUG,
        log_file=str(logs_dir / "responses.log"),
        use_colors=False,
    )

    # Error logger - logs all LLM errors
    # Console: WARNING and above, File: DEBUG and above
    error_logger = LoggerFactory.create_logger(
        name="llm.errors",
        logger_type=LoggerType.STANDARD,
        console_level=LogLevel.WARNING,
        file_level=LogLevel.DEBUG,
        log_file=str(logs_dir / "errors.log"),
        use_colors=False,
    )

    # General LLM logger for console output
    # Console: INFO and above, no separate file
    general_logger = LoggerFactory.get_logger(
        name="llm.utils",
        logger_type=LoggerType.STANDARD,
        console_level=LogLevel.INFO,
        use_colors=True,
    )

    return request_logger, response_logger, error_logger, general_logger


# Initialize loggers
_request_logger, _response_logger, _error_logger, _general_logger = _get_llm_loggers()


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

        _general_logger.debug(f"Created LLM session for app: {app_name}")
        _general_logger.add_context(
            app_name=app_name,
            session_id=self.session_id,
            user_id=self.user_id,
        )


def sanitize_instruction_for_adk(instruction: str) -> str:
    """
    Sanitize instruction text to prevent Google ADK from interpreting
    path parameters as template variables.

    This replaces curly braces in path parameters and other content
    that should not be treated as template variables.
    """
    import re

    # Replace path parameter patterns like {userId}, {brandId}, etc.
    # with escaped versions that won't trigger ADK template substitution
    path_param_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"

    def replace_path_param(match):
        param_name = match.group(1)
        # Use a different bracket style that ADK won't interpret as template variables
        return f"[{param_name}]"

    sanitized = re.sub(path_param_pattern, replace_path_param, instruction)

    # Also handle any other potential conflicts with ADK template syntax
    # ADK uses {+variable} syntax, so we need to be careful with any {+...} patterns
    sanitized = sanitized.replace("{+", "{{+")

    _general_logger.debug("Sanitized instruction for ADK compatibility")
    return sanitized


def prepare_endpoint_data_for_llm(endpoint_data: Dict) -> Dict:
    """
    Prepare endpoint data for LLM analysis by sanitizing path parameters
    and other content that might conflict with Google ADK template system.
    """
    import json

    # Convert to JSON string and back to handle nested structures
    json_str = json.dumps(endpoint_data)

    # Replace path parameters in the JSON string
    import re

    path_param_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"

    def replace_path_param(match):
        param_name = match.group(1)
        return f"[{param_name}]"

    sanitized_json = re.sub(path_param_pattern, replace_path_param, json_str)

    # Parse back to dict
    result = json.loads(sanitized_json)

    _general_logger.debug("Prepared endpoint data for LLM analysis")
    return result


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from LLM response text, handling various formats.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    if not response_text:
        _general_logger.warning("Empty response text provided for JSON extraction")
        return None

    _general_logger.debug(
        f"Attempting to extract JSON from response ({len(response_text)} chars)"
    )

    # Try to find JSON in code blocks first
    json_patterns = [
        r"```json\s*\n(.*?)\n```",
        r"```\s*\n(.*?)\n```",
        r"```json(.*?)```",
        r"```(.*?)```",
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                result = json.loads(match.strip())
                _general_logger.debug("Successfully extracted JSON from code block")
                return result
            except json.JSONDecodeError:
                continue

    # Try to parse the entire response as JSON
    try:
        result = json.loads(response_text.strip())
        _general_logger.debug("Successfully parsed entire response as JSON")
        return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    json_start = response_text.find("{")
    json_end = response_text.rfind("}")

    if json_start != -1 and json_end != -1 and json_end > json_start:
        try:
            json_text = response_text[json_start : json_end + 1]
            result = json.loads(json_text)
            _general_logger.debug("Successfully extracted JSON object from text")
            return result
        except json.JSONDecodeError:
            pass

    _general_logger.warning("Failed to extract valid JSON from response text")
    return None


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
        # Sanitize instruction to prevent ADK template variable conflicts
        self.instruction = sanitize_instruction_for_adk(instruction)
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verbose = verbose

        # Initialize logger with context and separate console/file levels
        console_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"llm.executor.{agent_name}",
            logger_type=LoggerType.STANDARD,
            console_level=console_level,
            file_level=LogLevel.DEBUG,  # Always log DEBUG to file
        )

        self.logger.add_context(
            agent_name=agent_name,
            app_name=session.app_name,
            session_id=session.session_id,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.logger.info(f"Initializing LLM executor for agent: {agent_name}")

        from google.adk.models.lite_llm import LiteLlm

        # Create the LLM agent
        self.agent = LlmAgent(
            name=agent_name,
            model=settings.llm.LLM_MODEL,
            # model=LiteLlm(model="openai/gpt-4o"),
            instruction=self.instruction,
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

        self.logger.debug("LLM agent and runner created successfully")

    async def execute(
        self, input_data: Union[str, Dict, BaseModel]
    ) -> Optional[Dict[str, Any]]:
        """Execute the LLM agent with retry logic and error handling."""
        # Prepare input - sanitize if it's a dict containing endpoint data
        if isinstance(input_data, BaseModel):
            # Convert to dict first to allow sanitization
            input_dict = input_data.model_dump()
            sanitized_input = prepare_endpoint_data_for_llm(input_dict)
            user_message = json.dumps(sanitized_input)
        elif isinstance(input_data, dict):
            sanitized_input = prepare_endpoint_data_for_llm(input_data)
            user_message = json.dumps(sanitized_input)
        else:
            # For string input, also sanitize potential path parameters
            user_message = sanitize_instruction_for_adk(str(input_data))

        user_input = types.Content(role="user", parts=[types.Part(text=user_message)])

        # Log the request
        _request_logger.info("LLM Request Initiated")
        _request_logger.add_context(
            agent_name=self.agent_name,
            app_name=self.session.app_name,
            session_id=self.session.session_id,
            timeout=self.timeout,
            max_retries=self.max_retries,
            input_type=type(input_data).__name__,
            message_length=len(user_message),
        )
        _request_logger.debug(f"Request instruction: {self.instruction}...")
        _request_logger.debug(f"Request message: {user_message}...")

        self.logger.info("Starting LLM agent execution")
        self.logger.add_context(input_type=type(input_data).__name__)

        # Execute with retries
        for retry in range(self.max_retries + 1):
            if retry > 0:
                self.logger.info(
                    f"Retry {retry}/{self.max_retries} after waiting {self.retry_delay}s"
                )
                if self.verbose:
                    self.logger.debug(
                        f"Retry attempt {retry} for agent {self.agent_name}"
                    )
                await asyncio.sleep(self.retry_delay)

            try:
                if self.verbose:
                    self.logger.debug(f"Running LLM agent: {self.agent_name}")

                start_time = time.time()
                raw_text = await self._get_llm_response(user_input)

                if not raw_text:
                    self.logger.warning("No response received from LLM")
                    if retry < self.max_retries:
                        continue

                    # Log the error
                    _error_logger.error(
                        "No response received from LLM after all retries"
                    )
                    _error_logger.add_context(
                        agent_name=self.agent_name,
                        session_id=self.session.session_id,
                        total_retries=retry + 1,
                        reason="empty_response",
                    )
                    return None

                # Log the response
                execution_time = round(time.time() - start_time, 2)
                _response_logger.info("LLM Response Received")
                _response_logger.add_context(
                    agent_name=self.agent_name,
                    session_id=self.session.session_id,
                    execution_time=execution_time,
                    response_length=len(raw_text),
                    retry_count=retry,
                )
                _response_logger.debug(f"Raw response: {raw_text}...")

                # Parse JSON response
                json_data = extract_json_from_response(raw_text)

                if json_data is None:
                    self.logger.warning("Failed to extract JSON from LLM response")
                    if self.verbose:
                        self.logger.debug(f"Raw response preview: {raw_text}...")

                    if retry < self.max_retries:
                        continue

                    # Log the parsing error
                    _error_logger.error("Failed to parse JSON from LLM response")
                    _error_logger.add_context(
                        agent_name=self.agent_name,
                        session_id=self.session.session_id,
                        response_preview=raw_text[:1000],  # Preview first 1000 chars
                        total_retries=retry + 1,
                        reason="json_parse_failure",
                    )
                    return None

                self.logger.info(
                    f"LLM execution completed successfully in {execution_time}s"
                )
                if self.verbose:
                    self.logger.debug(
                        f"Parsed JSON keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'non-dict result'}"
                    )

                return json_data

            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error during LLM processing: {error_msg}")

                # Log the error in detail
                _error_logger.error("Exception during LLM processing")
                _error_logger.add_context(
                    agent_name=self.agent_name,
                    session_id=self.session.session_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    retry_count=retry,
                    total_retries=self.max_retries,
                )

                if retry < self.max_retries:
                    continue

                # Final error after all retries
                _error_logger.critical("LLM execution failed after all retries")
                _error_logger.add_context(
                    agent_name=self.agent_name,
                    session_id=self.session.session_id,
                    final_error=error_msg,
                    total_attempts=retry + 1,
                )
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
                        if hasattr(event, "content") and event.content:
                            if hasattr(event.content, "parts"):
                                for part in event.content.parts:
                                    if hasattr(part, "text") and part.text:
                                        response_parts.append(part.text)
                                        if self.verbose:
                                            self.logger.debug(
                                                f"LLM Response Part received ({len(part.text)} chars)"
                                            )
                elif hasattr(runner_result, "__iter__"):
                    # Regular iterator - convert to async
                    for event in runner_result:
                        if hasattr(event, "content") and event.content:
                            if hasattr(event.content, "parts"):
                                for part in event.content.parts:
                                    if hasattr(part, "text") and part.text:
                                        response_parts.append(part.text)
                                        if self.verbose:
                                            self.logger.debug(
                                                f"LLM Response Part received ({len(part.text)} chars)"
                                            )
                else:
                    # Direct result
                    if hasattr(runner_result, "content"):
                        if hasattr(runner_result.content, "parts"):
                            for part in runner_result.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)
                                    if self.verbose:
                                        self.logger.debug(
                                            f"LLM Response Part received ({len(part.text)} chars)"
                                        )

                full_response = "".join(response_parts) if response_parts else None

                if self.verbose and full_response:
                    self.logger.debug(
                        f"Full LLM Response assembled ({len(full_response)} chars)"
                    )

                return full_response
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error during LLM generation: {error_msg}")

                # Log the generation error
                _error_logger.error("Error during LLM response generation")
                _error_logger.add_context(
                    agent_name=self.agent_name,
                    session_id=self.session.session_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    stage="response_generation",
                )
                return None

        try:
            result = await asyncio.wait_for(get_response(), timeout=self.timeout)
            if result:
                self.logger.debug("LLM response received within timeout")
            return result
        except asyncio.TimeoutError:
            timeout_msg = f"LLM request timed out after {self.timeout} seconds"
            self.logger.error(timeout_msg)

            # Log the timeout error
            _error_logger.error("LLM request timeout")
            _error_logger.add_context(
                agent_name=self.agent_name,
                session_id=self.session.session_id,
                timeout_seconds=self.timeout,
                error_type="timeout",
            )

            if self.verbose:
                self.logger.debug(f"Timeout occurred for agent {self.agent_name}")
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
    # Initialize logger for this function with separate console/file levels
    console_level = LogLevel.DEBUG if verbose else LogLevel.INFO
    logger = LoggerFactory.get_logger(
        name="llm.create_and_execute",
        logger_type=LoggerType.STANDARD,
        console_level=console_level,
        file_level=LogLevel.DEBUG,  # Always log DEBUG to file
    )

    logger.add_context(
        app_name=app_name,
        agent_name=agent_name,
        timeout=timeout,
        max_retries=max_retries,
    )

    logger.info(f"Creating and executing LLM agent: {agent_name}")

    try:
        session = LlmSession(app_name)

        # Sanitize instruction to prevent path parameter conflicts
        sanitized_instruction = sanitize_instruction_for_adk(instruction)

        executor = LlmExecutor(
            session=session,
            agent_name=agent_name,
            instruction=sanitized_instruction,
            input_schema=input_schema,
            output_schema=output_schema,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verbose=verbose,
        )

        result = await executor.execute(input_data)

        if result:
            logger.info("LLM agent execution completed successfully")
            if verbose:
                logger.debug(f"Result type: {type(result).__name__}")
        else:
            logger.warning("LLM agent execution returned no result")

        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in create_and_execute_llm_agent: {error_msg}")

        # Log the high-level error
        _error_logger.error("Error in create_and_execute_llm_agent function")
        _error_logger.add_context(
            app_name=app_name,
            agent_name=agent_name,
            error_type=type(e).__name__,
            error_message=error_msg,
            function="create_and_execute_llm_agent",
        )

        if verbose:
            logger.debug(f"Exception details: {error_msg}")
        return None
