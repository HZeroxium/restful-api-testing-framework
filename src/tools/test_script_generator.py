"""Test script generator orchestrator tool."""

from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
    ValidationScript,
)
from tools.test_script_generator_tools.request_param_script_generator import (
    RequestParamScriptGeneratorTool,
)
from tools.test_script_generator_tools.request_body_script_generator import (
    RequestBodyScriptGeneratorTool,
)
from tools.test_script_generator_tools.response_property_script_generator import (
    ResponsePropertyScriptGeneratorTool,
)
from tools.test_script_generator_tools.request_response_script_generator import (
    RequestResponseScriptGeneratorTool,
)
from common.logger import LoggerFactory, LoggerType, LogLevel


class TestScriptGeneratorTool(BaseTool):
    """
    Orchestrator tool for generating validation scripts for API endpoint tests.

    This tool coordinates specialized script generation tools to create:
    1. Request parameter validation scripts
    2. Request body validation scripts
    3. Response property validation scripts
    4. Request-response correlation validation scripts
    """

    def __init__(
        self,
        *,
        name: str = "test_script_generator",
        description: str = "Orchestrates validation script generation for API endpoint tests",
        config: Optional[Dict] = None,
        verbose: bool = True,
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
            name=f"tool.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

        # Initialize specialized script generation tools
        self.request_param_generator = RequestParamScriptGeneratorTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.request_body_generator = RequestBodyScriptGeneratorTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.response_property_generator = ResponsePropertyScriptGeneratorTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

        self.request_response_generator = RequestResponseScriptGeneratorTool(
            verbose=verbose, cache_enabled=cache_enabled, config=config
        )

    async def _execute(
        self, inp: TestScriptGeneratorInput
    ) -> TestScriptGeneratorOutput:
        """Orchestrate validation script generation using specialized tools."""
        endpoint = inp.endpoint_info
        test_data = inp.test_data
        constraints = inp.constraints or []

        self.logger.info(
            f"Starting test script generation for {endpoint.method.upper()} {endpoint.path}"
        )
        self.logger.add_context(
            endpoint_method=endpoint.method.upper(),
            endpoint_path=endpoint.path,
            input_constraints=len(constraints),
        )

        if self.verbose:
            self.logger.debug("=" * 80)
            self.logger.debug(
                f"TEST SCRIPT GENERATION FOR {endpoint.method.upper()} {endpoint.path}"
            )
            self.logger.debug("=" * 80)
            self.logger.debug(f"Input constraints: {len(constraints)}")

            # Log constraint breakdown
            constraint_types = {}
            for constraint in constraints:
                constraint_type = constraint.type
                constraint_types[constraint_type] = (
                    constraint_types.get(constraint_type, 0) + 1
                )

            for constraint_type, count in constraint_types.items():
                self.logger.debug(f"  - {constraint_type}: {count}")

        # Initialize result container
        all_validation_scripts: List[ValidationScript] = []
        generation_results = {}

        try:
            # 1. Generate request parameter validation scripts
            self.logger.debug(
                "Step 1: Generating request parameter validation scripts..."
            )

            param_output = await self.request_param_generator.execute(inp)
            all_validation_scripts.extend(param_output.validation_scripts)
            generation_results["param_scripts"] = {
                "count": len(param_output.validation_scripts),
                "status": "success",
            }

            self.logger.debug(
                f"Generated {len(param_output.validation_scripts)} parameter scripts"
            )

        except Exception as e:
            self.logger.error(f"Error generating parameter scripts: {str(e)}")
            generation_results["param_scripts"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 2. Generate request body validation scripts
            self.logger.debug("Step 2: Generating request body validation scripts...")

            body_output = await self.request_body_generator.execute(inp)
            all_validation_scripts.extend(body_output.validation_scripts)
            generation_results["body_scripts"] = {
                "count": len(body_output.validation_scripts),
                "status": "success",
            }

            self.logger.debug(
                f"Generated {len(body_output.validation_scripts)} body scripts"
            )

        except Exception as e:
            self.logger.error(f"Error generating body scripts: {str(e)}")
            generation_results["body_scripts"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 3. Generate response property validation scripts
            self.logger.debug(
                "Step 3: Generating response property validation scripts..."
            )

            response_output = await self.response_property_generator.execute(inp)
            all_validation_scripts.extend(response_output.validation_scripts)
            generation_results["response_scripts"] = {
                "count": len(response_output.validation_scripts),
                "status": "success",
            }

            self.logger.debug(
                f"Generated {len(response_output.validation_scripts)} response scripts"
            )

        except Exception as e:
            self.logger.error(f"Error generating response scripts: {str(e)}")
            generation_results["response_scripts"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        try:
            # 4. Generate request-response correlation validation scripts
            self.logger.debug(
                "Step 4: Generating request-response correlation validation scripts..."
            )

            correlation_output = await self.request_response_generator.execute(inp)
            all_validation_scripts.extend(correlation_output.validation_scripts)
            generation_results["correlation_scripts"] = {
                "count": len(correlation_output.validation_scripts),
                "status": "success",
            }

            self.logger.debug(
                f"Generated {len(correlation_output.validation_scripts)} correlation scripts"
            )

        except Exception as e:
            self.logger.error(f"Error generating correlation scripts: {str(e)}")
            generation_results["correlation_scripts"] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

        # If no scripts were generated from any tool, generate basic fallback scripts
        if not all_validation_scripts:
            self.logger.warning(
                "No scripts generated from specialized tools, creating basic fallback scripts"
            )
            all_validation_scripts = self._generate_basic_fallback_scripts(test_data)

        # Log summary results
        total_scripts = len(all_validation_scripts)
        self.logger.info(
            f"Script generation completed: {total_scripts} scripts generated"
        )
        self.logger.add_context(
            total_scripts=total_scripts,
            param_scripts=generation_results.get("param_scripts", {}).get("count", 0),
            body_scripts=generation_results.get("body_scripts", {}).get("count", 0),
            response_scripts=generation_results.get("response_scripts", {}).get(
                "count", 0
            ),
            correlation_scripts=generation_results.get("correlation_scripts", {}).get(
                "count", 0
            ),
        )

        if self.verbose:
            self.logger.debug("=" * 60)
            self.logger.debug("SCRIPT GENERATION COMPLETED")
            self.logger.debug("=" * 60)
            self.logger.debug("Script breakdown:")
            self.logger.debug(
                f"  - Parameter scripts: {generation_results.get('param_scripts', {}).get('count', 0)}"
            )
            self.logger.debug(
                f"  - Body scripts: {generation_results.get('body_scripts', {}).get('count', 0)}"
            )
            self.logger.debug(
                f"  - Response scripts: {generation_results.get('response_scripts', {}).get('count', 0)}"
            )
            self.logger.debug(
                f"  - Correlation scripts: {generation_results.get('correlation_scripts', {}).get('count', 0)}"
            )
            self.logger.debug(f"Total scripts generated: {total_scripts}")
            self.logger.debug("Status: Success")

        return TestScriptGeneratorOutput(validation_scripts=all_validation_scripts)

    def _generate_basic_fallback_scripts(self, test_data) -> List[ValidationScript]:
        """Generate basic validation scripts as fallback when all specialized tools fail."""
        import uuid

        self.logger.debug("Generating basic fallback validation scripts")

        expected_status_code = test_data.expected_status_code

        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic status code validation",
                script_type="response_property",
                validation_code=f"""
def validate_basic_status_code(request, response):
    \"\"\"Basic validation for response status code\"\"\"
    try:
        if isinstance(response, dict):
            return response.get("status_code") == {expected_status_code}
        else:
            return getattr(response, "status_code", None) == {expected_status_code}
    except Exception as e:
        return False
""",
                description=f"Basic validation that status code is {expected_status_code}",
            ),
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic response structure validation",
                script_type="response_property",
                validation_code="""
def validate_basic_response_structure(request, response):
    \"\"\"Basic validation for response structure\"\"\"
    try:
        # Check that response has some basic structure
        if isinstance(response, dict):
            return "status_code" in response
        else:
            return hasattr(response, "status_code")
    except Exception as e:
        return False
""",
                description="Basic validation for response structure",
            ),
        ]

    async def cleanup(self) -> None:
        """Clean up all specialized script generation tools."""
        self.logger.debug("Cleaning up TestScriptGeneratorTool resources")
        await self.request_param_generator.cleanup()
        await self.request_body_generator.cleanup()
        await self.response_property_generator.cleanup()
        await self.request_response_generator.cleanup()
