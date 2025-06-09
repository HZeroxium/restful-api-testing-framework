# tools/static_constraint_miner.py

from typing import Dict, List, Optional

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    ApiConstraint,
    RequestParamConstraintMinerInput,
    RequestBodyConstraintMinerInput,
    ResponsePropertyConstraintMinerInput,
    RequestResponseConstraintMinerInput,
)
from tools.constraint_miner.request_param_constraint_miner import (
    RequestParamConstraintMinerTool,
)
from tools.constraint_miner.request_body_constraint_miner import (
    RequestBodyConstraintMinerTool,
)
from tools.constraint_miner.response_property_constraint_miner import (
    ResponsePropertyConstraintMinerTool,
)
from tools.constraint_miner.request_response_constraint_miner import (
    RequestResponseConstraintMinerTool,
)


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

        if self.verbose:
            print(f"\n{'='*80}")
            print(
                f"STATIC CONSTRAINT MINING FOR {endpoint.method.upper()} {endpoint.path}"
            )
            print(f"{'='*80}")
            print(f"Configuration:")
            print(f"  - Include examples: {inp.include_examples}")
            print(f"  - Include schema constraints: {inp.include_schema_constraints}")
            print(
                f"  - Include correlation constraints: {inp.include_correlation_constraints}"
            )

        # Initialize result containers
        request_param_constraints = []
        request_body_constraints = []
        response_property_constraints = []
        request_response_constraints = []
        mining_results = {}

        try:
            # 1. Mine request parameter constraints
            if self.verbose:
                print(f"\nStep 1: Mining request parameter constraints...")

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

            if self.verbose:
                print(
                    f"  ✓ Found {len(request_param_constraints)} parameter constraints"
                )

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error mining parameter constraints: {str(e)}")
            mining_results["param_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 2. Mine request body constraints
            if self.verbose:
                print(f"\nStep 2: Mining request body constraints...")

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

            if self.verbose:
                print(f"  ✓ Found {len(request_body_constraints)} body constraints")

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error mining body constraints: {str(e)}")
            mining_results["body_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 3. Mine response property constraints
            if self.verbose:
                print(f"\nStep 3: Mining response property constraints...")

            response_input = ResponsePropertyConstraintMinerInput(
                endpoint_info=endpoint,
                include_examples=inp.include_examples,
                analyze_structure=inp.include_schema_constraints,
            )

            response_output = await self.response_property_miner.execute(response_input)
            response_property_constraints = response_output.response_constraints
            mining_results["response_mining"] = {
                "count": len(response_property_constraints),
                "status": "success",
            }

            if self.verbose:
                print(
                    f"  ✓ Found {len(response_property_constraints)} response constraints"
                )

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error mining response constraints: {str(e)}")
            mining_results["response_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 4. Mine request-response correlation constraints
            if inp.include_correlation_constraints:
                if self.verbose:
                    print(
                        f"\nStep 4: Mining request-response correlation constraints..."
                    )

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

                if self.verbose:
                    print(
                        f"  ✓ Found {len(request_response_constraints)} correlation constraints"
                    )
            else:
                if self.verbose:
                    print(f"\nStep 4: Skipping correlation constraints (disabled)")
                mining_results["correlation_mining"] = {
                    "count": 0,
                    "status": "skipped",
                }

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error mining correlation constraints: {str(e)}")
            mining_results["correlation_mining"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        # Calculate totals
        total_constraints = (
            len(request_param_constraints)
            + len(request_body_constraints)
            + len(response_property_constraints)
            + len(request_response_constraints)
        )

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"CONSTRAINT MINING COMPLETED")
            print(f"{'='*60}")
            print(f"Endpoint: {endpoint.method.upper()} {endpoint.path}")
            print(f"Total constraints found: {total_constraints}")
            print(f"Breakdown:")
            print(f"  - Parameter constraints: {len(request_param_constraints)}")
            print(f"  - Body constraints: {len(request_body_constraints)}")
            print(f"  - Response constraints: {len(response_property_constraints)}")
            print(f"  - Correlation constraints: {len(request_response_constraints)}")
            print(f"Status: Success")

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
            request_param_constraints=request_param_constraints,
            request_body_constraints=request_body_constraints,
            response_property_constraints=response_property_constraints,
            request_response_constraints=request_response_constraints,
            total_constraints=total_constraints,
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up all specialized mining tools."""
        await self.request_param_miner.cleanup()
        await self.request_body_miner.cleanup()
        await self.response_property_miner.cleanup()
        await self.request_response_miner.cleanup()
