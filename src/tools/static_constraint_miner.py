# tools/static_constraint_miner.py

import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.constants import LLM_INSTRUCTIONS


class StaticConstraintMinerTool(BaseTool):
    """
    Tool for mining static constraints from API endpoint information using LLM.

    This tool analyzes OpenAPI specifications using LLM to extract:
    1. Request-Response constraints: How request parameters affect response status/content
    2. Response-Property constraints: Rules about properties within the response
    """

    def __init__(
        self,
        *,
        name: str = "static_constraint_miner",
        description: str = "Mines static constraints from API endpoint information using LLM",
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

    async def _execute(
        self, inp: StaticConstraintMinerInput
    ) -> StaticConstraintMinerOutput:
        """Mine constraints from the endpoint information using LLM."""
        endpoint = inp.endpoint_info

        if self.verbose:
            print(
                f"StaticConstraintMiner: Mining constraints for {endpoint.method.upper()} {endpoint.path}"
            )

        # Define schemas for LLM interaction
        class RequestResponseConstraint(BaseModel):
            param: str = Field(
                ..., description="Name of the request parameter or body field"
            )
            property: str = Field(..., description="Name of the response JSON property")
            description: str = Field(
                ..., description="Natural language description of the constraint"
            )
            severity: str = Field(
                default="info", description="Severity level (info, warning, error)"
            )

        class ResponsePropertyConstraint(BaseModel):
            property: str = Field(..., description="Name of the response JSON property")
            description: str = Field(
                ..., description="Natural language description of the constraint"
            )
            severity: str = Field(
                default="info", description="Severity level (info, warning, error)"
            )

        class ConstraintExtractionResult(BaseModel):
            request_response_constraints: List[RequestResponseConstraint] = Field(
                default_factory=list
            )
            response_property_constraints: List[ResponsePropertyConstraint] = Field(
                default_factory=list
            )

        try:
            # Execute LLM agent with proper error handling
            if self.verbose:
                print("Executing LLM agent for constraint extraction...")

            raw_json = await create_and_execute_llm_agent(
                app_name="constraint_miner",
                agent_name="llm_constraint_miner",
                instruction=LLM_INSTRUCTIONS.get(
                    "constraint_miner",
                    "Extract constraints from the API endpoint specification.",
                ),
                input_data=endpoint.model_dump(),
                input_schema=type(endpoint),
                output_schema=ConstraintExtractionResult,
                timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
                max_retries=self.config.get("max_retries", 2) if self.config else 2,
                retry_delay=self.config.get("retry_delay", 1.0) if self.config else 1.0,
                verbose=self.verbose,
            )

            if raw_json is None:
                if self.verbose:
                    print("LLM failed, falling back to static constraint generation...")
                return self._generate_fallback_constraints(endpoint)

            # Process LLM output into constraints
            request_response_constraints, response_property_constraints = (
                self._process_llm_output(raw_json)
            )

            total_constraints = len(request_response_constraints) + len(
                response_property_constraints
            )

            # Create result summary
            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": total_constraints,
                "request_response_count": len(request_response_constraints),
                "response_property_count": len(response_property_constraints),
                "source": "llm",
                "status": "success",
            }

            if self.verbose:
                print(
                    f"Found {total_constraints} constraints for {endpoint.method.upper()} {endpoint.path}"
                )

            return StaticConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                request_response_constraints=request_response_constraints,
                response_property_constraints=response_property_constraints,
                total_constraints=total_constraints,
                result=result_summary,
            )

        except Exception as e:
            error_msg = f"Error during constraint mining: {str(e)}"
            if self.verbose:
                print(f"{error_msg}, falling back to static constraints...")
            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(self, endpoint) -> StaticConstraintMinerOutput:
        """Generate basic constraints when LLM fails."""
        request_response_constraints = []
        response_property_constraints = []

        # Generate basic constraints based on endpoint method
        if endpoint.method.upper() == "GET":
            # Basic GET constraints
            request_response_constraints.append(
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.REQUEST_RESPONSE,
                    description="GET request should return 200 status for valid requests",
                    severity="info",
                    source="fallback",
                    details={
                        "parameter": "general",
                        "response_property": "status_code",
                    },
                )
            )

            response_property_constraints.append(
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Response should have valid JSON structure",
                    severity="info",
                    source="fallback",
                    details={"property": "structure"},
                )
            )

        elif endpoint.method.upper() == "POST":
            request_response_constraints.append(
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.REQUEST_RESPONSE,
                    description="POST request should return 201 status for successful creation",
                    severity="info",
                    source="fallback",
                    details={"parameter": "body", "response_property": "status_code"},
                )
            )

        total_constraints = len(request_response_constraints) + len(
            response_property_constraints
        )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": total_constraints,
            "request_response_count": len(request_response_constraints),
            "response_property_count": len(response_property_constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        if self.verbose:
            print(f"Generated {total_constraints} fallback constraints")

        return StaticConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            request_response_constraints=request_response_constraints,
            response_property_constraints=response_property_constraints,
            total_constraints=total_constraints,
            result=result_summary,
        )

    def _create_empty_result(
        self, endpoint, error_message: str
    ) -> StaticConstraintMinerOutput:
        """Create an empty result with error information."""
        return StaticConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            request_response_constraints=[],
            response_property_constraints=[],
            total_constraints=0,
            result={
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "error": error_message,
                "status": "failed",
            },
        )

    def _process_llm_output(
        self, raw_json: Dict
    ) -> tuple[List[ApiConstraint], List[ApiConstraint]]:
        """Process LLM output into ApiConstraint objects."""
        request_response_constraints = []
        response_property_constraints = []

        try:
            # Process request-response constraints
            if "request_response_constraints" in raw_json:
                for constraint in raw_json["request_response_constraints"]:
                    if isinstance(constraint, dict):
                        constraint_id = str(uuid.uuid4())
                        request_response_constraints.append(
                            ApiConstraint(
                                id=constraint_id,
                                type=ConstraintType.REQUEST_RESPONSE,
                                description=constraint.get("description", ""),
                                severity=constraint.get("severity", "info"),
                                source="llm",
                                details={
                                    "parameter": constraint.get("param", ""),
                                    "response_property": constraint.get("property", ""),
                                },
                            )
                        )

            # Process response-property constraints
            if "response_property_constraints" in raw_json:
                for constraint in raw_json["response_property_constraints"]:
                    if isinstance(constraint, dict):
                        constraint_id = str(uuid.uuid4())
                        response_property_constraints.append(
                            ApiConstraint(
                                id=constraint_id,
                                type=ConstraintType.RESPONSE_PROPERTY,
                                description=constraint.get("description", ""),
                                severity=constraint.get("severity", "info"),
                                source="llm",
                                details={"property": constraint.get("property", "")},
                            )
                        )

        except Exception as e:
            if self.verbose:
                print(f"Error processing LLM output: {str(e)}")

        return request_response_constraints, response_property_constraints

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
