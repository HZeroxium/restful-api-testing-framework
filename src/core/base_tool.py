# core/base_tool.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union
from pydantic import ValidationError
import time

from ..schemas.core import ToolInput, ToolOutput
from ..common.logger import LoggerFactory, LoggerType, LogLevel


class BaseTool(ABC):
    """Base class for all tools in the framework."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Type[ToolInput] = ToolInput,
        output_schema: Type[ToolOutput] = ToolOutput,
        config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
        cache_ttl: int = 300,  # 5 minutes
    ):
        """Initialize the tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: Pydantic model for validating inputs
            output_schema: Pydantic model for validating outputs
            config: Configuration parameters
            verbose: Whether to log detailed information
            cache_enabled: Whether to cache tool execution results
            cache_ttl: Time-to-live for cached results in seconds
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.config = config or {}
        self.verbose = verbose

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}", logger_type=LoggerType.STANDARD, level=log_level
        )

        # Cache configuration
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._cache = {}  # {input_hash: (output, timestamp)}

    @abstractmethod
    async def _execute(self, input_data: ToolInput) -> Any:
        """Execute the tool's core logic.

        Args:
            input_data: Validated input data

        Returns:
            Raw output data
        """
        pass

    async def execute(self, input_data: Union[Dict[str, Any], ToolInput]) -> ToolOutput:
        """Execute the tool with validation and error handling.

        Args:
            input_data: The input data for the tool

        Returns:
            The tool's output
        """
        start_time = time.time()

        try:
            # Validate input if it's a dict
            if isinstance(input_data, dict):
                validated_input = self.input_schema(**input_data)
            else:
                validated_input = input_data

            # self.logger.info(f"Executing tool: {self.name}")
            self.logger.debug(f"Input: {validated_input}")

            # Check if result is cached
            if self.cache_enabled:
                cache_key = self._get_cache_key(validated_input)
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    self.logger.debug("Using cached result")
                    return cached_result

            # Execute the core logic
            raw_output = await self._execute(validated_input)

            # Validate and structure the output
            if isinstance(raw_output, dict):
                output = self.output_schema(**raw_output)
            elif isinstance(raw_output, self.output_schema):
                output = raw_output
            else:
                # Handle primitive return types or other structures
                output = self.output_schema(result=raw_output)

            # Cache the result
            if self.cache_enabled:
                self._add_to_cache(cache_key, output)

            execution_time = time.time() - start_time
            # self.logger.info(f"Tool {self.name} completed in {execution_time:.2f}s")
            self.logger.debug(f"Output: {output}")

            return output

        except ValidationError as e:
            self.logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error during tool execution: {e}")
            raise

    def _get_cache_key(self, input_data: ToolInput) -> str:
        """Generate a cache key from input data."""
        try:
            # Use JSON string representation which is always hashable
            return str(hash(input_data.model_dump_json()))
        except Exception as e:
            # Fallback in case of serialization issues
            self.logger.warning(f"Error generating cache key: {e}")
            return str(id(input_data))  # Use object ID as fallback

    def _get_from_cache(self, key: str) -> Optional[ToolOutput]:
        """Get a result from cache if it exists and is not expired."""
        if key in self._cache:
            output, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return output
            else:
                # Remove expired entry
                del self._cache[key]
        return None

    def _add_to_cache(self, key: str, output: ToolOutput) -> None:
        """Add a result to the cache."""
        self._cache[key] = (output, time.time())

    def clear_cache(self) -> None:
        """Clear the tool's cache."""
        self._cache = {}

    async def cleanup(self) -> None:
        """Clean up resources used by the tool."""
        # Default implementation does nothing
        pass

    def get_schema_description(self) -> Dict[str, Any]:
        """Get a description of the tool's input and output schemas."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }
