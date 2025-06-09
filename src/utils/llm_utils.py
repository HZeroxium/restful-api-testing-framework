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
    return json.loads(sanitized_json)


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from LLM response text, handling various formats.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    if not response_text:
        return None

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
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # Try to parse the entire response as JSON
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    json_start = response_text.find("{")
    json_end = response_text.rfind("}")

    if json_start != -1 and json_end != -1 and json_end > json_start:
        try:
            json_text = response_text[json_start : json_end + 1]
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

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

        # Create the LLM agent
        self.agent = LlmAgent(
            name=agent_name,
            model=settings.llm.LLM_MODEL,
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
                json_data = extract_json_from_response(raw_text)

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
                        if hasattr(event, "content") and event.content:
                            if hasattr(event.content, "parts"):
                                for part in event.content.parts:
                                    if hasattr(part, "text") and part.text:
                                        response_parts.append(part.text)
                                        if self.verbose:
                                            print(
                                                f"LLM Response Part: {part.text[:100]}..."
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
                                            print(
                                                f"LLM Response Part: {part.text[:100]}..."
                                            )
                else:
                    # Direct result
                    if hasattr(runner_result, "content"):
                        if hasattr(runner_result.content, "parts"):
                            for part in runner_result.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)
                                    if self.verbose:
                                        print(
                                            f"LLM Response Part: {part.text[:100]}..."
                                        )

                full_response = "".join(response_parts) if response_parts else None

                if self.verbose and full_response:
                    print(f"Full LLM Response: {full_response[:500]}...")

                return full_response
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

        return await executor.execute(input_data)
    except Exception as e:
        if verbose:
            print(f"Error in create_and_execute_llm_agent: {str(e)}")
        return None


def clean_json_response(response_text: str) -> str:
    """
    Clean and fix common JSON formatting issues in LLM responses.

    Args:
        response_text: Raw response text

    Returns:
        Cleaned JSON string
    """
    if not response_text:
        return "{}"

    # Remove common prefixes/suffixes
    text = response_text.strip()

    # Remove markdown code block markers
    text = re.sub(r"^```json\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)

    # Fix common JSON issues
    # Remove trailing commas
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    # Fix unescaped quotes in strings
    text = re.sub(r'(?<!\\)"(?=.*".*:)', '\\"', text)

    # Ensure proper quote escaping in validation_code
    lines = text.split("\n")
    in_validation_code = False
    cleaned_lines = []

    for line in lines:
        if '"validation_code"' in line:
            in_validation_code = True
        elif in_validation_code and (
            line.strip().endswith('"')
            or line.strip().endswith('",')
            or line.strip().endswith('",')
        ):
            in_validation_code = False

        if (
            in_validation_code
            and line.strip().startswith('"')
            and not line.strip().startswith('"validation_code"')
        ):
            # This is part of the validation code string - escape internal quotes
            line = line.replace('"', '\\"')

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def validate_json_structure(json_data: Dict[str, Any], required_fields: list) -> bool:
    """
    Validate that JSON data has required structure.

    Args:
        json_data: Parsed JSON data
        required_fields: List of required field names

    Returns:
        True if structure is valid
    """
    if not isinstance(json_data, dict):
        return False

    for field in required_fields:
        if field not in json_data:
            return False

    return True


def log_request_to_file(app_name: str, agent_name: str, prompt: str, input_data: Any):
    """Log LLM request to file for debugging."""
    import os
    from datetime import datetime

    try:
        log_dir = "logs/llm_requests"
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            log_dir, f"{app_name}_{agent_name}_{timestamp}_request.log"
        )

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"App: {app_name}\n")
            f.write(f"Agent: {agent_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write("PROMPT:\n")
            f.write(prompt)
            f.write("\n" + "=" * 80 + "\n")
            f.write("INPUT DATA:\n")
            f.write(str(input_data))
            f.write("\n")
    except Exception:
        pass  # Ignore logging errors


def log_response_to_file(app_name: str, agent_name: str, response: str):
    """Log LLM response to file for debugging."""
    import os
    from datetime import datetime

    try:
        log_dir = "logs/llm_responses"
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            log_dir, f"{app_name}_{agent_name}_{timestamp}_response.log"
        )

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"App: {app_name}\n")
            f.write(f"Agent: {agent_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write("RAW RESPONSE:\n")
            f.write(str(response))
            f.write("\n" + "=" * 80 + "\n")

            # Try to parse and pretty-print JSON
            try:
                json_data = extract_json_from_response(str(response))
                if json_data:
                    f.write("PARSED JSON:\n")
                    f.write(json.dumps(json_data, indent=2))
                    f.write("\n")
            except Exception:
                f.write("JSON PARSING FAILED\n")
    except Exception:
        pass  # Ignore logging errors


def log_error_to_file(app_name: str, agent_name: str, error: str, traceback_str: str):
    """Log LLM error to file for debugging."""
    import os
    from datetime import datetime

    try:
        log_dir = "logs/llm_errors"
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            log_dir, f"{app_name}_{agent_name}_{timestamp}_error.log"
        )

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"App: {app_name}\n")
            f.write(f"Agent: {agent_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write("ERROR:\n")
            f.write(error)
            f.write("\n" + "=" * 80 + "\n")
            f.write("TRACEBACK:\n")
            f.write(traceback_str)
            f.write("\n")
    except Exception:
        pass  # Ignore logging errors
