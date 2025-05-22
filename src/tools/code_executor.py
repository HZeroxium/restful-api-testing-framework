# tools/code_executor.py

import asyncio
import re
from typing import Any, Dict, List, Optional

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import built_in_code_execution
from google.genai import types

from core import BaseTool
from schemas.tools.code_executor import CodeExecutorInput, CodeExecutorOutput

# Defaults (override via config)
DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_APP_NAME = "code_executor_app"
DEFAULT_USER_ID = "user_default"


class CodeExecutorTool(BaseTool):
    """
    Validates & executes Python code via a Genie LLM + built-in executor.
    Strictly returns execution results; I/O (files/DB) happens externally.
    """

    def __init__(
        self,
        *,
        name: str = "code_executor",
        description: str = "LLM-backed Python code validator & executor",
        config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
        model: Optional[str] = None,
        restricted_modules: Optional[List[str]] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=CodeExecutorInput,
            output_schema=CodeExecutorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Merge defaults with config
        cfg = config or {}
        self.model = model or cfg.get("model", DEFAULT_MODEL)
        self.restricted_modules = restricted_modules or cfg.get(
            "restricted_modules", []
        )

        # ADK setup
        self.session_service = InMemorySessionService()
        self.app_name = cfg.get("app_name", DEFAULT_APP_NAME)
        self.user_id = cfg.get("user_id", DEFAULT_USER_ID)

        # Initialize LLM agent + runner
        self.agent = LlmAgent(
            name=f"{name}_agent",
            model=self.model,
            tools=[built_in_code_execution],
            instruction=(
                "You are a secure Python code validator and executor. "
                "1) Review the code for safety or syntax issues. "
                "2) Fix any problems. "
                "3) Execute the code. "
                "4) Return only the execution result or a clear error."
            ),
            description="Validates, auto-fixes, and executes Python code via LLM.",
        )
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    async def _execute(self, inp: CodeExecutorInput) -> CodeExecutorOutput:
        # 1) Create a unique session
        session_id = f"session_{hash(inp.code)}"
        self.session_service.create_session(
            app_name=self.app_name, user_id=self.user_id, session_id=session_id
        )

        # 2) Build LLM prompt
        prompt = self._build_prompt(inp)
        message = types.Content(role="user", parts=[types.Part(text=prompt)])

        # 3) Stream and collect results
        code_variant = None
        exec_outcome = None
        exec_output = ""
        final_response = ""
        start = asyncio.get_event_loop().time()

        try:
            async for event in self.runner.run_async(
                user_id=self.user_id, session_id=session_id, new_message=message
            ):
                for part in event.content.parts or []:
                    if part.executable_code:
                        code_variant = part.executable_code.code
                    if part.code_execution_result:
                        exec_outcome = part.code_execution_result.outcome
                        exec_output = part.code_execution_result.output or ""
                    if part.text and event.is_final_response():
                        final_response = part.text.strip()

            elapsed = asyncio.get_event_loop().time() - start

            # 4) Decide success/failure
            success = exec_outcome == "SUCCESS"
            # catch hidden errors in a successful run
            if success and exec_output:
                lowered = exec_output.lower()
                for kw in ("error:", "exception:", "traceback:"):
                    if kw in lowered:
                        self.logger.warning("LLM reported success but found error text")
                        break

            # extract specific error if failure
            error_msg = None
            if not success:
                match = re.search(
                    r"(error|exception):\s*(.*)", exec_output, re.IGNORECASE
                )
                error_msg = (
                    match.group(2).strip() if match else exec_output or final_response
                )

            return CodeExecutorOutput(
                result=exec_output or final_response or "",
                success=success,
                error=None if success else error_msg,
                stdout=exec_output if success else "",
                stderr=exec_output if not success else "",
                execution_time=elapsed,
                validated_code=code_variant or inp.code,
            )

        finally:
            # always tear down session
            try:
                self.session_service.delete_session(
                    app_name=self.app_name, user_id=self.user_id, session_id=session_id
                )
            except Exception as e:
                self.logger.warning("Failed to clean session: %s", e)

    def _build_prompt(self, inp: CodeExecutorInput) -> str:
        parts = [
            "Validate and execute this Python code safely:",
            "\n```python",
            inp.code,
            "```",
        ]
        if inp.context_variables:
            parts.append("\n# Context variables:")
            for k, v in inp.context_variables.items():
                parts.append(f"{k} = {v!r}")
        if inp.timeout:
            parts.append(f"\n# Timeout: {inp.timeout}s")
        if self.restricted_modules:
            parts.append("\n# Disallowed imports:")
            for m in self.restricted_modules:
                parts.append(f"- {m}")
        return "\n".join(parts)
