# tools/test_script_generator.py

import uuid
from typing import Dict, Optional

from core.base_tool import BaseTool
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
    ValidationScript,
)


class TestScriptGeneratorTool(BaseTool):
    """
    Tool for generating validation scripts for API endpoint tests.
    Currently returns mock scripts for demonstration purposes.
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
        """Generate validation scripts for the given test case."""
        endpoint = inp.endpoint_info
        test_case = inp.test_case
        validation_scripts = []

        # Mock implementation - just create basic scripts
        # In a real implementation, we'd analyze the expected behavior and generate appropriate validation scripts

        # Status code validation
        validation_scripts.append(
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Status code validation",
                script_type="status_code",
                validation_code=f"assert response.status_code == {test_case.expected_status_code}",
                description=f"Validate that status code is {test_case.expected_status_code}",
            )
        )

        # Response format validation (if success expected)
        if test_case.expected_status_code < 400:
            validation_scripts.append(
                ValidationScript(
                    id=str(uuid.uuid4()),
                    name="Response format validation",
                    script_type="response_format",
                    validation_code="assert isinstance(response.body, dict) or isinstance(response.body, list)",
                    description="Validate that response body is a valid JSON object or array",
                )
            )

        # Headers validation
        validation_scripts.append(
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Content-Type header validation",
                script_type="response_headers",
                validation_code="assert 'content-type' in response.headers",
                description="Validate that response has Content-Type header",
            )
        )

        return TestScriptGeneratorOutput(validation_scripts=validation_scripts)

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
