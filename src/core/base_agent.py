# core/base_agent.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from schemas.core import AgentInput, AgentOutput, AgentState
from core import BaseTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class BaseAgent(ABC):
    """Base class for all agents in the framework."""

    def __init__(
        self,
        name: str,
        description: str,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        verbose: bool = False,
    ):
        """Initialize the agent with tools and configuration.

        Args:
            name: Agent name
            description: Agent description
            tools: List of tools available to this agent
            config: Configuration parameters
            max_iterations: Maximum number of reasoning iterations
            verbose: Whether to log detailed information
        """
        self.name = name
        self.description = description
        self.tools = tools or []
        self.config = config or {}
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.state = AgentState()

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"agent.{name}", logger_type=LoggerType.STANDARD, level=log_level
        )

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent's toolset."""
        self.tools.append(tool)

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Get a tool by its name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    @abstractmethod
    async def plan(self, input_data: AgentInput) -> List[Dict[str, Any]]:
        """Plan the actions to take based on input.

        Args:
            input_data: The input data for the agent

        Returns:
            A list of actions to take
        """
        pass

    @abstractmethod
    async def execute_action(self, action: Dict[str, Any]) -> Any:
        """Execute a single action.

        Args:
            action: The action to execute

        Returns:
            The result of the action
        """
        pass

    async def run(self, input_data: Union[Dict[str, Any], AgentInput]) -> AgentOutput:
        """Run the agent on the given input.

        Args:
            input_data: The input data for the agent

        Returns:
            The agent's output
        """
        try:
            # Validate input if it's a dict
            if isinstance(input_data, dict):
                input_data = AgentInput(**input_data)

            # Initialize state for this run
            self.state.clear()
            self.state.input = input_data

            # Log the start of agent execution
            self.logger.info(f"Starting agent: {self.name}")
            self.logger.debug(f"Input: {input_data}")

            # Plan actions
            actions = await self.plan(input_data)

            # Execute actions
            results = []
            for action in actions:
                action_result = await self.execute_action(action)
                results.append(action_result)
                self.state.action_history.append(
                    {"action": action, "result": action_result}
                )

            # Generate final output
            output = self._generate_output(results)
            self.state.output = output

            self.logger.info(f"Agent {self.name} completed successfully")
            self.logger.debug(f"Output: {output}")

            return output

        except ValidationError as e:
            self.logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error during agent execution: {e}")
            raise

    @abstractmethod
    def _generate_output(self, results: List[Any]) -> AgentOutput:
        """Generate the final output from action results.

        Args:
            results: Results from executed actions

        Returns:
            Final agent output
        """
        pass

    def get_available_tools_description(self) -> str:
        """Get descriptions of all available tools."""
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)

    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        for tool in self.tools:
            await tool.cleanup()
