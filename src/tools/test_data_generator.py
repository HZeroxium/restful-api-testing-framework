# tools/test_data_generator.py

import uuid
import json
from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_data_generator import (
    TestDataGeneratorInput,
    TestDataGeneratorOutput,
    TestData,
)


class TestDataGeneratorTool(BaseTool):
    """
    Tool for generating intelligent test data for API endpoints using LLM.
    This tool analyzes API schemas and generates realistic test scenarios.
    """

    def __init__(
        self,
        *,
        name: str = "test_data_generator",
        description: str = "Generates intelligent test data for API endpoints",
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
        """Generate test data for the given endpoint using LLM."""
        # Get endpoint info using the property getter
        endpoint = (
            inp.get_endpoint_info
            if hasattr(inp, "get_endpoint_info")
            else inp.endpoint_info
        )
        test_case_count = inp.test_case_count
        include_invalid_data = inp.include_invalid_data

        if self.verbose:
            print(
                f"Generating {test_case_count} test cases for {endpoint.method.upper()} {endpoint.path}"
                f" (include invalid data: {include_invalid_data})"
            )

        # Try to generate test data using LLM
        try:
            test_data_collection = await self._generate_llm_test_data(
                endpoint, test_case_count, include_invalid_data
            )

            # Validate and ensure we have the correct number of test cases
            if len(test_data_collection) < test_case_count:
                if self.verbose:
                    print(
                        f"LLM returned {len(test_data_collection)} test cases, but {test_case_count} were requested. "
                        "Generating additional test cases using fallback method."
                    )
                # Generate additional test cases to meet the requested count
                fallback_count = test_case_count - len(test_data_collection)
                fallback_data = self._generate_fallback_test_data(
                    endpoint, fallback_count, include_invalid_data
                )
                test_data_collection.extend(fallback_data.test_data_collection)

            return TestDataGeneratorOutput(test_data_collection=test_data_collection)
        except Exception as e:
            if self.verbose:
                print(
                    f"Error during LLM test data generation: {str(e)}. Using fallback test data."
                )
            return self._generate_fallback_test_data(
                endpoint, test_case_count, include_invalid_data
            )

    async def _generate_llm_test_data(
        self, endpoint, test_case_count, include_invalid_data
    ) -> List[TestData]:
        """Generate test data using LLM with improved error handling."""
        from utils.llm_utils import create_and_execute_llm_agent

        # Prepare the endpoint info as JSON for the LLM prompt
        endpoint_json = {
            "method": endpoint.method,
            "path": endpoint.path,
            "description": endpoint.description,
            "input_schema": endpoint.input_schema,
            "output_schema": endpoint.output_schema,
            "auth_required": endpoint.auth_required,
            "auth_type": endpoint.auth_type,
            "tags": endpoint.tags,
        }

        # Prepare a structured prompt with clear instructions and expected output format
        prompt = f"""You are a Test Data Generator for API testing. Your task is to create realistic test data for API endpoints.

INPUT:
I'm providing information about an API endpoint:
{json.dumps(endpoint_json, indent=2)}

I need you to generate {test_case_count} test cases for this endpoint.
{"Include some invalid test data for negative testing." if include_invalid_data else "All test cases should be valid."}

OUTPUT:
Return a JSON object with an array of test cases using EXACTLY this format:
```json
{{
  "test_cases": [
    {{
      "name": "Get all products - basic request",
      "description": "Verify retrieving all products with default parameters",
      "request_params": {{"page": 1}},
      "request_headers": {{"Authorization": "Bearer valid_token"}},
      "request_body": null,
      "expected_status_code": 200,
      "expected_response_schema": {{"type": "object"}},
      "expected_response_contains": ["data", "current_page"],
      "is_valid_request": true
    }},
    // Additional test cases...
  ]
}}
```
GUIDELINES:
- For {endpoint.method} requests, focus on {'query parameters' if endpoint.method.upper() == 'GET' else 'request body data'}
- {'Create invalid test cases that should trigger error responses' if include_invalid_data else 'Create valid test cases with different parameter combinations'}
- For valid cases, use expected_status_code 200 for GET, 201 for POST, etc.
- For invalid cases, use status codes like 400, 401, 403, 404, etc.
- {"Include authorization headers since auth is required" if endpoint.auth_required else "No authorization is required for this endpoint"}
- Test parameters with different values and combinations
- Each test case should be realistic and test a specific scenario

Review your JSON output before responding to ensure it's valid and matches the requested format exactly.
"""

        # Execute LLM agent
        raw_json = await create_and_execute_llm_agent(
            app_name="test_data_generator",
            agent_name="llm_test_data_generator",
            instruction="You are an API test data generator. Generate test cases in the format requested.",
            input_data=prompt,
            timeout=60.0,
            max_retries=2,
            retry_delay=1.0,
            verbose=self.verbose,
        )

        if raw_json is None:
            if self.verbose:
                print("No response received from LLM")
            return []

        # Convert LLM output to TestData objects
        test_data_collection = []

        if "test_cases" in raw_json:
            for test_case in raw_json["test_cases"]:
                # Ensure all required fields are present
                name = test_case.get(
                    "name", f"Test case for {endpoint.method} {endpoint.path}"
                )
                description = test_case.get(
                    "description", f"Testing {endpoint.method} {endpoint.path}"
                )
                expected_status_code = test_case.get("expected_status_code", 200)

                # Create TestData object
                test_data = TestData(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description,
                    request_params=test_case.get("request_params"),
                    request_headers=test_case.get("request_headers"),
                    request_body=test_case.get("request_body"),
                    expected_status_code=expected_status_code,
                    expected_response_schema=test_case.get("expected_response_schema"),
                    expected_response_contains=test_case.get(
                        "expected_response_contains"
                    ),
                )
                test_data_collection.append(test_data)

        return test_data_collection

    def _generate_fallback_test_data(
        self, endpoint, test_case_count: int, include_invalid_data: bool
    ) -> TestDataGeneratorOutput:
        """Generate basic test data as a fallback when LLM fails."""
        test_data_collection = []

        # Always include at least one success case
        test_data_collection.append(
            TestData(
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

        # Add invalid data test if requested
        if include_invalid_data and test_case_count > 1:
            # Validation error test
            if endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
                test_data_collection.append(
                    TestData(
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

            # Unauthorized test if auth is required
            if endpoint.auth_required and len(test_data_collection) < test_case_count:
                test_data_collection.append(
                    TestData(
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

            # Not found test for GET requests with IDs
            if (
                endpoint.method.upper() == "GET"
                and ("{id}" in endpoint.path or "/:id" in endpoint.path)
                and len(test_data_collection) < test_case_count
            ):
                test_data_collection.append(
                    TestData(
                        id=str(uuid.uuid4()),
                        name=f"Not found test for {endpoint.name}",
                        description=f"Test {endpoint.method} {endpoint.path} with non-existent ID",
                        request_params={},
                        request_headers=(
                            {"Authorization": "Bearer mock_token"}
                            if endpoint.auth_required
                            else {}
                        ),
                        request_body=None,
                        expected_status_code=404,
                        expected_response_schema={},
                    )
                )

        # Fill remaining slots with variations of success cases if needed
        while len(test_data_collection) < test_case_count:
            test_data_collection.append(
                TestData(
                    id=str(uuid.uuid4()),
                    name=f"Success test variant for {endpoint.name} (#{len(test_data_collection)+1})",
                    description=f"Additional test for {endpoint.method} {endpoint.path} with valid data",
                    request_params={} if endpoint.method.upper() == "GET" else None,
                    request_headers=(
                        {"Authorization": "Bearer mock_token"}
                        if endpoint.auth_required
                        else {}
                    ),
                    request_body=(
                        {}
                        if endpoint.method.upper() in ["POST", "PUT", "PATCH"]
                        else None
                    ),
                    expected_status_code=(
                        200
                        if endpoint.method.upper() == "GET"
                        else 201 if endpoint.method.upper() == "POST" else 200
                    ),
                    expected_response_schema={},
                )
            )

        return TestDataGeneratorOutput(test_data_collection=test_data_collection)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
