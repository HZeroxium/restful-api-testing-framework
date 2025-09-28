# src/sequence_runner/data_merge.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple, List
from .models import DataRow, StepModel

logger = logging.getLogger(__name__)

NOT_SURE = "%not-sure%"

def _coerce_scalar(v: Any) -> Any:
    """Chuyển '123'->123, '1.5'->1.5, 'true'/'false'->bool. Giữ '' (empty) nguyên để test."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s == "":
        return v  # giữ nguyên empty string
    # số thực: cho phép đúng 1 dấu chấm
    return v


def _extract_path_vars(src: Dict[str, Any], path_var_names: set,
                       csv_path_vars: Dict[str, Any], not_sure_params: Dict[str, bool]):
    """Trích path vars từ dict 'src' nếu có; nhận diện %not-sure%."""
    for k, v in src.items():
        if k in path_var_names and v is not None:
            if v == NOT_SURE:
                not_sure_params[k] = True
                logger.info(f"  🔍 Found %not-sure% marker for path variable {k}")
            else:
                csv_path_vars[k] = v


def _apply_params(target_params: Dict[str, Any], data: Dict[str, Any], path_var_names: set, where: str):
    """Đưa các cặp key/value (không phải path vars) vào params/body."""
    for k, v in data.items():
        if k in path_var_names:
            continue
        target_params[k] = _coerce_scalar(v)


def merge_test_data(
    base_params: Dict[str, Any],
    base_body: Dict[str, Any],
    test_data_row: Dict[str, Any],
    endpoint: str = "",
    path_vars: Dict[str, Any] | None = None,
    data_for: str = "params",
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, bool]]:
    """
    Hợp nhất dữ liệu test row vào params/body.

    Ưu tiên:
      - Path vars từ CSV (kể cả trong 'data' JSON) -> trả về ở csv_path_vars
      - %not-sure% trên path vars -> trả về ở not_sure_params (để resolver xử lý tiếp)
      - Không ghi đè path vars vào params/body (tránh trùng)
      - Giữ empty string trong query (để test), loại None khỏi query

    Trả về:
      merged_params, merged_body, csv_path_vars, not_sure_params
    """
    merged_params = dict(base_params or {})
    merged_body = dict(base_body or {})
    path_var_names = set((path_vars or {}).keys())

    csv_path_vars: Dict[str, Any] = {}
    not_sure_params: Dict[str, bool] = {}

    if not test_data_row:
        return merged_params, merged_body, csv_path_vars, not_sure_params

    metadata_fields = {"index", "expected_status_code", "expected_code", "reason"}

    def apply_kv(k: str, v: Any, target: str):
        v = _coerce_scalar(v)
        if target == "params":
            merged_params[k] = v
        else:
            merged_body[k] = v

    # --- Trường hợp nested {"param": {...}, "body": {...}} ---
    if "param" in test_data_row or "body" in test_data_row:
        logger.info("  📋 Processing nested test data structure (param/body)")

        # param block
        param_block = test_data_row.get("param") or {}
        for k, v in param_block.items():
            if k in metadata_fields or k is None or v is None:
                continue
            if k == "data" and isinstance(v, str):
                # v là JSON string -> bung ra
                try:
                    obj = json.loads(v)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON in nested param.data: {v[:120]}")
                    continue
                if isinstance(obj, dict):
                    # Ưu tiên obj["data"] nếu có
                    payload = obj.get("data", obj)
                    if isinstance(payload, dict):
                        _extract_path_vars(payload, path_var_names, csv_path_vars, not_sure_params)
                        _apply_params(merged_params, payload, path_var_names, where="params")
                continue

            # thường
            if k in path_var_names:
                csv_path_vars[k] = v
            else:
                apply_kv(k, v, "params")

        # body block
        body_block = test_data_row.get("body") or {}
        for k, v in body_block.items():
            if k in metadata_fields or k is None or v is None:
                continue
            if k in path_var_names:
                # path var không đổ vào body
                csv_path_vars[k] = v
                continue
            if k == "data" and isinstance(v, str):
                try:
                    obj = json.loads(v)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON in nested body.data: {v[:120]}")
                    continue
                if isinstance(obj, dict):
                    payload = obj.get("data", obj)
                    if isinstance(payload, dict):
                        _extract_path_vars(payload, path_var_names, csv_path_vars, not_sure_params)
                        _apply_params(merged_body, payload, path_var_names, where="body")
                continue
            apply_kv(k, v, "body")

        return merged_params, merged_body, csv_path_vars, not_sure_params

    # --- Trường hợp flat row (không có 'param'/'body') ---
    for k, v in test_data_row.items():
        if k in metadata_fields or k is None or v is None:
            continue
        if k == "data" and isinstance(v, str):
            try:
                obj = json.loads(v)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON in data: {v[:120]}")
                continue
            if isinstance(obj, dict):
                payload = obj.get("data", obj)
                if isinstance(payload, dict):
                    _extract_path_vars(payload, path_var_names, csv_path_vars, not_sure_params)
                    if data_for == "params":
                        _apply_params(merged_params, payload, path_var_names, where="params")
                    else:
                        _apply_params(merged_body, payload, path_var_names, where="body")
            continue

        # cặp key/value trực tiếp
        if k in path_var_names:
            csv_path_vars[k] = v
            continue
        apply_kv(k, v, data_for)

    # Lọc param để bỏ None nếu không đến từ test data (giữ empty string để test)
    # (ở đây merged_params đã được coerce; None chỉ còn từ base_params)
    merged_params = {k: v for k, v in merged_params.items() if v is not None}

    return merged_params, merged_body, csv_path_vars, not_sure_params


def merge_test_data_with_models(
    step: StepModel,
    data_rows: List[DataRow],
    data_for: str = "params",
) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, bool]]]:
    """
    Merge test data using models. 
    Returns list of (merged_params, merged_body, csv_path_vars, not_sure_params) for each data row.
    """
    results = []
    
    for data_row in data_rows:
        # Convert DataRow to dict format for existing merge function
        test_data_dict = {
            "index": data_row.index,
            "data": data_row.data,
            "expected_status_code": str(data_row.expected_status_code.value) if data_row.expected_status_code else None,
            "reason": data_row.reason,
            **data_row.extra
        }
        
        result = merge_test_data(
            step.query_parameters,
            step.request_body,
            test_data_dict,
            step.endpoint,
            step.path_variables,
            data_for=data_for
        )
        results.append(result)
    
    return results
