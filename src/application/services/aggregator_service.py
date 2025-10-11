"""
Service for aggregating constraint mining and validation script generation operations.
"""

import time
from datetime import datetime
from typing import Optional

from ..services.constraint_service import ConstraintService
from ..services.validation_script_service import ValidationScriptService
from ..services.endpoint_service import EndpointService
from ..services.test_data_service import TestDataService
from ..services.test_execution_service import TestExecutionService
from app.api.dto.aggregator_dto import ConstraintsScriptsAggregatorResponse
from app.api.dto.constraint_dto import MineConstraintsResponse
from app.api.dto.validation_script_dto import GenerateScriptsResponse
from schemas.tools.openapi_parser import EndpointInfo
from schemas.core.execution_history import ExecutionHistory


class AggregatorService:
    """Service for aggregating multiple operations into a single workflow."""

    def __init__(
        self,
        constraint_service: ConstraintService,
        validation_script_service: ValidationScriptService,
        endpoint_service: EndpointService,
        test_data_service: TestDataService,
        test_execution_service: TestExecutionService,
    ):
        self.constraint_service = constraint_service
        self.validation_script_service = validation_script_service
        self.endpoint_service = endpoint_service
        self.test_data_service = test_data_service
        self.test_execution_service = test_execution_service
        self.logger = constraint_service.logger

    async def mine_constraints_and_generate_scripts(
        self, endpoint_name: str
    ) -> ConstraintsScriptsAggregatorResponse:
        """
        Mine constraints and generate validation scripts for an endpoint in sequence.

        Args:
            endpoint_name: Name of the endpoint to process

        Returns:
            Aggregated response with both constraint mining and script generation results
        """
        start_time = time.time()
        execution_timestamp = datetime.now().isoformat()

        self.logger.info(
            f"Starting aggregated operations for endpoint: {endpoint_name}"
        )

        # Initialize response variables
        constraints_result: Optional[MineConstraintsResponse] = None
        scripts_result: Optional[GenerateScriptsResponse] = None
        constraints_error: Optional[str] = None
        scripts_error: Optional[str] = None
        constraints_mining_success = False
        scripts_generation_success = False
        deleted_constraints_count = 0
        deleted_scripts_count = 0

        try:
            # Step 1: Find endpoint by name
            endpoint = await self.endpoint_service.get_endpoint_by_name(endpoint_name)
            if not endpoint:
                error_msg = f"Endpoint '{endpoint_name}' not found"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            self.logger.info(
                f"Found endpoint: {endpoint.id} - {endpoint.path} {endpoint.method}"
            )

            # Step 2: Mine constraints (with override to delete existing ones)
            try:
                self.logger.info("Starting constraint mining with override...")

                # Get count of existing constraints before deletion
                existing_constraints = await self.constraint_service.constraint_repository.get_by_endpoint_id(
                    endpoint.id
                )
                deleted_constraints_count = len(existing_constraints)

                constraint_output = (
                    await self.constraint_service.mine_constraints_for_endpoint(
                        endpoint.id, override_existing=True
                    )
                )

                # Convert to response format
                constraints_result = MineConstraintsResponse.from_miner_output(
                    constraint_output, endpoint.id
                )
                constraints_mining_success = True
                self.logger.info(
                    f"Constraint mining completed: {constraints_result.total_constraints} constraints found"
                )

            except Exception as e:
                constraints_error = str(e)
                self.logger.error(f"Constraint mining failed: {e}")
                # Continue with script generation even if constraint mining fails

            # Step 3: Generate validation scripts (with override to delete existing ones)
            try:
                self.logger.info(
                    "Starting validation script generation with override..."
                )

                # Get count of existing scripts before deletion
                existing_scripts = await self.validation_script_service.script_repository.get_by_endpoint_id(
                    endpoint.id
                )
                deleted_scripts_count = len(existing_scripts)

                script_output = (
                    await self.validation_script_service.generate_scripts_for_endpoint(
                        endpoint.id, override_existing=True
                    )
                )

                # Convert to response format
                scripts_result = GenerateScriptsResponse.from_generator_output(
                    script_output, endpoint.id
                )
                scripts_generation_success = True
                self.logger.info(
                    f"Script generation completed: {scripts_result.total_scripts} scripts generated"
                )

            except Exception as e:
                scripts_error = str(e)
                self.logger.error(f"Script generation failed: {e}")

            # Calculate total execution time
            total_execution_time = time.time() - start_time

            # Determine overall success
            overall_success = constraints_mining_success and scripts_generation_success

            # Create aggregated response
            response = ConstraintsScriptsAggregatorResponse(
                endpoint_name=endpoint_name,
                endpoint_id=endpoint.id,
                constraints_result=constraints_result
                or MineConstraintsResponse(
                    endpoint_id=endpoint.id,
                    endpoint_method=endpoint.method,
                    endpoint_path=endpoint.path,
                    constraints=[],
                    request_param_constraints=[],
                    request_body_constraints=[],
                    response_property_constraints=[],
                    request_response_constraints=[],
                    total_constraints=0,
                    result={},
                ),
                scripts_result=scripts_result
                or GenerateScriptsResponse(
                    endpoint_id=endpoint.id, scripts=[], total_scripts=0
                ),
                total_constraints=(
                    constraints_result.total_constraints if constraints_result else 0
                ),
                total_scripts=scripts_result.total_scripts if scripts_result else 0,
                total_execution_time=total_execution_time,
                deleted_constraints_count=deleted_constraints_count,
                deleted_scripts_count=deleted_scripts_count,
                constraints_mining_success=constraints_mining_success,
                scripts_generation_success=scripts_generation_success,
                overall_success=overall_success,
                constraints_error=constraints_error,
                scripts_error=scripts_error,
                execution_timestamp=execution_timestamp,
            )

            if overall_success:
                self.logger.info(
                    f"Aggregated operations completed successfully for '{endpoint_name}': "
                    f"{response.total_constraints} constraints, {response.total_scripts} scripts "
                    f"in {total_execution_time:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Aggregated operations completed with issues for '{endpoint_name}': "
                    f"constraints={'✓' if constraints_mining_success else '✗'}, "
                    f"scripts={'✓' if scripts_generation_success else '✗'}"
                )

            return response

        except ValueError as e:
            # Re-raise ValueError (like endpoint not found) to be handled by router
            raise e
        except Exception as e:
            total_execution_time = time.time() - start_time
            error_msg = (
                f"Aggregated operations failed for endpoint '{endpoint_name}': {e}"
            )
            self.logger.error(error_msg)

            # Return error response with available data
            return ConstraintsScriptsAggregatorResponse(
                endpoint_name=endpoint_name,
                endpoint_id="unknown",
                constraints_result=MineConstraintsResponse(
                    endpoint_id="unknown",
                    endpoint_method="unknown",
                    endpoint_path="unknown",
                    constraints=[],
                    request_param_constraints=[],
                    request_body_constraints=[],
                    response_property_constraints=[],
                    request_response_constraints=[],
                    total_constraints=0,
                    result={},
                ),
                scripts_result=GenerateScriptsResponse(
                    endpoint_id="unknown", scripts=[], total_scripts=0
                ),
                total_constraints=0,
                total_scripts=0,
                total_execution_time=total_execution_time,
                deleted_constraints_count=0,
                deleted_scripts_count=0,
                constraints_mining_success=False,
                scripts_generation_success=False,
                overall_success=False,
                constraints_error=constraints_error or error_msg,
                scripts_error=scripts_error,
                execution_timestamp=execution_timestamp,
            )

    async def run_full_pipeline_for_endpoint(
        self,
        endpoint_name: str,
        base_url: str,
        test_count: int = 5,
        include_invalid: bool = True,
        override_existing: bool = True,
    ) -> dict:
        """
        Run the complete testing pipeline for an endpoint.

        This method orchestrates the full testing workflow:
        1. Mine constraints (if not exist or override)
        2. Generate validation scripts (if not exist or override)
        3. Generate test data
        4. Execute tests with real API calls
        5. Save execution results
        6. Return comprehensive report

        Args:
            endpoint_name: Name of the endpoint to test
            base_url: Base URL for API calls
            test_count: Number of test data items to generate
            include_invalid: Whether to include invalid test data
            override_existing: Whether to override existing constraints/scripts

        Returns:
            Dictionary with comprehensive pipeline results
        """
        start_time = time.time()
        execution_timestamp = datetime.now().isoformat()

        self.logger.info(f"Starting full pipeline for endpoint: {endpoint_name}")

        pipeline_results = {
            "endpoint_name": endpoint_name,
            "base_url": base_url,
            "execution_timestamp": execution_timestamp,
            "steps": {},
            "overall_success": False,
            "total_execution_time": 0.0,
        }

        try:
            # Step 1: Find endpoint
            endpoint = await self.endpoint_service.get_endpoint_by_name(endpoint_name)
            if not endpoint:
                error_msg = f"Endpoint '{endpoint_name}' not found"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            pipeline_results["endpoint_id"] = endpoint.id
            pipeline_results["endpoint_info"] = {
                "path": endpoint.path,
                "method": endpoint.method,
                "description": endpoint.description,
                "dataset_id": endpoint.dataset_id,
            }

            self.logger.info(
                f"Found endpoint: {endpoint.id} - {endpoint.path} {endpoint.method}"
            )

            # Step 2: Mine constraints (with override)
            step_start = time.time()
            try:
                self.logger.info("Step 2: Mining constraints...")
                constraint_output = (
                    await self.constraint_service.mine_constraints_for_endpoint(
                        endpoint.id, override_existing=override_existing
                    )
                )

                pipeline_results["steps"]["constraints"] = {
                    "success": True,
                    "constraints_found": len(constraint_output.constraints),
                    "execution_time": time.time() - step_start,
                }
                self.logger.info(
                    f"Constraints mined: {len(constraint_output.constraints)} constraints"
                )

            except Exception as e:
                pipeline_results["steps"]["constraints"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - step_start,
                }
                self.logger.error(f"Constraint mining failed: {e}")

            # Step 3: Generate validation scripts (with override)
            step_start = time.time()
            try:
                self.logger.info("Step 3: Generating validation scripts...")
                script_output = (
                    await self.validation_script_service.generate_scripts_for_endpoint(
                        endpoint.id, override_existing=override_existing
                    )
                )

                pipeline_results["steps"]["validation_scripts"] = {
                    "success": True,
                    "scripts_generated": len(script_output.validation_scripts),
                    "execution_time": time.time() - step_start,
                }
                self.logger.info(
                    f"Validation scripts generated: {len(script_output.validation_scripts)} scripts"
                )

            except Exception as e:
                pipeline_results["steps"]["validation_scripts"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - step_start,
                }
                self.logger.error(f"Validation script generation failed: {e}")

            # Step 4: Generate test data
            step_start = time.time()
            try:
                self.logger.info("Step 4: Generating test data...")

                # Convert endpoint to dict for the generator
                endpoint_dict = {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "description": endpoint.description,
                    "input_schema": endpoint.input_schema,
                    "output_schema": endpoint.output_schema,
                    "tags": endpoint.tags,
                    "auth_required": endpoint.auth_required,
                    "auth_type": endpoint.auth_type,
                    "dataset_id": endpoint.dataset_id,
                }

                test_data_output = (
                    await self.test_data_service.generate_test_data_for_endpoint(
                        endpoint_id=endpoint.id,
                        endpoint_info=endpoint_dict,
                        count=test_count,
                        include_invalid=include_invalid,
                        override_existing=override_existing,
                    )
                )

                pipeline_results["steps"]["test_data"] = {
                    "success": True,
                    "test_data_generated": len(test_data_output.test_data_collection),
                    "execution_time": time.time() - step_start,
                }
                self.logger.info(
                    f"Test data generated: {len(test_data_output.test_data_collection)} items"
                )

            except Exception as e:
                pipeline_results["steps"]["test_data"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - step_start,
                }
                self.logger.error(f"Test data generation failed: {e}")

            # Step 5: Execute tests
            step_start = time.time()
            execution_result = None
            try:
                self.logger.info("Step 5: Executing tests...")
                execution_result = (
                    await self.test_execution_service.execute_test_for_endpoint(
                        endpoint_id=endpoint.id,
                        endpoint_name=endpoint_name,
                        base_url=base_url,
                        dataset_id=endpoint.dataset_id,
                        timeout=30,
                    )
                )

                pipeline_results["steps"]["test_execution"] = {
                    "success": True,
                    "execution_id": execution_result.id,
                    "total_tests": execution_result.total_tests,
                    "passed_tests": execution_result.passed_tests,
                    "failed_tests": execution_result.failed_tests,
                    "success_rate": execution_result.success_rate,
                    "execution_time": time.time() - step_start,
                }
                self.logger.info(
                    f"Test execution completed: {execution_result.passed_tests}/{execution_result.total_tests} passed "
                    f"({execution_result.success_rate:.2%} success rate)"
                )

            except Exception as e:
                pipeline_results["steps"]["test_execution"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - step_start,
                }
                self.logger.error(f"Test execution failed: {e}")

            # Calculate overall success
            steps_success = [
                pipeline_results["steps"].get("constraints", {}).get("success", False),
                pipeline_results["steps"]
                .get("validation_scripts", {})
                .get("success", False),
                pipeline_results["steps"].get("test_data", {}).get("success", False),
                pipeline_results["steps"]
                .get("test_execution", {})
                .get("success", False),
            ]
            pipeline_results["overall_success"] = all(steps_success)
            pipeline_results["total_execution_time"] = time.time() - start_time

            # Add execution result details if available
            if execution_result:
                pipeline_results["execution_details"] = {
                    "execution_id": execution_result.id,
                    "overall_status": execution_result.overall_status,
                    "total_execution_time_ms": execution_result.total_execution_time_ms,
                    "test_results_summary": {
                        "total": execution_result.total_tests,
                        "passed": execution_result.passed_tests,
                        "failed": execution_result.failed_tests,
                        "success_rate": execution_result.success_rate,
                    },
                }

            if pipeline_results["overall_success"]:
                self.logger.info(
                    f"Full pipeline completed successfully for '{endpoint_name}' "
                    f"in {pipeline_results['total_execution_time']:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Full pipeline completed with issues for '{endpoint_name}': "
                    f"Some steps may have failed"
                )

            return pipeline_results

        except ValueError as e:
            # Re-raise ValueError (like endpoint not found) to be handled by router
            raise e
        except Exception as e:
            pipeline_results["overall_success"] = False
            pipeline_results["total_execution_time"] = time.time() - start_time
            pipeline_results["error"] = str(e)

            self.logger.error(
                f"Full pipeline failed for endpoint '{endpoint_name}': {e}"
            )
            return pipeline_results
