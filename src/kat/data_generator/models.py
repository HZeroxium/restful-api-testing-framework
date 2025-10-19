
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


@dataclass
class LoadedArtifacts:
    operation_sequences: Dict[str, List[List[str]]]   # { endpointSig: [[chain1...], [chain2...]] }
    topolist: List[str]                                # [ endpointSig, ... ]
    endpoint_schema_dependencies: Dict[str, Any]       # { endpointSig: ... }
    endpoints_belong_to_schemas: Dict[str, List[str]]  # { schemaName: [producerEndpointSig, ...] }

@dataclass
class EndpointCache:
    endpoint: str
    cache: Dict[str, Any]                               
@dataclass
class DependencyBlock:
    endpoint: str                 # ví dụ: "get-/api/v1/Bills"
    schema: Optional[str]         # ví dụ: "Bill"
    json: str                     # chuỗi JSON đã minify (một object đại diện)

@dataclass
class DependencyContext:
    schemas: List[str]            # ví dụ: ["Bill","Stage","Publication"]
    blocks: List[DependencyBlock] # các object upstream gọn để đưa vào prompt



class LineDataBase(BaseModel):
    index: int
    expected_code: Optional[str] = None    # chấp nhận '2xx', '4xx', '200', '400', ...
    reason: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)  # JSON đã parse từ cột 'data' (nếu là JSON hợp lệ)
    raw_json: Optional[str] = None                        # giữ lại chuỗi gốc ở cột 'data' để trace

    class Config:
        extra = "ignore"

class SingleEndpointDetailedResult(BaseModel):
    endpoint: str
    param_2xx: List[LineDataBase] = Field(default_factory=list)
    param_4xx: List[LineDataBase] = Field(default_factory=list)
    body_2xx:  List[LineDataBase] = Field(default_factory=list)
    body_4xx:  List[LineDataBase] = Field(default_factory=list)

    csv_params_file: Optional[str] = None
    csv_body_file: Optional[str] = None
