"""
REST API Agent implementation that works with RestApiTool objects from OpenAPIToolset.
"""

import re
from typing import Any, Dict, List, Optional, Union

from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import (
    RestApiTool,
)

from core import BaseAgent
from schemas.core import AgentInput, AgentOutput


class RestApiAgent(BaseAgent):
    """
    An agent that works with auto-generated RestApiTool instances from OpenAPIToolset.
    Allows execution of REST API calls via natural language or direct endpoint references.
    """

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        name: str = "rest_api_agent",
        description: str = "Executes REST API operations from OpenAPI specs",
        tools: Optional[List[RestApiTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        verbose: bool = False,
    ):
        """Initialize the RestApiAgent with tools and configuration."""
        super().__init__(
            name=name,
            description=description,
            tools=tools or [],  # Will be populated with RestApiTool instances
            config=config or {},
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.model_name = model_name
        self.tools_by_path = self._index_tools_by_path()

    def _index_tools_by_path(self) -> Dict[str, RestApiTool]:
        """Create an index of tools by their HTTP method and path."""
        result = {}
        for tool in self.tools:
            if not isinstance(tool, RestApiTool):
                continue

            # Extract method and path from the endpoint string
            endpoint_str = str(tool.endpoint)
            method_match = re.search(r"method='([^']*)'", endpoint_str)
            path_match = re.search(r"path='([^']*)'", endpoint_str)

            if method_match and path_match:
                method = method_match.group(1).upper()
                path = path_match.group(1)
                key = f"{method} {path}"
                result[key] = tool

                # Debug the available methods on this tool
                if self.verbose:
                    self.logger.debug(f"Tool methods for {key}: {dir(tool)}")
                    self.logger.debug(f"Endpoint methods: {dir(tool.endpoint)}")

        return result

    async def plan(self, input_data: AgentInput) -> List[Dict[str, Any]]:
        """
        Plan the actions to take based on the input query.
        For REST API agent, this means identifying which endpoint to call.
        """
        query = input_data.query.strip()
        actions = []

        # Direct endpoint reference pattern (e.g., "CALL GET /posts/1")
        direct_match = re.match(
            r"(?:CALL\s+)?(\w+)\s+(/\S+)(?:\s+(.*))?", query, re.IGNORECASE
        )
        if direct_match:
            method = direct_match.group(1).upper()
            path = direct_match.group(2)
            args_str = direct_match.group(3) or "{}"

            # Try to parse arguments if provided
            try:
                import json

                args = json.loads(args_str)
            except:
                args = {}

            endpoint_key = f"{method} {path}"
            exact_path_match = self.tools_by_path.get(endpoint_key)

            # If not exact match, try to match with path parameters
            if not exact_path_match:
                for key, tool in self.tools_by_path.items():
                    tool_method, tool_path = key.split(" ", 1)
                    if tool_method == method and self._match_path_pattern(
                        tool_path, path
                    ):
                        exact_path_match = tool
                        # Extract path parameters
                        path_params = self._extract_path_params(tool_path, path)
                        args.update(path_params)
                        break

            if exact_path_match:
                actions.append(
                    {
                        "tool": exact_path_match.name,
                        "tool_input": args,
                        "method": method,
                        "path": path,
                    }
                )
            else:
                actions.append(
                    {"error": f"No matching endpoint found for {method} {path}"}
                )
        else:
            # Fallback to simple method+path extraction
            for tool in self.tools:
                if (
                    tool.name.lower() in query.lower()
                    or tool.description.lower() in query.lower()
                ):
                    actions.append(
                        {
                            "tool": tool.name,
                            "tool_input": {},
                            "description": tool.description,
                        }
                    )
                    break

            if not actions:
                actions.append(
                    {
                        "error": f"Could not determine which API endpoint to call from: {query}"
                    }
                )

        return actions

    def _match_path_pattern(self, pattern: str, actual_path: str) -> bool:
        """Check if actual_path matches the pattern with path parameters."""
        # Convert pattern like /users/{id} to regex /users/([^/]+)
        regex_pattern = re.sub(r"{([^}]+)}", r"([^/]+)", pattern)
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, actual_path))

    def _extract_path_params(self, pattern: str, actual_path: str) -> Dict[str, str]:
        """Extract path parameters from actual_path based on pattern."""
        params = {}
        # Extract parameter names from pattern
        param_names = re.findall(r"{([^}]+)}", pattern)

        # Convert pattern to regex with capturing groups
        regex_pattern = re.sub(r"{([^}]+)}", r"([^/]+)", pattern)
        regex_pattern = f"^{regex_pattern}$"

        # Extract values using regex
        match = re.match(regex_pattern, actual_path)
        if match and param_names:
            for i, name in enumerate(param_names, 1):
                value = match.group(i)
                # Try to convert to int if possible
                try:
                    params[name] = int(value)
                except ValueError:
                    params[name] = value

        return params

    async def execute_action(self, action: Dict[str, Any]) -> Any:
        """Execute a single action, which involves calling a REST API endpoint."""
        if "error" in action:
            return {"error": action["error"]}

        tool_name = action.get("tool")
        tool_input = action.get("tool_input", {})

        for tool in self.tools:
            if tool.name == tool_name and isinstance(tool, RestApiTool):
                try:
                    # Debug log to inspect the tool and available methods
                    if self.verbose:
                        self.logger.debug(f"Tool {tool_name} type: {type(tool)}")
                        self.logger.debug(f"Tool methods: {dir(tool)}")
                        self.logger.debug(f"Tool input: {tool_input}")

                    # Create a dummy tool_context that RestApiTool expects
                    dummy_tool_context = {
                        "channel": {"user_id": "user1"},
                        "session_id": "session1",
                    }

                    # Get path and method information for better error reporting
                    method = action.get("method", "").upper()
                    path = action.get("path", "")

                    # Extract potential path parameters from the URL
                    # For example: /posts/1 for endpoint /posts/{id} needs {'id': 1}
                    path_params = {}
                    if path and "{" in tool.endpoint.path:
                        # Get the endpoint path pattern with parameters
                        endpoint_path = tool.endpoint.path

                        # Find parameter names in the pattern
                        param_names = re.findall(r"{([^}]+)}", endpoint_path)

                        # Create regex pattern to extract values
                        regex_pattern = (
                            "^" + re.sub(r"{([^}]+)}", r"([^/]+)", endpoint_path) + "$"
                        )

                        # Extract values using regex
                        match = re.match(regex_pattern, path)
                        if match and param_names:
                            for i, name in enumerate(param_names, 1):
                                value = match.group(i)
                                # Try to convert to int if possible
                                try:
                                    path_params[name] = int(value)
                                except ValueError:
                                    path_params[name] = value

                    # Merge path parameters into tool_input
                    tool_input.update(path_params)

                    # Call the tool correctly
                    self.logger.debug(
                        f"Calling {tool_name} with args={tool_input}, tool_context={dummy_tool_context}"
                    )
                    result = await self._call_tool_safely(
                        tool, tool_input, dummy_tool_context
                    )

                    return {
                        "success": True,
                        "result": result,
                        "tool": tool_name,
                        "method": method,
                        "path": path,
                    }
                except Exception as e:
                    self.logger.error(f"Error executing {tool_name}: {str(e)}")
                    return {"success": False, "error": str(e), "tool": tool_name}

        return {"error": f"Tool '{tool_name}' not found"}

    async def _call_tool_safely(self, tool, args, tool_context):
        """Safely call a RestApiTool with proper error handling and multiple calling conventions."""
        try:
            # First try: Using the endpoint's direct call method
            # This is the most likely to work based on error messages
            if hasattr(tool, "endpoint") and hasattr(tool.endpoint, "call"):
                self.logger.debug("Attempting to call via tool.endpoint.call")
                return await tool.endpoint.call(args=args, tool_context=tool_context)
        except Exception as e1:
            self.logger.warning(f"Endpoint call failed: {str(e1)}")

        try:
            # Second try: Call with tool.call method (newer ADK versions)
            self.logger.debug("Attempting to call via tool.call")
            return await tool.call(args=args, tool_context=tool_context)
        except Exception as e2:
            self.logger.warning(f"Tool.call method failed: {str(e2)}")

        try:
            # Third try: Use the direct execute method if available
            if hasattr(tool, "execute"):
                self.logger.debug("Attempting to call via tool.execute")
                return await tool.execute(args=args, tool_context=tool_context)
        except Exception as e3:
            self.logger.warning(f"Execute method failed: {str(e3)}")

        # If we reach here, all attempts failed
        raise Exception(
            f"All calling conventions failed for RestApiTool. Latest error: {str(e3 if 'e3' in locals() else e2 if 'e2' in locals() else e1)}"
        )

    def _get_tool_call_method(self, tool: RestApiTool, method: str):
        """Determine the best way to execute a RestApiTool."""
        # For Google ADK RestApiTool, the call method is the preferred way
        if hasattr(tool, "call"):
            return tool.call

        # Fallbacks in case the tool structure changes
        for method_name in ["execute_operation", "execute", method.lower()]:
            if hasattr(tool, method_name):
                return getattr(tool, method_name)

        # If tool has an endpoint attribute with a call method
        if hasattr(tool, "endpoint") and hasattr(tool.endpoint, "call"):
            return tool.endpoint.call

        # Last resort - use the operation_parser if available
        if hasattr(tool, "_operation_parser") and hasattr(
            tool._operation_parser, "call"
        ):
            return tool._operation_parser.call

        # No suitable method found
        raise AttributeError(f"Cannot determine how to execute tool {tool.name}")

    async def _arun(self, input_data: AgentInput) -> AgentOutput:
        """
        Plans actions based on input, executes them, and generates output.
        The main asynchronous method to run the agent's logic.
        """
        # Plan the actions
        actions = await self.plan(input_data)

        # Execute each action and collect results
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)

        # Generate and return the output
        return self._generate_output(results)

    def _generate_output(self, results: List[Any]) -> AgentOutput:
        """Generate the final output from action results."""
        if not results:
            return AgentOutput(response="No actions were executed.", tool_calls=[])

        # Process results
        tool_calls = []
        success_count = 0
        error_messages = []

        for result in results:
            if isinstance(result, dict):
                tool_calls.append(result)
                if result.get("success", False):
                    success_count += 1
                elif "error" in result:
                    error_messages.append(result["error"])

        # Generate human-readable response
        if success_count == len(results):
            response = f"Successfully executed {success_count} API calls."
            if success_count == 1 and "result" in results[0]:
                response += f"\nResult: {results[0]['result']}"
        else:
            response = f"Executed {len(results)} API calls with {success_count} successes and {len(error_messages)} failures."
            if error_messages:
                response += f"\nErrors: {'; '.join(error_messages)}"

        return AgentOutput(response=response, tool_calls=tool_calls)
