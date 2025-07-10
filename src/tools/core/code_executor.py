# tools/code_executor.py

import asyncio
import re
import io
import contextlib
from typing import Any, Dict, List, Optional
import traceback

from ...core.base_tool import BaseTool
from ...schemas.tools.code_executor import CodeExecutorInput, CodeExecutorOutput
from ...common.logger import LoggerFactory, LoggerType, LogLevel


class CodeExecutorTool(BaseTool):
    """
    Validates & executes Python code via native Python execution.
    Executes Python functions with provided context variables and returns the result.
    """

    def __init__(
        self,
        *,
        name: str = "code_executor",
        description: str = "Python code validator & executor",
        config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
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

        # Initialize custom logger with enhanced file logging
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO

        # Ensure logs/tools directory exists
        from pathlib import Path

        logs_dir = Path("logs/tools")
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
            file_level=LogLevel.DEBUG,  # Always DEBUG to file for detailed debugging
            log_file=str(logs_dir / "code_executor.log"),
        )

        # Merge defaults with config
        cfg = config or {}
        self.restricted_modules = restricted_modules or cfg.get(
            "restricted_modules", []
        )
        self.timeout_seconds = cfg.get("timeout", 30)  # Default timeout: 30 seconds

    async def _execute(self, inp: CodeExecutorInput) -> CodeExecutorOutput:
        """Execute Python code natively"""
        self.logger.debug("Starting code execution")
        self.logger.debug(f"Code to execute:\n{inp.code}")
        self.logger.debug(
            f"Context variables: {inp.context_variables if inp.context_variables else 'None'}"
        )

        self.logger.add_context(
            code_length=len(inp.code),
            has_context_vars=bool(inp.context_variables),
            timeout=inp.timeout or self.timeout_seconds,
        )

        # Log detailed execution info for debugging
        self.logger.debug(f"=== CODE EXECUTION START ===")
        self.logger.debug(f"Code length: {len(inp.code)}")
        self.logger.debug(f"Has context vars: {bool(inp.context_variables)}")
        self.logger.debug(f"Timeout: {inp.timeout or self.timeout_seconds}")
        self.logger.debug(f"Context vars: {inp.context_variables}")

        result = await self._execute_native(inp)

        # Log execution results
        self.logger.debug(f"=== CODE EXECUTION END ===")
        self.logger.debug(f"Success: {result.success}")
        self.logger.debug(f"Result: {result.stdout}")
        self.logger.debug(f"Error: {result.error}")
        self.logger.debug(f"Execution time: {result.execution_time:.3f}s")
        self.logger.debug(f"Stdout: {result.stdout}")
        self.logger.debug(f"Stderr: {result.stderr}")

        return result

    async def _execute_native(self, inp: CodeExecutorInput) -> CodeExecutorOutput:
        """Execute Python code natively using Python's built-in functions"""
        code = inp.code
        context_vars = inp.context_variables or {}
        timeout = inp.timeout or self.timeout_seconds

        self.logger.debug("Preparing code execution environment")
        self.logger.debug(f"Context variables provided: {context_vars}")
        self.logger.add_context(context_var_count=len(context_vars))

        # Create a namespace for execution
        namespace = {**context_vars}
        self.logger.debug(f"Initial namespace keys: {list(namespace.keys())}")

        # Prepare output capturing
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Track execution time
        start = asyncio.get_event_loop().time()

        # Validate syntax first
        try:
            compiled_code = compile(code, "<string>", "exec")
            self.logger.debug("Code syntax validation successful")
        except SyntaxError as e:
            elapsed = asyncio.get_event_loop().time() - start
            self.logger.error(f"Syntax error in code: {str(e)}")
            self.logger.debug(f"Failed code:\n{code}")
            return CodeExecutorOutput(
                result="",
                success=False,
                error=f"Syntax error: {str(e)}",
                stdout="",
                stderr=str(e),
                execution_time=elapsed,
                validated_code=code,
            )

        # Check for restricted modules
        if self.restricted_modules:
            import_pattern = r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)"
            for line in code.split("\n"):
                match = re.match(import_pattern, line)
                if match:
                    module_name = match.group(1).split(".")[0]
                    if module_name in self.restricted_modules:
                        elapsed = asyncio.get_event_loop().time() - start
                        self.logger.warning(
                            f"Restricted module usage detected: {module_name}"
                        )
                        return CodeExecutorOutput(
                            result="",
                            success=False,
                            error=f"ImportError: Use of restricted module '{module_name}' is not allowed",
                            stdout="",
                            stderr=f"ImportError: Use of restricted module '{module_name}' is not allowed",
                            execution_time=elapsed,
                            validated_code=code,
                        )

        self.logger.debug(f"Starting code execution with timeout {timeout} seconds")

        # Execute with timeout and output capturing
        async def execute_with_timeout():
            try:
                with contextlib.redirect_stdout(
                    stdout_capture
                ), contextlib.redirect_stderr(stderr_capture):
                    # Execute the code in the namespace
                    exec(compiled_code, namespace)

                    # Check if the code defines any functions
                    functions = {
                        name: obj
                        for name, obj in namespace.items()
                        if callable(obj)
                        and name not in context_vars
                        and not name.startswith("__")
                    }

                    # If there's a function defined and no explicit _result,
                    # try to execute the first function with available context
                    result = namespace.get("_result", None)
                    if result is None and functions:
                        # Get the first defined function
                        func_name, func = next(iter(functions.items()))
                        self.logger.debug(f"Executing function: {func_name}")

                        # Check if we have matching parameters for this function
                        import inspect

                        sig = inspect.signature(func)
                        params = sig.parameters

                        # If we have parameters to pass
                        if params:
                            # Try to match parameter names with context variables
                            args = {}
                            for param_name in params:
                                if param_name in context_vars:
                                    args[param_name] = context_vars[param_name]

                            # Execute the function with matched args
                            if args:
                                self.logger.debug(
                                    f"Calling function with args: {list(args.keys())}"
                                )
                                result = func(**args)
                            else:
                                # Try to execute without args if no match found
                                self.logger.debug("Calling function without args")
                                result = func()
                        else:
                            # Function takes no arguments
                            self.logger.debug("Calling function with no parameters")
                            result = func()

                    return True, result
            except Exception as e:
                self.logger.debug(f"Code execution error: {str(e)}")
                return False, e

        try:
            success, result = await asyncio.wait_for(
                execute_with_timeout(), timeout=timeout
            )
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start
            self.logger.error(f"Code execution timed out after {timeout} seconds")
            return CodeExecutorOutput(
                result="",
                success=False,
                error=f"Execution timed out after {timeout} seconds",
                stdout=stdout_capture.getvalue(),
                stderr=f"TimeoutError: Execution exceeded {timeout} seconds",
                execution_time=elapsed,
                validated_code=code,
            )

        elapsed = asyncio.get_event_loop().time() - start
        stdout_value = stdout_capture.getvalue()
        stderr_value = stderr_capture.getvalue()

        if success:
            # If result is an exception, it's a failure
            if isinstance(result, Exception):
                error_msg = str(result)
                self.logger.error(f"Code execution resulted in exception: {error_msg}")
                self.logger.debug(f"Exception type: {type(result).__name__}")
                self.logger.debug(f"Stdout: {stdout_value}")
                self.logger.debug(f"Stderr: {stderr_value}")
                return CodeExecutorOutput(
                    result="",
                    success=False,
                    error=error_msg,
                    stdout=stdout_value,
                    stderr=stderr_value or error_msg,
                    execution_time=elapsed,
                    validated_code=code,
                )

            # Success case - return the result or stdout if result is None
            # self.logger.info(f"Code execution successful in {elapsed:.3f}s")
            self.logger.debug(f"Result type: {type(result).__name__}")
            self.logger.debug(f"Result value: {result}")
            self.logger.debug(f"Stdout: {stdout_value}")
            self.logger.debug(f"Stderr: {stderr_value}")

            # Determine final result value
            final_result = str(result) if result is not None else stdout_value
            self.logger.debug(f"Final result returned: {final_result}")

            return CodeExecutorOutput(
                result=final_result,
                success=True,
                error=None,
                stdout=stdout_value,
                stderr=stderr_value,
                execution_time=elapsed,
                validated_code=code,
            )
        else:
            # Handle execution error
            error_msg = (
                str(result) if isinstance(result, Exception) else "Execution failed"
            )
            tb = ""
            if isinstance(result, Exception):
                tb = "".join(
                    traceback.format_exception(
                        type(result), result, result.__traceback__
                    )
                )
            self.logger.error(f"Code execution failed: {error_msg}")
            self.logger.debug(
                f"Error type: {type(result).__name__ if isinstance(result, Exception) else 'Unknown'}"
            )
            self.logger.debug(f"Traceback: {tb}")
            self.logger.debug(f"Stdout: {stdout_value}")
            self.logger.debug(f"Stderr: {stderr_value}")
            return CodeExecutorOutput(
                result="",
                success=False,
                error=error_msg,
                stdout=stdout_value,
                stderr=tb or error_msg,
                execution_time=elapsed,
                validated_code=code,
            )
