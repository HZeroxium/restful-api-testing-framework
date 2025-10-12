"""Test script generator orchestrator tool."""

from typing import Dict, Optional, List

from core.base_tool import BaseTool
from schemas.tools.test_script_generator import (
    TestScriptGeneratorInput,
    TestScriptGeneratorOutput,
    ValidationScript,
)
from schemas.tools.constraint_miner import ApiConstraint
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
        constraints = inp.constraints or []

        # Store original constraint IDs and replace with placeholder for LLM
        original_constraint_ids = {}
        for i, constraint in enumerate(constraints):
            original_id = constraint.id
            # Use index as key since we'll iterate in same order
            original_constraint_ids[i] = original_id
            constraint.id = "placeholder_id"

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
            all_validation_scripts = self._generate_basic_fallback_scripts()

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

        # Restore original constraint IDs and assign to validation scripts
        self._restore_constraint_ids_and_assign_to_scripts(
            constraints, original_constraint_ids, all_validation_scripts
        )

        return TestScriptGeneratorOutput(validation_scripts=all_validation_scripts)

    def _restore_constraint_ids_and_assign_to_scripts(
        self,
        constraints: List[ApiConstraint],
        original_constraint_ids: Dict[str, str],
        validation_scripts: List[ValidationScript],
    ) -> None:
        """
        Restore original constraint IDs and assign them to validation scripts.

        Args:
            constraints: List of constraints with placeholder IDs
            original_constraint_ids: Mapping of placeholder to original IDs
            validation_scripts: List of generated validation scripts
        """
        # First, restore the original constraint IDs
        for i, constraint in enumerate(constraints):
            original_id = original_constraint_ids[i]
            constraint.id = original_id
            self.logger.debug(
                f"Restored constraint ID from 'placeholder_id' to '{original_id}'"
            )

        # Create a mapping of constraint types to constraints for easier matching
        constraints_by_type = {}
        for constraint in constraints:
            constraint_type = constraint.type.value.lower()  # Convert enum to string
            if constraint_type not in constraints_by_type:
                constraints_by_type[constraint_type] = []
            constraints_by_type[constraint_type].append(constraint)

        # Assign constraint IDs to validation scripts based on script type
        constraint_usage_count = (
            {}
        )  # Track how many times each constraint has been used

        for script in validation_scripts:
            script_type = script.script_type.lower()

            # Find matching constraints by type
            if script_type in constraints_by_type:
                available_constraints = constraints_by_type[script_type]

                # Use the first available constraint of this type
                # If multiple scripts of same type, use constraints in order
                constraint_index = constraint_usage_count.get(script_type, 0)

                if constraint_index < len(available_constraints):
                    selected_constraint = available_constraints[constraint_index]
                    script.constraint_id = selected_constraint.id
                    constraint_usage_count[script_type] = constraint_index + 1
                    self.logger.debug(
                        f"Assigned script '{script.name}' (type: {script_type}) to constraint '{selected_constraint.id}'"
                    )
                else:
                    # If we run out of constraints of this type, use the last one
                    selected_constraint = available_constraints[-1]
                    script.constraint_id = selected_constraint.id
            else:
                # If no matching constraint type, try to find a fallback
                # Look for request_response type or use the first available constraint
                if "request_response" in constraints_by_type:
                    script.constraint_id = constraints_by_type["request_response"][0].id
                elif constraints:
                    script.constraint_id = constraints[0].id
                else:
                    script.constraint_id = None

        # NEW: Normalize all validation scripts before returning
        from utils.code_script_utils import normalize_validation_script

        for script in validation_scripts:
            original_code = script.validation_code
            script.validation_code = normalize_validation_script(original_code)
            if original_code != script.validation_code:
                self.logger.debug(f"Normalized validation script: {script.name}")

        self.logger.debug(
            f"Restored constraint IDs and assigned to {len(validation_scripts)} validation scripts"
        )
        self.logger.debug(f"Constraint usage count: {constraint_usage_count}")

    def _generate_basic_fallback_scripts(self) -> List[ValidationScript]:
        """Generate basic validation scripts as fallback when all specialized tools fail."""
        import uuid

        self.logger.debug("Generating basic fallback validation scripts")

        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic status code validation",
                script_type="response_property",
                validation_code="""
def validate_basic_status_code(request, response):
    \"\"\"Basic validation for response status code\"\"\"
    try:
        if isinstance(response, dict):
            status_code = response.get("status_code")
            return status_code is not None and 200 <= status_code < 300
        else:
            status_code = getattr(response, "status_code", None)
            return status_code is not None and 200 <= status_code < 300
    except Exception as e:
        return False
""",
                description="Basic validation that status code is successful (2xx)",
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
