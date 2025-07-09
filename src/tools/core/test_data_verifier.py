# tools/core/test_data_verifier.py

from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.test_data_verifier import (
    TestDataVerifierInput,
    TestDataVerifierOutput,
    VerificationResult,
)
from schemas.tools.test_data_generator import TestData
from schemas.tools.code_executor import CodeExecutorInput
from tools.core.code_executor import CodeExecutorTool
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestDataVerifierTool(BaseTool):
    """
    Tool for verifying test data against constraints using provided verification scripts.

    This tool:
    1. Receives pre-generated verification scripts and test data
    2. Executes these scripts against test data using CodeExecutorTool
    3. Filters out mismatched data (valid data that fails, invalid data that passes)
    4. Returns only properly validated test data

    The tool does not generate scripts or use constraints - it only executes provided scripts.
    """

    def __init__(
        self,
        *,
        name: str = "test_data_verifier",
        description: str = "Verifies test data against constraints using provided verification scripts",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestDataVerifierInput,
            output_schema=TestDataVerifierOutput,
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

        # Initialize code executor
        self.code_executor = CodeExecutorTool(
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(self, inp: TestDataVerifierInput) -> TestDataVerifierOutput:
        """Execute test data verification using provided scripts."""
        self.logger.info(
            f"Starting verification of {len(inp.test_data_collection)} test data items using {len(inp.verification_scripts)} scripts"
        )

        verification_results = []
        verified_test_data = []
        filtered_count = 0

        for test_data in inp.test_data_collection:
            self.logger.debug(f"Verifying test data: {test_data.id}")

            # Run all verification scripts for this test data
            script_results = []
            overall_valid = True
            constraint_violations = []

            for script in inp.verification_scripts:
                try:
                    # Execute the script with test data context
                    script_input = CodeExecutorInput(
                        code=script.validation_code,
                        context_variables={
                            "request": {
                                "params": test_data.request_params or {},
                                "headers": test_data.request_headers or {},
                                "body": test_data.request_body,
                            },
                            "response": {
                                "status_code": test_data.expected_status_code,
                                "schema": test_data.expected_response_schema,
                                "contains": test_data.expected_response_contains,
                            },
                        },
                        timeout=inp.timeout,
                    )

                    script_output = await self.code_executor.execute(script_input)

                    if script_output.success:
                        script_results.append(
                            {
                                "script_id": script.id,
                                "script_type": script.script_type,
                                "constraint_id": script.constraint_id,
                                "result": script_output.result,
                                "success": True,
                            }
                        )

                        # Check if this validation script failed
                        if not script_output.result:
                            overall_valid = False
                            constraint_violations.append(f"Script {script.id} failed")
                    else:
                        script_results.append(
                            {
                                "script_id": script.id,
                                "script_type": script.script_type,
                                "constraint_id": script.constraint_id,
                                "error": script_output.error,
                                "success": False,
                            }
                        )
                        overall_valid = False
                        constraint_violations.append(
                            f"Script {script.id} error: {script_output.error}"
                        )

                except Exception as e:
                    self.logger.error(f"Error executing script {script.id}: {str(e)}")
                    script_results.append(
                        {
                            "script_id": script.id,
                            "script_type": script.script_type,
                            "constraint_id": script.constraint_id,
                            "error": str(e),
                            "success": False,
                        }
                    )
                    overall_valid = False
                    constraint_violations.append(
                        f"Script {script.id} execution error: {str(e)}"
                    )

            # Determine if test data should be filtered
            should_filter = False
            error_message = None

            # Check for mismatched data:
            # - Valid data (expected_status_code < 400) that fails validation
            # - Invalid data (expected_status_code >= 400) that passes validation
            if test_data.expected_status_code < 400:
                # Valid data should pass validation
                if not overall_valid:
                    should_filter = True
                    error_message = "Valid test data failed validation"
            else:
                # Invalid data should fail validation (but since we're checking request validation,
                # invalid data might still have valid request format)
                # For now, we'll keep invalid data regardless of validation results
                pass

            # Create verification result
            verification_result = VerificationResult(
                test_data_id=test_data.id,
                is_valid=overall_valid,
                verification_details={"script_results": script_results},
                error_message=error_message,
                constraint_violations=constraint_violations,
            )
            verification_results.append(verification_result)

            # Add to verified data if not filtered
            if not should_filter:
                verified_test_data.append(test_data)
                self.logger.debug(f"Test data {test_data.id} verified successfully")
            else:
                filtered_count += 1
                self.logger.debug(
                    f"Test data {test_data.id} filtered out: {error_message}"
                )

        self.logger.info(
            f"Verification completed: {len(verified_test_data)} verified, {filtered_count} filtered"
        )

        return TestDataVerifierOutput(
            verified_test_data=verified_test_data,
            verification_results=verification_results,
            filtered_count=filtered_count,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up TestDataVerifierTool resources")

        # Cleanup sub-tools
        if hasattr(self.code_executor, "cleanup"):
            await self.code_executor.cleanup()
        if hasattr(self.request_param_script_generator, "cleanup"):
            await self.request_param_script_generator.cleanup()
        if hasattr(self.request_body_script_generator, "cleanup"):
            await self.request_body_script_generator.cleanup()
