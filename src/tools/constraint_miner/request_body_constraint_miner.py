# tools/constraint_miner/request_body_constraint_miner.py

"""Request body constraint mining tool."""

import uuid
from typing import Dict, List, Optional
import json

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    RequestBodyConstraintMinerInput,
    RequestBodyConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.constraint_miner import REQUEST_BODY_CONSTRAINT_PROMPT
from pydantic import BaseModel, Field
from common.logger import LoggerFactory, LoggerType, LogLevel


class RequestBodyConstraintMinerTool(BaseTool):
    """Tool for mining request body constraints using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_body_constraint_miner",
        description: str = "Mines constraints from API request body",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=RequestBodyConstraintMinerInput,
            output_schema=RequestBodyConstraintMinerOutput,
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
        self, inp: RequestBodyConstraintMinerInput
    ) -> RequestBodyConstraintMinerOutput:
        """Mine request body constraints from endpoint information."""
        endpoint = inp.endpoint_info

        if self.verbose:
            self.logger.info(f"Analyzing {endpoint.method.upper()} {endpoint.path}")

        # Skip if method typically doesn't use request body
        if endpoint.method.upper() in ["GET", "DELETE", "HEAD", "OPTIONS"]:
            if self.verbose:
                self.logger.info(
                    f"Skipping request body analysis for {endpoint.method.upper()} method"
                )

            return RequestBodyConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                body_constraints=[],
                total_constraints=0,
                result={
                    "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                    "total_constraints": 0,
                    "reason": "Method doesn't typically use request body",
                    "status": "skipped",
                },
            )

        # Define simplified LLM response schema without additionalProperties issues
        class RequestBodyConstraint(BaseModel):
            field_path: str = Field(..., description="Path to field in request body")
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of constraint")
            severity: str = Field(default="info", description="Severity level")
            validation_rule: str = Field(..., description="Validation rule identifier")
            # Simplified additional fields
            required: Optional[bool] = Field(
                None, description="Whether field is required"
            )
            data_type: Optional[str] = Field(None, description="Expected data type")
            format: Optional[str] = Field(None, description="Expected format")

        class RequestBodyConstraintResult(BaseModel):
            constraints: List[RequestBodyConstraint] = Field(default_factory=list)

        try:
            # Format the prompt with sanitized endpoint data
            from utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_BODY_CONSTRAINT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2)
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="request_body_miner",
                agent_name="body_constraint_analyzer",
                instruction=formatted_prompt,
                input_data=sanitized_endpoint_data,
                input_schema=type(endpoint),
                output_schema=RequestBodyConstraintResult,
                timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
                max_retries=self.config.get("max_retries", 2) if self.config else 2,
                verbose=self.verbose,
            )

            constraints = []
            if raw_json and "constraints" in raw_json:
                for constraint_data in raw_json["constraints"]:
                    # Create details dict from the constraint data
                    details = {
                        "field_path": constraint_data.get("field_path", ""),
                        "constraint_type": constraint_data.get("constraint_type", ""),
                        "validation_rule": constraint_data.get("validation_rule", ""),
                    }

                    # Add optional fields if present
                    optional_fields = ["required", "data_type", "format"]
                    for field in optional_fields:
                        if constraint_data.get(field) is not None:
                            details[field] = constraint_data[field]

                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.REQUEST_BODY,
                        description=constraint_data.get("description", ""),
                        severity=constraint_data.get("severity", "info"),
                        source="llm",
                        details=details,
                    )
                    constraints.append(constraint)

            if self.verbose:
                self.logger.info(f"Found {len(constraints)} request body constraints")

            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": len(constraints),
                "source": "llm",
                "status": "success",
                "constraint_types": list(
                    set(c.details.get("constraint_type", "") for c in constraints)
                ),
            }

            return RequestBodyConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                body_constraints=constraints,
                total_constraints=len(constraints),
                result=result_summary,
            )

        except Exception as e:
            self.logger.error(f"Error in request body constraint mining: {str(e)}")
            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(
        self, endpoint
    ) -> RequestBodyConstraintMinerOutput:
        """Generate basic request body constraints when LLM fails."""
        constraints = []

        # Generate basic constraints for request body
        if endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
            constraint = ApiConstraint(
                id=str(uuid.uuid4()),
                type=ConstraintType.REQUEST_BODY,
                description="Request body should be valid JSON",
                severity="error",
                source="fallback",
                details={
                    "field_path": "root",
                    "constraint_type": "structure",
                    "validation_rule": "valid_json",
                },
            )
            constraints.append(constraint)

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        return RequestBodyConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            body_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
