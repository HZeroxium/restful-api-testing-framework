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
from config.constraint_mining_config import (
    ConstraintSeverity,
    LLMPromptConfig,
)
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

        self.logger.info(f"Analyzing {endpoint.method.upper()} {endpoint.path}")
        self.logger.add_context(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            endpoint_name=getattr(endpoint, "name", "unknown"),
        )

        # Define simplified LLM response schema without additionalProperties issues
        class ParameterConstraint(BaseModel):
            parameter_name: str = Field(..., description="Name of the parameter")
            parameter_type: str = Field(..., description="Type: query, path, or header")
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of constraint")
            severity: str = Field(
                default=ConstraintSeverity.INFO, description="Severity level"
            )
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
            self.logger.debug("Starting LLM analysis for parameter constraints")

            # Format the prompt with sanitized endpoint data
            from ...utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_PARAM_CONSTRAINT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2)
            )

            self.logger.debug("Executing LLM agent for parameter constraint extraction")

            # Execute LLM analysis with improved error handling
            raw_json = await create_and_execute_llm_agent(
                app_name="request_param_constraint_miner",
                agent_name="request_param_constraint_miner",
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
                self.logger.debug(
                    f"Processing {len(raw_json['constraints'])} raw constraints from LLM"
                )

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
                        severity=constraint_data.get(
                            "severity", ConstraintSeverity.INFO
                        ),
                        source="llm",
                        details=details,
                    )
                    constraints.append(constraint)

            # If no constraints found, generate fallback
            if not constraints:
                self.logger.warning(
                    "No constraints from LLM, generating fallback constraints"
                )
                return self._generate_fallback_constraints(endpoint)

            self.logger.info(
                f"Successfully extracted {len(constraints)} parameter constraints"
            )

            result_summary = {
                "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
                "total_constraints": len(constraints),
                "source": "llm",
                "status": LLMPromptConfig.STATUS_SUCCESS,
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
            self.logger.debug("Falling back to basic constraint generation")
            # Return fallback constraints
            return self._generate_fallback_constraints(endpoint)

    def _generate_fallback_constraints(
        self, endpoint
    ) -> RequestParamConstraintMinerOutput:
        """Generate basic parameter constraints when LLM fails."""
        constraints = []

        self.logger.debug("Generating fallback parameter constraints")

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
                        severity=ConstraintSeverity.ERROR,
                        source=LLMPromptConfig.FALLBACK_SOURCE,
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
                        severity=ConstraintSeverity.ERROR,
                        source=LLMPromptConfig.FALLBACK_SOURCE,
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
                severity=ConstraintSeverity.INFO,
                source=LLMPromptConfig.FALLBACK_SOURCE,
                details={
                    "parameter_name": "general",
                    "parameter_type": "query",
                    "constraint_type": "basic_validation",
                    "validation_rule": "basic_param_check",
                },
            )
            constraints.append(constraint)

        self.logger.warning(
            f"Generated {len(constraints)} fallback parameter constraints"
        )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": LLMPromptConfig.FALLBACK_SOURCE,
            "status": LLMPromptConfig.STATUS_SUCCESS_FALLBACK,
            "reason": LLMPromptConfig.FALLBACK_REASON_LLM_ERROR,
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
        self.logger.debug("Cleaning up RequestParamConstraintMinerTool resources")
        pass
