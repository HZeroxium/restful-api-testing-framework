# tools/test_collection_generator.py

from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.test_collection_generator import (
    TestCollectionGeneratorInput,
    TestCollectionGeneratorOutput,
    TestCollection,
)
from schemas.tools.test_suite_generator import TestSuiteGeneratorInput
from tools.test_suite_generator import TestSuiteGeneratorTool


class TestCollectionGeneratorTool(BaseTool):
    """
    Tool for generating test collections across multiple endpoints.
    """

    def __init__(
        self,
        *,
        name: str = "test_collection_generator",
        description: str = "Generates test collections across multiple endpoints",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestCollectionGeneratorInput,
            output_schema=TestCollectionGeneratorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        # Initialize the test suite generator tool
        self.test_suite_generator = TestSuiteGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(
        self, inp: TestCollectionGeneratorInput
    ) -> TestCollectionGeneratorOutput:
        """Generate a test collection across multiple endpoints."""
        test_suites = []

        # Generate a test suite for each endpoint
        for endpoint in inp.endpoints:
            suite_input = TestSuiteGeneratorInput(
                endpoint_info=endpoint,
                test_case_count=inp.test_case_count,
                include_invalid_data=inp.include_invalid_data,
            )
            suite_output = await self.test_suite_generator.execute(suite_input)
            test_suites.append(suite_output.test_suite)

        # Create the test collection
        test_collection = TestCollection(
            name=f"Test collection for {inp.api_name} v{inp.api_version}",
            description=f"Automated test collection for {inp.api_name} API v{inp.api_version}",
            test_suites=test_suites,
        )

        return TestCollectionGeneratorOutput(test_collection=test_collection)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        await self.test_suite_generator.cleanup()
