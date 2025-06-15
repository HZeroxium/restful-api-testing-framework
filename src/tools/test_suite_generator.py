# tools/test_suite_generator.py

from typing import Dict, Optional, List
import uuid

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
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestSuiteGeneratorTool(BaseTool):
    """
    Tool for generating complete test suites for API endpoints.

    This tool orchestrates the generation of:
    1. Test data for the endpoint
    2. Test cases with validation scripts
    3. A complete test suite
    """

    def __init__(
        self,
        *,
        name: str = "test_suite_generator",
        description: str = "Generates complete test suites for API endpoints",
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

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize required tools
        self.test_data_generator = TestDataGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        self.test_case_generator = TestCaseGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

    async def _execute(self, inp: TestSuiteGeneratorInput) -> TestSuiteGeneratorOutput:
        """Generate a complete test suite for the endpoint."""
        endpoint_info = inp.endpoint_info
        test_case_count = inp.test_case_count or 2
        include_invalid_data = inp.include_invalid_data or False

        self.logger.info(
            f"Generating test suite for {endpoint_info.method.upper()} {endpoint_info.path}"
        )
        self.logger.add_context(
            endpoint_method=endpoint_info.method.upper(),
            endpoint_path=endpoint_info.path,
            test_case_count=test_case_count,
            include_invalid_data=include_invalid_data,
        )

        if self.verbose:
            self.logger.debug("=" * 80)
            self.logger.debug(
                f"GENERATING TEST SUITE FOR {endpoint_info.method.upper()} {endpoint_info.path}"
            )
            self.logger.debug("=" * 80)
            self.logger.debug("Parameters:")
            self.logger.debug(f"  - Test case count: {test_case_count}")
            self.logger.debug(f"  - Include invalid data: {include_invalid_data}")

        try:
            # Step 1: Generate test data
            self.logger.debug("Step 1: Generating test data...")

            data_input = TestDataGeneratorInput(
                endpoint_info=endpoint_info,
                test_case_count=test_case_count,
                include_invalid_data=include_invalid_data,
            )

            data_output = await self.test_data_generator.execute(data_input)
            test_data_collection = data_output.test_data_collection

            self.logger.debug(f"Generated {len(test_data_collection)} test data items")

            # Step 2: Generate test cases with validation scripts
            self.logger.debug(
                "Step 2: Generating test cases with validation scripts..."
            )

            test_cases = []
            total_validation_scripts = 0

            for i, test_data in enumerate(test_data_collection):
                self.logger.debug(
                    f"Generating test case {i+1}/{len(test_data_collection)}"
                )

                case_input = TestCaseGeneratorInput(
                    endpoint_info=endpoint_info,
                    test_data=test_data,
                    name=f"Test case {i+1} for {endpoint_info.method.upper()} {endpoint_info.path}",
                    description=f"Generated test case {i+1} based on constraints and test data",
                )

                case_output = await self.test_case_generator.execute(case_input)
                test_case = case_output.test_case
                test_cases.append(test_case)

                scripts_count = len(test_case.validation_scripts)
                total_validation_scripts += scripts_count

                self.logger.debug(
                    f"Generated {scripts_count} validation scripts for test case {i+1}"
                )

            # Step 3: Create test suite
            test_suite = TestSuite(
                id=str(uuid.uuid4()),
                name=f"Test Suite for {endpoint_info.method.upper()} {endpoint_info.path}",
                description=f"Generated test suite for {endpoint_info.name or endpoint_info.path}",
                endpoint_info=endpoint_info,
                test_cases=test_cases,
            )

            self.logger.info(f"Test suite generation completed successfully")
            self.logger.add_context(
                test_suite_id=test_suite.id,
                total_test_cases=len(test_cases),
                total_validation_scripts=total_validation_scripts,
            )

            if self.verbose:
                self.logger.debug("=" * 60)
                self.logger.debug("TEST SUITE GENERATION COMPLETED")
                self.logger.debug("=" * 60)
                self.logger.debug(f"Test Suite: {test_suite.name}")
                self.logger.debug(f"Total test cases: {len(test_cases)}")
                self.logger.debug(
                    f"Total validation scripts: {total_validation_scripts}"
                )
                self.logger.debug("Status: Success")

            return TestSuiteGeneratorOutput(test_suite=test_suite)

        except Exception as e:
            self.logger.error(f"Error in test suite generation: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")

            # Return minimal test suite with error information
            error_test_suite = TestSuite(
                id=str(uuid.uuid4()),
                name=f"Error Test Suite for {endpoint_info.method.upper()} {endpoint_info.path}",
                description=f"Error occurred during generation: {str(e)}",
                endpoint_info=endpoint_info,
                test_cases=[],
            )

            self.logger.warning(f"Returning error test suite due to generation failure")
            return TestSuiteGeneratorOutput(test_suite=error_test_suite)

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up TestSuiteGeneratorTool resources")
        await self.test_data_generator.cleanup()
        await self.test_case_generator.cleanup()
