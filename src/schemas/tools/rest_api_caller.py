# schemas/tools/rest_api_caller.py

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RestRequest(BaseModel):
    """Encapsulates HTTP request parameters."""

    method: str = Field(..., description="HTTP method, e.g., GET, POST")
    url: str = Field(..., description="Full URL of the REST endpoint")
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Optional HTTP headers"
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Query parameters"
    )
    json: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON body for POST/PUT"
    )


class RestResponse(BaseModel):
    """Wraps HTTP response data."""

    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(..., description="Response headers")
    body: Any = Field(..., description="Parsed JSON or text response")


class RestApiCallerInput(BaseModel):
    """Input schema for REST API Caller tool."""

    request: RestRequest = Field(..., description="Details of the HTTP request")


class RestApiCallerOutput(BaseModel):
    """Output schema from REST API Caller tool."""

    request: RestRequest = Field(..., description="Original HTTP request")
    response: RestResponse = Field(..., description="Wrapped HTTP response")
    elapsed: float = Field(..., description="Time taken to perform the request (s)")
