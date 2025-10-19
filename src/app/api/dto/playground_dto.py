from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


class PlaygroundExecuteRequest(BaseModel):
    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE, PATCH")
    base_url: str = Field(..., description="Base URL, e.g., https://api.example.com")
    path: str = Field(..., description="Path, e.g., /v1/things")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None)
    timeout: Optional[float] = Field(default=15.0, ge=1.0, le=120.0)
    retries: Optional[int] = Field(default=2, ge=0, le=5)
    # Token authentication support
    token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (will be added to Authorization header)",
    )


class PlaygroundExecuteResponse(BaseModel):
    url: str = Field(..., description="Final request URL")
    status_code: int = Field(...)
    headers: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None)
    elapsed_ms: float = Field(...)
    error: Optional[str] = Field(default=None)
