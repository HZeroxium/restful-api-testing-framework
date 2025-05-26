# tools/test_case_generator.py

from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.test_case_generator import (
    TestCaseGeneratorInput,
    TestCaseGeneratorOutput,
    TestCase,
)
from schemas.tools.test_script_generator import TestScriptGeneratorInput
from tools.test_script_generator import TestScriptGeneratorTool


class TestCaseGeneratorTool(BaseTool):
    """
    Tool for generating complete test cases with validation scripts.
    This combines test data and validation scripts into a single test case.
    """

    def __init__(
        self,
        *,
        name: str = "test_case_generator",
        description: str = "Generates test cases with validation scripts",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestCaseGeneratorInput,
            output_schema=TestCaseGeneratorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        # Initialize the test script generator tool
        self.test_script_generator = TestScriptGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(self, inp: TestCaseGeneratorInput) -> TestCaseGeneratorOutput:
        """Generate a complete test case with validation scripts."""
        # The test data is already provided in the input
        test_data = inp.test_data

        # Override name and description if provided
        name = inp.name or test_data.name
        description = inp.description or test_data.description

        # Generate validation scripts for this test data
        script_input = TestScriptGeneratorInput(
            endpoint_info=inp.endpoint_info,
            test_data=test_data,  # Changed from test_case to test_data
        )
        script_output = await self.test_script_generator.execute(script_input)

        # Create the TestCase by combining test data with validation scripts
        test_case = TestCase(
            id=test_data.id,
            name=name,
            description=description,
            request_params=test_data.request_params,
            request_headers=test_data.request_headers,
            request_body=test_data.request_body,
            expected_status_code=test_data.expected_status_code,
            expected_response_schema=test_data.expected_response_schema,
            expected_response_contains=test_data.expected_response_contains,
            validation_scripts=script_output.validation_scripts,
        )

        return TestCaseGeneratorOutput(test_case=test_case)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        await self.test_script_generator.cleanup()
