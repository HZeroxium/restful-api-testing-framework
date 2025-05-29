# tools/test_script_generator.py

import uuid
from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
    ValidationScript,
)
from schemas.tools.constraint_miner import ApiConstraint
from config.settings import settings
from config.constants import LLM_INSTRUCTIONS


class TestScriptGeneratorTool(BaseTool):
    """
    Tool for generating validation scripts for API endpoint tests.
    Uses LLM to generate detailed validation scripts based on constraints.
    """

    def __init__(
        self,
        *,
        name: str = "test_script_generator",
        description: str = "Generates validation scripts for API endpoint tests",
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
        """Generate validation scripts for the given test data and constraints."""
        endpoint = inp.endpoint_info
        test_data = inp.test_data
        constraints = inp.constraints or []

        if self.verbose:
            print(
                f"Generating validation scripts for {endpoint.method} {endpoint.path}"
            )
            print(f"Using {len(constraints)} constraints")

        # Always generate basic validation scripts
        validation_scripts = self._generate_basic_scripts(test_data)

        # If we have constraints, use LLM to generate advanced validation scripts
        if constraints:
            try:
                constraint_scripts = await self._generate_constraint_based_scripts(
                    endpoint, test_data, constraints
                )
                validation_scripts.extend(constraint_scripts)
            except Exception as e:
                if self.verbose:
                    print(f"Error generating constraint-based scripts: {str(e)}")
                # Continue with basic scripts if constraint-based generation fails

        return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

    def _generate_basic_scripts(self, test_data) -> List[ValidationScript]:
        """Generate basic validation scripts that don't require LLM."""
        validation_scripts = []
        expected_status_code = test_data.expected_status_code

        # Status code validation
        validation_scripts.append(
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Status code validation",
                script_type="status_code",
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
            )
        )

        # Response format validation (if success expected)
        if expected_status_code < 400:
            validation_scripts.append(
                ValidationScript(
                    id=str(uuid.uuid4()),
                    name="Response format validation",
                    script_type="response_format",
                    validation_code="""
def validate_response_format(request, response):
    \"\"\"Validate that response body is a valid JSON object or array\"\"\"
    try:
        # Handle both dictionary and object access
        body = None
        if isinstance(response, dict):
            body = response.get("body")
        else:
            body = getattr(response, "body", None)
        
        return isinstance(body, dict) or isinstance(body, list)
    except Exception as e:
        return False
""",
                    description="Validate that response body is a valid JSON object or array",
                )
            )

        # Headers validation
        validation_scripts.append(
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Content-Type header validation",
                script_type="response_headers",
                validation_code="""
def validate_content_type(request, response):
    \"\"\"Validate that response has Content-Type header\"\"\"
    try:
        # Handle both dictionary and object access
        headers = None
        if isinstance(response, dict):
            headers = response.get("headers", {})
        else:
            headers = getattr(response, "headers", {})
            
        # Check for content-type in a case-insensitive way
        return any(k.lower() == 'content-type' for k in headers.keys())
    except Exception as e:
        return False
""",
                description="Validate that response has Content-Type header",
            )
        )

        return validation_scripts

    async def _generate_constraint_based_scripts(
        self, endpoint, test_data, constraints: List[ApiConstraint]
    ) -> List[ValidationScript]:
        """Generate validation scripts based on the provided constraints using LLM."""
        # Initialize LLM components - similar to StaticConstraintMinerTool
        import json
        import uuid
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.memory import InMemoryMemoryService
        from google.genai import types
        from pydantic import BaseModel, Field
        from typing import List, Dict, Any

        # Define a schema for LLM input
        class LlmScriptGeneratorInput(BaseModel):
            endpoint: Dict[str, Any] = Field(
                ..., description="API endpoint information"
            )
            test_data: Dict[str, Any] = Field(
                ..., description="Test data for validation"
            )
            constraints: List[Dict[str, Any]] = Field(
                ..., description="Constraints to validate against"
            )

        # Define a schema for LLM output - using a simplified version for the LLM
        # but will map to our full ValidationScript schema
        class LlmValidationScriptOutput(BaseModel):
            name: str
            script_type: str
            validation_code: str
            description: str

        class ValidationScriptOutput(BaseModel):
            validation_scripts: List[LlmValidationScriptOutput]

        # Set up session services
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        memory_service = InMemoryMemoryService()

        # Create a unique session ID
        session_id = str(uuid.uuid4())
        user_id = "system"

        # Initialize session
        session_service.create_session(
            app_name="validation_script_generator",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

        # Prepare input data for LLM
        llm_input = LlmScriptGeneratorInput(
            endpoint={
                "method": endpoint.method,
                "path": endpoint.path,
                "description": endpoint.description,
            },
            test_data=test_data.model_dump(),
            constraints=[c.model_dump() for c in constraints],
        )

        # Create the LLM agent
        script_generator_agent = LlmAgent(
            name="llm_script_generator",
            model=settings.llm.LLM_MODEL,
            instruction=LLM_INSTRUCTIONS["test_script_generator"],
            input_schema=LlmScriptGeneratorInput,
            output_schema=ValidationScriptOutput,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        # Create a runner
        runner = Runner(
            app_name="validation_script_generator",
            agent=script_generator_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            memory_service=memory_service,
        )

        # Prepare input for the LLM
        user_input = types.Content(
            role="user", parts=[types.Part(text=llm_input.model_dump_json())]
        )

        # Run the agent
        raw_json = None
        try:
            if self.verbose:
                print(f"Running LLM to generate validation scripts")

            for event in runner.run(
                session_id=session_id,
                user_id=user_id,
                new_message=user_input,
            ):
                if event.content:
                    text = "".join(part.text for part in event.content.parts)
                    try:
                        raw_json = json.loads(text)
                        break  # We got valid JSON, exit the loop
                    except json.JSONDecodeError:
                        if self.verbose:
                            print(
                                "Failed to decode JSON from agent response. Continuing..."
                            )
                        continue

            if raw_json is None:
                if self.verbose:
                    print("No valid response received from the agent.")
                return []

        except Exception as e:
            if self.verbose:
                print(f"Error during LLM processing: {str(e)}")
            return []

        # Convert LLM output to ValidationScript objects
        validation_scripts = []

        if "validation_scripts" in raw_json:
            for i, script_data in enumerate(raw_json["validation_scripts"]):
                # Map constraints to scripts
                constraint_id = constraints[i].id if i < len(constraints) else None

                # Check if the validation code contains a proper function definition
                validation_code = script_data["validation_code"]
                if not validation_code.strip().startswith("def "):
                    # Wrap the code in a function if not already wrapped
                    function_name = f"validate_{i}"
                    validation_code = f"""
def {function_name}(request, response):
    \"\"\"Auto-wrapped validation function\"\"\"
    try:
{self._indent_code(validation_code, 8)}
    except Exception as e:
        return False
"""

                script = ValidationScript(
                    id=str(uuid.uuid4()),
                    name=script_data["name"],
                    script_type=script_data["script_type"],
                    validation_code=validation_code,
                    description=script_data["description"],
                    constraint_id=constraint_id,
                )
                validation_scripts.append(script)

        return validation_scripts

    def _indent_code(self, code: str, spaces: int) -> str:
        """Helper function to indent code properly."""
        lines = code.strip().split("\n")
        indented_lines = [" " * spaces + line for line in lines]
        return "\n".join(indented_lines)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
