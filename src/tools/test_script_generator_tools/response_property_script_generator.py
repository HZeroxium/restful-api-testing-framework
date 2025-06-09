"""Response property validation script generator."""

import uuid
from typing import Dict, List, Optional
import json
import math

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
        chunk_threshold: int = 20,
        max_chunk_size: int = 15,
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
        self.chunk_threshold = chunk_threshold
        self.max_chunk_size = max_chunk_size

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

        # Determine if chunking is needed
        if len(response_constraints) <= self.chunk_threshold:
            # Process as single chunk
            return await self._process_single_chunk(
                endpoint, test_data, response_constraints
            )
        else:
            # Process in multiple chunks
            return await self._process_multiple_chunks(
                endpoint, test_data, response_constraints
            )

    async def _process_single_chunk(
        self, endpoint, test_data, response_constraints: List
    ) -> TestScriptGeneratorOutput:
        """Process all constraints as a single chunk."""
        if self.verbose:
            print(
                f"Processing as single chunk ({len(response_constraints)} constraints)"
            )

        try:
            validation_scripts = await self._generate_scripts_for_chunk(
                endpoint, test_data, response_constraints, chunk_index=0, total_chunks=1
            )

            if not validation_scripts:
                validation_scripts = self._generate_basic_response_scripts(test_data)

            if self.verbose:
                print(
                    f"Generated {len(validation_scripts)} response validation scripts"
                )

            return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

        except Exception as e:
            if self.verbose:
                print(f"Error in single chunk processing: {str(e)}")
                import traceback

                traceback.print_exc()

            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_constraint_based_fallback_scripts(
                    response_constraints, test_data
                )
            )

    async def _process_multiple_chunks(
        self, endpoint, test_data, response_constraints: List
    ) -> TestScriptGeneratorOutput:
        """Process constraints in multiple chunks."""
        num_chunks = math.ceil(len(response_constraints) / self.max_chunk_size)

        if self.verbose:
            print(
                f"Processing in {num_chunks} chunks ({len(response_constraints)} constraints, max {self.max_chunk_size} per chunk)"
            )

        all_validation_scripts = []
        chunk_results = []

        for chunk_index in range(num_chunks):
            start_idx = chunk_index * self.max_chunk_size
            end_idx = min(start_idx + self.max_chunk_size, len(response_constraints))
            chunk_constraints = response_constraints[start_idx:end_idx]

            if self.verbose:
                print(
                    f"Processing chunk {chunk_index + 1}/{num_chunks}: constraints {start_idx + 1}-{end_idx} ({len(chunk_constraints)} constraints)"
                )

            try:
                chunk_scripts = await self._generate_scripts_for_chunk(
                    endpoint, test_data, chunk_constraints, chunk_index, num_chunks
                )

                all_validation_scripts.extend(chunk_scripts)
                chunk_results.append(
                    {
                        "chunk_index": chunk_index,
                        "constraints_processed": len(chunk_constraints),
                        "scripts_generated": len(chunk_scripts),
                        "status": "success",
                    }
                )

                if self.verbose:
                    print(
                        f"Chunk {chunk_index + 1} completed: {len(chunk_scripts)} scripts generated"
                    )

            except Exception as e:
                if self.verbose:
                    print(f"Error in chunk {chunk_index + 1}: {str(e)}")

                # Generate fallback scripts for this chunk
                fallback_scripts = self._generate_constraint_based_fallback_scripts(
                    chunk_constraints, test_data
                )
                all_validation_scripts.extend(fallback_scripts)

                chunk_results.append(
                    {
                        "chunk_index": chunk_index,
                        "constraints_processed": len(chunk_constraints),
                        "scripts_generated": len(fallback_scripts),
                        "status": "fallback",
                        "error": str(e),
                    }
                )

        # Ensure we have scripts for all constraints
        if len(all_validation_scripts) < len(response_constraints):
            if self.verbose:
                print(
                    f"⚠️  Generated {len(all_validation_scripts)} scripts but expected {len(response_constraints)}"
                )

            # Fill missing scripts with constraint-specific ones
            while len(all_validation_scripts) < len(response_constraints):
                missing_constraint = response_constraints[len(all_validation_scripts)]
                basic_script = self._generate_constraint_specific_script(
                    missing_constraint, len(all_validation_scripts)
                )
                all_validation_scripts.append(basic_script)

        if not all_validation_scripts:
            all_validation_scripts = self._generate_basic_response_scripts(test_data)

        if self.verbose:
            print(
                f"Multi-chunk processing completed: {len(all_validation_scripts)} total scripts generated"
            )
            for result in chunk_results:
                status_emoji = "✅" if result["status"] == "success" else "⚠️"
                print(
                    f"  {status_emoji} Chunk {result['chunk_index'] + 1}: {result['scripts_generated']} scripts ({result['status']})"
                )

        return TestScriptGeneratorOutput(validation_scripts=all_validation_scripts)

    async def _generate_scripts_for_chunk(
        self,
        endpoint,
        test_data,
        chunk_constraints: List,
        chunk_index: int,
        total_chunks: int,
    ) -> List[ValidationScript]:
        """Generate validation scripts for a specific chunk of constraints."""

        # Define LLM response schema
        class ScriptOutput(BaseModel):
            name: str
            script_type: str
            validation_code: str
            description: str

        class ValidationScriptResult(BaseModel):
            validation_scripts: List[ScriptOutput] = Field(default_factory=list)

        # Prepare data for LLM
        from utils.llm_utils import prepare_endpoint_data_for_llm

        sanitized_endpoint_data = prepare_endpoint_data_for_llm(endpoint.model_dump())

        # Create chunk-specific prompt
        chunk_info = (
            f" (Chunk {chunk_index + 1} of {total_chunks})" if total_chunks > 1 else ""
        )

        formatted_prompt = RESPONSE_PROPERTY_SCRIPT_PROMPT.format(
            endpoint_data=json.dumps(sanitized_endpoint_data, indent=2),
            constraints_data=json.dumps(
                [c.model_dump() for c in chunk_constraints], indent=2
            ),
            test_data=json.dumps(test_data.model_dump(), indent=2),
            constraint_count=len(chunk_constraints),
        )

        # Add chunk-specific instructions if processing multiple chunks
        if total_chunks > 1:
            formatted_prompt += f"""

CHUNK PROCESSING NOTICE{chunk_info}:
- You are processing {len(chunk_constraints)} constraints out of a total larger set
- Focus on generating exactly {len(chunk_constraints)} validation scripts
- Each script should correspond to one constraint in the provided list
- Ensure script names and descriptions are specific to avoid conflicts with other chunks
- Include constraint IDs in script comments for traceability
"""

        # Execute LLM analysis
        raw_json = await create_and_execute_llm_agent(
            app_name=f"response_property_script_generator_chunk_{chunk_index}",
            agent_name=f"response_script_analyzer_chunk_{chunk_index}",
            instruction=formatted_prompt,
            input_data={
                "endpoint": sanitized_endpoint_data,
                "constraints": [c.model_dump() for c in chunk_constraints],
                "test_data": test_data.model_dump(),
                "constraint_count": len(chunk_constraints),
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            },
            output_schema=ValidationScriptResult,
            timeout=self.config.get("timeout", 150.0) if self.config else 150.0,
            max_retries=self.config.get("max_retries", 3) if self.config else 3,
            verbose=self.verbose,
        )

        validation_scripts = []
        if self.verbose:
            print(f"Raw JSON from LLM (chunk {chunk_index + 1}): {raw_json}")

        if raw_json and isinstance(raw_json, dict) and "validation_scripts" in raw_json:
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
                    function_name = f"validate_response_chunk_{chunk_index}_{i}"
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
                if i < len(chunk_constraints):
                    constraint_id = chunk_constraints[i].id

                # Create unique script name to avoid conflicts across chunks
                script_name = script_data.get("name", f"Response validation {i + 1}")
                if total_chunks > 1:
                    script_name = f"{script_name} (Chunk {chunk_index + 1})"

                script = ValidationScript(
                    id=str(uuid.uuid4()),
                    name=script_name,
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
                    f"Warning: Invalid or missing validation_scripts in LLM response for chunk {chunk_index + 1}"
                )

        # Ensure we have the right number of scripts for this chunk
        if len(validation_scripts) != len(chunk_constraints):
            if self.verbose:
                print(
                    f"⚠️  Chunk {chunk_index + 1}: Generated {len(validation_scripts)} scripts but expected {len(chunk_constraints)}"
                )

            # Fill missing scripts with constraint-specific ones
            while len(validation_scripts) < len(chunk_constraints):
                missing_constraint = chunk_constraints[len(validation_scripts)]
                basic_script = self._generate_constraint_specific_script(
                    missing_constraint, len(validation_scripts)
                )
                # Update script name for chunk context
                if total_chunks > 1:
                    basic_script.name = f"{basic_script.name} (Chunk {chunk_index + 1})"
                validation_scripts.append(basic_script)

        return validation_scripts

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
