# tools/constraint_miner/request_param_constraint_miner.py

"""Request parameter constraint mining tool."""

import uuid
from typing import Dict, List, Optional
import json

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    RequestParamConstraintMinerInput,
    RequestParamConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.constraint_miner import REQUEST_PARAM_CONSTRAINT_PROMPT
from pydantic import BaseModel, Field
from common.logger import LoggerFactory, LoggerType, LogLevel


class RequestParamConstraintMinerTool(BaseTool):
    """Tool for mining request parameter constraints using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_param_constraint_miner",
        description: str = "Mines constraints from API request parameters",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=RequestParamConstraintMinerInput,
            output_schema=RequestParamConstraintMinerOutput,
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
        self, inp: RequestParamConstraintMinerInput
    ) -> RequestParamConstraintMinerOutput:
        """Mine parameter constraints from endpoint information."""
        endpoint = inp.endpoint_info

        if self.verbose:
            self.logger.info(f"Analyzing {endpoint.method.upper()} {endpoint.path}")

        # Define simplified LLM response schema without additionalProperties issues
        class ParameterConstraint(BaseModel):
            parameter_name: str = Field(..., description="Name of the parameter")
            parameter_type: str = Field(..., description="Type: query, path, or header")
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of constraint")
            severity: str = Field(default="info", description="Severity level")
            validation_rule: str = Field(..., description="Validation rule identifier")
            # Simplified additional fields
            allowed_values: Optional[List[str]] = Field(
                None, description="Allowed enum values"
            )
            min_value: Optional[float] = Field(None, description="Minimum value")
            max_value: Optional[float] = Field(None, description="Maximum value")
            pattern: Optional[str] = Field(None, description="Regex pattern")
            expected_type: Optional[str] = Field(None, description="Expected data type")

        class ParameterConstraintResult(BaseModel):
            constraints: List[ParameterConstraint] = Field(default_factory=list)

        try:
            # Format the prompt with sanitized endpoint data
            from utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_PARAM_CONSTRAINT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2)
            )

            # Execute LLM analysis with improved error handling
            raw_json = await create_and_execute_llm_agent(
                app_name="request_param_miner",
                agent_name="param_constraint_analyzer",
                instruction=formatted_prompt,
                input_data=sanitized_endpoint_data,
                input_schema=type(endpoint),
                output_schema=ParameterConstraintResult,
                timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
                max_retries=self.config.get("max_retries", 2) if self.config else 2,
                verbose=self.verbose,
            )

            constraints = []
            if raw_json and "constraints" in raw_json:
                for constraint_data in raw_json["constraints"]:
                    # Create details dict from the constraint data
                    details = {
                        "parameter_name": constraint_data.get("parameter_name", ""),
                        "parameter_type": constraint_data.get("parameter_type", ""),
                        "constraint_type": constraint_data.get("constraint_type", ""),
                        "validation_rule": constraint_data.get("validation_rule", ""),
                    }

                    # Add optional fields if present
                    optional_fields = [
                        "allowed_values",
                        "min_value",
                        "max_value",
                        "pattern",
                        "expected_type",
                    ]
                    for field in optional_fields:
                        if constraint_data.get(field) is not None:
                            details[field] = constraint_data[field]

                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.REQUEST_PARAM,
                        description=constraint_data.get("description", ""),
                        severity=constraint_data.get("severity", "info"),
                        source="llm",
                        details=details,
                    )
                    constraints.append(constraint)

            # If no constraints found, generate fallback
            if not constraints:
                if self.verbose:
                    self.logger.warning(
                        "No constraints from LLM, generating fallback..."
                    )
                return self._generate_fallback_constraints(endpoint)

            if self.verbose:
                self.logger.info(f"Found {len(constraints)} parameter constraints")

            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": len(constraints),
                "source": "llm",
                "status": "success",
                "constraint_types": list(
                    set(c.details.get("constraint_type", "") for c in constraints)
                ),
            }

            return RequestParamConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                param_constraints=constraints,
                total_constraints=len(constraints),
                result=result_summary,
            )

        except Exception as e:
            self.logger.error(f"Error in parameter constraint mining: {str(e)}")
            # Return fallback constraints
            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(
        self, endpoint
    ) -> RequestParamConstraintMinerOutput:
        """Generate basic parameter constraints when LLM fails."""
        constraints = []

        # Generate basic constraints based on common patterns
        if hasattr(endpoint, "parameters") and endpoint.parameters:
            for param in endpoint.parameters:
                param_name = param.get("name", "")
                param_in = param.get("in", "query")
                param_required = param.get("required", False)

                if param_required and param_name:
                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.REQUEST_PARAM,
                        description=f"Parameter '{param_name}' is required",
                        severity="error",
                        source="fallback",
                        details={
                            "parameter_name": param_name,
                            "parameter_type": param_in,
                            "constraint_type": "required",
                            "validation_rule": "required_param",
                        },
                    )
                    constraints.append(constraint)

                # Add type constraints if schema is available
                if param.get("schema", {}).get("type"):
                    param_type = param["schema"]["type"]
                    constraint = ApiConstraint(
                        id=str(uuid.uuid4()),
                        type=ConstraintType.REQUEST_PARAM,
                        description=f"Parameter '{param_name}' must be of type {param_type}",
                        severity="error",
                        source="fallback",
                        details={
                            "parameter_name": param_name,
                            "parameter_type": param_in,
                            "constraint_type": "type_validation",
                            "validation_rule": f"type_{param_type}",
                            "expected_type": param_type,
                        },
                    )
                    constraints.append(constraint)

        # Add common fallback constraints
        if not constraints:
            # Generate basic parameter validation constraint
            constraint = ApiConstraint(
                id=str(uuid.uuid4()),
                type=ConstraintType.REQUEST_PARAM,
                description="Basic parameter validation",
                severity="info",
                source="fallback",
                details={
                    "parameter_name": "general",
                    "parameter_type": "query",
                    "constraint_type": "basic_validation",
                    "validation_rule": "basic_param_check",
                },
            )
            constraints.append(constraint)

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        return RequestParamConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            param_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
