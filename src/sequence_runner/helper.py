import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple, Iterable, Optional
import io, base64
import json
# src/sequence_runner/validator.py
import json
from typing import Any, Dict, List

import yaml
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
def _tiny_png_bytes() -> bytes:
    # 1x1 transparent PNG
    _B64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    return base64.b64decode(_B64)
def _read_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        raise FileNotFoundError(f"File not found: {path}")
def _bytes_from_data_url(data_url: str) -> Tuple[str, bytes]:
    head, _, b64 = data_url.partition(",")
    mime = "application/octet-stream"
    if head.startswith("data:"):
        mime = head[5:].split(";")[0] or mime
    ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
    }.get(mime, "bin")
    raw = base64.b64decode(b64)
    return (f"upload.{ext}", raw)

def _split_body_into_form_and_files(body: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, tuple]]:
    """
    Convert JSON body to (form_fields, files) for requests.
    Recognizes file-ish keys and special values:
      - keys: avatar/file/image/upload/attachment
      - 'file:/path.png' → path upload
      - 'dummy:png'      → generate 1x1 PNG bytes
      - 'data:image/...;base64,....' → data URL
      - existing real paths still work
    """
    if not isinstance(body, dict):
        return {}, {}

    form_fields: Dict[str, Any] = {}
    files: Dict[str, tuple] = {}

    for k, v in body.items():
        if isinstance(v, str):
            val = v.strip()

            # data URL inline
            if val.startswith("data:image/"):
                fname, data = _bytes_from_data_url(val)
                files[k] = (fname, io.BytesIO(data))
                continue

            # dummy placeholder image
            if val.lower().startswith("dummy:png"):
                files[k] = ("avatar.png", io.BytesIO(_tiny_png_bytes()))
                continue

            # explicit file path via file:
            if val.startswith("file:"):
                p = Path(val[5:])
                if p.exists() and p.is_file():
                    files[k] = (p.name, p.open("rb"))
                else:
                    # keep as form value; server may reject (useful signal)
                    form_fields[k] = val
                continue

            # bare path string that actually exists
            p = Path(val)
            if p.exists() and p.is_file():
                files[k] = (p.name, p.open("rb"))
                continue

            # not a real file → keep as plain form value
            form_fields[k] = val
            continue

        form_fields[k] = "" if v is None else v

    return form_fields, files
def parse_endpoint_meta( endpoint: str) -> Dict[str, Any]:
    """
    Unified endpoint parser and helper.

    Accepts forms like:
      - 'get-/projects/{id}/branches'
      - '/projects/{id}/branches'
      - 'POST-/api/v1/items/{itemId}'

    Returns a dict with:
      {
        "method": "GET",
        "path": "/projects/{id}/branches",
        "normalized": "get-/projects/{id}/branches",
        "cache_key": "get-_projects__id__branches",
        "has_vars": True,
        "stripped_path": "/projects"
      }
    """
    import re

    # --- Determine method and path ---
    method = "GET"
    path = endpoint
    if "-" in endpoint:
        maybe_method, rest = endpoint.split("-", 1)
        if maybe_method.upper() in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
            method = maybe_method.upper()
            path = rest

    # --- Normalized name (canonical) ---
    normalized = f"{method.lower()}-{path}"

    # --- Detect unresolved path variables ---
    has_vars = bool(re.search(r"\{[^}]+\}", path))

    # --- Strip trailing variable (for preloading convenience) ---
    stripped_path = re.sub(r"/\{[^}]+\}$", "", path)

    # --- Build safe cache key ---
    cache_key = (
        normalized.replace("/", "_")
        .replace("{", "")
        .replace("}", "")
        .strip("_")
    )

    return {
        "method": method,
        "path": path,
        "normalized": normalized,
        "cache_key": cache_key,
        "has_vars": has_vars,
        "stripped_path": stripped_path,
    }
convert_path_fn = lambda x: re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", x))
def get_endpoint_id(swagger_spec, endpoint):
    method = endpoint.split("-")[0]
    path = "-".join(endpoint.split("-")[1:])
    endpoint_spec = swagger_spec["paths"][path][method]
    try:
        operation_id = endpoint_spec["operationId"]
    except:
        operation_id = method.upper()

    unique_name = f"{convert_path_fn(path)}_{operation_id}"
    return unique_name


def _split_endpoint_sig(endpoint_sig: str) -> Tuple[str, str]:
    """'get-/a/b/{id}' -> ('get', '/a/b/{id}')"""
    method = endpoint_sig.split("-")[0].lower()
    path = "-".join(endpoint_sig.split("-")[1:])
    if not path.startswith("/"):
        path = "/" + path
    return method, path
def load_swagger(path):
    '''
    Break the Swagger spec into semantic parts
    ---
    Input:
        path: path to the Swagger spec
    '''
    # Check if file is existed
    if not os.path.exists(path):
        print(f'File {path} is not existed')
        return None
    
    if path.endswith('.yml') or path.endswith('.yaml'):
        # Read YAML file
        with open(path, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    elif path.endswith('.json'):
        # Read JSON file
        with open(path) as f:
            return json.load(f)
    else:
        print(f'File {path} is not supported. Must be in YAML or JSON format.')
        return None