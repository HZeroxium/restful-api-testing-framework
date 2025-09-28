# src/sequence_runner/validator.py
from __future__ import annotations
import json
from typing import Any, Dict, List
from .models import DataRow, StatusSpec

def _coerce_expected(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return str(int(v))
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return None

def _extract_from_json_str(s: str) -> str | None:
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return _coerce_expected(obj.get("expected_code")) or _coerce_expected(obj.get("expected_status_code"))
    except json.JSONDecodeError:
        pass
    return None

def extract_expected_status(test_data_row: Dict) -> str:
    """
    Ưu tiên:
    row.expected_status_code / expected_code
    → row.param.expected_status_code / expected_code
    → row.body.expected_status_code / expected_code
    → row.param.data(JSON).expected_* / row.body.data(JSON).expected_* / row.data(JSON).expected_*
    → default '2xx'
    """
    if not test_data_row:
        return "2xx"

    # root
    for k in ("expected_status_code", "expected_code"):
        v = _coerce_expected(test_data_row.get(k))
        if v:
            return v

    # nested param/body
    for section in ("param", "body"):
        sec = test_data_row.get(section)
        if isinstance(sec, dict):
            for k in ("expected_status_code", "expected_code"):
                v = _coerce_expected(sec.get(k))
                if v:
                    return v
            # nested data json
            dv = sec.get("data")
            if isinstance(dv, str):
                v = _extract_from_json_str(dv)
                if v:
                    return v

    # root data json
    dv = test_data_row.get("data")
    if isinstance(dv, str):
        v = _extract_from_json_str(dv)
        if v:
            return v

    return "2xx"

def is_status_match(actual_status: int, expected_pattern: str) -> bool:
    if not expected_pattern:
        return True
    p = str(expected_pattern).strip().lower()

    # 2xx / 4xx dạng class
    if len(p) == 3 and p.endswith("xx") and p[0].isdigit():
        return str(actual_status).startswith(p[0])

    # exact number
    if p.isdigit():
        try:
            return actual_status == int(p)
        except ValueError:
            return False

    # range: 200-299
    if "-" in p:
        try:
            left, right = p.split("-", 1)
            return int(left) <= actual_status <= int(right)
        except ValueError:
            return False

    # fallback: coi là 2xx
    return 200 <= actual_status < 300


def extract_expected_status_from_data_row(data_row: DataRow) -> StatusSpec:
    """Extract expected status from DataRow model"""
    if data_row.expected_status_code:
        return data_row.expected_status_code
    
    # Try to extract from data JSON
    try:
        data_dict = data_row.data_dict
        for key in ("expected_status_code", "expected_code"):
            if key in data_dict:
                value = _coerce_expected(data_dict[key])
                if value:
                    return StatusSpec(value=value)
    except Exception:
        pass
    
    return StatusSpec.default_ok()


def validate_status_with_model(actual_status: int, expected_status: StatusSpec) -> bool:
    """Validate status using StatusSpec model"""
    return expected_status.matches(actual_status)
