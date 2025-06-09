"""Response property validation script generator."""

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
from config.prompts.test_script_generator import RESPONSE_PROPERTY_SCRIPT_PROMPT
from pydantic import BaseModel, Field


class ResponsePropertyScriptGeneratorTool(BaseTool):
    """Tool for generating response property validation scripts using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "response_property_script_generator",
        description: str = "Generates validation scripts for response properties",
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
        """Generate response property validation scripts."""
        endpoint = inp.endpoint_info
        test_data = inp.test_data
        constraints = inp.constraints or []

        # Filter constraints to only response property constraints
        response_constraints = [c for c in constraints if c.type == "response_property"]

        if self.verbose:
            print(
                f"ResponsePropertyScriptGenerator: Processing {len(response_constraints)} response constraints"
            )

        if not response_constraints:
            if self.verbose:
                print(
                    "No response property constraints found, generating basic scripts"
                )
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_basic_response_scripts(test_data)
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

            formatted_prompt = RESPONSE_PROPERTY_SCRIPT_PROMPT.format(
                endpoint_data=json.dumps(sanitized_endpoint_data, indent=2),
                constraints_data=json.dumps(
                    [c.model_dump() for c in response_constraints], indent=2
                ),
                test_data=json.dumps(test_data.model_dump(), indent=2),
                constraint_count=len(response_constraints),
            )

            # Execute LLM analysis
            raw_json = await create_and_execute_llm_agent(
                app_name="response_property_script_generator",
                agent_name="response_script_analyzer",
                instruction=formatted_prompt,
                input_data={
                    "endpoint": sanitized_endpoint_data,
                    "constraints": [c.model_dump() for c in response_constraints],
                    "test_data": test_data.model_dump(),
                    "constraint_count": len(response_constraints),
                },
                output_schema=ValidationScriptResult,
                timeout=self.config.get("timeout", 150.0) if self.config else 150.0,
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
                        function_name = f"validate_response_{i}"
                        validation_code = f"""
def {function_name}(request, response):
    \"\"\"Auto-wrapped response validation function\"\"\"
    try:
{self._indent_code(validation_code, 8)}
    except Exception as e:
        return False
"""

                    # Map to corresponding constraint
                    constraint_id = None
                    if i < len(response_constraints):
                        constraint_id = response_constraints[i].id

                    script = ValidationScript(
                        id=str(uuid.uuid4()),
                        name=script_data.get("name", f"Response validation {i + 1}"),
                        script_type="response_property",
                        validation_code=validation_code,
                        description=script_data.get(
                            "description", "Response property validation"
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
            if len(validation_scripts) != len(response_constraints):
                if self.verbose:
                    print(
                        f"⚠️  Generated {len(validation_scripts)} scripts but expected {len(response_constraints)}"
                    )

                # Fill missing scripts with constraint-specific ones
                while len(validation_scripts) < len(response_constraints):
                    missing_constraint = response_constraints[len(validation_scripts)]
                    basic_script = self._generate_constraint_specific_script(
                        missing_constraint, len(validation_scripts)
                    )
                    validation_scripts.append(basic_script)

            if not validation_scripts:
                validation_scripts = self._generate_basic_response_scripts(test_data)

            if self.verbose:
                print(
                    f"Generated {len(validation_scripts)} response validation scripts"
                )

            return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

        except Exception as e:
            if self.verbose:
                print(f"Error generating response scripts: {str(e)}")
                import traceback

                traceback.print_exc()
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_constraint_based_fallback_scripts(
                    response_constraints, test_data
                )
            )

    def _generate_constraint_specific_script(
        self, constraint, index: int
    ) -> ValidationScript:
        """Generate a basic script for a specific constraint."""
        property_path = constraint.details.get("property_path", f"property_{index}")
        constraint_type = constraint.details.get("constraint_type", "type")
        data_type = constraint.details.get("data_type", "string").lower()

        # Map data types to Python types
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "(int, float)",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }

        python_type = type_mapping.get(data_type, "str")

        # Handle nested property paths
        if "." in property_path:
            path_parts = property_path.split(".")
            access_code = "body"
            for part in path_parts:
                if "[*]" in part:
                    array_prop = part.replace("[*]", "")
                    access_code = f"item.get('{array_prop}') if isinstance({access_code}, list) and {access_code} else None"
                else:
                    access_code = f"{access_code}.get('{part}') if isinstance({access_code}, dict) else None"
        else:
            access_code = (
                f"body.get('{property_path}') if isinstance(body, dict) else None"
            )

        validation_code = f"""
def validate_{property_path.replace('.', '_').replace('[*]', '_array')}_{constraint_type}(request, response):
    \"\"\"Validate {property_path} property {constraint_type} constraint - Reference: {constraint.id}\"\"\"
    try:
        body = response.get('body') if isinstance(response, dict) else getattr(response, 'body', {{}})
        value = {access_code}
        if value is not None:
            return isinstance(value, {python_type})
        return True  # Property may not exist in all responses
    except Exception as e:
        return False
"""

        return ValidationScript(
            id=str(uuid.uuid4()),
            name=f"Validate {property_path} {constraint_type}",
            script_type="response_property",
            validation_code=validation_code,
            description=f"Validates {property_path} property {constraint_type} constraint",
            constraint_id=constraint.id,
        )

    def _generate_constraint_based_fallback_scripts(
        self, constraints, test_data
    ) -> List[ValidationScript]:
        """Generate fallback scripts based on actual constraints."""
        scripts = []
        for i, constraint in enumerate(constraints):
            script = self._generate_constraint_specific_script(constraint, i)
            scripts.append(script)

        if not scripts:
            scripts = self._generate_basic_response_scripts(test_data)

        return scripts

    def _generate_basic_response_scripts(self, test_data) -> List[ValidationScript]:
        """Generate basic response validation scripts as fallback."""
        expected_status_code = test_data.expected_status_code

        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Status code validation",
                script_type="response_property",
                validation_code=f"""
def validate_status_code(request, response):
    \"\"\"Validate that status code matches the expected value\"\"\"
    try:
        # Handle both dictionary and object access
        if isinstance(response, dict):
            return response.get("status_code") == {expected_status_code}
        else:
            return getattr(response, "status_code", None) == {expected_status_code}
    except Exception as e:
        return False
""",
                description=f"Validate that status code is {expected_status_code}",
            ),
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Response format validation",
                script_type="response_property",
                validation_code="""
def validate_response_format(request, response):
    \"\"\"Validate that response body is valid JSON\"\"\"
    try:
        # Handle both dictionary and object access
        body = None
        if isinstance(response, dict):
            body = response.get("body")
        else:
            body = getattr(response, "body", None)
        
        return isinstance(body, dict) or isinstance(body, list) or body is None
    except Exception as e:
        return False
""",
                description="Validate that response body is valid JSON",
            ),
        ]

    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper function to indent code properly."""
        lines = code.strip().split("\n")
        indented_lines = [" " * spaces + line for line in lines]
        return "\n".join(indented_lines)

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
