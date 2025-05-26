# tools/test_suite_generator.py

from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_suite_generator import (
    TestSuiteGeneratorInput,
    TestSuiteGeneratorOutput,
    TestSuite,
)
from schemas.tools.test_case_generator import TestCase, TestCaseGeneratorInput
from schemas.tools.test_data_generator import TestDataGeneratorInput
from tools.test_data_generator import TestDataGeneratorTool
from tools.test_case_generator import TestCaseGeneratorTool


class TestSuiteGeneratorTool(BaseTool):
    """
    Tool for generating test suites for API endpoints.
    A test suite contains multiple test cases for a specific endpoint.
    """

    def __init__(
        self,
        *,
        name: str = "test_suite_generator",
        description: str = "Generates test suites for API endpoints",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestSuiteGeneratorInput,
            output_schema=TestSuiteGeneratorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        # Initialize the required tools
        self.test_data_generator = TestDataGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        self.test_case_generator = TestCaseGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(self, inp: TestSuiteGeneratorInput) -> TestSuiteGeneratorOutput:
        """Generate a test suite for the given endpoint."""
        # Step 1: Use the test data generator to create raw test data
        test_data_input = TestDataGeneratorInput(
            endpoint_info=inp.endpoint_info,
            test_case_count=inp.test_case_count,
            include_invalid_data=inp.include_invalid_data,
        )
        test_data_output = await self.test_data_generator.execute(test_data_input)

        # Step 2: Transform each test data into a test case using the TestCaseGenerator
        test_cases: List[TestCase] = []
        for test_data in test_data_output.test_data_collection:
            case_input = TestCaseGeneratorInput(
                endpoint_info=inp.endpoint_info,
                test_data=test_data,
                # Let the TestCaseGenerator use default name and description from test_data
            )
            case_output = await self.test_case_generator.execute(case_input)
            test_cases.append(case_output.test_case)

        # Step 3: Create a test suite with the generated test cases
        test_suite = TestSuite(
            endpoint_info=inp.endpoint_info,
            test_cases=test_cases,
            name=f"Test suite for {inp.endpoint_info.method.upper()} {inp.endpoint_info.path}",
            description=f"Automated test suite for endpoint {inp.endpoint_info.method.upper()} {inp.endpoint_info.path}",
        )

        return TestSuiteGeneratorOutput(test_suite=test_suite)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        await self.test_data_generator.cleanup()
        await self.test_case_generator.cleanup()
