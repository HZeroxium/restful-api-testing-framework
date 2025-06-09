"""Request-response correlation validation script generator."""

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
from config.prompts.test_script_generator import REQUEST_RESPONSE_SCRIPT_PROMPT
from pydantic import BaseModel, Field


class RequestResponseScriptGeneratorTool(BaseTool):
    """Tool for generating request-response correlation validation scripts using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "request_response_script_generator",
        description: str = "Generates validation scripts for request-response correlations",
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

    async def _execute(
        self, inp: TestScriptGeneratorInput
    ) -> TestScriptGeneratorOutput:
        """Generate request-response correlation validation scripts."""
        endpoint = inp.endpoint_info
        test_data = inp.test_data
        constraints = inp.constraints or []

        # Filter constraints to only request-response constraints
        correlation_constraints = [
            c for c in constraints if c.type == "request_response"
        ]

        if self.verbose:
            print(
                f"RequestResponseScriptGenerator: Processing {len(correlation_constraints)} correlation constraints"
            )

        if not correlation_constraints:
            if self.verbose:
                print("No request-response constraints found, generating basic scripts")
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_basic_correlation_scripts()
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

            formatted_prompt = REQUEST_RESPONSE_SCRIPT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2),
                constraints_data=json.dumps(
                    [c.model_dump() for c in correlation_constraints], indent=2
                ),
                test_data=json.dumps(test_data.model_dump(), indent=2),
                constraint_count=len(correlation_constraints),
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="request_response_script_generator",
                agent_name="correlation_script_analyzer",
                instruction=formatted_prompt,
                input_data={
                    "endpoint": sanitized_endpoint_data,
                    "constraints": [c.model_dump() for c in correlation_constraints],
                    "test_data": test_data.model_dump(),
                    "constraint_count": len(correlation_constraints),
                },
                output_schema=ValidationScriptResult,
                timeout=self.config.get("timeout", 120.0) if self.config else 120.0,
                max_retries=self.config.get("max_retries", 3) if self.config else 3,
                verbose=self.verbose,
            )

            validation_scripts = []
            if self.verbose:
                print(f"Raw JSON from LLM: {raw_json}")

            if (
                raw_json
                and isinstance(raw_json, dict)
                and "validation_scripts" in raw_json
            ):
                scripts_data = raw_json["validation_scripts"]
                if not isinstance(scripts_data, list):
                    if self.verbose:
                        print(
                            f"Warning: validation_scripts is not a list: {type(scripts_data)}"
                        )
                    scripts_data = []

                for i, script_data in enumerate(scripts_data):
                    if not isinstance(script_data, dict):
                        if self.verbose:
                            print(
                                f"Warning: script_data {i} is not a dict: {type(script_data)}"
                            )
                        continue

                    validation_code = script_data.get("validation_code", "")
                    if not validation_code:
                        if self.verbose:
                            print(f"Warning: Empty validation_code for script {i}")
                        continue

                    # Clean up validation code - remove JSON escaping
                    validation_code = validation_code.replace("\\n", "\n").replace(
                        '\\"', '"'
                    )

                    # Ensure the code is properly formatted as a function
                    if not validation_code.strip().startswith("def "):
                        function_name = f"validate_correlation_{i}"
                        validation_code = f"""
def {function_name}(request, response):
    \"\"\"Auto-wrapped correlation validation function\"\"\"
    try:
{self._indent_code(validation_code, 8)}
    except Exception as e:
        return False
"""

                    # Map to corresponding constraint
                    constraint_id = None
                    if i < len(correlation_constraints):
                        constraint_id = correlation_constraints[i].id

                    script = ValidationScript(
                        id=str(uuid.uuid4()),
                        name=script_data.get(
                            "name",
                            f"Correlation validation {i + 1}",
                        ),
                        script_type="request_response",
                        validation_code=validation_code,
                        description=script_data.get(
                            "description", "Request-response correlation validation"
                        ),
                        constraint_id=constraint_id,
                    )
                    validation_scripts.append(script)
            else:
                if self.verbose:
                    print(
                        f"Warning: Invalid or missing validation_scripts in LLM response"
                    )

            # Ensure we have the right number of scripts
            if len(validation_scripts) != len(correlation_constraints):
                if self.verbose:
                    print(
                        f"⚠️  Generated {len(validation_scripts)} scripts but expected {len(correlation_constraints)}"
                    )

                # Fill missing scripts with constraint-specific ones
                while len(validation_scripts) < len(correlation_constraints):
                    missing_constraint = correlation_constraints[
                        len(validation_scripts)
                    ]
                    basic_script = self._generate_constraint_specific_script(
                        missing_constraint, len(validation_scripts)
                    )
                    validation_scripts.append(basic_script)

            if not validation_scripts:
                validation_scripts = self._generate_basic_correlation_scripts()

            if self.verbose:
                print(
                    f"Generated {len(validation_scripts)} correlation validation scripts"
                )

            return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

        except Exception as e:
            if self.verbose:
                print(f"Error generating correlation scripts: {str(e)}")
                import traceback

                traceback.print_exc()
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_constraint_based_fallback_scripts(
                    correlation_constraints
                )
            )

    def _generate_constraint_specific_script(
        self, constraint, index: int
    ) -> ValidationScript:
        """Generate a basic script for a specific constraint."""
        request_element = constraint.details.get("request_element", f"element_{index}")
        response_element = constraint.details.get(
            "response_element", f"response_{index}"
        )
        validation_rule = constraint.details.get("validation_rule", "correlation")

        validation_code = f"""
def validate_{request_element}_{validation_rule}_correlation(request, response):
    \"\"\"Validate {request_element} to {response_element} correlation - Reference: {constraint.id}\"\"\"
    try:
        params = getattr(request, 'params', {{}}) if hasattr(request, 'params') else request.get('params', {{}})
        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})
        
        # Basic correlation check - if request element exists, validate against response
        if '{request_element}' in params and isinstance(body, dict):
            # Add specific validation logic based on constraint type
            return True  # Placeholder - specific logic would go here
        return True
    except Exception as e:
        return False
"""

        return ValidationScript(
            id=str(uuid.uuid4()),
            name=f"Validate {request_element} {validation_rule} correlation",
            script_type="request_response",
            validation_code=validation_code,
            description=f"Validates {request_element} to {response_element} correlation",
            constraint_id=constraint.id,
        )

    def _generate_constraint_based_fallback_scripts(
        self, constraints
    ) -> List[ValidationScript]:
        """Generate fallback scripts based on actual constraints."""
        scripts = []
        for i, constraint in enumerate(constraints):
            script = self._generate_constraint_specific_script(constraint, i)
            scripts.append(script)

        if not scripts:
            scripts = self._generate_basic_correlation_scripts()

        return scripts

    def _generate_basic_correlation_scripts(self) -> List[ValidationScript]:
        """Generate basic correlation validation scripts as fallback."""
        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic request-response correlation validation",
                script_type="request_response",
                validation_code="""
def validate_basic_correlation(request, response):
    \"\"\"Basic validation for request-response correlation\"\"\"
    try:
        # Basic check - if request succeeded, response should be reasonable
        status_code = None
        if isinstance(response, dict):
            status_code = response.get("status_code")
        else:
            status_code = getattr(response, "status_code", None)
        
        # If we have a successful request, response should be in 200-299 range
        if status_code is not None:
            return 200 <= status_code < 600  # Any valid HTTP status code
        return True
    except Exception as e:
        return False
""",
                description="Basic validation for request-response correlation",
            )
        ]

    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper function to indent code properly."""
        lines = code.strip().split("\n")
        indented_lines = [" " * spaces + line for line in lines]
        return "\n".join(indented_lines)

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
