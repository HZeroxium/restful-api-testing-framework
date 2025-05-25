# tools/test_data_generator.py

import uuid
from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.openapi_parser import EndpointInfo
from schemas.tools.test_data_generator import (
    TestDataGeneratorInput,
    TestDataGeneratorOutput,
    TestCase,
)


class TestDataGeneratorTool(BaseTool):
    """
    Tool for generating test data for API endpoints.
    Currently returns mock data for demonstration purposes.
    """

    def __init__(
        self,
        *,
        name: str = "test_data_generator",
        description: str = "Generates test data for API endpoints",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestDataGeneratorInput,
            output_schema=TestDataGeneratorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(self, inp: TestDataGeneratorInput) -> TestDataGeneratorOutput:
        """Generate test data for the given endpoint."""
        endpoint = inp.endpoint_info
        test_cases = []

        # Mock implementation - just create basic test cases
        # In a real implementation, we'd analyze the input schema and generate appropriate test data

        # Generate a success test case
        test_cases.append(
            TestCase(
                id=str(uuid.uuid4()),
                name=f"Success test for {endpoint.name}",
                description=f"Test {endpoint.method} {endpoint.path} with valid data",
                request_params={} if endpoint.method.upper() == "GET" else None,
                request_headers=(
                    {"Authorization": "Bearer mock_token"}
                    if endpoint.auth_required
                    else {}
                ),
                request_body=(
                    {} if endpoint.method.upper() in ["POST", "PUT", "PATCH"] else None
                ),
                expected_status_code=(
                    200
                    if endpoint.method.upper() == "GET"
                    else 201 if endpoint.method.upper() == "POST" else 200
                ),
                expected_response_schema={},
            )
        )

        # Generate a validation error test case
        if inp.include_invalid_data and endpoint.method.upper() in [
            "POST",
            "PUT",
            "PATCH",
        ]:
            test_cases.append(
                TestCase(
                    id=str(uuid.uuid4()),
                    name=f"Validation error test for {endpoint.name}",
                    description=f"Test {endpoint.method} {endpoint.path} with invalid data",
                    request_params={},
                    request_headers=(
                        {"Authorization": "Bearer mock_token"}
                        if endpoint.auth_required
                        else {}
                    ),
                    request_body={"invalid_field": "invalid_value"},
                    expected_status_code=400,
                    expected_response_schema={},
                )
            )

        # Generate an unauthorized test case if auth is required
        if endpoint.auth_required:
            test_cases.append(
                TestCase(
                    id=str(uuid.uuid4()),
                    name=f"Unauthorized test for {endpoint.name}",
                    description=f"Test {endpoint.method} {endpoint.path} without authorization",
                    request_params={} if endpoint.method.upper() == "GET" else None,
                    request_headers={},  # No auth header
                    request_body=(
                        {}
                        if endpoint.method.upper() in ["POST", "PUT", "PATCH"]
                        else None
                    ),
                    expected_status_code=401,
                    expected_response_schema={},
                )
            )

        return TestDataGeneratorOutput(test_cases=test_cases)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
