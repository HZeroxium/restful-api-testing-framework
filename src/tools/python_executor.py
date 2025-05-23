# tools/python_script_executor.py

import asyncio
from typing import Any, Dict, List, Optional

# Google ADK imports
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import built_in_code_execution
from google.genai import types

# Local imports
from src.core import BaseTool
from src.schemas.tools import (
    PythonScriptExecutorInput,
    PythonScriptExecutorOutput,
)

# Default configuration
DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_APP_NAME = "python_executor_app"
DEFAULT_USER_ID = "user_default"


class PythonScriptExecutorTool(BaseTool):
    """A tool that validates and executes Python scripts using Google's LLM."""

    def __init__(
        self,
        name: str = "python_script_executor",
        description: str = "Validates and executes Python scripts safely using LLM validation",
        config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
        model: str = DEFAULT_MODEL,
        restricted_modules: Optional[List[str]] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=PythonScriptExecutorInput,
            output_schema=PythonScriptExecutorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Configuration
        self.model = model
        self.restricted_modules = restricted_modules or []

        # Setup ADK components
        self.session_service = InMemorySessionService()
        self.app_name = (
            config.get("app_name", DEFAULT_APP_NAME) if config else DEFAULT_APP_NAME
        )

        # Setup the LLM agent
        self.code_agent = LlmAgent(
            name=f"{name}_agent",
            model=self.model,
            tools=[built_in_code_execution],
            instruction=(
                "You are a Python code validator and executor. "
                "When given Python code, first check for any issues. "
                "If the code looks safe and correct, execute it. "
                "If there are issues, fix them before execution. "
                "Return the execution result or error message."
            ),
            description="Agent that validates and executes Python code safely.",
        )

        # Initialize the runner
        self.runner = Runner(
            agent=self.code_agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    async def _execute(
        self, input_data: PythonScriptExecutorInput
    ) -> PythonScriptExecutorOutput:
        """Validate and execute the Python script using LLM and built-in code execution."""
        # Create a unique session ID
        session_id = f"session_{hash(input_data.code)}"
        user_id = DEFAULT_USER_ID

        # Set up session
        self.session_service.create_session(
            app_name=self.app_name, user_id=user_id, session_id=session_id
        )

        # Prepare the input message
        prompt = self._build_prompt(input_data)
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        # Track execution results
        code_snippet = None
        execution_outcome = None
        execution_output = None
        final_text = None
        error_message = None
        execution_time = 0
        start_time = asyncio.get_event_loop().time()

        try:
            # Run the code through the LLM agent
            async for event in self.runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content
            ):
                # Process streaming response
                for part in event.content.parts or []:
                    # Track generated code
                    if part.executable_code:
                        code_snippet = part.executable_code.code
                        self.logger.debug(f"Generated/validated code:\n{code_snippet}")

                    # Track execution result
                    if part.code_execution_result:
                        execution_outcome = part.code_execution_result.outcome
                        execution_output = part.code_execution_result.output
                        self.logger.debug(
                            f"Execution {execution_outcome}, output:\n{execution_output}"
                        )

                    # Track final response
                    if part.text and event.is_final_response():
                        final_text = part.text.strip()
                        self.logger.info(f"Final response: {final_text}")

            execution_time = asyncio.get_event_loop().time() - start_time

            # Determine success status more accurately
            # Check both outcome and for error keywords in output
            is_success = execution_outcome == "SUCCESS"

            # If output contains error-related text but outcome is SUCCESS, further analyze
            if is_success and execution_output:
                error_indicators = [
                    "error:",
                    "exception:",
                    "traceback:",
                    "an error occurred",
                ]
                lower_output = execution_output.lower()
                if any(indicator in lower_output for indicator in error_indicators):
                    self.logger.warning(
                        "Success reported but error indicators found in output"
                    )
                    # Keep success True if these are just mentioned in output but not actual errors

            # For error case, extract specific error message
            if not is_success and execution_output:
                # Try to extract the specific error message from output
                import re

                error_match = re.search(
                    r"(error|exception):\s*(.*?)($|\n)", execution_output.lower()
                )
                if error_match:
                    error_message = error_match.group(2).strip()
                else:
                    error_message = execution_output

            return PythonScriptExecutorOutput(
                result=execution_output or final_text or "No output",
                success=is_success,
                error=(
                    None
                    if is_success
                    else (error_message or execution_output or "Execution failed")
                ),
                stdout=execution_output if is_success else "",
                stderr="" if is_success else (execution_output or ""),
                execution_time=execution_time,
                validated_code=code_snippet or input_data.code,
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Error during script execution: {e}")
            return PythonScriptExecutorOutput(
                result=None,
                success=False,
                error=str(e),
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                validated_code=code_snippet or input_data.code,
            )
        finally:
            # Clean up the session
            try:
                self.session_service.delete_session(
                    app_name=self.app_name, user_id=user_id, session_id=session_id
                )
            except Exception as e:
                self.logger.warning(f"Error cleaning up session: {e}")

    def _build_prompt(self, input_data: PythonScriptExecutorInput) -> str:
        """Build the prompt for the LLM agent."""
        prompt_parts = [
            "Please validate and execute the following Python code:",
            "\n```python",
            input_data.code,
            "```\n",
        ]

        # Add context variables if provided
        if input_data.context_variables:
            prompt_parts.append("\nUse these context variables:")
            for key, value in input_data.context_variables.items():
                prompt_parts.append(f"- {key}: {repr(value)}")

        # Add timeout information if provided
        if input_data.timeout:
            prompt_parts.append(f"\nTimeout: {input_data.timeout} seconds")

        # Add restrictions
        if self.restricted_modules:
            prompt_parts.append("\nRestricted modules (do not use):")
            for module in self.restricted_modules:
                prompt_parts.append(f"- {module}")

        return "\n".join(prompt_parts)

    async def cleanup(self) -> None:
        """Clean up resources used by the tool."""
        # Nothing to clean up as sessions are deleted after each execution
        pass
