import uuid
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from core.base_tool import BaseTool
from schemas.tools.constraint_miner import (
    StaticConstraintMinerInput,
    StaticConstraintMinerOutput,
    ApiConstraint,
    ConstraintType,
)
from config.settings import settings


class StaticConstraintMinerTool(BaseTool):
    """
    Tool for mining static constraints from API endpoint information using LLM.

    This tool analyzes OpenAPI specifications using LLM to extract:
    1. Request-Response constraints: How request parameters affect response status/content
    2. Response-Property constraints: Rules about properties within the response
    """

    def __init__(
        self,
        *,
        name: str = "static_constraint_miner",
        description: str = "Mines static constraints from API endpoint information using LLM",
        config: Optional[Dict] = None,
        verbose: bool = False,
        cache_enabled: bool = False,
    ):
        super().__init__(
            name=name,
            description=description,
            input_schema=StaticConstraintMinerInput,
            output_schema=StaticConstraintMinerOutput,
            config=config,
            verbose=verbose,
            cache_enabled=cache_enabled,
        )

    async def _execute(
        self, inp: StaticConstraintMinerInput
    ) -> StaticConstraintMinerOutput:
        """Mine constraints from the endpoint information using LLM."""
        endpoint = inp.endpoint_info

        if self.verbose:
            print(f"StaticConstraintMiner: Mining constraints for {endpoint.method.upper()} {endpoint.path}")

        # Initialize LLM components
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.memory import InMemoryMemoryService
        from google.adk.models.lite_llm import LiteLlm
        from google.genai import types

        # Define a schema for LLM output that matches what we expect to get from the LLM
        class RequestResponseConstraint(BaseModel):
            param: str = Field(
                ..., description="Name of the request parameter or body field"
            )
            property: str = Field(..., description="Name of the response JSON property")
            description: str = Field(
                ..., description="Natural language description of the constraint"
            )
            severity: str = Field(
                default="info", description="Severity level (info, warning, error)"
            )

        class ResponsePropertyConstraint(BaseModel):
            property: str = Field(..., description="Name of the response JSON property")
            description: str = Field(
                ..., description="Natural language description of the constraint"
            )
            severity: str = Field(
                default="info", description="Severity level (info, warning, error)"
            )

        class ConstraintExtractionResult(BaseModel):
            request_response_constraints: List[RequestResponseConstraint] = Field(
                default_factory=list
            )
            response_property_constraints: List[ResponsePropertyConstraint] = Field(
                default_factory=list
            )

        # Set up session services
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        memory_service = InMemoryMemoryService()

        # Create a unique session ID
        session_id = str(uuid.uuid4())
        user_id = "system"

        # Initialize session
        session_service.create_session(
            app_name="constraint_miner",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

        # Create the LLM agent
        constraint_miner_agent = LlmAgent(
            name="llm_constraint_miner",
            # model=LiteLlm(
            #     model=settings.llm.LLM_MODEL,
            #     # temperature=settings.llm.TEMPERATURE,
            #     # max_tokens=settings.llm.MAX_TOKENS,
            # ),
            model=settings.llm.LLM_MODEL,
            instruction=""",
You are a Constraint Miner for REST APIs. Your job is to analyze an API endpoint specification and extract two types of constraints:

1. Request-Response Constraints: These are constraints between request parameters and response properties. These indicate how specific request parameters affect what's returned in the response.

2. Response-Property Constraints: These are constraints on the response properties themselves, such as rules about what values they can have or relationships between different response properties.

INPUT:
  You will receive a JSON object matching the EndpointInfo schema containing information about an API endpoint.

OUTPUT:
  Return a JSON object exactly matching the ConstraintExtractionResult schema with extracted constraints.
  
EXAMPLES OF CONSTRAINTS:
- Request-Response: "The 'page' parameter determines which subset of results appears in the response data array"
- Request-Response: "When 'is_rental' is true, only products with is_rental=true will be included in results"
- Response-Property: "The 'total' property must be greater than or equal to the number of items in the 'data' array"
- Response-Property: "When 'last_page' equals 'current_page', the 'to' property equals 'total'"

Be thorough and extract all constraints you can identify. For each constraint, provide a clear description and indicate the severity (info, warning, error).
""",
            input_schema=type(endpoint),
            output_schema=ConstraintExtractionResult,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        # Create a runner
        runner = Runner(
            app_name="constraint_miner",
            agent=constraint_miner_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            memory_service=memory_service,
        )

        # Prepare input for the LLM
        user_input = types.Content(
            role="user", parts=[types.Part(text=json.dumps(endpoint.model_dump()))]
        )

        # Run the agent and get constraints
        raw_json = None
        try:
            if self.verbose:
                print(
                    f"Running LLM to extract constraints for {endpoint.method.upper()} {endpoint.path}"
                )

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
                return StaticConstraintMinerOutput(
                    endpoint_method=endpoint.method,
                    endpoint_path=endpoint.path,
                    total_constraints=0,
                    result={"error": "No valid response received from LLM"},
                )

        except Exception as e:
            if self.verbose:
                print(f"Error during LLM processing: {str(e)}")
            return StaticConstraintMinerOutput(
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                total_constraints=0,
                result={"error": str(e)},
            )

        # Convert LLM output to our constraint format
        request_response_constraints = []
        response_property_constraints = []

        # Process request-response constraints
        if "request_response_constraints" in raw_json:
            for constraint in raw_json["request_response_constraints"]:
                constraint_id = str(uuid.uuid4())
                request_response_constraints.append(
                    ApiConstraint(
                        id=constraint_id,
                        type=ConstraintType.REQUEST_RESPONSE,
                        description=constraint["description"],
                        severity=constraint.get("severity", "info"),
                        source="llm",
                        details={
                            "parameter": constraint["param"],
                            "response_property": constraint["property"],
                        },
                    )
                )

        # Process response-property constraints
        if "response_property_constraints" in raw_json:
            for constraint in raw_json["response_property_constraints"]:
                constraint_id = str(uuid.uuid4())
                response_property_constraints.append(
                    ApiConstraint(
                        id=constraint_id,
                        type=ConstraintType.RESPONSE_PROPERTY,
                        description=constraint["description"],
                        severity=constraint.get("severity", "info"),
                        source="llm",
                        details={"property": constraint["property"]},
                    )
                )

        total_constraints = len(request_response_constraints) + len(
            response_property_constraints
        )

        # Create result summary
        result_summary = {
            "endpoint": f"{endpoint.method.upper()} {endpoint.path}",
            "total_constraints": total_constraints,
            "request_response_count": len(request_response_constraints),
            "response_property_count": len(response_property_constraints),
            "source": "llm",
        }

        if self.verbose:
            print(
                f"Found {total_constraints} constraints for {endpoint.method.upper()} {endpoint.path}"
            )

        return StaticConstraintMinerOutput(
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            request_response_constraints=request_response_constraints,
            response_property_constraints=response_property_constraints,
            total_constraints=total_constraints,
            result=result_summary,
        )

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass
