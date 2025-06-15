from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Server:
    url: str
    description: Optional[str] = None


@dataclass
class Info:
    title: str
    version: str
    description: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    license: Optional[Dict[str, Any]] = None


@dataclass
class Parameter:
    name: str
    in_: str
    required: bool
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


@dataclass
class RequestBody:
    content_type: str
    schema: Dict[str, Any]


@dataclass
class Response:
    status_code: str
    description: Optional[str]
    content_type: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


@dataclass
class Endpoint:
    path: str
    method: str
    summary: Optional[str]
    description: Optional[str]
    operation_id: Optional[str]
    tags: List[str]
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: List[Response] = field(default_factory=list)


@dataclass
class OpenAPISpec:
    openapi: str
    info: Info
    servers: List[Server]
    tags: List[Dict[str, Any]]
    paths: List[Endpoint]
    components: Dict[str, Any]
