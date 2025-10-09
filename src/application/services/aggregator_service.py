"""
Service for aggregating constraint mining and validation script generation operations.
"""

import time
from datetime import datetime
from typing import Optional

from ..services.constraint_service import ConstraintService
from ..services.validation_script_service import ValidationScriptService
from ..services.endpoint_service import EndpointService
from app.api.dto.aggregator_dto import ConstraintsScriptsAggregatorResponse
from app.api.dto.constraint_dto import MineConstraintsResponse
from app.api.dto.validation_script_dto import GenerateScriptsResponse
from schemas.tools.openapi_parser import EndpointInfo


class AggregatorService:
    """Service for aggregating multiple operations into a single workflow."""

    def __init__(
        self,
        constraint_service: ConstraintService,
        validation_script_service: ValidationScriptService,
        endpoint_service: EndpointService,
    ):
        self.constraint_service = constraint_service
        self.validation_script_service = validation_script_service
        self.endpoint_service = endpoint_service
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
