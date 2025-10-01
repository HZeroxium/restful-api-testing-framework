"""Request parameter validation script generator."""

import uuid
from typing import Dict, List, Optional
import json

from core.base_tool import BaseTool
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
    ValidationScript,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.test_script_generator import REQUEST_PARAM_SCRIPT_PROMPT
from pydantic import BaseModel, Field
from common.logger import LoggerFactory, LoggerType, LogLevel


class RequestParamScriptGeneratorTool(BaseTool):
    """Tool for generating request parameter validation scripts using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_param_script_generator",
        description: str = "Generates validation scripts for request parameters",
        config: Optional[Dict] = None,
        verbose: bool = True,
        cache_enabled: bool = True,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=TestScriptGeneratorInput,
            output_schema=TestScriptGeneratorOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

        # Initialize custom logger
        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"script-generator.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    async def _execute(
        self, inp: TestScriptGeneratorInput
    ) -> TestScriptGeneratorOutput:
        """Generate request parameter validation scripts."""
        endpoint = inp.endpoint_info
        constraints = inp.constraints or []

        # Filter constraints to only request parameter constraints
        param_constraints = [c for c in constraints if c.type == "request_param"]

        self.logger.info(f"Processing {len(param_constraints)} parameter constraints")
        if self.verbose:
            self.logger.debug(f"Endpoint: {endpoint.method.upper()} {endpoint.path}")

        if not param_constraints:
            self.logger.warning(
                "No request parameter constraints found, generating basic scripts"
            )
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_basic_param_scripts()
            )

        # Define LLM response schema
        class ScriptOutput(BaseModel):
            name: str
            script_type: str
            validation_code: str
            description: str

        class ValidationScriptResult(BaseModel):
            validation_scripts: List[ScriptOutput] = Field(default_factory=list)

        try:
            # Prepare data for LLM
            from ...utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_PARAM_SCRIPT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2),
                constraints_data=json.dumps(
                    [c.model_dump() for c in param_constraints], indent=2
                ),
                constraint_count=len(param_constraints),
            )

            self.logger.debug(
                f"Sending prompt to LLM with {len(param_constraints)} constraints"
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="request_param_script_generator",
                agent_name="request_param_script_generator",
                instruction=formatted_prompt,
                input_data={
                    "endpoint": sanitized_endpoint_data,
                    "constraints": [c.model_dump() for c in param_constraints],
                    "constraint_count": len(param_constraints),
                },
                output_schema=ValidationScriptResult,
                timeout=self.config.get("timeout", 120.0) if self.config else 120.0,
                max_retries=self.config.get("max_retries", 3) if self.config else 3,
                verbose=self.verbose,
            )

            validation_scripts = []

            if (
                raw_json
                and isinstance(raw_json, dict)
                and "validation_scripts" in raw_json
            ):
                scripts_data = raw_json["validation_scripts"]
                if not isinstance(scripts_data, list):
                    self.logger.warning(
                        f"validation_scripts is not a list: {type(scripts_data)}"
                    )
                    scripts_data = []

                for i, script_data in enumerate(scripts_data):
                    if not isinstance(script_data, dict):
                        self.logger.warning(
                            f"script_data {i} is not a dict: {type(script_data)}"
                        )
                        continue

                    validation_code = script_data.get("validation_code", "")
                    if not validation_code:
                        self.logger.warning(f"Empty validation_code for script {i}")
                        continue

                    # Clean up validation code - remove JSON escaping
                    validation_code = validation_code.replace("\\n", "\n").replace(
                        '\\"', '"'
                    )

                    # Ensure the code is properly formatted as a function
                    if not validation_code.strip().startswith("def "):
                        function_name = f"validate_param_{i}"
                        validation_code = f"""
def {function_name}(request, response):
    \"\"\"Auto-wrapped parameter validation function\"\"\"
    try:
{self._indent_code(validation_code, 8)}
    except Exception as e:
        return False
"""

                    # Map to corresponding constraint
                    constraint_id = None
                    if i < len(param_constraints):
                        constraint_id = param_constraints[i].id

                    script = ValidationScript(
                        id=str(uuid.uuid4()),
                        name=script_data.get(
                            "name",
                            f"Parameter validation {i + 1}",
                        ),
                        script_type="request_param",
                        validation_code=validation_code,
                        description=script_data.get(
                            "description", "Request parameter validation"
                        ),
                        constraint_id=constraint_id,
                    )
                    validation_scripts.append(script)
            else:
                self.logger.warning(
                    "Invalid or missing validation_scripts in LLM response"
                )

            # Log parsing results
            self.logger.debug(
                f"Successfully parsed {len(validation_scripts)} scripts from LLM response"
            )

            # Ensure we have the right number of scripts
            if len(validation_scripts) != len(param_constraints):
                self.logger.warning(
                    f"Generated {len(validation_scripts)} scripts but expected {len(param_constraints)}"
                )

                # Fill missing scripts with basic ones
                while len(validation_scripts) < len(param_constraints):
                    missing_constraint = param_constraints[len(validation_scripts)]
                    basic_script = self._generate_constraint_specific_script(
                        missing_constraint, len(validation_scripts)
                    )
                    validation_scripts.append(basic_script)

            if not validation_scripts:
                validation_scripts = self._generate_basic_param_scripts()

            self.logger.info(
                f"Generated {len(validation_scripts)} parameter validation scripts"
            )

            return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

        except Exception as e:
            self.logger.error(f"Error generating parameter scripts: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            # Generate fallback scripts based on constraints
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_constraint_based_fallback_scripts(
                    param_constraints
                )
            )

    def _generate_constraint_specific_script(
        self, constraint, index: int
    ) -> ValidationScript:
        """Generate a basic script for a specific constraint."""
        param_name = constraint.details.get("parameter_name", f"param_{index}")
        constraint_type = constraint.details.get("constraint_type", "type")
        expected_type = constraint.details.get("expected_type", "string").lower()

        self.logger.debug(f"Generating constraint-specific script for {param_name}")

        # Map expected types to Python types
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "(int, float)",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }

        python_type = type_mapping.get(expected_type, "str")

        validation_code = f"""
def validate_{param_name}_{constraint_type}(request, response):
    \"\"\"Validate {param_name} parameter {constraint_type} constraint - Reference: {constraint.id}\"\"\"
    try:
        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})
        if '{param_name}' in params:
            return isinstance(params['{param_name}'], {python_type})
        return True  # Optional parameter
    except Exception as e:
        return False
"""

        return ValidationScript(
            id=str(uuid.uuid4()),
            name=f"Validate {param_name} {constraint_type}",
            script_type="request_param",
            validation_code=validation_code,
            description=f"Validates {param_name} parameter {constraint_type} constraint",
            constraint_id=constraint.id,
        )

    def _generate_constraint_based_fallback_scripts(
        self, constraints
    ) -> List[ValidationScript]:
        """Generate fallback scripts based on actual constraints."""
        self.logger.info("Generating constraint-based fallback scripts")
        scripts = []
        for i, constraint in enumerate(constraints):
            script = self._generate_constraint_specific_script(constraint, i)
            scripts.append(script)

        if not scripts:
            scripts = self._generate_basic_param_scripts()

        return scripts

    def _generate_basic_param_scripts(self) -> List[ValidationScript]:
        """Generate basic parameter validation scripts as fallback."""
        self.logger.info("Generating basic parameter validation scripts")
        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic parameter type validation",
                script_type="request_param",
                validation_code="""
def validate_basic_parameters(request, response):
    \"\"\"Basic validation for request parameters\"\"\"
    try:
        # Check if request has parameters attribute
        if hasattr(request, 'params') or isinstance(request, dict):
            params = getattr(request, 'params', {}) if hasattr(request, 'params') else request.get('params', {})
            # Basic validation - parameters should be strings or basic types
            for key, value in params.items():
                if value is not None and not isinstance(value, (str, int, float, bool)):
                    return False
            return True
        return True
    except Exception as e:
        return False
""",
                description="Basic validation for request parameter types",
            )
        ]

    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper function to indent code properly."""
        lines = code.strip().split("\n")
        indented_lines = [" " * spaces + line for line in lines]
        return "\n".join(indented_lines)

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up RequestParamScriptGeneratorTool resources")
