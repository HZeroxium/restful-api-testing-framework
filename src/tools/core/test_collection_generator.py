# tools/test_collection_generator.py

from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.test_collection_generator import (
    TestCollectionGeneratorInput,
    TestCollectionGeneratorOutput,
    TestCollection,
)
from schemas.tools.test_suite_generator import TestSuiteGeneratorInput
from tools.core.test_suite_generator import TestSuiteGeneratorTool
from common.logger import LoggerFactory, LoggerType, LogLevel


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

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize the test suite generator tool
        self.test_suite_generator = TestSuiteGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

    async def _execute(
        self, inp: TestCollectionGeneratorInput
    ) -> TestCollectionGeneratorOutput:
        """Generate a test collection across multiple endpoints."""
        self.logger.info(
            f"Generating test collection for {inp.api_name} v{inp.api_version}"
        )
        self.logger.add_context(
            api_name=inp.api_name,
            api_version=inp.api_version,
            endpoint_count=len(inp.endpoints),
            test_case_count=inp.test_case_count,
            include_invalid_data=inp.include_invalid_data,
        )

        test_suites = []

        # Generate a test suite for each endpoint
        for i, endpoint in enumerate(inp.endpoints):
            self.logger.debug(
                f"Processing endpoint {i+1}/{len(inp.endpoints)}: {endpoint.method.upper()} {endpoint.path}"
            )

            suite_input = TestSuiteGeneratorInput(
                endpoint_info=endpoint,
                test_case_count=inp.test_case_count,
                include_invalid_data=inp.include_invalid_data,
            )
            suite_output = await self.test_suite_generator.execute(suite_input)
            test_suites.append(suite_output.test_suite)

            self.logger.debug(
                f"Generated test suite for {endpoint.method.upper()} {endpoint.path} with {len(suite_output.test_suite.test_cases)} test cases"
            )

        # Create the test collection
        collection_name = f"Test collection for {inp.api_name} v{inp.api_version}"
        collection_description = (
            f"Automated test collection for {inp.api_name} API v{inp.api_version}"
        )

        test_collection = TestCollection(
            name=collection_name,
            description=collection_description,
            test_suites=test_suites,
        )

        total_test_cases = sum(len(suite.test_cases) for suite in test_suites)
        self.logger.info(
            f"Test collection generated successfully: {len(test_suites)} test suites, {total_test_cases} total test cases"
        )

        return TestCollectionGeneratorOutput(test_collection=test_collection)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        self.logger.debug("Cleaning up test collection generator resources")
        await self.test_suite_generator.cleanup()
