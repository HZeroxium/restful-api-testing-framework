# tools/constraint_miner/request_response_constraint_miner.py

"""Request-response correlation constraint mining tool."""

import uuid
from typing import Dict, List, Optional
import json

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    RequestResponseConstraintMinerInput,
    RequestResponseConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.constraint_miner import REQUEST_RESPONSE_CONSTRAINT_PROMPT
from pydantic import BaseModel, Field
from common.logger import LoggerFactory, LoggerType, LogLevel


class RequestResponseConstraintMinerTool(BaseTool):
    """Tool for mining request-response correlation constraints using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_response_constraint_miner",
        description: str = "Mines correlation constraints between requests and responses",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=RequestResponseConstraintMinerInput,
            output_schema=RequestResponseConstraintMinerOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"constraint-miner.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    async def _execute(
        self, inp: RequestResponseConstraintMinerInput
    ) -> RequestResponseConstraintMinerOutput:
        """Mine request-response correlation constraints from endpoint information."""
        endpoint = inp.endpoint_info

        if self.verbose:
            self.logger.info(f"Analyzing {endpoint.method.upper()} {endpoint.path}")

        # Define simplified LLM response schema without additionalProperties issues
        class RequestResponseConstraint(BaseModel):
            request_element: str = Field(
                ..., description="Request parameter/field name"
            )
            request_location: str = Field(
                ..., description="Location: query, path, body, header"
            )
            response_element: str = Field(
                ..., description="Response property or status affected"
            )
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of correlation")
            severity: str = Field(default="info", description="Severity level")
            validation_rule: str = Field(..., description="Validation rule identifier")
            # Simplified additional fields
            condition: Optional[str] = Field(
                None, description="Condition for the constraint"
            )

        class RequestResponseConstraintResult(BaseModel):
            constraints: List[RequestResponseConstraint] = Field(default_factory=list)

        try:
            # Format the prompt with sanitized endpoint data
            from ...utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_RESPONSE_CONSTRAINT_PROMPT.replace(
                "{{endpoint_data}}", json.dumps(sanitized_endpoint_data, indent=2)
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="request_response_constraint_miner",
                agent_name="request_response_constraint_miner",
                instruction=formatted_prompt,
                input_data=sanitized_endpoint_data,
                input_schema=type(endpoint),
                output_schema=RequestResponseConstraintResult,
                timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
                max_retries=self.config.get("max_retries", 2) if self.config else 2,
                verbose=self.verbose,
            )

            constraints = []
            if raw_json and "constraints" in raw_json:
                for constraint_data in raw_json["constraints"]:
                    # Create details dict from the constraint data
                    details = {
                        "request_element": constraint_data.get("request_element", ""),
                        "request_location": constraint_data.get("request_location", ""),
                        "response_element": constraint_data.get("response_element", ""),
                        "constraint_type": constraint_data.get("constraint_type", ""),
                        "validation_rule": constraint_data.get("validation_rule", ""),
                    }

                    # Add optional fields if present
                    if constraint_data.get("condition"):
                        details["condition"] = constraint_data["condition"]

                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.REQUEST_RESPONSE,
                        description=constraint_data.get("description", ""),
                        severity=constraint_data.get("severity", "info"),
                        source="llm",
                        details=details,
                    )
                    constraints.append(constraint)

            if self.verbose:
                self.logger.info(
                    f"Found {len(constraints)} request-response correlation constraints"
                )

            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": len(constraints),
                "source": "llm",
                "status": "success",
                "constraint_types": list(
                    set(c.details.get("constraint_type", "") for c in constraints)
                ),
            }

            return RequestResponseConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                correlation_constraints=constraints,
                total_constraints=len(constraints),
                result=result_summary,
            )

        except Exception as e:
            self.logger.error(f"Error in request-response constraint mining: {str(e)}")
            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(
        self, endpoint
    ) -> RequestResponseConstraintMinerOutput:
        """Generate basic correlation constraints when LLM fails."""
        constraints = []

        # Generate basic request-response correlations
        if endpoint.method.upper() == "POST":
            constraints.append(
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.REQUEST_RESPONSE,
                    description="Valid POST request should return 201 status with location header",
                    severity="info",
                    source="fallback",
                    details={
                        "request_element": "body",
                        "request_location": "body",
                        "response_element": "status_code",
                        "constraint_type": "status_mapping",
                        "validation_rule": "post_success_201",
                    },
                )
            )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        return RequestResponseConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            correlation_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
