# tools/operation_sequencer.py

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
)
from utils.llm_utils import extract_json_from_text
from config.settings import settings
from config.constants import DEFAULT_LLM_TIMEOUT


class OperationSequencerTool(BaseTool):
    """
    Tool for sequencing API operations based on their dependencies.

    This tool analyzes API endpoints and identifies dependencies between them,
    then creates sequences of operations that should be executed in order.
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

    async def _execute(self, inp: OperationSequencerInput) -> OperationSequencerOutput:
        """Sequence operations based on dependencies using LLM."""
        endpoints = inp.endpoints
        collection_name = inp.collection_name or "API Operations"
        include_data_mapping = inp.include_data_mapping

        if self.verbose:
            print(
                f"OperationSequencer: Analyzing {len(endpoints)} operations for {collection_name}"
            )

        # Check if we have too many endpoints and batch them if needed
        MAX_ENDPOINTS_PER_BATCH = (
            20  # Limit endpoints per analysis to prevent context overflow
        )
        if len(endpoints) > MAX_ENDPOINTS_PER_BATCH:
            if self.verbose:
                print(
                    f"Large number of endpoints detected ({len(endpoints)}). Processing in batches..."
                )

            return await self._process_in_batches(
                endpoints, collection_name, include_data_mapping
            )

        # Prepare input for the LLM - convert endpoints to simplified format
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
                        code: {
                            "description": details.get("description", "")[
                                :100
                            ],  # Truncate long descriptions
                        }
                        for code, details in getattr(endpoint, "responses", {}).items()
                    },
                }
            )

        llm_input = {
            "endpoints": endpoint_data,
            "collection_name": collection_name,
            "include_data_mapping": include_data_mapping,
        }

        # Execute the LLM with timeout and retries
        timeout = self.config.get("timeout", DEFAULT_LLM_TIMEOUT)
        max_retries = self.config.get("max_retries", 2)  # Default to 2 retries
        retry_delay = self.config.get("retry_delay", 1.0)  # Default to 1 second

        for retry in range(max_retries + 1):
            if retry > 0:
                if self.verbose:
                    print(
                        f"Retry {retry}/{max_retries} after waiting {retry_delay}s..."
                    )
                await asyncio.sleep(retry_delay)

            try:
                # Initialize LLM components
                from google.adk.agents import LlmAgent
                from google.adk.runners import Runner
                from google.adk.sessions import InMemorySessionService
                from google.adk.artifacts import InMemoryArtifactService
                from google.adk.memory import InMemoryMemoryService
                from google.genai import types

                # Set up session services
                session_service = InMemorySessionService()
                artifact_service = InMemoryArtifactService()
                memory_service = InMemoryMemoryService()
                session_id = str(uuid.uuid4())
                user_id = "system"

                # Initialize session
                session_service.create_session(
                    app_name="operation_sequencer",
                    user_id=user_id,
                    session_id=session_id,
                    state={},
                )

                # Use simple fixed instruction string that matches successful tools
                instruction = "You are an API Operation Sequencer. Analyze endpoints and create sequences of operations with dependencies. Note: Path parameters are shown in square brackets like [userId] instead of curly braces."

                # Create the LLM agent without schema validation to prevent errors
                sequencer_agent = LlmAgent(
                    name="llm_operation_sequencer",
                    model=settings.llm.LLM_MODEL,
                    instruction=instruction,
                    disallow_transfer_to_parent=True,
                    disallow_transfer_to_peers=True,
                )

                # Create a runner
                runner = Runner(
                    app_name="operation_sequencer",
                    agent=sequencer_agent,
                    session_service=session_service,
                    artifact_service=artifact_service,
                    memory_service=memory_service,
                )

                # Prepare prompt directly in user message
                prompt = """
Analyze these API endpoints and identify dependencies between operations. 
Create sequences of operations that should be executed in order.

Note: Path parameters are shown in square brackets (e.g., [userId], [brandId]) instead of curly braces.

Focus on:
1. Path parameters that match IDs returned by other endpoints
2. Request body fields that require data from GET responses
3. Natural workflows like create-retrieve-update-delete sequences

Return a JSON object with this structure:
{
  "sequences": [
    {
      "name": "Descriptive name of the sequence",
      "description": "Detailed explanation of the sequence's purpose",
      "operations": ["GET /path1", "POST /path2", "PUT /path3/[id]"],
      "dependencies": [
        {
          "source": "PUT /path3/[id]",
          "target": "POST /path2",
          "reason": "Need ID from POST /path2 response to use in PUT /path3/[id] path",
          "data_mapping": {"id": "response.id"}
        }
      ]
    }
  ]
}

Create multiple logical sequences for complete user journeys or workflows.
Explain why each dependency exists.

Here are the endpoints to analyze:
"""

                # Sanitize the llm_input before including it
                from utils.llm_utils import prepare_endpoint_data_for_llm

                sanitized_llm_input = prepare_endpoint_data_for_llm(llm_input)

                # Create complete user message with prompt and sanitized endpoint data
                user_message = prompt + "\n" + json.dumps(sanitized_llm_input, indent=2)

                # Prepare user message
                user_input = types.Content(
                    role="user", parts=[types.Part(text=user_message)]
                )

                if self.verbose:
                    print(f"Running LLM to identify operation sequences")

                # Execute with timeout protection
                start_time = time.time()

                async def get_llm_response():
                    result_text = ""
                    try:
                        for event in runner.run(
                            session_id=session_id,
                            user_id=user_id,
                            new_message=user_input,
                        ):
                            if event.content:
                                result_text = "".join(
                                    part.text for part in event.content.parts
                                )
                        return result_text
                    except Exception as e:
                        if self.verbose:
                            print(f"Error during LLM generation: {str(e)}")
                        return ""

                # Execute with timeout protection
                try:
                    raw_text = await asyncio.wait_for(
                        get_llm_response(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    if self.verbose:
                        print(f"LLM request timed out after {timeout} seconds")
                    raw_text = ""

                # Process the LLM response
                if not raw_text:
                    if self.verbose:
                        print("No response received from LLM")
                    # If this isn't the last retry, continue to the next iteration
                    if retry < max_retries:
                        continue
                    # On last retry, return empty result
                    return OperationSequencerOutput(
                        sequences=[],
                        total_sequences=0,
                        result={"error": "No response received from LLM after retries"},
                    )

                # Extract JSON from text response
                json_data = None
                try:
                    # Try direct JSON parsing first
                    json_data = json.loads(raw_text)
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from text
                    try:
                        # Look for JSON content that might be wrapped in markdown code blocks
                        if "```json" in raw_text:
                            json_parts = raw_text.split("```json")
                            if len(json_parts) > 1:
                                json_content = json_parts[1].split("```")[0].strip()
                                json_data = json.loads(json_content)
                        elif "```" in raw_text:
                            json_parts = raw_text.split("```")
                            if len(json_parts) > 1:
                                json_content = json_parts[1].strip()
                                json_data = json.loads(json_content)
                        else:
                            # Try to find JSON object using regex
                            pattern = r"\{[\s\S]*\}"
                            matches = re.search(pattern, raw_text)
                            if matches:
                                json_data = json.loads(matches.group(0))
                    except Exception:
                        if self.verbose:
                            print(
                                "Failed to extract JSON from text with standard methods"
                            )
                        json_data = None

                # If we still don't have JSON data, try the utility function
                if not json_data:
                    try:
                        json_data = await extract_json_from_text(raw_text)
                    except:
                        json_data = None

                # If still no valid JSON, return error
                if not json_data:
                    if self.verbose:
                        print(f"Failed to extract JSON from LLM response")
                        print(f"Raw response preview: {raw_text[:200]}...")
                    return OperationSequencerOutput(
                        sequences=[],
                        total_sequences=0,
                        result={
                            "error": "Failed to extract valid JSON from LLM response"
                        },
                    )

                # Convert LLM output to our schema format
                operation_sequences = []

                if "sequences" in json_data:
                    for seq in json_data["sequences"]:
                        # Ensure we have all required fields
                        if not all(
                            key in seq for key in ["name", "description", "operations"]
                        ):
                            if self.verbose:
                                print(
                                    f"Skipping incomplete sequence: {seq.get('name', 'unnamed')}"
                                )
                            continue

                        dependencies = []

                        # Process dependencies with safe handling
                        for dep in seq.get("dependencies", []):
                            if not isinstance(dep, dict) or not all(
                                key in dep for key in ["source", "target", "reason"]
                            ):
                                continue

                            # Extract required fields with safety checks
                            source = dep.get("source", "")
                            target = dep.get("target", "")
                            reason = dep.get("reason", "")

                            # Skip invalid dependencies
                            if not source or not target:
                                continue

                            # Ensure data_mapping is a valid dict
                            data_mapping = dep.get("data_mapping", {})
                            if not isinstance(data_mapping, dict):
                                data_mapping = {}

                            try:
                                dependencies.append(
                                    OperationDependency(
                                        source_operation=source,
                                        target_operation=target,
                                        reason=reason,
                                        data_mapping=data_mapping,
                                    )
                                )
                            except Exception as e:
                                if self.verbose:
                                    print(f"Error creating dependency: {str(e)}")
                                continue

                        # Create sequence
                        try:
                            sequence = OperationSequence(
                                id=str(uuid.uuid4()),
                                name=seq["name"],
                                description=seq["description"],
                                operations=seq["operations"],
                                dependencies=dependencies,
                            )
                            operation_sequences.append(sequence)
                        except Exception as e:
                            if self.verbose:
                                print(f"Error creating sequence: {str(e)}")
                            continue

                # Create result summary
                result_summary = {
                    "total_endpoints": len(endpoints),
                    "total_sequences": len(operation_sequences),
                    "has_dependencies": any(
                        seq.dependencies for seq in operation_sequences
                    ),
                    "collection_name": collection_name,
                    "execution_time": round(time.time() - start_time, 2),
                }

                if self.verbose:
                    print(f"Found {len(operation_sequences)} operation sequences")

                    # Print a few examples
                    for i, seq in enumerate(operation_sequences[:2]):
                        print(f"\nSequence {i+1}: {seq.name}")
                        print(f"Description: {seq.description}")
                        print(f"Operations ({len(seq.operations)}):")
                        for op in seq.operations:
                            print(f"  - {op}")
                        if seq.dependencies:
                            print(f"Dependencies ({len(seq.dependencies)}):")
                            for dep in seq.dependencies[:3]:
                                print(
                                    f"  - {dep.source_operation} depends on {dep.target_operation}: {dep.reason}"
                                )
                                if dep.data_mapping:
                                    print(f"    Data mapping: {dep.data_mapping}")

                return OperationSequencerOutput(
                    sequences=operation_sequences,
                    total_sequences=len(operation_sequences),
                    result=result_summary,
                )

            except Exception as e:
                if self.verbose:
                    print(f"Error during LLM processing: {str(e)}")
                return OperationSequencerOutput(
                    sequences=[],
                    total_sequences=0,
                    result={"error": str(e)},
                )

    async def _process_in_batches(
        self, endpoints: List[Any], collection_name: str, include_data_mapping: bool
    ) -> OperationSequencerOutput:
        """Process large numbers of endpoints in smaller batches."""
        BATCH_SIZE = 15  # Reduced batch size for better stability
        all_sequences = []
        batch_results = {}

        # Group endpoints by their first path segment for more logical batching
        endpoint_groups = {}
        for endpoint in endpoints:
            # Extract first path segment
            path_parts = endpoint.path.strip("/").split("/")
            first_segment = path_parts[0] if path_parts else ""

            if first_segment not in endpoint_groups:
                endpoint_groups[first_segment] = []
            endpoint_groups[first_segment].append(endpoint)

        # Process each group
        group_count = 0
        for group_name, group_endpoints in endpoint_groups.items():
            group_count += 1
            if self.verbose:
                print(
                    f"Processing endpoint group '{group_name}' with {len(group_endpoints)} endpoints"
                )

            # Further batch if the group is still too large
            batch_num = 0
            for i in range(0, len(group_endpoints), BATCH_SIZE):
                batch_num += 1
                batch = group_endpoints[i : i + BATCH_SIZE]

                if self.verbose:
                    print(f"Processing batch {batch_num} ({len(batch)} endpoints)")

                # Create input for this batch
                batch_input = OperationSequencerInput(
                    endpoints=batch,
                    collection_name=f"{collection_name} - {group_name}",
                    include_data_mapping=include_data_mapping,
                )

                # Process batch
                try:
                    batch_output = await self._execute(batch_input)
                    batch_results[f"{group_name}_batch{batch_num}"] = {
                        "endpoints": len(batch),
                        "sequences": len(batch_output.sequences),
                    }

                    # Collect sequences
                    if batch_output.sequences:
                        all_sequences.extend(batch_output.sequences)
                except Exception as e:
                    if self.verbose:
                        print(f"Error processing batch: {str(e)}")
                    batch_results[f"{group_name}_batch{batch_num}"] = {
                        "endpoints": len(batch),
                        "sequences": 0,
                        "error": str(e),
                    }

                # Short pause to avoid rate limiting
                await asyncio.sleep(0.5)

        # Create combined output
        result_summary = {
            "total_endpoints": len(endpoints),
            "total_sequences": len(all_sequences),
            "has_dependencies": any(seq.dependencies for seq in all_sequences),
            "collection_name": collection_name,
            "processed_in_batches": True,
            "batch_count": group_count,
            "batch_results": batch_results,
        }

        if self.verbose:
            print(
                f"Combined results: Found {len(all_sequences)} operation sequences from all batches"
            )

        return OperationSequencerOutput(
            sequences=all_sequences,
            total_sequences=len(all_sequences),
            result=result_summary,
        )

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
        pass
