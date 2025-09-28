# src/sequence_runner/parsers.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

from .models import (
    TestCaseCore,
    DataRow,
    InjectedDataset,
    TestCaseWithDataset,
)

JsonLike = Union[str, bytes, Dict[str, Any]]

# ===== Exceptions =====
class ParserError(Exception):
    """Base error for parsing layer."""

class TestCaseJsonError(ParserError):
    pass

class CsvParseError(ParserError):
    pass


# ===== JSON Test Case =====
def parse_test_case_core_from_dict(d: Dict[str, Any]) -> TestCaseCore:
    """
    Nhận dict đã load từ JSON.
    - Chấp nhận trường 'test_case' bọc ngoài (format bạn đang dùng).
    - Bỏ qua mọi field lạ (pydantic StepModel/ResponseValidation đã tự validate).
    - Không yêu cầu 'test_data' trong JSON (nếu có cũng bị lờ đi).
    """
    # Cho phép 2 format: { "test_case": {...} } hoặc {...} trực tiếp
    payload = d.get("test_case", d)

    if not isinstance(payload, dict):
        raise TestCaseJsonError("Invalid JSON structure: 'test_case' must be an object")

    try:
        return TestCaseCore.parse_obj(payload)  # pydantic v1-style, v2 cũng hỗ trợ qua shim
    except Exception as e:
        raise TestCaseJsonError(f"Failed to parse TestCaseCore: {e}") from e


def parse_test_case_core_from_str(s: str) -> TestCaseCore:
    try:
        d = json.loads(s)
    except Exception as e:
        raise TestCaseJsonError(f"Invalid JSON string: {e}") from e
    return parse_test_case_core_from_dict(d)


def parse_test_case_core_from_path(path: Path) -> TestCaseCore:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        raise TestCaseJsonError(f"Cannot read JSON file: {path}: {e}") from e
    return parse_test_case_core_from_str(text)


# ===== CSV → DataRow =====
def _read_csv_rows(fp: TextIO) -> List[Dict[str, Any]]:
    """
    Đọc CSV thành list[dict]. Không ép tên cột; DataRow.from_csv_row sẽ xử lý.
    """
    import csv

    try:
        reader = csv.DictReader(fp)
        return list(reader)
    except Exception as e:
        raise CsvParseError(f"Failed to read CSV: {e}") from e


def parse_csv_to_data_rows(source: Union[Path, TextIO, str]) -> List[DataRow]:
    """
    Nhận:
      - Path tới file CSV
      - File-like (đã mở)
      - Nội dung CSV dạng string
    Trả về: List[DataRow]
    """
    rows: List[Dict[str, Any]]
    close_after = False

    if isinstance(source, Path):
        try:
            # utf-8-sig để ăn BOM nếu có
            fp = source.open("r", encoding="utf-8-sig", newline="")
            close_after = True
        except Exception as e:
            raise CsvParseError(f"Cannot open CSV file: {source}: {e}") from e
        try:
            rows = _read_csv_rows(fp)
        finally:
            if close_after:
                fp.close()

    elif hasattr(source, "read"):
        rows = _read_csv_rows(source)  # type: ignore[arg-type]

    elif isinstance(source, str):
        from io import StringIO
        rows = _read_csv_rows(StringIO(source))

    else:
        raise CsvParseError("Unsupported CSV source type")

    # Map từng dict -> DataRow (giữ extra cột ở DataRow.extra)
    out: List[DataRow] = []
    for r in rows:
        try:
            out.append(DataRow.from_csv_row(r))
        except Exception as e:
            raise CsvParseError(f"Bad CSV row {r}: {e}") from e
    return out


# ===== Compose: TestCase + Dataset =====
def build_dataset(
    param_rows: Optional[List[DataRow]] = None,
    body_rows: Optional[List[DataRow]] = None,
) -> InjectedDataset:
    return InjectedDataset(
        param_rows=param_rows or [],
        body_rows=body_rows or [],
    )


def build_test_case_with_dataset(
    case: TestCaseCore,
    param_rows: Optional[List[DataRow]] = None,
    body_rows: Optional[List[DataRow]] = None,
) -> TestCaseWithDataset:
    """
    Ghép core + dataset (inject từ CSV).
    """
    ds = build_dataset(param_rows, body_rows)
    return TestCaseWithDataset(test_case=case, dataset=ds)


def parse_all_from_files(
    json_path: Path,
    param_csv: Optional[Path] = None,
    body_csv: Optional[Path] = None,
) -> TestCaseWithDataset:
    """
    Một-shot:
      - đọc JSON test case
      - đọc 0..2 file CSV (param/body)
      - trả về TestCaseWithDataset
    """
    case = parse_test_case_core_from_path(json_path)
    pr = parse_csv_to_data_rows(param_csv) if param_csv else []
    br = parse_csv_to_data_rows(body_csv) if body_csv else []
    return build_test_case_with_dataset(case, pr, br)
