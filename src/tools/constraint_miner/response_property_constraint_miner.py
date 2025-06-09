# tools/constraint_miner/response_property_constraint_miner.py

"""Response property constraint mining tool."""
import uuid
import json
from typing import Dict, List, Optional, Tuple
import math

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    ResponsePropertyConstraintMinerInput,
    ResponsePropertyConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from utils.llm_utils import create_and_execute_llm_agent
from config.prompts.constraint_miner import RESPONSE_PROPERTY_CONSTRAINT_PROMPT
from pydantic import BaseModel, Field


class ResponsePropertyConstraintMinerTool(BaseTool):
    """Tool for mining response property constraints using LLM analysis."""

    def __init__(
        self,
        *,
        name: str = "response_property_constraint_miner",
        description: str = "Mines constraints from API response properties",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
        chunk_threshold: int = 20,
        max_chunk_size: int = 15,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=ResponsePropertyConstraintMinerInput,
            output_schema=ResponsePropertyConstraintMinerOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )
        self.chunk_threshold = chunk_threshold
        self.max_chunk_size = max_chunk_size

    async def _execute(
        self, inp: ResponsePropertyConstraintMinerInput
    ) -> ResponsePropertyConstraintMinerOutput:
        """Mine response property constraints from endpoint information."""
        endpoint = inp.endpoint_info

        if self.verbose:
            print(
                f"ResponsePropertyConstraintMiner: Analyzing {endpoint.method.upper()} {endpoint.path}"
            )

        try:
            # Estimate complexity and determine if chunking is needed
            complexity_estimate = self._estimate_response_complexity(endpoint)

            if self.verbose:
                print(f"Estimated complexity: {complexity_estimate} properties")

            if complexity_estimate <= self.chunk_threshold:
                # Process as single chunk
                return await self._process_single_chunk(endpoint, complexity_estimate)
            else:
                # Process in multiple chunks
                return await self._process_multiple_chunks(
                    endpoint, complexity_estimate
                )

        except Exception as e:
            if self.verbose:
                print(f"Error in response property constraint mining: {str(e)}")
            return self._generate_fallback_constraints(endpoint)

    def _estimate_response_complexity(self, endpoint) -> int:
        """Estimate the number of properties that will be analyzed."""
        complexity = 0

        # Count response schemas and their properties
        if hasattr(endpoint, "responses") and endpoint.responses:
            for status_code, response_info in endpoint.responses.items():
                if hasattr(response_info, "content") and response_info.content:
                    for content_type, content_info in response_info.content.items():
                        if hasattr(content_info, "schema") and content_info.schema:
                            complexity += self._count_schema_properties(
                                content_info.schema
                            )

                # Add header constraints
                if hasattr(response_info, "headers") and response_info.headers:
                    complexity += len(response_info.headers)

        # Add basic response constraints (status codes, content-type, etc.)
        complexity += 3  # Basic response structure constraints

        return max(complexity, 5)  # Minimum estimate

    def _count_schema_properties(self, schema) -> int:
        """Recursively count properties in a schema."""
        count = 0

        if hasattr(schema, "properties") and schema.properties:
            count += len(schema.properties)

            # Count nested properties
            for prop_name, prop_schema in schema.properties.items():
                if hasattr(prop_schema, "properties"):
                    count += self._count_schema_properties(prop_schema)
                elif hasattr(prop_schema, "items") and hasattr(
                    prop_schema.items, "properties"
                ):
                    count += self._count_schema_properties(prop_schema.items)

        return count

    async def _process_single_chunk(
        self, endpoint, complexity_estimate: int
    ) -> ResponsePropertyConstraintMinerOutput:
        """Process the entire endpoint as a single chunk."""
        if self.verbose:
            print(f"Processing as single chunk (complexity: {complexity_estimate})")

        constraints = await self._mine_constraints_for_chunk(
            endpoint, chunk_index=0, total_chunks=1, focus_areas=["all"]
        )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "llm",
            "status": "success",
            "processing_method": "single_chunk",
            "complexity_estimate": complexity_estimate,
        }

        return ResponsePropertyConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            response_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def _process_multiple_chunks(
        self, endpoint, complexity_estimate: int
    ) -> ResponsePropertyConstraintMinerOutput:
        """Process the endpoint in multiple chunks."""
        num_chunks = math.ceil(complexity_estimate / self.max_chunk_size)

        if self.verbose:
            print(
                f"Processing in {num_chunks} chunks (complexity: {complexity_estimate})"
            )

        all_constraints = []
        chunk_results = []

        # Define focus areas for different chunks
        focus_areas = self._generate_focus_areas(endpoint, num_chunks)

        for chunk_index in range(num_chunks):
            if self.verbose:
                print(
                    f"Processing chunk {chunk_index + 1}/{num_chunks}: {focus_areas[chunk_index]}"
                )

            try:
                chunk_constraints = await self._mine_constraints_for_chunk(
                    endpoint,
                    chunk_index=chunk_index,
                    total_chunks=num_chunks,
                    focus_areas=focus_areas[chunk_index],
                )

                all_constraints.extend(chunk_constraints)
                chunk_results.append(
                    {
                        "chunk_index": chunk_index,
                        "focus_areas": focus_areas[chunk_index],
                        "constraints_found": len(chunk_constraints),
                        "status": "success",
                    }
                )

                if self.verbose:
                    print(
                        f"Chunk {chunk_index + 1} completed: {len(chunk_constraints)} constraints"
                    )

            except Exception as e:
                if self.verbose:
                    print(f"Error in chunk {chunk_index + 1}: {str(e)}")

                chunk_results.append(
                    {
                        "chunk_index": chunk_index,
                        "focus_areas": focus_areas[chunk_index],
                        "constraints_found": 0,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        # Deduplicate constraints
        all_constraints = self._deduplicate_constraints(all_constraints)

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(all_constraints),
            "source": "llm",
            "status": "success",
            "processing_method": "multi_chunk",
            "complexity_estimate": complexity_estimate,
            "chunks_processed": num_chunks,
            "chunk_results": chunk_results,
        }

        return ResponsePropertyConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            response_constraints=all_constraints,
            total_constraints=len(all_constraints),
            result=result_summary,
        )

    def _generate_focus_areas(self, endpoint, num_chunks: int) -> List[List[str]]:
        """Generate focus areas for each chunk based on endpoint analysis."""
        focus_areas = []

        # Define potential focus areas
        all_areas = [
            "response_structure",
            "data_types",
            "headers",
            "status_codes",
            "nested_objects",
            "arrays",
            "validation_rules",
            "format_constraints",
        ]

        # Distribute areas across chunks
        areas_per_chunk = max(1, len(all_areas) // num_chunks)

        for i in range(num_chunks):
            start_idx = i * areas_per_chunk
            end_idx = start_idx + areas_per_chunk

            if i == num_chunks - 1:  # Last chunk gets remaining areas
                chunk_areas = all_areas[start_idx:]
            else:
                chunk_areas = all_areas[start_idx:end_idx]

            focus_areas.append(chunk_areas)

        return focus_areas

    async def _mine_constraints_for_chunk(
        self, endpoint, chunk_index: int, total_chunks: int, focus_areas: List[str]
    ) -> List[ApiConstraint]:
        """Mine constraints for a specific chunk with focused analysis."""

        # Define simplified LLM response schema
        class ResponsePropertyConstraint(BaseModel):
            property_path: str = Field(..., description="Path to property in response")
            description: str = Field(..., description="Constraint description")
            constraint_type: str = Field(..., description="Type of constraint")
            severity: str = Field(default="info", description="Severity level")
            validation_rule: str = Field(..., description="Validation rule identifier")
            applies_to_status: List[int] = Field(
                default_factory=list, description="Status codes"
            )
            data_type: Optional[str] = Field(None, description="Data type")
            format: Optional[str] = Field(None, description="Format specification")

        class ResponsePropertyConstraintResult(BaseModel):
            constraints: List[ResponsePropertyConstraint] = Field(default_factory=list)

        # Prepare endpoint data
        from utils.llm_utils import prepare_endpoint_data_for_llm

        sanitized_endpoint_data = prepare_endpoint_data_for_llm(endpoint.model_dump())

        # Create focused prompt
        focused_prompt = self._create_focused_prompt(
            sanitized_endpoint_data, focus_areas, chunk_index, total_chunks
        )

        # Execute LLM analysis
        raw_json = await create_and_execute_llm_agent(
            app_name=f"response_property_miner_chunk_{chunk_index}",
            agent_name=f"response_constraint_analyzer_chunk_{chunk_index}",
            instruction=focused_prompt,
            input_data=sanitized_endpoint_data,
            input_schema=type(endpoint),
            output_schema=ResponsePropertyConstraintResult,
            timeout=self.config.get("timeout", 60.0) if self.config else 60.0,
            max_retries=self.config.get("max_retries", 2) if self.config else 2,
            verbose=self.verbose,
        )

        constraints = []
        if raw_json and "constraints" in raw_json:
            for constraint_data in raw_json["constraints"]:
                # Create details dict from the constraint data
                details = {
                    "property_path": constraint_data.get("property_path", ""),
                    "constraint_type": constraint_data.get("constraint_type", ""),
                    "validation_rule": constraint_data.get("validation_rule", ""),
                    "applies_to_status": constraint_data.get("applies_to_status", []),
                    "chunk_index": chunk_index,
                    "focus_areas": focus_areas,
                }

                # Add optional fields if present
                if constraint_data.get("data_type"):
                    details["data_type"] = constraint_data["data_type"]
                if constraint_data.get("format"):
                    details["format"] = constraint_data["format"]

                constraint = ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description=constraint_data.get("description", ""),
                    severity=constraint_data.get("severity", "info"),
                    source="llm",
                    details=details,
                )
                constraints.append(constraint)

        return constraints

    def _create_focused_prompt(
        self,
        endpoint_data: Dict,
        focus_areas: List[str],
        chunk_index: int,
        total_chunks: int,
    ) -> str:
        """Create a focused prompt for the specific chunk."""

        focus_instructions = {
            "response_structure": "Focus on overall response structure, required fields, and object hierarchies.",
            "data_types": "Focus on data type validation for all response properties.",
            "headers": "Focus on response headers, content-type, and header-specific constraints.",
            "status_codes": "Focus on status code specific constraints and error responses.",
            "nested_objects": "Focus on nested object properties and their constraints.",
            "arrays": "Focus on array properties, item constraints, and collection validation.",
            "validation_rules": "Focus on value validation rules, ranges, patterns, and business logic constraints.",
            "format_constraints": "Focus on format constraints like dates, URLs, emails, and string patterns.",
        }

        focus_instruction = "\n".join(
            [
                f"- {focus_instructions.get(area, f'Focus on {area}')}"
                for area in focus_areas
            ]
        )

        base_prompt = RESPONSE_PROPERTY_CONSTRAINT_PROMPT.format(
            endpoint_data=json.dumps(endpoint_data, indent=2)
        )

        focused_prompt = f"""
{base_prompt}

FOCUSED ANALYSIS - Chunk {chunk_index + 1} of {total_chunks}:
{focus_instruction}

Important: 
- This is chunk {chunk_index + 1} of {total_chunks} chunks for this endpoint
- Focus specifically on the areas listed above
- Provide comprehensive constraints for your focus areas
- Ensure constraints are specific and actionable
- Each constraint should have clear validation rules
"""

        return focused_prompt

    def _deduplicate_constraints(
        self, constraints: List[ApiConstraint]
    ) -> List[ApiConstraint]:
        """Remove duplicate constraints based on property path and constraint type."""
        seen = set()
        deduplicated = []

        for constraint in constraints:
            # Create a key based on property path and constraint type
            key = (
                constraint.details.get("property_path", ""),
                constraint.details.get("constraint_type", ""),
                constraint.details.get("validation_rule", ""),
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(constraint)
            elif self.verbose:
                print(f"Removed duplicate constraint: {constraint.description[:50]}...")

        if self.verbose and len(constraints) != len(deduplicated):
            print(f"Deduplicated {len(constraints)} -> {len(deduplicated)} constraints")

        return deduplicated

    def _generate_fallback_constraints(
        self, endpoint
    ) -> ResponsePropertyConstraintMinerOutput:
        """Generate basic response constraints when LLM fails."""
        constraints = []

        # Generate common response constraints
        constraints.extend(
            [
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Successful GET response should return valid JSON structure",
                    severity="error",
                    source="fallback",
                    details={
                        "property_path": "root",
                        "constraint_type": "structure",
                        "validation_rule": "valid_json",
                        "applies_to_status": [200],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Response should include Content-Type header",
                    severity="warning",
                    source="fallback",
                    details={
                        "property_path": "headers.content-type",
                        "constraint_type": "format",
                        "validation_rule": "content_type_present",
                        "applies_to_status": [200, 201, 202],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Error responses should include error message or code",
                    severity="warning",
                    source="fallback",
                    details={
                        "property_path": "error",
                        "constraint_type": "structure",
                        "validation_rule": "error_info_present",
                        "applies_to_status": [400, 401, 403, 404, 500],
                    },
                ),
                ApiConstraint(
                    id=str(uuid.uuid4()),
                    type=ConstraintType.RESPONSE_PROPERTY,
                    description="Timestamps should be in ISO 8601 format",
                    severity="info",
                    source="fallback",
                    details={
                        "property_path": "*.created_at,*.updated_at,*.timestamp",
                        "constraint_type": "format",
                        "validation_rule": "iso8601_datetime",
                        "applies_to_status": [200, 201],
                    },
                ),
            ]
        )

        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": len(constraints),
            "source": "fallback",
            "status": "success_fallback",
        }

        return ResponsePropertyConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            response_constraints=constraints,
            total_constraints=len(constraints),
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
