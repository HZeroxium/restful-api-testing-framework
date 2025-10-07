from __future__ import annotations
import re
from typing import Optional
from pydantic import BaseModel, validator

_STATUS_RE = re.compile(
    r"^(?:[1-5]xx|[1-5]\d{2}|[1-5]\d{2}-[1-5]\d{2})$",
    re.IGNORECASE,
)

class StatusSpec(BaseModel):
    """
    Chuẩn hoá expected status: '2xx' | '404' | '200-299'.
    Không ràng buộc logic service. Dùng .matches(actual) để assert.
    """
    value: Optional[str] = None  # None => ngầm định '2xx'

    @validator("value", pre=True)
    def _normalize(cls, v):
        if v is None or str(v).strip() == "":
            return None
        v = str(v).strip().lower()
        if not _STATUS_RE.match(v):
            raise ValueError(f"Invalid expected_status_code format: {v}")
        return v

    def matches(self, actual_status: int) -> bool:
        if self.value is None:
            return 200 <= actual_status < 300
        v = self.value
        if v.endswith("xx"):
            return v[0] == str(actual_status)[0]
        if "-" in v:
            a, b = v.split("-")
            return int(a) <= actual_status <= int(b)
        return int(v) == actual_status

    @classmethod
    def default_ok(cls) -> "StatusSpec":
        return cls(value=None)  # nghĩa là 2xx mặc định
