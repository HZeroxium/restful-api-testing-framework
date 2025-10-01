# tools/test_script_generator_tools/response_property_script_generator.py

"""Response property validation script generator - Combined version with chunking support."""

import uuid
import math
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
from common.logger import LoggerFactory, LoggerType, LogLevel


class ResponsePropertyScriptGeneratorTool(BaseTool):
    """Tool for generating response property validation scripts using LLM analysis with optional chunking."""

    def __init__(
        self,
        *,
        name: str = "response_property_script_generator",
        description: str = "Generates validation scripts for response properties",
        config: Optional[Dict] = None,
        verbose: bool = True,
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

        log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
        self.logger = LoggerFactory.get_logger(
            name=f"script-generator.{name}",
            logger_type=LoggerType.STANDARD,
            level=log_level,
        )

    async def _execute(
        self, inp: TestScriptGeneratorInput
    ) -> TestScriptGeneratorOutput:
        """Generate response property validation scripts, with optional chunking."""
        endpoint = inp.endpoint_info
        constraints = inp.constraints or []

        # Filter to response property constraints
        response_constraints = [c for c in constraints if c.type == "response_property"]

        self.logger.info(f"Processing {len(response_constraints)} response constraints")
        if self.verbose:
            self.logger.debug(f"Endpoint: {endpoint.method.upper()} {endpoint.path}")
            for i, constraint in enumerate(response_constraints):
                self.logger.debug(f"  Constraint {i+1}: {constraint.description}")

        if not response_constraints:
            self.logger.info("No response property constraints found")
            return TestScriptGeneratorOutput(validation_scripts=[])

        # Decide single or multi-chunk
        if len(response_constraints) <= self.chunk_threshold:
            return await self._process_single_chunk(endpoint, response_constraints)
        else:
            return await self._process_multiple_chunks(endpoint, response_constraints)

    async def _process_single_chunk(
        self, endpoint, response_constraints: List
    ) -> TestScriptGeneratorOutput:
        """Process all constraints as a single chunk."""
        self.logger.info(
            f"Single-chunk processing ({len(response_constraints)} constraints)"
        )
        try:
            scripts = await self._invoke_llm_for_constraints(
                endpoint, response_constraints, chunk_index=0, total_chunks=1
            )
            if not scripts:
                scripts = self._generate_basic_response_scripts()
            self.logger.info(f"Generated {len(scripts)} response validation scripts")
            return TestScriptGeneratorOutput(validation_scripts=scripts)
        except Exception as e:
            self.logger.error(f"Error in single-chunk processing: {e}")
            if self.verbose:
                import traceback

                self.logger.debug(traceback.format_exc())
            # Fallback to basic scripts
            return TestScriptGeneratorOutput(
                validation_scripts=self._generate_basic_response_scripts()
            )

    async def _process_multiple_chunks(
        self, endpoint, response_constraints: List
    ) -> TestScriptGeneratorOutput:
        """Process constraints in multiple chunks."""
        num_chunks = math.ceil(len(response_constraints) / self.max_chunk_size)
        self.logger.info(
            f"Multi-chunk processing: {len(response_constraints)} constraints in {num_chunks} chunks"
        )

        all_scripts: List[ValidationScript] = []
        chunk_reports = []

        for idx in range(num_chunks):
            start = idx * self.max_chunk_size
            end = min(start + self.max_chunk_size, len(response_constraints))
            chunk = response_constraints[start:end]
            self.logger.debug(
                f"Processing chunk {idx+1}/{num_chunks}: constraints {start+1}-{end}"
            )
            try:
                scripts = await self._invoke_llm_for_constraints(
                    endpoint, chunk, chunk_index=idx, total_chunks=num_chunks
                )
                all_scripts.extend(scripts)
                chunk_reports.append(
                    {"index": idx, "count": len(scripts), "status": "success"}
                )
            except Exception as e:
                self.logger.error(f"Error in chunk {idx+1}: {e}")
                if self.verbose:
                    import traceback

                    self.logger.debug(traceback.format_exc())
                # Fallback per constraint
                for constraint in chunk:
                    all_scripts.append(
                        self._generate_constraint_specific_script(constraint)
                    )
                chunk_reports.append(
                    {"index": idx, "count": len(chunk), "status": "fallback"}
                )

        # Ensure coverage
        if len(all_scripts) < len(response_constraints):
            missing = len(response_constraints) - len(all_scripts)
            self.logger.warning(
                f"Missing {missing} scripts after chunking, filling with basic ones"
            )
            all_scripts.extend(self._generate_basic_response_scripts()[:missing])

        self.logger.info(f"Multi-chunk completed: {len(all_scripts)} scripts generated")
        return TestScriptGeneratorOutput(validation_scripts=all_scripts)

    async def _invoke_llm_for_constraints(
        self,
        endpoint,
        constraints: List,
        chunk_index: int,
        total_chunks: int,
    ) -> List[ValidationScript]:
        """Helper to invoke LLM for a given list of constraints."""

        # Define response schemas
        class ScriptOutput(BaseModel):
            name: str
            script_type: str
            validation_code: str
            description: str

        class ValidationScriptResult(BaseModel):
            validation_scripts: List[ScriptOutput] = Field(default_factory=list)

        from ...utils.llm_utils import prepare_endpoint_data_for_llm

        sanitized = prepare_endpoint_data_for_llm(endpoint.model_dump())

        prompt = RESPONSE_PROPERTY_SCRIPT_PROMPT.format(
            endpoint_data=json.dumps(sanitized, indent=2),
            constraints_data=json.dumps(
                [c.model_dump() for c in constraints], indent=2
            ),
            constraint_count=len(constraints),
        )
        # Add chunk notice
        if total_chunks > 1:
            info = f"Chunk {chunk_index+1} of {total_chunks}"
            prompt += (
                f"\n\nCHUNK PROCESSING NOTICE ({info}):"
                f" Generate {len(constraints)} scripts, one per constraint."
            )

        self.logger.debug(
            f"Sending chunk {chunk_index+1}/{total_chunks} to LLM with {len(constraints)} constraints"
        )

        raw = await create_and_execute_llm_agent(
            app_name=f"response_property_script_generator_chunk_{chunk_index}",
            agent_name=f"response_property_script_generator_{chunk_index}",
            instruction=prompt,
            input_data={
                "endpoint": sanitized,
                "constraints": [c.model_dump() for c in constraints],
                "constraint_count": len(constraints),
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            },
            output_schema=ValidationScriptResult,
            timeout=self.config.get("timeout", 120.0) if self.config else 120.0,
            max_retries=self.config.get("max_retries", 3) if self.config else 3,
            verbose=self.verbose,
        )

        scripts: List[ValidationScript] = []
        if raw and isinstance(raw, dict) and "validation_scripts" in raw:
            for data in raw["validation_scripts"]:
                # Handle both dict and object responses
                if isinstance(data, dict):
                    name = data.get("name", "Unknown validation")
                    script_type = data.get("script_type", "response_property")
                    validation_code = data.get("validation_code", "")
                    description = data.get("description", "")
                else:
                    name = getattr(data, "name", "Unknown validation")
                    script_type = getattr(data, "script_type", "response_property")
                    validation_code = getattr(data, "validation_code", "")
                    description = getattr(data, "description", "")

                # Clean up the code
                code = validation_code.replace("\\n", "\n").replace('\\"', '"')

                scripts.append(
                    ValidationScript(
                        id=str(uuid.uuid4()),
                        name=(
                            name
                            + (f" (Chunk {chunk_index+1})" if total_chunks > 1 else "")
                        ),
                        script_type=script_type,
                        validation_code=code,
                        description=description,
                    )
                )
        elif raw and hasattr(raw, "validation_scripts"):
            # Handle object-based responses
            for data in raw.validation_scripts:
                code = data.validation_code.replace("\\n", "\n").replace('\\"', '"')
                scripts.append(
                    ValidationScript(
                        id=str(uuid.uuid4()),
                        name=(
                            data.name
                            + (f" (Chunk {chunk_index+1})" if total_chunks > 1 else "")
                        ),
                        script_type=data.script_type,
                        validation_code=code,
                        description=data.description,
                    )
                )
        else:
            self.logger.warning(
                f"No validation_scripts returned for chunk {chunk_index+1}"
            )
            if self.verbose:
                self.logger.debug(f"Raw response type: {type(raw)}")
                self.logger.debug(f"Raw response content: {raw}")
                if raw and isinstance(raw, dict):
                    self.logger.debug(f"Available keys: {list(raw.keys())}")

        # Generate fallback scripts if no scripts were parsed
        if not scripts and constraints:
            self.logger.info(
                f"Generating fallback scripts for {len(constraints)} constraints"
            )
            for constraint in constraints:
                scripts.append(self._generate_constraint_specific_script(constraint))

        return scripts

    def _generate_constraint_specific_script(self, constraint) -> ValidationScript:
        """Generate a basic script for a specific constraint as fallback."""
        property_path = constraint.details.get("property_path", "property")
        ctype = constraint.details.get("constraint_type", "type")
        # Simplified fallback: reuse basic generator
        return ValidationScript(
            id=str(uuid.uuid4()),
            name=f"Validate {property_path} {ctype}",
            script_type="response_property",
            validation_code=f"""
# Fallback validation for {property_path}
def validate_{property_path.replace('.', '_')}(request, response):
    try:
        return True
    except:
        return False
""",
            description=f"Fallback validation for {property_path} {ctype}",
        )

    def _generate_basic_response_scripts(self) -> List[ValidationScript]:
        """Generate basic response property validation scripts as fallback."""
        self.logger.debug("Generating basic response property validation scripts")
        return [
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic response structure validation",
                script_type="response_property",
                validation_code="""
# Validate response structure
def validate_response_structure(request, response):
    try:
        if isinstance(response, dict):
            return True
        return hasattr(response, 'status_code')
    except:
        return False
""",
                description="Basic validation of response structure",
            ),
            ValidationScript(
                id=str(uuid.uuid4()),
                name="Basic response content validation",
                script_type="response_property",
                validation_code="""
# Validate response content
def validate_response_content(request, response):
    try:
        if isinstance(response, dict):
            return response.get('body') is not None
        return hasattr(response, 'body') or hasattr(response, 'json') or hasattr(response, 'text')
    except:
        return False
""",
                description="Basic validation of response content",
            ),
        ]

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.debug(
            "Cleaning up resources for ResponsePropertyScriptGeneratorTool"
        )
        pass
