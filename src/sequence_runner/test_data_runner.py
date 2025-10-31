from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union
import csv, json, random, hashlib

from sequence_runner.helper import get_endpoint_id


# Minimal TestRow
@dataclass
class TestRow:
    """Represents a single test row loaded from CSV (simple version)."""
    index: str
    data_json: str
    expected_status_code: str
    reason: str

    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> "TestRow":
        """Safely construct a TestRow from a CSV row."""
        return TestRow(
            index=str(row.get("index", "")).strip(),
            data_json=str(row.get("data", "")).strip(),
            expected_status_code=str(row.get("expected_status_code", "")).strip(),
            reason=str(row.get("reason", "")).strip(),
        )


def _read_csv(csv_path: Union[str, Path]) -> List[TestRow]:
    rows: List[TestRow] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(TestRow.from_csv_row(r))
    return rows


def _group_by_code(rows: Sequence[TestRow]) -> Tuple[List[TestRow], List[TestRow]]:
    two_xx = [r for r in rows if str(r.expected_status_code).startswith("2")]
    four_xx = [r for r in rows if not str(r.expected_status_code).startswith("2")]
    return two_xx, four_xx


def _hash_key(r: TestRow, by: Literal["data", "reason", "index"] = "data") -> str:
    if by == "reason":
        payload = r.reason
    elif by == "index":
        payload = r.index
    else:
        payload = r.data_json
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ===========================================================
# TestDataRunner (returns TestRow)
# ===========================================================
class TestDataRunner:
    """Loads CSVs and selects subsets of TestRow data."""

    def __init__(
        self,
        csv_files: Union[str, Path, Sequence[Union[str, Path]]],
        seed: Optional[int] = None,
    ) -> None:
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        if isinstance(csv_files, (str, Path)):
            csv_files = [csv_files]
        self.csv_files = [Path(p) for p in csv_files]

        self.rows: List[TestRow] = []
        for p in self.csv_files:
            if not p.exists():
                raise FileNotFoundError(f"CSV not found: {p}")
            self.rows.extend(_read_csv(p))

    # ---------------------- selection strategies ----------------------

    def select_random_quota(self, want_2xx: int, want_4xx: int, allow_less: bool = True) -> List[TestRow]:
        """Randomly sample N 2xx and M 4xx rows."""
        two_xx, four_xx = _group_by_code(self.rows)

        def _sample(pool: List[TestRow], k: int) -> List[TestRow]:
            if k <= 0:
                return []
            if len(pool) >= k:
                return random.sample(pool, k)
            if not allow_less:
                raise ValueError(f"Requested {k} rows but only {len(pool)} available.")
            return list(pool)

        pick = _sample(two_xx, want_2xx) + _sample(four_xx, want_4xx)
        random.shuffle(pick)
        return pick

    def select_all(self) -> List[TestRow]:
        """Return all available rows."""
        return list(self.rows)

    def select_unique_by(self, total: int, unique_key: Literal["data", "reason", "index"] = "data",
                         prefer: Literal["2xx", "4xx", "none"] = "none") -> List[TestRow]:
        """Keep unique rows by data/reason/index, prefer 2xx or 4xx if specified."""
        chosen: Dict[str, TestRow] = {}
        order: List[TestRow] = list(self.rows)
        if prefer in ("2xx", "4xx"):
            pref_is_2xx = prefer == "2xx"
            order.sort(key=lambda r: (not str(r.expected_status_code).startswith("2")) ^ pref_is_2xx)

        for r in order:
            h = _hash_key(r, by=unique_key)
            if h not in chosen:
                chosen[h] = r
            if len(chosen) >= total:
                break
        out = list(chosen.values())[:total]
        random.shuffle(out)
        return out

    def get_first_2xx_row(self) -> Optional[TestRow]:
        """Return the first TestRow with a 2xx expected status code, or None if none exist."""
        for row in self.rows:
            if str(row.expected_status_code).startswith("2"):
                return row
        return None


# ===========================================================
# Executable data builder for an endpoint
# ===========================================================


def _path_to_slug(path: str) -> str:
    """Convert '/a/{id}/b' -> '_a__id__b' (file-system safe-ish slug)."""
    return path.replace("/", "_").replace("{", "").replace("}", "")


def _build_csv_base_name(method: str, path: str, operation_id: Optional[str]) -> str:
    """
    Filename base used by the generator:
      <path_slug>_<operationId>
    If operation_id is None, fall back to METHOD uppercased.
    """
    slug = _path_to_slug(path)
    op = operation_id.strip() if operation_id else method.upper()
    return f"{slug}_{op}"


def _parse_data_cell_json(row: Optional[TestRow]) -> Optional[dict]:
    """
    Turn a TestRow.data_json into a dict:
      - JSON object -> returned as-is
      - JSON array/primitive -> wrapped under {'data': <value>}
      - invalid/missing -> None
    """
    if row is None or not row.data_json:
        return None
    try:
        obj = json.loads(row.data_json)
        if isinstance(obj, dict):
            return obj
        return {"data": obj}
    except Exception:
        return None


def _pick_first_2xx_row_from_csv(csv_path: Path) -> Optional[TestRow]:
    if not csv_path.exists():
        return None
    try:
        rows = _read_csv(csv_path)
    except Exception:
        return None
    for r in rows:
        if str(r.expected_status_code).strip().lower().startswith("2"):
            return r
    return None



def get_first_2xx_executable_data_for_endpoint(
    endpoint_sig: str,
    swagger_spec: dict,
    csv_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Auto-locate and load CSV test data for the given endpoint.
    Uses your helper `get_endpoint_id` to determine the correct file name.
    """
    # Use your helper to get canonical base name
    base_name = get_endpoint_id(swagger_spec, endpoint_sig)

    if csv_dir is None:
        raise FileNotFoundError("Could not locate CSV directory. Set KAT_CSV_DIR or provide FileService path.")

    param_csv = csv_dir / f"{base_name}_param.csv"
    body_csv  = csv_dir / f"{base_name}_body.csv"

    param_row = _pick_first_2xx_row_from_csv(param_csv)
    body_row  = _pick_first_2xx_row_from_csv(body_csv)

    parameters   = _parse_data_cell_json(param_row)
    request_body = _parse_data_cell_json(body_row)

    return {
        "parameters": parameters,
        "requestBody": request_body,
    }