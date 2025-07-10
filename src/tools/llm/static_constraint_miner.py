# tools/static_constraint_miner.py

from typing import Dict, List, Optional

from ...core.base_tool import BaseTool
from ...schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    RequestParamConstraintMinerInput,
    RequestBodyConstraintMinerInput,
    ResponsePropertyConstraintMinerInput,
    RequestResponseConstraintMinerInput,
)
from ..constraint_miner_tools.request_param_constraint_miner import (
    RequestParamConstraintMinerTool,
)
from ..constraint_miner_tools.request_body_constraint_miner import (
    RequestBodyConstraintMinerTool,
)
from ..constraint_miner_tools.response_property_constraint_miner import (
    ResponsePropertyConstraintMinerTool,
)
from ..constraint_miner_tools.request_response_constraint_miner import (
    RequestResponseConstraintMinerTool,
)
from ...common.logger import LoggerFactory, LoggerType, LogLevel


class StaticConstraintMinerTool(BaseTool):
    """
    Orchestrator tool for mining static constraints from API endpoint information.

    This tool coordinates specialized constraint mining tools to extract:
    1. Request parameter constraints
    2. Request body constraints
    3. Response property constraints
    4. Request-response correlation constraints
    """

    def __init__(
        self,
        *,
        name: str = "static_constraint_miner",
        description: str = "Orchestrates constraint mining from API endpoint information",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=StaticConstraintMinerInput,
            output_schema=StaticConstraintMinerOutput,
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

        # Initialize specialized constraint mining tools
        self.request_param_miner = RequestParamConstraintMinerTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.request_body_miner = RequestBodyConstraintMinerTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.response_property_miner = ResponsePropertyConstraintMinerTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.request_response_miner = RequestResponseConstraintMinerTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

    async def _execute(
        self, inp: StaticConstraintMinerInput
    ) -> StaticConstraintMinerOutput:
        """Orchestrate constraint mining using specialized tools."""
        endpoint = inp.endpoint_info

        self.logger.info(
            f"Starting static constraint mining for {endpoint.method.upper()} {endpoint.path}"
        )
        self.logger.add_context(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            constraint_types=inp.constraint_types,
            include_examples=inp.include_examples,
            include_schema_constraints=inp.include_schema_constraints,
            include_correlation_constraints=inp.include_correlation_constraints,
        )

        if self.verbose:
            self.logger.debug(
                "Configuration details",
                constraint_types=inp.constraint_types,
                include_examples=inp.include_examples,
                include_schema_constraints=inp.include_schema_constraints,
                include_correlation_constraints=inp.include_correlation_constraints,
            )

        # Initialize result containers
        request_param_constraints = []
        request_body_constraints = []
        response_property_constraints = []
        request_response_constraints = []
        mining_results = {}

        # Check which constraint types to mine
        mine_request_param = "REQUEST_PARAM" in inp.constraint_types
        mine_request_body = "REQUEST_BODY" in inp.constraint_types
        mine_response_property = "RESPONSE_PROPERTY" in inp.constraint_types
        mine_request_response = "REQUEST_RESPONSE" in inp.constraint_types

        try:
            # 1. Mine request parameter constraints
            if mine_request_param:
                self.logger.debug("Mining request parameter constraints")

                param_input = RequestParamConstraintMinerInput(
                    endpoint_info=endpoint,
                    include_examples=inp.include_examples,
                    focus_on_validation=True,
                )

                param_output = await self.request_param_miner.execute(param_input)
                request_param_constraints = param_output.param_constraints
                mining_results["param_mining"] = {
                    "count": len(request_param_constraints),
                    "status": "success",
                }

                self.logger.debug(
                    f"Found {len(request_param_constraints)} parameter constraints"
                )
            else:
                self.logger.debug("Skipping request parameter constraint mining")

        except Exception as e:
            self.logger.error(f"Error mining parameter constraints: {str(e)}")
            mining_results["param_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 2. Mine request body constraints
            if mine_request_body:
                self.logger.debug("Mining request body constraints")

                body_input = RequestBodyConstraintMinerInput(
                    endpoint_info=endpoint,
                    include_examples=inp.include_examples,
                    focus_on_schema=inp.include_schema_constraints,
                )

                body_output = await self.request_body_miner.execute(body_input)
                request_body_constraints = body_output.body_constraints
                mining_results["body_mining"] = {
                    "count": len(request_body_constraints),
                    "status": "success",
                }

                self.logger.debug(
                    f"Found {len(request_body_constraints)} body constraints"
                )
            else:
                self.logger.debug("Skipping request body constraint mining")

        except Exception as e:
            self.logger.error(f"Error mining body constraints: {str(e)}")
            mining_results["body_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 3. Mine response property constraints
            if mine_response_property:
                self.logger.debug("Mining response property constraints")

                response_input = ResponsePropertyConstraintMinerInput(
                    endpoint_info=endpoint,
                    include_examples=inp.include_examples,
                    analyze_structure=inp.include_schema_constraints,
                )

                response_output = await self.response_property_miner.execute(
                    response_input
                )
                response_property_constraints = response_output.response_constraints
                mining_results["response_mining"] = {
                    "count": len(response_property_constraints),
                    "status": "success",
                }

                self.logger.debug(
                    f"Found {len(response_property_constraints)} response constraints"
                )
            else:
                self.logger.debug("Skipping response property constraint mining")

        except Exception as e:
            self.logger.error(f"Error mining response constraints: {str(e)}")
            mining_results["response_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 4. Mine request-response correlation constraints
            if mine_request_response and inp.include_correlation_constraints:
                self.logger.debug("Mining request-response correlation constraints")

                correlation_input = RequestResponseConstraintMinerInput(
                    endpoint_info=endpoint,
                    include_correlations=True,
                    analyze_status_codes=True,
                )

                correlation_output = await self.request_response_miner.execute(
                    correlation_input
                )
                request_response_constraints = (
                    correlation_output.correlation_constraints
                )
                mining_results["correlation_mining"] = {
                    "count": len(request_response_constraints),
                    "status": "success",
                }

                self.logger.debug(
                    f"Found {len(request_response_constraints)} correlation constraints"
                )
            else:
                self.logger.debug(
                    "Skipping correlation constraints (disabled or not requested)"
                )
                mining_results["correlation_mining"] = {
                    "count": 0,
                    "status": "skipped",
                }

        except Exception as e:
            self.logger.error(f"Error mining correlation constraints: {str(e)}")
            mining_results["correlation_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        # Combine all constraints
        all_constraints = (
            request_param_constraints
            + request_body_constraints
            + response_property_constraints
            + request_response_constraints
        )

        # Calculate totals
        total_constraints = len(all_constraints)

        self.logger.info(
            f"Constraint mining completed: {total_constraints} total constraints found"
        )
        self.logger.add_context(
            total_constraints=total_constraints,
            param_constraints=len(request_param_constraints),
            body_constraints=len(request_body_constraints),
            response_constraints=len(response_property_constraints),
            correlation_constraints=len(request_response_constraints),
        )

        if self.verbose:
            self.logger.debug(
                "Constraint breakdown",
                parameter_constraints=len(request_param_constraints),
                body_constraints=len(request_body_constraints),
                response_constraints=len(response_property_constraints),
                correlation_constraints=len(request_response_constraints),
            )

        # Create result summary
        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": total_constraints,
            "mining_results": mining_results,
            "status": "success",
            "constraint_breakdown": {
                "request_param": len(request_param_constraints),
                "request_body": len(request_body_constraints),
                "response_property": len(response_property_constraints),
                "request_response": len(request_response_constraints),
            },
        }

        return StaticConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            constraints=all_constraints,
            request_param_constraints=request_param_constraints,
            request_body_constraints=request_body_constraints,
            response_property_constraints=response_property_constraints,
            request_response_constraints=request_response_constraints,
            total_constraints=total_constraints,
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up all specialized mining tools."""
        self.logger.debug("Cleaning up static constraint miner tools")
        await self.request_param_miner.cleanup()
        await self.request_body_miner.cleanup()
        await self.response_property_miner.cleanup()
        await self.request_response_miner.cleanup()
