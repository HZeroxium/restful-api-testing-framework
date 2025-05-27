import asyncio
import json
from typing import List
from pydantic import BaseModel, Field

# ADK imports
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm

# Content types for runner input
from google.genai import types

# Schema for API endpoint
from schemas.tools.openapi_parser import EndpointInfo, AuthType


# ─── 1. CONSTRAINT SCHEMA ───────────────────────────────────────────────────────────


class RequestResponseConstraint(BaseModel):
    param: str = Field(..., description="Name of the request parameter or body field")
    property: str = Field(..., description="Name of the response JSON property")


class ResponsePropertyConstraint(BaseModel):
    property: str = Field(..., description="Name of the response JSON property")
    description: str = Field(
        ..., description="Natural language description of the constraint"
    )


class ConstraintExtractionResult(BaseModel):
    request_response_constraints: List[RequestResponseConstraint]
    response_property_constraints: List[ResponsePropertyConstraint]


# ─── 2. DEFINE STATIC MINING AGENT ─────────────────────────────────────────────────

static_miner = LlmAgent(
    name="static_constraint_miner",
    model=LiteLlm(
        model="openai/gpt-4o",
    ),
    instruction="""
You are a Static Constraint Miner.

INPUT:
  A JSON object matching the EndpointInfo schema.

OUTPUT:
  A JSON object exactly matching ConstraintExtractionResult schema.
""",
    input_schema=EndpointInfo,
    output_schema=ConstraintExtractionResult,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


async def main():
    # ─── 3. INIT SERVICES & SESSION ────────────────────────────────────────────────
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()

    # Tạo session trước khi chạy runner
    session_service.create_session(
        app_name="constraint_miner_app",
        user_id="user1",
        session_id="session1",
        state={},
    )

    runner = Runner(
        app_name="constraint_miner_app",
        agent=static_miner,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
    )

    # ─── 4. SAMPLE BASED ON API SPEC ──────────────────────────────────────────────
    example = EndpointInfo(
        name="get_products",
        description="Retrieve all products",
        path="/products",
        method="GET",
        tags=[],
        auth_required=False,
        auth_type=None,
        input_schema={
            "properties": {
                "by_brand": {"description": "Id of brand", "type": "STRING"},
                "by_category": {"description": "Id of category", "type": "STRING"},
                "is_rental": {
                    "description": "Retrieve rental products",
                    "type": "STRING",
                },
                "between": {
                    "description": "Define price range e.g. price,10,30",
                    "type": "STRING",
                },
                "sort": {
                    "description": "Sort: name,asc|desc or price,asc|desc",
                    "type": "STRING",
                },
                "page": {"description": "Page number", "type": "INTEGER"},
            },
            "type": "OBJECT",
        },
        output_schema={
            "200": {
                "description": "Successful operation",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "OBJECT",
                            "properties": {
                                "current_page": {"type": "INTEGER", "example": 1},
                                "data": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "id": {"type": "STRING", "example": "1"},
                                            "name": {
                                                "type": "STRING",
                                                "example": "new brand",
                                            },
                                            "description": {
                                                "type": "STRING",
                                                "example": "Lorem ipsum",
                                            },
                                            "price": {
                                                "type": "NUMBER",
                                                "example": 9.99,
                                            },
                                            "is_location_offer": {
                                                "type": "BOOLEAN",
                                                "example": 1,
                                            },
                                            "is_rental": {
                                                "type": "BOOLEAN",
                                                "example": 0,
                                            },
                                            "in_stock": {
                                                "type": "BOOLEAN",
                                                "example": 0,
                                            },
                                            "brand": {
                                                "type": "OBJECT",
                                                "properties": {
                                                    "id": {"type": "STRING"},
                                                    "name": {
                                                        "type": "STRING",
                                                        "example": "new brand",
                                                    },
                                                    "slug": {
                                                        "type": "STRING",
                                                        "example": "new-brand",
                                                    },
                                                },
                                            },
                                            "category": {
                                                "type": "OBJECT",
                                                "properties": {
                                                    "id": {"type": "STRING"},
                                                    "parent_id": {"type": "STRING"},
                                                    "name": {
                                                        "type": "STRING",
                                                        "example": "new category",
                                                    },
                                                    "slug": {
                                                        "type": "STRING",
                                                        "example": "new-category",
                                                    },
                                                    "sub_categories": {"type": "ARRAY"},
                                                },
                                            },
                                            "product_image": {
                                                "type": "OBJECT",
                                                "properties": {
                                                    "by_name": {"type": "STRING"},
                                                    "by_url": {"type": "STRING"},
                                                    "source_name": {"type": "STRING"},
                                                    "source_url": {"type": "STRING"},
                                                    "file_name": {"type": "STRING"},
                                                    "title": {"type": "STRING"},
                                                    "id": {"type": "STRING"},
                                                },
                                            },
                                        },
                                    },
                                },
                                "from": {"type": "INTEGER", "example": 1},
                                "last_page": {"type": "INTEGER", "example": 1},
                                "per_page": {"type": "INTEGER", "example": 1},
                                "to": {"type": "INTEGER", "example": 1},
                                "total": {"type": "INTEGER", "example": 1},
                            },
                        }
                    }
                },
            },
            "404": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "OBJECT",
                            "properties": {
                                "message": {
                                    "type": "STRING",
                                    "example": "Requested item not found",
                                }
                            },
                        }
                    }
                },
            },
            "405": {
                "description": "Method not allowed",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "OBJECT",
                            "properties": {
                                "message": {
                                    "type": "STRING",
                                    "example": "Method is not allowed",
                                }
                            },
                        }
                    }
                },
            },
        },
    )

    # ─── 5. PREPARE USER INPUT ──────────────────────────────────────────────────────
    # Đóng gói JSON của example vào types.Content
    user_input = types.Content(
        role="user", parts=[types.Part(text=json.dumps(example.model_dump()))]
    )

    # ─── 6. RUN AGENT ───────────────────────────────────────────────────────────────
    raw_json = None
    for event in runner.run(
        session_id="session1",
        user_id="user1",
        new_message=user_input,  # đúng kiểu Content :contentReference[oaicite:7]{index=7}
    ):
        if event.content:
            text = "".join(part.text for part in event.content.parts)
            try:
                raw_json = json.loads(text)
            except json.JSONDecodeError:
                print("Failed to decode JSON from agent response.")

    # ─── 7. VALIDATE & IN KẾT QUẢ ──────────────────────────────────────────────────
    if raw_json is not None:
        print(json.dumps(raw_json, indent=2))
    else:
        print("No valid response received from the agent.")


if __name__ == "__main__":
    asyncio.run(main())
