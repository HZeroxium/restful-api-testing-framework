from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
# nếu bạn có StatusSpec riêng, giữ import này:
# from .status import StatusSpec
# tạm thời fallback nếu chưa có StatusSpec:
from .status import StatusSpec

TEST_CASE_DIR_NAME = "KAT_CLONE_TEST_CASES"

# ====== RESPONSE VALIDATION ======
class ResponseValidation(BaseModel):
    status_code: Optional[StatusSpec] = None
    body_validation: Dict[str, Any] = Field(default_factory=dict)

# ====== STEP ======
class StepModel(BaseModel):
    step_number: int
    endpoint: str
    method: str = "GET"  # dùng str thôi, không custom type
    path_variables: Dict[str, Any] = Field(default_factory=dict)
    query_parameters: Dict[str, Any] = Field(default_factory=dict)
    request_body: Dict[str, Any] = Field(default_factory=dict)
    response_validation: Optional[ResponseValidation] = None
    data_dependencies: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def _method_ok(cls, v: str) -> str:
        v = (v or "").upper()
        allowed = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if v not in allowed:
            raise ValueError(f"Unsupported HTTP method: {v}")
        return v

# ====== TEST CASE CORE (JSON) ======
class TestCaseCore(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    endpoint: str
    sequence_index: Optional[int] = None
    steps: List[StepModel]

    def default_expected(self) -> StatusSpec:
        return StatusSpec.default_ok()

# ====== CSV DATA ROW ======
class DataRow(BaseModel):
    index: int
    data: str
    expected_status_code: Optional[StatusSpec] = None
    reason: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    @property
    def data_dict(self) -> Dict[str, Any]:
        import json
        try:
            return json.loads(self.data) if self.data else {}
        except json.JSONDecodeError:
            return {}

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "DataRow":
        normalized = {k: (v if v != "" else None) for k, v in row.items()}
        std = {"index", "data", "expected_status_code", "reason"}
        extra = {k: v for k, v in normalized.items() if k not in std}
        return cls(
            index=int(normalized.get("index") or 0),
            data=str(normalized.get("data") or "{}"),
            expected_status_code=(StatusSpec(normalized.get("expected_status_code"))
                                  if normalized.get("expected_status_code") else None),
            reason=normalized.get("reason"),
            extra=extra
        )

# ====== DATASET GHÉP ======
class InjectedDataset(BaseModel):
    param_rows: List[DataRow] = Field(default_factory=list)
    body_rows: List[DataRow] = Field(default_factory=list)

class TestCaseWithDataset(BaseModel):
    test_case: TestCaseCore
    dataset: InjectedDataset = Field(default_factory=InjectedDataset)

# ====== PATHS (dataclass) ======
@dataclass
class Paths:
    base_dir: Path
    test_case_dir: Path
    test_data_dir: Path
    topolist_path: Path
    output_csv_dir: Path
    output_dir: Path
