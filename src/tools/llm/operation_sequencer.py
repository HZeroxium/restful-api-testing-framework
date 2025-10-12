# tools/llm/operation_sequencer.py

import uuid
import json
import asyncio
import time
import re
from typing import Dict, List, Optional, Any

from core.base_tool import BaseTool
from schemas.tools.operation_sequencer import (
    OperationSequencerInput,
    OperationSequencerOutput,
    OperationSequence,
    OperationDependency,
    DependencyGraph,
    OperationNode,
    DependencyEdge,
)
from tools.llm.operation_sequencer_helpers.schema_analyzer import SchemaBasedAnalyzer
from utils.llm_utils import (
    create_and_execute_llm_agent,
    extract_json_from_response as extract_json_from_text,
)
from config.settings import settings
from config.constants import DEFAULT_LLM_TIMEOUT
from common.logger import LoggerFactory, LoggerType, LogLevel
from pydantic import BaseModel, Field


class SequenceRefinementOutput(BaseModel):
    """Output schema for LLM sequence refinement."""

    sequences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Validated/enhanced existing sequences"
    )
    new_sequences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Completely new sequences identified by LLM"
    )


class OperationSequencerTool(BaseTool):
    """
    Tool for sequencing API operations based on their dependencies.

    This tool uses a hybrid approach: schema-based analysis first (fast, deterministic),
    then LLM refinement to add context and handle complex cases.
    """

    def __init__(
        self,
        *,
        name: str = "operation_sequencer",
        description: str = "Sequences API operations based on dependencies",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=OperationSequencerInput,
            output_schema=OperationSequencerOutput,
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

    async def _execute(self, inp: OperationSequencerInput) -> OperationSequencerOutput:
        """Hybrid approach: Schema analysis + LLM refinement."""
        endpoints = inp.endpoints
        collection_name = inp.collection_name or "API Operations"
        include_data_mapping = inp.include_data_mapping

        self.logger.info(f"Analyzing {len(endpoints)} operations for {collection_name}")
        self.logger.add_context(
            endpoints_count=len(endpoints),
            collection_name=collection_name,
            include_data_mapping=include_data_mapping,
        )

        # Step 1: Schema-based analysis (fast, deterministic)
        self.logger.info("Starting schema-based dependency analysis...")
        schema_analyzer = SchemaBasedAnalyzer(endpoints)
        schema_nodes, schema_edges = schema_analyzer.analyze_dependencies()
        schema_sequences = schema_analyzer.generate_sequences(
            schema_nodes, schema_edges
        )

        self.logger.info(
            f"Schema analysis found {len(schema_sequences)} sequences with {len(schema_edges)} dependencies"
        )

        # Step 2: LLM refinement (adds context, handles complex cases)
        # Only send simplified endpoint data + schema analysis results to LLM
        llm_input = {
            "endpoints": self._simplify_endpoints_for_llm(endpoints),
            "schema_analysis": {
                "sequences": [seq.model_dump() for seq in schema_sequences],
                "dependencies_count": len(schema_edges),
            },
            "collection_name": collection_name,
            "include_data_mapping": include_data_mapping,
        }

        # Call LLM to refine and add additional insights
        llm_sequences = await self._call_llm_for_refinement(llm_input)

        # Step 3: Merge results (schema-based + LLM insights)
        final_sequences = self._merge_sequences(schema_sequences, llm_sequences)

        # Step 4: Build dependency graph
        graph = self._build_dependency_graph(
            schema_nodes, schema_edges, final_sequences
        )

        return OperationSequencerOutput(
            sequences=final_sequences,
            total_sequences=len(final_sequences),
            graph=graph,
            analysis_method="hybrid",
            result={
                "schema_sequences": len(schema_sequences),
                "llm_sequences": len(llm_sequences),
                "final_sequences": len(final_sequences),
                "total_dependencies": len(schema_edges),
            },
        )

    def _simplify_endpoints_for_llm(self, endpoints: List[Any]) -> List[Dict]:
        """Extract minimal info for LLM context."""
        endpoint_data = []
        for endpoint in endpoints:
            endpoint_data.append(
                {
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "name": getattr(
                        endpoint, "name", f"{endpoint.method} {endpoint.path}"
                    ),
                    "description": getattr(endpoint, "description", ""),
                    # Simplify schemas to reduce context size
                    "parameters": [
                        {
                            "name": param.get("name", ""),
                            "required": param.get("required", False),
                            "in": param.get("in", ""),
                            "description": param.get("description", ""),
                            "type": param.get(
                                "type", param.get("schema", {}).get("type", "")
                            ),
                        }
                        for param in getattr(endpoint, "parameters", [])
                    ][
                        :5
                    ],  # Limit to 5 parameters to save tokens
                    # Include only necessary request body fields
                    "request_body": self._simplify_request_body(
                        getattr(endpoint, "request_body", None)
                    ),
                    # Include only necessary response fields
                    "responses": {
                        code: {"description": details.get("description", "")[:100]}
                        for code, details in getattr(endpoint, "responses", {}).items()
                    },
                }
            )
        return endpoint_data

    async def _call_llm_for_refinement(
        self, llm_input: Dict
    ) -> List[OperationSequence]:
        """Ask LLM to refine schema-based sequences and add insights."""
        try:
            # Use standard LLM agent pattern
            result = await create_and_execute_llm_agent(
                app_name="operation_sequencer",
                agent_name="sequence_refiner",
                instruction=self._build_refinement_instruction(llm_input),
                input_data=llm_input,
                output_schema=SequenceRefinementOutput,
                timeout=self.config.get("llm_timeout", DEFAULT_LLM_TIMEOUT),
                max_retries=self.config.get("max_retries", 2),
                verbose=self.verbose,
                cache_enabled=self.cache_enabled,
            )

            # Extract sequences from both validated and new sequences
            all_sequences = []

            # Process validated/enhanced sequences
            for seq_data in result.sequences:
                sequence = self._parse_sequence_data(seq_data)
                if sequence:
                    all_sequences.append(sequence)

            # Process new sequences
            for seq_data in result.new_sequences:
                sequence = self._parse_sequence_data(seq_data)
                if sequence:
                    all_sequences.append(sequence)

            self.logger.info(f"LLM refinement generated {len(all_sequences)} sequences")
            return all_sequences

        except Exception as e:
            self.logger.warning(f"LLM refinement failed: {str(e)}")
            return []

    def _build_refinement_instruction(self, llm_input: Dict) -> str:
        """Build the instruction for LLM refinement."""
        schema_sequences = llm_input["schema_analysis"]["sequences"]
        # endpoints are already simplified in _execute method
        simplified_endpoints = llm_input["endpoints"]

        return f"""You are an API Operation Sequencer. Analyze the endpoints and existing sequences.

Schema Analysis Results:
{json.dumps(schema_sequences, indent=2)}

API Endpoints:
{json.dumps(simplified_endpoints, indent=2)}

Your Tasks:
1. VALIDATE existing schema-generated sequences
2. GENERATE new sequences for patterns schema analysis missed:
   - Different workflow patterns (create, read, update, delete flows)
   - Cross-resource workflows
   - Hierarchical access patterns
   - Authentication/authorization flows
3. ENHANCE sequence descriptions and dependency reasons
4. IDENTIFY complex dependencies schema analysis couldn't detect

Requirements:
- Each sequence must have at least 2 operations
- Operations can appear in multiple sequences
- Provide clear dependency reasons
- Include data_mapping for parameter passing

Return JSON:
{{
  "sequences": [...validated/enhanced existing sequences...],
  "new_sequences": [...completely new sequences you identified...]
}}"""

    def _parse_sequence_data(
        self, seq_data: Dict[str, Any]
    ) -> Optional[OperationSequence]:
        """Parse sequence data from LLM response into OperationSequence object."""
        try:
            # Extract dependencies
            dependencies = []
            for dep_data in seq_data.get("dependencies", []):
                dependency = OperationDependency(
                    source_operation=dep_data.get("source_operation", ""),
                    target_operation=dep_data.get("target_operation", ""),
                    reason=dep_data.get("reason", ""),
                    data_mapping=dep_data.get("data_mapping", {}),
                )
                dependencies.append(dependency)

            # Create sequence
            sequence = OperationSequence(
                id=seq_data.get("id", str(uuid.uuid4())),
                name=seq_data.get("name", "Unnamed Sequence"),
                description=seq_data.get("description", ""),
                operations=seq_data.get("operations", []),
                dependencies=dependencies,
                sequence_type=seq_data.get("sequence_type", "unknown"),
                priority=seq_data.get("priority", 3),
                metadata=seq_data.get("metadata", {}),
            )

            return sequence

        except Exception as e:
            self.logger.warning(f"Failed to parse sequence data: {str(e)}")
            return None

    def _merge_sequences(
        self, schema_seqs: List[OperationSequence], llm_seqs: List[OperationSequence]
    ) -> List[OperationSequence]:
        """Merge schema-based and LLM sequences, prioritizing schema-based for conflicts."""
        # Start with schema-based sequences (higher confidence)
        final_sequences = list(schema_seqs)

        # Add LLM sequences that don't conflict
        for llm_seq in llm_seqs:
            # Check if this sequence conflicts with existing ones
            conflicts = False
            for existing_seq in final_sequences:
                if existing_seq.name.lower() == llm_seq.name.lower() or set(
                    existing_seq.operations
                ) == set(llm_seq.operations):
                    conflicts = True
                    break

            if not conflicts:
                # Add LLM sequence with lower confidence metadata
                if not llm_seq.metadata:
                    llm_seq.metadata = {}
                llm_seq.metadata["confidence"] = (
                    0.8  # LLM sequences have lower confidence
                )
                final_sequences.append(llm_seq)

        return final_sequences

    def _build_dependency_graph(
        self,
        nodes: List[OperationNode],
        edges: List[DependencyEdge],
        sequences: List[OperationSequence],
    ) -> DependencyGraph:
        """Build graph representation for visualization."""
        # Add sequence metadata to nodes
        node_map = {node.id: node for node in nodes}
        for sequence in sequences:
            for operation in sequence.operations:
                # Find corresponding node
                for node in nodes:
                    if node.operation == operation:
                        if not node.metadata:
                            node.metadata = {}
                        node.metadata["sequences"] = node.metadata.get("sequences", [])
                        if sequence.name not in node.metadata["sequences"]:
                            node.metadata["sequences"].append(sequence.name)

        # Add graph metadata
        metadata = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_sequences": len(sequences),
            "analysis_method": "hybrid",
            "generated_at": time.time(),
        }

        return DependencyGraph(nodes=nodes, edges=edges, metadata=metadata)

    def _simplify_request_body(self, request_body: Optional[Dict]) -> Optional[Dict]:
        """Simplify the request body schema to reduce context size."""
        if not request_body:
            return None

        result = {}
        # Extract only essential information
        if "content" in request_body:
            content_types = list(request_body["content"].keys())
            if content_types:
                result["content_type"] = content_types[0]
                schema = request_body["content"][content_types[0]].get("schema", {})
                if "properties" in schema:
                    # Only get property names, not full definitions
                    result["properties"] = list(schema["properties"].keys())
                    result["required"] = schema.get("required", [])

        return result

    async def cleanup(self) -> None:
        """Clean up any resources."""
        self.logger.debug("Cleaning up OperationSequencerTool resources")
