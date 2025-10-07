# src/sequence_runner/url_builder.py
from __future__ import annotations

import re
from typing import Dict, List, Tuple, Any
from urllib.parse import urlencode
import json

_METHOD_PREFIX = re.compile(r"^(get|post|put|delete|patch)-", re.IGNORECASE)
_PATH_VARS = re.compile(r"\{(\w+)\}")

def clean_endpoint(endpoint: str) -> str:
    """
    Loại bỏ tiền tố method kiểu 'get-/path' → '/path'.
    Không động chạm nội dung còn lại.
    """
    return _METHOD_PREFIX.sub("", endpoint or "")

def required_path_vars(cleaned_endpoint: str) -> List[str]:
    """Trả về danh sách biến path bắt buộc: ['billId', ...]."""
    return _PATH_VARS.findall(cleaned_endpoint or "")

def substitute_path_vars(cleaned_endpoint: str, path_vars: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Thay thế {var} bằng giá trị trong path_vars (bỏ qua nếu None).
    Trả về (final_endpoint, still_unresolved_vars).
    """
    final_endpoint = cleaned_endpoint
    unresolved = []
    for var in required_path_vars(cleaned_endpoint):
        val = path_vars.get(var, None)
        if val is None:
            unresolved.append(var)
            continue
        final_endpoint = final_endpoint.replace(f"{{{var}}}", str(val))
    # Nếu còn pattern {var} -> vẫn coi là unresolved
    # (phòng trường hợp path_vars[var] là None hoặc thiếu key)
    leftover = _PATH_VARS.findall(final_endpoint)
    unresolved = list(set(unresolved + leftover))
    return final_endpoint, unresolved

def _coerce_for_query(v: Any) -> str:
    """
    Chuyển giá trị sang chuỗi query:
    - None: raise (để caller lọc trước)
    - "", giữ nguyên rỗng
    - bool/int/float/str: str(v)
    - list/tuple/dict/khác: json.dumps (để không mất dữ liệu)
    """
    if v is None:
        raise ValueError("None is not allowed for query values")
    if isinstance(v, str):
        return v  # giữ "" nếu có
    if isinstance(v, (bool, int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)

def build_urls(
    base_url: str,
    final_endpoint: str,
    params: Dict[str, Any] | None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Dựng URL:
    - base_with_path: base_url + final_endpoint
    - full_with_query: + '?' + query nếu có
    - cleaned_params: đã loại None, giữ "".
      * list values -> doseq (k=a&k=b)
    """
    base_with_path = f"{base_url.rstrip('/')}{final_endpoint}"
    if not params:
        return base_with_path, base_with_path, {}

    cleaned: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue  # bỏ None
        cleaned[k] = v

    # Chuẩn hoá value trước khi encode
    pairs: List[Tuple[str, str]] = []
    for k, v in cleaned.items():
        if isinstance(v, (list, tuple)):
            for item in v:
                if item is None:
                    continue
                pairs.append((k, _coerce_for_query(item)))
        else:
            pairs.append((k, _coerce_for_query(v)))

    if pairs:
        query = urlencode(pairs, doseq=True)
        full = f"{base_with_path}?{query}"
    else:
        full = base_with_path

    return base_with_path, full, cleaned
