# tools/test_suite_generator.py
from typing import Dict, Optional, List
import uuid
from datetime import datetime

from ...core.base_tool import BaseTool
from ...schemas.tools.test_suite_generator import (
    TestSuiteGeneratorInput,
    TestSuiteGeneratorOutput,
    TestSuite,
)
from ...schemas.tools.test_case_generator import TestCaseGeneratorInput
from ...schemas.tools.test_data_generator import TestDataGeneratorInput
from ...schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    ApiConstraint,
)
from ...schemas.tools.test_script_generator import TestScriptGeneratorInput
from ...schemas.tools.test_data_verifier import TestDataVerifierInput
from ..llm.test_data_generator import TestDataGeneratorTool
from ..llm.static_constraint_miner import StaticConstraintMinerTool
from ..llm.test_script_generator import TestScriptGeneratorTool
from ..core.test_case_generator import TestCaseGeneratorTool
from ..core.test_data_verifier import TestDataVerifierTool
from ...common.logger import LoggerFactory, LoggerType, LogLevel
from ...utils.comprehensive_report_utils import (
    ComprehensiveReportGenerator,
    ReportConfig,
    create_safe_endpoint_name,
)


class TestSuiteGeneratorTool(BaseTool):
    """
    Tool for generating complete test suites for API endpoints.

    This tool implements the complete pipeline for each endpoint:
    1. Mines constraints using StaticConstraintMiner
    2. Generates test data using TestDataGenerator
    3. Generates validation scripts using TestScriptGenerator
    4. Verifies test data using TestDataVerifier to filter out mismatched data
    5. Creates test cases using TestCaseGenerator
    6. Assembles the complete test suite

    This ensures each endpoint is processed only once with no duplicate LLM calls.
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

        # Initialize custom logger with enhanced file logging
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO

        # Ensure logs/tools directory exists
        from pathlib import Path

        logs_dir = Path("logs/tools")
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.logger = LoggerFactory.get_logger(
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            console_level=log_level,
            file_level=LogLevel.DEBUG,  # Always DEBUG to file for detailed debugging
            log_file=str(logs_dir / "test_suite_generator.log"),
        )

        # Initialize required tools - this is the complete pipeline for each endpoint
        self.constraint_miner = StaticConstraintMinerTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        self.test_data_generator = TestDataGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        self.test_script_generator = TestScriptGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        self.test_data_verifier = TestDataVerifierTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        self.test_case_generator = TestCaseGeneratorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
            config=config,
        )

        # Initialize comprehensive report generator
        self.report_generator = ComprehensiveReportGenerator(
            config=ReportConfig(
                base_output_dir="test_reports",
                include_verbose_details=verbose,
                save_raw_data=True,
                create_human_readable=True,
            ),
            verbose=verbose,
        )

    async def _execute(self, inp: TestSuiteGeneratorInput) -> TestSuiteGeneratorOutput:
        """Generate a complete test suite for the endpoint using the proper pipeline."""
        endpoint_info = inp.endpoint_info
        test_case_count = inp.test_case_count or 2
        include_invalid_data = inp.include_invalid_data or False

        self.logger.info(
            f"Starting complete pipeline for {endpoint_info.method.upper()} {endpoint_info.path}"
        )
        self.logger.debug(f"=== TEST SUITE GENERATION START ===")
        self.logger.debug(f"Endpoint: {endpoint_info.method} {endpoint_info.path}")
        self.logger.debug(f"Test case count: {test_case_count}")
        self.logger.debug(f"Include invalid data: {include_invalid_data}")
        self.logger.debug(f"Endpoint info: {endpoint_info}")

        self.logger.add_context(
            endpoint_method=endpoint_info.method.upper(),
            endpoint_path=endpoint_info.path,
            test_case_count=test_case_count,
            include_invalid_data=include_invalid_data,
        )

        if self.verbose:
            self.logger.debug("=" * 80)
            self.logger.debug(
                f"STARTING PIPELINE FOR {endpoint_info.method.upper()} {endpoint_info.path}"
            )
            self.logger.debug("=" * 80)
            self.logger.debug("Pipeline Steps:")
            self.logger.debug("  1. Mine constraints")
            self.logger.debug("  2. Generate test data")
            self.logger.debug("  3. Generate validation scripts")
            self.logger.debug("  4. Verify test data (filter mismatches)")
            self.logger.debug("  5. Generate test cases")
            self.logger.debug("  6. Assemble test suite")

        try:
            # Step 1: Mine constraints (once per endpoint)
            self.logger.info("Step 1: Mining constraints from endpoint specification")
            constraint_input = StaticConstraintMinerInput(
                endpoint_info=endpoint_info,
                include_examples=True,
                include_schema_constraints=True,
                include_correlation_constraints=True,
            )

            constraint_output: StaticConstraintMinerOutput = (
                await self.constraint_miner.execute(constraint_input)
            )

            # Combine all constraint types
            all_constraints: List[ApiConstraint] = []
            all_constraints.extend(constraint_output.request_param_constraints)
            all_constraints.extend(constraint_output.request_body_constraints)
            all_constraints.extend(constraint_output.response_property_constraints)
            all_constraints.extend(constraint_output.request_response_constraints)

            self.logger.info(f"Mined {len(all_constraints)} constraints")
            if self.verbose:
                constraint_breakdown = {
                    "request_param": len(constraint_output.request_param_constraints),
                    "request_body": len(constraint_output.request_body_constraints),
                    "response_property": len(
                        constraint_output.response_property_constraints
                    ),
                    "request_response": len(
                        constraint_output.request_response_constraints
                    ),
                }
                for constraint_type, count in constraint_breakdown.items():
                    self.logger.debug(f"  - {constraint_type}: {count}")

            # Step 2: Generate test data (once per endpoint)
            self.logger.info("Step 2: Generating test data")
            test_data_input = TestDataGeneratorInput(
                endpoint_info=endpoint_info,
                test_case_count=test_case_count,
                include_invalid_data=include_invalid_data,
            )

            test_data_output = await self.test_data_generator.execute(test_data_input)
            test_data_collection = test_data_output.test_data_collection

            self.logger.info(f"Generated {len(test_data_collection)} test data items")

            # Step 3: Generate validation scripts (once per endpoint)
            self.logger.info("Step 3: Generating validation scripts")
            script_input = TestScriptGeneratorInput(
                endpoint_info=endpoint_info,
                constraints=all_constraints,
            )

            script_output = await self.test_script_generator.execute(script_input)
            validation_scripts = script_output.validation_scripts

            self.logger.info(f"Generated {len(validation_scripts)} validation scripts")

            # Separate scripts for test data verification vs test case validation
            test_data_verification_scripts = []
            test_case_validation_scripts = []

            for script in validation_scripts:
                # Scripts for verifying test data (request param/body constraints)
                if script.script_type in ["request_param", "request_body"]:
                    test_data_verification_scripts.append(script)
                # Scripts for validating responses (response property/correlation constraints)
                else:
                    test_case_validation_scripts.append(script)

            self.logger.debug(
                f"Separated scripts: {len(test_data_verification_scripts)} for test data verification, "
                f"{len(test_case_validation_scripts)} for test case validation"
            )

            # Step 4: Verify test data (filter out mismatched data)
            self.logger.info("Step 4: Verifying test data to filter mismatches")
            verifier_input = TestDataVerifierInput(
                test_data_collection=test_data_collection,
                verification_scripts=test_data_verification_scripts,
                timeout=30,
            )

            verifier_output = await self.test_data_verifier.execute(verifier_input)
            verified_test_data = verifier_output.verified_test_data

            self.logger.info(
                f"Verified test data: {len(verified_test_data)} valid, "
                f"{verifier_output.filtered_count} filtered out as mismatched"
            )

            # Step 5: Generate test cases (once per verified test data item)
            self.logger.info("Step 5: Generating test cases with validation scripts")
            test_cases = []
            total_validation_scripts = 0

            for i, test_data in enumerate(verified_test_data):
                self.logger.debug(
                    f"Generating test case {i+1}/{len(verified_test_data)}"
                )

                # For invalid test data (status code >= 400), only use status code validation
                if test_data.expected_status_code >= 400:
                    validation_scripts_for_case = (
                        []
                    )  # Skip response validation for error cases
                else:
                    validation_scripts_for_case = test_case_validation_scripts

                case_input = TestCaseGeneratorInput(
                    endpoint_info=endpoint_info,
                    test_data=test_data,
                    validation_scripts=validation_scripts_for_case,
                    name=f"Test case {i+1} for {endpoint_info.method.upper()} {endpoint_info.path}",
                    description=f"Generated test case {i+1} based on verified test data",
                )

                case_output = await self.test_case_generator.execute(case_input)
                test_case = case_output.test_case
                test_cases.append(test_case)

                scripts_count = len(test_case.validation_scripts)
                total_validation_scripts += scripts_count

                self.logger.debug(
                    f"Generated test case with {scripts_count} validation scripts"
                )

            # Step 6: Create test suite
            self.logger.info("Step 6: Assembling complete test suite")

            # Create a meaningful suite name including API information if available
            suite_name_parts = []
            if inp.api_name:
                suite_name_parts.append(inp.api_name)
            if inp.api_version:
                suite_name_parts.append(f"v{inp.api_version}")

            suite_name_prefix = (
                " ".join(suite_name_parts) if suite_name_parts else "API"
            )
            suite_name = f"{suite_name_prefix} - {endpoint_info.method.upper()} {endpoint_info.path}"

            test_suite = TestSuite(
                id=str(uuid.uuid4()),
                name=suite_name,
                description=f"Complete test suite for {endpoint_info.name or endpoint_info.path}",
                endpoint_info=endpoint_info,
                test_cases=test_cases,
            )

            # Step 7: Capture comprehensive report data
            self.logger.info("Step 7: Capturing comprehensive report data")

            # Create safe endpoint name for reporting
            endpoint_name = create_safe_endpoint_name(
                {
                    "method": endpoint_info.method,
                    "path": endpoint_info.path,
                    "name": endpoint_info.name,
                }
            )

            # Capture all pipeline data for comprehensive reporting
            comprehensive_report_data = {
                "constraints": {
                    "all_constraints": [
                        constraint.model_dump() for constraint in all_constraints
                    ],
                    "request_param_constraints": [
                        constraint.model_dump()
                        for constraint in constraint_output.request_param_constraints
                    ],
                    "request_body_constraints": [
                        constraint.model_dump()
                        for constraint in constraint_output.request_body_constraints
                    ],
                    "response_property_constraints": [
                        constraint.model_dump()
                        for constraint in constraint_output.response_property_constraints
                    ],
                    "request_response_constraints": [
                        constraint.model_dump()
                        for constraint in constraint_output.request_response_constraints
                    ],
                },
                "test_data": {
                    "test_data_collection": [
                        data.model_dump() for data in test_data_collection
                    ],
                    "verification_scripts": [
                        script.model_dump() for script in test_data_verification_scripts
                    ],
                    "verified_test_data": [
                        data.model_dump() for data in verified_test_data
                    ],
                    "filtered_count": verifier_output.filtered_count,
                    "verification_results": verifier_output.verification_results,
                },
                "validation_scripts": {
                    "all_validation_scripts": [
                        script.model_dump() for script in validation_scripts
                    ],
                    "test_data_verification_scripts": [
                        script.model_dump() for script in test_data_verification_scripts
                    ],
                    "test_case_validation_scripts": [
                        script.model_dump() for script in test_case_validation_scripts
                    ],
                },
                "pipeline_metadata": {
                    "endpoint_name": endpoint_name,
                    "endpoint_info": endpoint_info.model_dump(),
                    "test_case_count": test_case_count,
                    "include_invalid_data": include_invalid_data,
                    "api_name": inp.api_name,
                    "api_version": inp.api_version,
                    "pipeline_timestamp": datetime.now().isoformat(),
                },
                "statistics": {
                    "total_constraints": len(all_constraints),
                    "total_test_data_generated": len(test_data_collection),
                    "total_test_data_verified": len(verified_test_data),
                    "total_validation_scripts": len(validation_scripts),
                    "total_test_cases": len(test_cases),
                    "total_validation_scripts_per_case": total_validation_scripts,
                    "verification_success_rate": (
                        (len(verified_test_data) / len(test_data_collection) * 100)
                        if test_data_collection
                        else 0
                    ),
                },
            }

            self.logger.info(f"Pipeline completed successfully")
            self.logger.add_context(
                test_suite_id=test_suite.id,
                total_test_cases=len(test_cases),
                total_validation_scripts=total_validation_scripts,
                mined_constraints=len(all_constraints),
                generated_test_data=len(test_data_collection),
                verified_test_data=len(verified_test_data),
                filtered_mismatches=verifier_output.filtered_count,
            )

            if self.verbose:
                self.logger.debug("=" * 60)
                self.logger.debug("PIPELINE COMPLETED SUCCESSFULLY")
                self.logger.debug("=" * 60)
                self.logger.debug(f"Test Suite: {test_suite.name}")
                self.logger.debug(f"Total constraints mined: {len(all_constraints)}")
                self.logger.debug(
                    f"Total test data generated: {len(test_data_collection)}"
                )
                self.logger.debug(
                    f"Total test data verified: {len(verified_test_data)}"
                )
                self.logger.debug(
                    f"Mismatched data filtered: {verifier_output.filtered_count}"
                )
                self.logger.debug(f"Total test cases: {len(test_cases)}")
                self.logger.debug(
                    f"Total validation scripts: {total_validation_scripts}"
                )
                self.logger.debug("Status: Success")

            return TestSuiteGeneratorOutput(
                test_suite=test_suite,
                comprehensive_report_data=comprehensive_report_data,
            )

        except Exception as e:
            self.logger.error(f"Error in test suite pipeline: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")

            # Return minimal test suite with error information
            error_test_suite = TestSuite(
                id=str(uuid.uuid4()),
                name=f"Error Test Suite for {endpoint_info.method.upper()} {endpoint_info.path}",
                description=f"Error occurred during pipeline execution: {str(e)}",
                endpoint_info=endpoint_info,
                test_cases=[],
            )

            self.logger.warning(f"Returning error test suite due to pipeline failure")
            return TestSuiteGeneratorOutput(
                test_suite=error_test_suite,
                comprehensive_report_data=None,
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up test suite generator resources")
        await self.constraint_miner.cleanup()
        await self.test_data_generator.cleanup()
        await self.test_script_generator.cleanup()
        await self.test_data_verifier.cleanup()
        await self.test_case_generator.cleanup()
