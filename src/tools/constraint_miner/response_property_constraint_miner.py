# tools/constraint_miner/response_property_constraint_miner.py

"""Response property constraint mining tool."""

import uuid
from typing import Dict, List, Optional
import json

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    ResponsePropertyConstraintMinerInput,
    ResponsePropertyConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.constraint_miner import RESPONSE_PROPERTY_CONSTRAINT_PROMPT
from pydantic import BaseModel, Field


class ResponsePropertyConstraintMinerTool(BaseTool):
    """Tool for mining response property constraints using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "response_property_constraint_miner",
        description: str = "Mines constraints from API response properties",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=ResponsePropertyConstraintMinerInput,
            output_schema=ResponsePropertyConstraintMinerOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(
        self, inp: ResponsePropertyConstraintMinerInput
    ) -> ResponsePropertyConstraintMinerOutput:
        """Mine response property constraints from endpoint information."""
        endpoint = inp.endpoint_info

        if self.verbose:
            print(
                f"ResponsePropertyConstraintMiner: Analyzing {endpoint.method.upper()} {endpoint.path}"
            )

        # Define simplified LLM response schema without additionalProperties issues
        class ResponsePropertyConstraint(BaseModel):
            property_path: str = Field(..., description="Path to property in response")
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of constraint")
            severity: str = Field(default="info", description="Severity level")
            validation_rule: str = Field(..., description="Validation rule identifier")
            applies_to_status: List[int] = Field(
                default_factory=list, description="Status codes"
            )
            # Simplified details without additionalProperties
            data_type: Optional[str] = Field(None, description="Data type")
            format: Optional[str] = Field(None, description="Format specification")

        class ResponsePropertyConstraintResult(BaseModel):
            constraints: List[ResponsePropertyConstraint] = Field(default_factory=list)

        try:
            # Format the prompt with sanitized endpoint data
            from utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = RESPONSE_PROPERTY_CONSTRAINT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2)
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="response_property_miner",
                agent_name="response_constraint_analyzer",
                instruction=formatted_prompt,
                input_data=sanitized_endpoint_data,
                input_schema=type(endpoint),
                output_schema=ResponsePropertyConstraintResult,
                timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
                max_retries=self.config.get("max_retries", 2) if self.config else 2,
                verbose=self.verbose,
            )

            constraints = []
            if raw_json and "constraints" in raw_json:
                for constraint_data in raw_json["constraints"]:
                    # Create details dict from the constraint data
                    details = {
                        "property_path": constraint_data.get("property_path", ""),
                        "constraint_type": constraint_data.get("constraint_type", ""),
                        "validation_rule": constraint_data.get("validation_rule", ""),
                        "applies_to_status": constraint_data.get(
                            "applies_to_status", []
                        ),
                    }

                    # Add optional fields if present
                    if constraint_data.get("data_type"):
                        details["data_type"] = constraint_data["data_type"]
                    if constraint_data.get("format"):
                        details["format"] = constraint_data["format"]

                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.RESPONSE_PROPERTY,
                        description=constraint_data.get("description", ""),
                        severity=constraint_data.get("severity", "info"),
                        source="llm",
                        details=details,
                    )
                    constraints.append(constraint)

            # If LLM didn't return constraints, use fallback
            if not constraints:
                if self.verbose:
                    print("No constraints from LLM, using fallback...")
                return self._generate_fallback_constraints(endpoint)

            if self.verbose:
                print(f"Found {len(constraints)} response property constraints")

            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": len(constraints),
                "source": "llm",
                "status": "success",
                "constraint_types": list(
                    set(c.details.get("constraint_type", "") for c in constraints)
                ),
            }

            return ResponsePropertyConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                response_constraints=constraints,
                total_constraints=len(constraints),
                result=result_summary,
            )

        except Exception as e:
            if self.verbose:
                print(f"Error in response property constraint mining: {str(e)}")

            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(
        self, endpoint
    ) -> ResponsePropertyConstraintMinerOutput:
        """Generate basic response constraints when LLM fails."""
        constraints = []

        # Generate common response constraints
        constraints.extend(
            [
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Successful GET response should return valid JSON structure",
                    severity="error",
                    source="fallback",
                    details={
                        "property_path": "root",
                        "constraint_type": "structure",
                        "validation_rule": "valid_json",
                        "applies_to_status": [200],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Response should include Content-Type header",
                    severity="warning",
                    source="fallback",
                    details={
                        "property_path": "headers.content-type",
                        "constraint_type": "format",
                        "validation_rule": "content_type_present",
                        "applies_to_status": [200, 201, 202],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Error responses should include error message or code",
                    severity="warning",
                    source="fallback",
                    details={
                        "property_path": "error",
                        "constraint_type": "structure",
                        "validation_rule": "error_info_present",
                        "applies_to_status": [400, 401, 403, 404, 500],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Timestamps should be in ISO 8601 format",
                    severity="info",
                    source="fallback",
                    details={
                        "property_path": "*.created_at,*.updated_at,*.timestamp",
                        "constraint_type": "format",
                        "validation_rule": "iso8601_datetime",
                        "applies_to_status": [200, 201],
                    },
                ),
            ]
        )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        return ResponsePropertyConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            response_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
