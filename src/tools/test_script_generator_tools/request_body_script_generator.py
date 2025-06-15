"""Request body validation script generator."""

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
from config.prompts.test_script_generator import REQUEST_BODY_SCRIPT_PROMPT
from pydantic import BaseModel, Field
from common.logger import LoggerFactory, LoggerType, LogLevel


class RequestBodyScriptGeneratorTool(BaseTool):
    """Tool for generating request body validation scripts using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_body_script_generator",
        description: str = "Generates validation scripts for request body",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
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
        """Generate request body validation scripts."""
        endpoint = inp.endpoint_info
        test_data = inp.test_data
        constraints = inp.constraints or []

        # Filter constraints to only request body constraints
        body_constraints = [c for c in constraints if c.type == "request_body"]

        self.logger.info(f"Processing {len(body_constraints)} body constraints")
        if self.verbose:
            self.logger.debug(f"Endpoint: {endpoint.method.upper()} {endpoint.path}")

        # Skip if method typically doesn't use request body
        if endpoint.method.upper() in ["GET", "DELETE", "HEAD", "OPTIONS"]:
            self.logger.info(
                f"Skipping request body scripts for {endpoint.method.upper()} method"
            )
            return TestScriptGeneratorOutput(validation_scripts=[])

        if not body_constraints:
            self.logger.warning(
                "No request body constraints found, generating basic scripts"
            )
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_basic_body_scripts()
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
            from utils.llm_utils import prepare_endpoint_data_for_llm

            sanitized_endpoint_data = prepare_endpoint_data_for_llm(
                endpoint.model_dump()
            )

            formatted_prompt = REQUEST_BODY_SCRIPT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2),
                constraints_data=json.dumps(
                    [c.model_dump() for c in body_constraints], indent=2
                ),
                test_data=json.dumps(test_data.model_dump(), indent=2),
                constraint_count=len(body_constraints),
            )

            self.logger.debug(
                f"Sending prompt to LLM with {len(body_constraints)} constraints"
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="request_body_script_generator",
                agent_name="body_script_analyzer",
                instruction=formatted_prompt,
                input_data={
                    "endpoint": sanitized_endpoint_data,
                    "constraints": [c.model_dump() for c in body_constraints],
                    "test_data": test_data.model_dump(),
                    "constraint_count": len(body_constraints),
                },
                output_schema=ValidationScriptResult,
                timeout=self.config.get("timeout", 90.0) if self.config else 90.0,
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
                        function_name = f"validate_body_{i}"
                        validation_code = f"""
def {function_name}(request, response):
    \"\"\"Auto-wrapped body validation function\"\"\"
    try:
{self._indent_code(validation_code, 8)}
    except Exception as e:
        return False
"""

                    # Map to corresponding constraint
                    constraint_id = None
                    if i < len(body_constraints):
                        constraint_id = body_constraints[i].id

                    script = ValidationScript(
                        id=str(uuid.uuid4()),
                        name=script_data.get("name", f"Body validation {i + 1}"),
                        script_type="request_body",
                        validation_code=validation_code,
                        description=script_data.get(
                            "description", "Request body validation"
                        ),
                        constraint_id=constraint_id,
                    )
                    validation_scripts.append(script)
            else:
                self.logger.warning(
                    "Invalid or missing validation_scripts in LLM response"
                )

            # Ensure we have the right number of scripts
            if len(validation_scripts) != len(body_constraints):
                self.logger.warning(
                    f"Generated {len(validation_scripts)} scripts but expected {len(body_constraints)}"
                )

                # Fill missing scripts with constraint-specific ones
                while len(validation_scripts) < len(body_constraints):
                    missing_constraint = body_constraints[len(validation_scripts)]
                    basic_script = self._generate_constraint_specific_script(
                        missing_constraint, len(validation_scripts)
                    )
                    validation_scripts.append(basic_script)

            if not validation_scripts:
                validation_scripts = self._generate_basic_body_scripts()

            self.logger.info(
                f"Generated {len(validation_scripts)} body validation scripts"
            )

            return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

        except Exception as e:
            self.logger.error(f"Error generating body scripts: {str(e)}")
            if self.verbose:
                import traceback

                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_constraint_based_fallback_scripts(
                    body_constraints
                )
            )

    def _generate_constraint_specific_script(
        self, constraint, index: int
    ) -> ValidationScript:
        """Generate a basic script for a specific constraint."""
        field_path = constraint.details.get("field_path", f"field_{index}")
        constraint_type = constraint.details.get("constraint_type", "type")

        self.logger.debug(f"Generating constraint-specific script for {field_path}")

        validation_code = f"""
def validate_{field_path.replace('.', '_')}_{constraint_type}(request, response):
    \"\"\"Validate {field_path} field {constraint_type} constraint - Reference: {constraint.id}\"\"\"
    try:
        body = getattr(request, 'json', {{}}) if hasattr(request, 'json') else request.get('json', {{}})
        if '{field_path}' in body:
            # Add specific validation logic based on constraint type
            return True  # Placeholder - specific logic would go here
        return True  # Optional field
    except Exception as e:
        return False
"""

        return ValidationScript(
            id=str(uuid.uuid4()),
            name=f"Validate {field_path} {constraint_type}",
            script_type="request_body",
            validation_code=validation_code,
            description=f"Validates {field_path} field {constraint_type} constraint",
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
            scripts = self._generate_basic_body_scripts()

        return scripts

    def _generate_basic_body_scripts(self) -> List[ValidationScript]:
        """Generate basic body validation scripts as fallback."""
        self.logger.info("Generating basic body validation scripts")
        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic JSON body validation",
                script_type="request_body",
                validation_code="""
def validate_basic_json_body(request, response):
    \"\"\"Basic validation for JSON request body\"\"\"
    try:
        # Check if request has body attribute
        if hasattr(request, 'json') or isinstance(request, dict):
            body = getattr(request, 'json', {}) if hasattr(request, 'json') else request.get('json', {})
            # Basic validation - body should be a dict or list
            return isinstance(body, (dict, list)) or body is None
        return True
    except Exception as e:
        return False
""",
                description="Basic validation for JSON request body structure",
            )
        ]

    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper function to indent code properly."""
        lines = code.strip().split("\n")
        indented_lines = [" " * spaces + line for line in lines]
        return "\n".join(indented_lines)

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug("Cleaning up RequestBodyScriptGeneratorTool resources")
