# utils/rest_api_caller_factory.py

from typing import Dict, List, Optional, Any
import re
import urllib.parse

from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.rest_api_caller import RestRequest, RestApiCallerInput
from tools.rest_api_caller import RestApiCallerTool


class RestApiCallerFactory:
    """
    Factory class that creates RestApiCallerTool instances from OpenAPI specifications.
    """

    def __init__(
        self,
        server_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        """
        Initialize the factory with base settings for all generated tools.

        Args:
            server_url: Base URL for the API server
            default_headers: Headers to include in all requests
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
            cache_enabled: Enable response caching
        """
        self.server_url = server_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.config = {"timeout": timeout}
        self.verbose = verbose
        self.cache_enabled = cache_enabled

    def create_tool_from_endpoint(
        self, endpoint: EndpointInfo, tool_id: Optional[str] = None
    ) -> RestApiCallerTool:
        """
        Create a RestApiCallerTool instance for a specific endpoint.

        Args:
            endpoint: The endpoint information from OpenAPI spec
            tool_id: Optional identifier for the tool

        Returns:
            A configured RestApiCallerTool for the endpoint
        """
        # Generate a reasonable name for the tool if not provided
        name = (
            tool_id or f"{endpoint.method.lower()}_{self._path_to_name(endpoint.path)}"
        )

        # Create detailed description based on endpoint info
        description = self._build_description(endpoint)

        # Create a tool specialized for this endpoint
        tool = EndpointSpecificRestApiCallerTool(
            name=name,
            description=description,
            endpoint=endpoint,
            server_url=self.server_url,
            default_headers=self.default_headers,
            config=self.config,
            verbose=self.verbose,
            cache_enabled=self.cache_enabled,
        )

        return tool

    def create_tools_from_endpoints(
        self, endpoints: List[EndpointInfo]
    ) -> Dict[str, RestApiCallerTool]:
        """
        Create a dictionary of RestApiCallerTool instances from a list of endpoints.

        Args:
            endpoints: List of endpoint information from OpenAPI spec

        Returns:
            Dictionary mapping tool names to RestApiCallerTool instances
        """
        tools = {}

        for endpoint in endpoints:
            # Generate a unique name for each endpoint
            name = f"{endpoint.method.lower()}_{self._path_to_name(endpoint.path)}"
            tool = self.create_tool_from_endpoint(endpoint, name)
            tools[name] = tool

        return tools

    def _path_to_name(self, path: str) -> str:
        """Convert API path to a valid Python identifier for the tool name."""
        # Replace path parameters like {id} with '_id_'
        path = re.sub(r"{([^}]+)}", r"_\1_", path)
        # Replace special characters with underscores
        path = re.sub(r"[^a-zA-Z0-9_]", "_", path)
        # Remove leading/trailing underscores and collapse multiple underscores
        path = re.sub(r"_+", "_", path).strip("_")
        return path

    def _build_description(self, endpoint: EndpointInfo) -> str:
        """Build a detailed description for the tool based on endpoint info."""
        desc = [f"[{endpoint.method.upper()}] {endpoint.path}"]

        if endpoint.description:
            desc.append(endpoint.description)

        # Input parameters information
        if endpoint.input_schema:
            desc.append("\nParameters:")
            if "properties" in endpoint.input_schema:
                for name, details in endpoint.input_schema["properties"].items():
                    param_desc = details.get("description", "")
                    required = (
                        " (required)"
                        if name in endpoint.input_schema.get("required", [])
                        else ""
                    )
                    desc.append(f"- {name}{required}: {param_desc}")

        # Authentication requirements
        if endpoint.auth_required:
            auth_type = endpoint.auth_type.value if endpoint.auth_type else "unknown"
            desc.append(f"\nAuthentication required: {auth_type}")

        return "\n".join(desc)


class EndpointSpecificRestApiCallerTool(RestApiCallerTool):
    """
    A specialized RestApiCallerTool that's configured for a specific API endpoint.
    """

    def __init__(
        self,
        name: str,
        description: str,
        endpoint: EndpointInfo,
        server_url: str,
        default_headers: Dict[str, str],
        config: Optional[dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        """Initialize with endpoint-specific configuration."""
        super().__init__(
            name=name,
            description=description,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        self.endpoint = endpoint
        self.server_url = server_url
        self.default_headers = default_headers

    async def execute(self, inp: Any) -> Any:
        """
        Execute the API call with proper input validation handling.

        This method handles both direct parameter dictionaries and properly
        formatted RestApiCallerInput objects.
        """
        # If input is not already a RestApiCallerInput, process it appropriately
        if not isinstance(inp, RestApiCallerInput):
            # Create RestRequest from input parameters
            request = self._build_request(inp)
            # Then create the proper input object
            inp = RestApiCallerInput(request=request)

        # Now call the parent execute method with properly formatted input
        return await super().execute(inp)

    async def _execute(self, inp: RestApiCallerInput) -> Any:
        """
        Execute the API call for this specific endpoint.

        The input has already been validated as a proper RestApiCallerInput.
        """
        # At this point, inp is guaranteed to be a RestApiCallerInput
        req = inp.request
        return await super()._execute(inp)

    def _build_request(self, params: Any) -> RestRequest:
        """
        Build a RestRequest object from input parameters.

        Maps the input parameters to the appropriate parts of the request
        based on the OpenAPI endpoint specification.
        """
        # Start with the full URL
        url = f"{self.server_url}{self.endpoint.path}"

        # Initialize request components
        headers = dict(self.default_headers)
        query_params = {}
        path_params = {}
        json_body = None

        # Extract path parameters
        path_param_names = re.findall(r"{([^}]+)}", self.endpoint.path)

        # Process parameters based on their location (path, query, body)
        if hasattr(params, "dict"):  # If it's a Pydantic model
            param_dict = params.dict(exclude_unset=True)
        else:
            param_dict = params if isinstance(params, dict) else vars(params)

        # First, extract and apply path parameters
        for name in path_param_names:
            # Convert camelCase/snake_case differences if needed
            snake_name = name.replace("-", "_")
            camel_name = "".join(
                word.capitalize() if i > 0 else word
                for i, word in enumerate(snake_name.split("_"))
            )

            # Try different name variations
            param_value = None
            for param_name in [name, snake_name, camel_name]:
                if param_name in param_dict:
                    param_value = param_dict[param_name]
                    path_params[name] = param_value
                    # Remove from params so we don't process it again
                    param_dict.pop(param_name, None)
                    break

        # Apply path parameters to the URL
        for name, value in path_params.items():
            placeholder = f"{{{name}}}"
            url = url.replace(placeholder, urllib.parse.quote(str(value)))

        # Process remaining parameters based on the OpenAPI spec
        for param_name, param_value in param_dict.items():
            # Skip None values
            if param_value is None:
                continue

            # Determine parameter location (query vs. body)
            # For simplicity, we'll put everything that's not a path parameter in either query or body
            # based on HTTP method
            if self.endpoint.method.upper() in ["GET", "DELETE"]:
                # For GET/DELETE, parameters go in query string
                query_params[param_name] = param_value
            else:
                # For other methods, we'll put them in the JSON body if they're not path parameters
                if json_body is None:
                    json_body = {}
                json_body[param_name] = param_value

        # Create and return the RestRequest
        return RestRequest(
            method=self.endpoint.method,
            url=url,
            headers=headers if headers else None,
            params=query_params if query_params else None,
            json=json_body,
        )
