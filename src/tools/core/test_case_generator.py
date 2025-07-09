# tools/test_case_generator.py

from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_case_generator import (
    TestCaseGeneratorInput,
    TestCaseGeneratorOutput,
    TestCase,
)
from schemas.tools.test_script_generator import TestScriptGeneratorInput
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    ApiConstraint,
    StaticConstraintMinerOutput,
)
from tools.llm.test_script_generator import TestScriptGeneratorTool
from tools.llm.static_constraint_miner import StaticConstraintMinerTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestCaseGeneratorTool(BaseTool):
    """
    Tool for generating complete test cases with validation scripts.
    This combines test data and validation scripts into a single test case.
    It uses StaticConstraintMinerTool to mine constraints from endpoints
    and passes them to TestScriptGeneratorTool to generate validation scripts.
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

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize the required tools
        self.test_script_generator = TestScriptGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        self.constraint_miner = StaticConstraintMinerTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        # Cache for constraints to avoid re-mining the same endpoint
        self._constraint_cache: Dict[str, List[ApiConstraint]] = {}

    async def _execute(self, inp: TestCaseGeneratorInput) -> TestCaseGeneratorOutput:
        """Generate a complete test case with validation scripts."""
        endpoint_info = inp.endpoint_info
        test_data = inp.test_data

        # Override name and description if provided
        name = inp.name or test_data.name
        description = inp.description or test_data.description

        self.logger.info(f"Generating test case: {name}")
        self.logger.add_context(
            endpoint_method=endpoint_info.method,
            endpoint_path=endpoint_info.path,
            test_data_id=test_data.id,
            test_case_name=name,
        )

        constraint = None

        if inp.constraints:
            # Use provided constraints if available
            constraints = inp.constraints
            self.logger.debug(f"Using provided constraints: {len(constraints)}")
        else:
            # If no constraints provided, mine them from the endpoint
            self.logger.debug(
                "No constraints provided, mining constraints for endpoint"
            )
            # Generate or retrieve constraints for the endpoint
            constraints = await self._get_constraints_for_endpoint(endpoint_info)

        self.logger.debug(f"Total constraints available: {len(constraints)}")
        if constraints and self.verbose:
            constraint_breakdown = {}
            for constraint in constraints:
                constraint_type = constraint.type
                constraint_breakdown[constraint_type] = (
                    constraint_breakdown.get(constraint_type, 0) + 1
                )

            self.logger.debug("Constraint breakdown", **constraint_breakdown)

        # Generate validation scripts for this test data using the constraints
        self.logger.debug("Generating validation scripts")

        script_input = TestScriptGeneratorInput(
            endpoint_info=endpoint_info,
            test_data=test_data,
            constraints=constraints,
        )
        script_output = await self.test_script_generator.execute(script_input)

        self.logger.debug(
            f"Generated {len(script_output.validation_scripts)} validation scripts"
        )

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

        self.logger.info(
            f"Test case generated successfully with {len(script_output.validation_scripts)} validation scripts"
        )

        return TestCaseGeneratorOutput(test_case=test_case)

    async def _get_constraints_for_endpoint(self, endpoint_info) -> List[ApiConstraint]:
        """Get constraints for an endpoint, using cache if available."""
        # Create a unique key for the endpoint
        endpoint_key = f"{endpoint_info.method}_{endpoint_info.path}"

        # Return cached constraints if available
        if endpoint_key in self._constraint_cache:
            cached_constraints = self._constraint_cache[endpoint_key]
            self.logger.debug(
                f"Using cached constraints for {endpoint_key}: {len(cached_constraints)} constraints"
            )
            return cached_constraints

        try:
            self.logger.debug(f"Mining constraints for {endpoint_key}")

            # Create input for constraint miner
            miner_input = StaticConstraintMinerInput(
                endpoint_info=endpoint_info,
                include_examples=True,
                include_schema_constraints=True,
                include_correlation_constraints=True,
            )

            # Execute the constraint miner
            miner_output: StaticConstraintMinerOutput = (
                await self.constraint_miner.execute(miner_input)
            )

            # Combine all constraints from the new structure
            all_constraints = (
                miner_output.request_param_constraints
                + miner_output.request_body_constraints
                + miner_output.response_property_constraints
                + miner_output.request_response_constraints
            )

            self.logger.debug(f"Mined {len(all_constraints)} constraints total")

            # Cache the constraints for future use
            self._constraint_cache[endpoint_key] = all_constraints

            return all_constraints

        except Exception as e:
            # If constraint mining fails, log the error and return empty list
            self.logger.error(f"Error mining constraints: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(
                    f"Constraint mining error traceback: {traceback.format_exc()}"
                )
            return []

    async def cleanup(self) -> None:
        """Clean up any resources."""
        self.logger.debug("Cleaning up test case generator resources")
        await self.test_script_generator.cleanup()
        await self.constraint_miner.cleanup()
        self._constraint_cache.clear()
