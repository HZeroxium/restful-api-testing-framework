# kat/data_endpoint_dependency.py
from __future__ import annotations

import csv
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional as TypingOptional
from urllib.parse import urlparse

from pyparsing import Optional
import requests

from kat.data_generator.models import EndpointCache, LoadedArtifacts, DependencyBlock, DependencyContext


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)




class DataEndpointDependency:
    DEFAULT_CONFIG: Dict[str, Any] = {
        "cache_file": "_dep_cache.json",
        "log_level": "INFO",
    }
    def __init__(
        self,
        odg_dir: str,
        config: Dict[str, Any] | None = None,
        swagger_spec: dict  | None = None,
        artifacts: LoadedArtifacts | None = None,
        csv_dir: str | None = None,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self.headers = headers 
        self.workdir: Path = Path(odg_dir)
        self.config: Dict[str, Any] = {**self.DEFAULT_CONFIG, **(config or {})}
        self.swagger_spec: dict = swagger_spec
        self.artifacts: LoadedArtifacts | None = artifacts
        self.csv_dir: Path = Path(csv_dir)
        self.cache: list[EndpointCache] = self.load_cache()
        # setup logging level
        try:
            logger.setLevel(getattr(logging, str(self.config["log_level"]).upper(), logging.INFO))
        except Exception:
            logger.setLevel(logging.INFO)

        # artifact paths



    # ---------- Public API ----------
    # ---------- RESPONSE SCHEMA & TRIM SINGLETON ----------
    def load_cache(self) -> list[EndpointCache]:
        """
        Scan <workdir>/cache for *.json files, load them into memory, and return
        a list[EndpointCache]. Also stores a fast lookup dict on self.cache_index.

        Endpoint resolution strategy:
        1) If cache JSON contains request.method + request.url, try to infer
            endpoint_sig by matching the URL path to a swagger path template.
        2) Otherwise, use the filename stem (without '-response_cache') as a
            fallback endpoint identifier (sanitized name).

        Returns
        -------
        List[EndpointCache]
        """
        cache_dir = self.workdir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        def _filename_to_hint(p: Path) -> str:
            name = p.stem  # e.g., "get-_api_v1_Bills_-response_cache" or "get-_api_v1_Bills-..."
            # strip a known suffix, if present
            if name.endswith("-response_cache"):
                name = name[: -len("-response_cache")]
            return name

        def _infer_from_request(obj: dict) -> str | None:
            """
            Try to reconstruct endpoint_sig from cached request info + swagger spec.
            """
            try:
                req = obj.get("request") or {}
                method = (req.get("method") or "").lower()
                url = req.get("url") or ""
                if not method or not url or not isinstance(self.swagger_spec, dict):
                    return None

                # actual path in the real call
                path_actual = urlparse(url).path

                # iterate swagger paths and find a template that matches the concrete path
                paths = (self.swagger_spec.get("paths") or {}).keys()
                for template in paths:
                    # convert swagger template "/a/{id}/b" to regex "^/a/[^/]+/b$"
                    pattern = "^" + re.sub(r"\{[^/}]+\}", r"[^/]+", template) + "$"
                    if re.match(pattern, path_actual):
                        return f"{method}-{template}"
                return None
            except Exception:
                return None

        entries: list[EndpointCache] = []
        cache_index: dict[str, dict] = {}

        for f in sorted(cache_dir.glob("*.json")):
            try:
                with f.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except Exception as e:
                logger.warning("Skipping unreadable cache file %s: %s", f, e)
                continue

            endpoint_sig = _infer_from_request(payload)
            if not endpoint_sig:
                endpoint_sig = _filename_to_hint(f)

            entries.append(EndpointCache(endpoint=endpoint_sig, cache=payload))
            cache_index[endpoint_sig] = payload

        # keep an in-memory index for fast lookups (doesn't clash with your existing attributes)
        self.cache_index = cache_index

        logger.info("Loaded %d cache entries from %s", len(entries), cache_dir)
        return entries



    def _deref(self, schema: dict) -> dict:
        """Deref 1 cấp nếu có $ref; nếu không, trả chính schema."""
        if not isinstance(schema, dict):
            return schema
        ref = schema.get("$ref")
        if not ref:
            return schema
        # $ref dạng "#/components/schemas/X" hoặc "#/definitions/X"
        try:
            sub = ref.lstrip("#/").split("/")
            cur = self.swagger_spec
            for k in sub:
                cur = cur[k]
            return cur if isinstance(cur, dict) else schema
        except Exception:
            return schema

    def _collect_first_2xx_resp(self, responses: dict) -> tuple[str, dict] | tuple[None, None]:
        """
        Tìm response code ưu tiên: 200 trước, nếu không có thì 2xx đầu tiên.
        Trả (code, respObj)
        """
        if not isinstance(responses, dict):
            return (None, None)
        if "200" in responses:
            return ("200", responses["200"])
        for code, obj in responses.items():
            try:
                c = int(code)
                if 200 <= c < 300:
                    return (code, obj)
            except Exception:
                continue
        return (None, None)

    def _preferred_json_response(self, resp_obj: dict) -> dict | None:
        """
        Từ 1 resp object (OpenAPI v3), chọn content 'application/json' (hoặc json-like đầu tiên).
        Trả về schema (có thể vẫn còn $ref).
        """
        if not isinstance(resp_obj, dict):
            return None
        content = resp_obj.get("content") or {}
        if "application/json" in content:
            return content["application/json"].get("schema")
        # json-like khác
        for mt, val in content.items():
            if isinstance(mt, str) and ("json" in mt or mt.endswith("+json")):
                return (val or {}).get("schema")
        # swagger 2.0 (resp_obj có thể đã là schema)
        schema = resp_obj.get("schema")
        return schema

    def _get_response_schema_core(self, method: str, path: str) -> dict | None:
        """
        Core: từ (method, path) → lấy schema JSON cho response 200/2xx.
        """
        try:
            op = (self.swagger_spec.get("paths", {}) or {}).get(path, {}) \
                    .get(method.lower(), {}) or {}
            responses = op.get("responses") or {}
            _, resp_obj = self._collect_first_2xx_resp(responses)
            if not resp_obj:
                return None
            schema = self._preferred_json_response(resp_obj)
            if not schema:
                return None
            return self._deref(schema)
        except Exception:
            return None

    def get_json_response_schema(self, endpoint_sig: str) -> dict | None:
        """
        Public: lấy schema JSON đã deref cho response 200/2xx của endpoint.
        """
        method, path = self._split_endpoint_sig(endpoint_sig)
        return self._get_response_schema_core(method, path)

    def _trim_by_schema(self, data: Any, schema: dict) -> Any:
        """
        Đi đệ quy theo schema:
        - Nếu schema.type == 'array': giữ tối đa 1 phần tử (index 0) và trim theo items.
        - Nếu schema.type == 'object': trim từng field theo properties; có additionalProperties thì áp dụng lên từng value.
        - Nếu primitive hoặc schema không rõ: trả nguyên data.
        """
        if not isinstance(schema, dict):
            return data

        # Deref 1 lần cho node hiện tại
        schema = self._deref(schema)
        stype = schema.get("type")

        # Trường hợp oneOf/anyOf/allOf: chọn nhánh đầu tiên có type, để tối giản
        for comb in ("oneOf", "anyOf", "allOf"):
            if comb in schema and isinstance(schema[comb], list) and schema[comb]:
                # lấy nhánh đầu tiên rồi tiếp tục
                return self._trim_by_schema(data, self._deref(schema[comb][0]))

        if stype == "array":
            items_schema = self._deref(schema.get("items") or {})
            if isinstance(data, list) and data:
                first = data[0]
                return [self._trim_by_schema(first, items_schema)]
            else:
                # không phải list hoặc rỗng → trả list rỗng (tối thiểu)
                return []

        if stype == "object":
            if not isinstance(data, dict):
                return data  # không ép kiểu, giữ nguyên
            props = schema.get("properties") or {}
            addl  = schema.get("additionalProperties", None)

            out = {}
            # chỉ giữ các key tồn tại trong data; trim theo schema từng field
            for k, v in data.items():
                if k in props:
                    out[k] = self._trim_by_schema(v, self._deref(props[k]))
                elif isinstance(addl, dict):
                    out[k] = self._trim_by_schema(v, self._deref(addl))
                else:
                    # nếu không có schema cho field này, giữ nguyên v ngắn gọn
                    out[k] = v
            return out

        # primitives hoặc không có type
        return data

    def trim_response_to_singleton(self, endpoint_sig: str, data: Any) -> Any:
        """
        Public: Trim dữ liệu response của endpoint về dạng 'singleton' theo schema:
        - Nếu response là array → chỉ giữ phần tử đầu tiên (đã trim đệ quy).
        - Bên trong object, mọi field kiểu array cũng chỉ giữ 1 phần tử.
        """
        schema = self.get_json_response_schema(endpoint_sig)
        if not schema:
            # Không tìm thấy schema → trả nguyên data (không dám đoán)
            return data
        return self._trim_by_schema(data, schema)

    # ---------- Helpers ----------


    def _schemas_for_endpoint(self, endpoint_sig: str) -> List[str]:
        """
        Trả về danh sách schema liên quan đến endpoint từ artifacts.endpoint_schema_dependencies.
        endpoint_schema_dependencies có dạng:
            { endpointSig: { "SchemaA": {...paramMap...}, "SchemaB": {...} } }
        → trả keys = ["SchemaA", "SchemaB"]
        """
        if not self.artifacts:
            return []
        deps = self.artifacts.endpoint_schema_dependencies.get(endpoint_sig, {})
        if isinstance(deps, dict):
            return list(deps.keys())
        return []
    def _producer_endpoints_for(self, endpoint_sig: str) -> List[str]:
        """
        Lấy chuỗi phụ thuộc đầu tiên (first chain) từ operation_sequences[endpoint_sig].
        Nếu không có, trả về [].
        - Giữ nguyên trật tự trong chain đầu tiên.
        - Bỏ endpoint đích (endpoint_sig) nếu nó xuất hiện cuối cùng.
        """
        if not self.artifacts:
            return []

        seqs = self.artifacts.operation_sequences.get(endpoint_sig)
        if not seqs or not isinstance(seqs, list):
            return []

        # Lấy chain đầu tiên
        first_chain = None
        for chain in seqs:
            if isinstance(chain, list) and chain:
                first_chain = chain
                break
        if not first_chain:
            return []

        # Bỏ endpoint đích nếu nó nằm cuối
        producers = list(first_chain)
        if producers and producers[-1] == endpoint_sig:
            producers = producers[:-1]

        return producers
# --- add inside class DataEndpointDependency ---

    def _safe_endpoint_sig(self, endpoint_sig: str) -> str:
        """
        Chuyển endpoint_sig thành tên file an toàn:
        - thay mọi ký tự không phải [A-Za-z0-9_.-] bằng '_'
        """
        return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in endpoint_sig)

    def _cache_file_for_endpoint(self, endpoint_sig: str) -> Path:
        """
        Trả về đường dẫn file cache theo format:
        <workdir>/cache/<sanitized-endpoint>-response_cache.json
        """
        cache_dir = self.workdir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{self._safe_endpoint_sig(endpoint_sig)}-response_cache.json"
        return cache_dir / fname
    def _get_base_url(self) -> str:
        """
        Lấy base URL từ swagger:
        - OpenAPI 3.x: spec["servers"][0]["url"]
        - Swagger 2.0: schemes[0]://host + basePath
        """
        spec = getattr(self, "swagger_spec", None) or {}
        # OpenAPI 3.x
        servers = spec.get("servers")
        if isinstance(servers, list) and servers:
            url = servers[0].get("url", "").strip()
            return url.rstrip("/")
        # Swagger 2.0
        host = spec.get("host")
        base_path = spec.get("basePath", "") or ""
        schemes = spec.get("schemes", []) or ["https"]
        if host:
            scheme = schemes[0] if schemes else "https"
            return f"{scheme}://{host}{base_path}".rstrip("/")
        # Fallback
        return ""

    def get_ref(spec: dict, ref: str):
        sub = ref[2:].split('/')
        schema = spec
        for e in sub:
            schema = schema.get(e, {})
        return schema

    def _get_endpoint_param_locs(self, method: str, path: str) -> dict:
        """
        Trả về mapping tên-param → 'path'|'query'|'header'|'cookie' theo swagger.
        """
        locs = {}
        try:
            ep = self.swagger_spec["paths"][path][method]
            params = ep.get("parameters", []) or []
            for p in params:
                # resolve $ref nếu có
                if "$ref" in p:
                    p = self.get_ref(self.swagger_spec, p["$ref"])
                name = p.get("name")
                pin = p.get("in")
                if name and pin:
                    locs[name] = pin.lower()
        except Exception:
            pass
        return locs

    def _apply_path_params(self, path: str, path_params: dict) -> str:
        """
        Thay các {name} trong path bằng str(value).
        """
        out = path
        for k, v in (path_params or {}).items():
            out = out.replace("{"+k+"}", str(v))
        return out

    # ---- helpers: minimal request extraction ------------------------------------
    def _merged_params(self, path: str, method: str):
        """Path-level params + op-level params (op override)."""
        path_item = (self.swagger_spec.get('paths', {}) or {}).get(path, {}) or {}
        op_obj    = (path_item.get(method.lower(), {}) or {})
        merged = {}
        for p in (path_item.get('parameters', []) or []) + (op_obj.get('parameters', []) or []):
            key = (p.get('name'), p.get('in'))
            merged[key] = p
        return list(merged.values())

    def _get_request_body_schema(self, path: str, method: str):
        """Resolve requestBody schema object (dereferenced)."""
        op = (self.swagger_spec.get('paths', {}) or {}).get(path, {}) \
            .get(method.lower(), {}) or {}
        rb = (op.get('requestBody') or {})
        if not rb:
            return None
        # OpenAPI v3 content
        content = rb.get('content') or {}
        # prefer application/json
        for mt in ['application/json', 'application/*+json']:
            if mt in content:
                schema = content[mt].get('schema') or {}
                break
        else:
        # any first content
            if content:
                schema = next(iter(content.values())).get('schema', {}) or {}
            else:
                schema = rb.get('schema', {}) or {}

        # $ref → deref
        from kat.utils.swagger_utils.swagger_utils import find_object_with_key, get_ref
        ref = find_object_with_key(schema, '$ref')
        return get_ref(self.swagger_spec, ref['$ref']) if ref else schema

    def _prune_body_to_required(self, body: dict, schema: dict):
        """
        Trả về một bản sao của body CHỈ gồm các field required (đệ quy).
        Nếu field required không có trong body thì bỏ qua (không tự synthesize).
        """
        if not isinstance(body, dict) or not isinstance(schema, dict):
            return body

        required = set(schema.get('required') or [])
        props    = schema.get('properties') or {}
        minimal  = {}

        # luôn giữ các field required; nếu có nested object thì prune đệ quy
        for name in required:
            if name not in body:
                continue
            val = body[name]
            sch = props.get(name, {})
            if isinstance(val, dict) and isinstance(sch, dict) and sch.get('type') == 'object':
                minimal[name] = self._prune_body_to_required(val, sch)
            elif isinstance(val, list) and isinstance(sch, dict) and sch.get('type') == 'array':
                item_sch = (sch.get('items') or {})
                pruned = []
                for item in val:
                    pruned.append(self._prune_body_to_required(item, item_sch) if isinstance(item, dict) else item)
                minimal[name] = pruned
            else:
                minimal[name] = val

        return minimal

    def _build_minimal_request_parts(self, endpoint_sig: str, exec_data: dict):
        method, raw_path = self._split_endpoint_sig(endpoint_sig)

        params_spec   = self._merged_params(raw_path, method)
        path_params   = {}
        query_params  = {}
        header_params = dict(self.headers)  # copy so we don't mutate self.headers
        cookie_params = {}

        provided = exec_data.get('parameters') or {}

        for p in params_spec:
            name = p.get('name')
            loc  = p.get('in')
            reqd = bool(p.get('required'))
            if loc == 'path' and name in provided:
                path_params[name] = provided[name]
            elif reqd and name in provided:
                if loc == 'query':
                    query_params[name] = provided[name]
                elif loc == 'header':
                    header_params[name] = provided[name]
                elif loc == 'cookie':
                    cookie_params[name] = provided[name]

        # optional: drop accidental None values
        header_params = {k: v for k, v in header_params.items() if v is not None}

        json_body = None
        if exec_data.get('requestBody') is not None:
            json_body = exec_data['requestBody']

        return path_params, query_params, header_params, cookie_params, json_body

    def call_api_to_get_data_for_ep(self, endpoint_sig: str):
        """
        Gọi API thật dựa trên swagger 'servers' (hoặc host/basePath) và chỉ gửi *tối thiểu cần thiết*:
        - Path params
        - Các query/header/cookie param có required=true
        - Request body chỉ gồm các field required theo schema
        """
        exec_data = self.get_executable_data_for_endpoint(endpoint_sig)
        if not exec_data or (exec_data.get("parameters") is None and exec_data.get("requestBody") is None):
            logger.info("No executable data found for %s", endpoint_sig)
            return None

        method, raw_path = self._split_endpoint_sig(endpoint_sig)
        base_url = self._get_base_url()
        if not base_url:
            logger.warning("Base URL not found in swagger spec.")
            return None

        # Chỉ lấy phần tối thiểu
        (path_params, query_params, header_params, cookie_params, json_body) = \
            self._build_minimal_request_parts(endpoint_sig, exec_data)

        # Thay path params
        final_path = self._apply_path_params(raw_path, path_params)
        url = f"{base_url}{final_path}"

        try:
            import requests
            resp = requests.request(
                method=method.upper(),
                url=url,
                params=query_params or None,        # để requests tự encode
                json=json_body if method.upper() in ("POST","PUT","PATCH") else None,
                headers=header_params or None,
                cookies=cookie_params or None,
                timeout=30,
            )

            logger.info(
                "Called api : %s %s | query=%s headers=%s body=%s",
                method.upper(), url, query_params, header_params, json_body
            )
        except Exception as e:
            logger.warning("HTTP call failed for %s: %s", endpoint_sig, e)
            return None

        try:
            content = resp.json()
            # Chỉ trim nếu là JSON-like (list/dict)
            if isinstance(content, (dict, list)):
                content = self.trim_response_to_singleton(endpoint_sig, content)
        except ValueError:
            # Không phải JSON → giữ nguyên text
            content = resp.text

        cached_obj = {
            "status": resp.status_code,
            "body": content,
            "request": {
                "method": method.upper(),
                "url": url,
                "params": query_params or {},
                "path_params": path_params or {},
                "headers": header_params or {},
                "cookies": cookie_params or {},
                "json": json_body if method.upper() in ("POST","PUT","PATCH") else None,
            },
        }

        cache_path = self._cache_file_for_endpoint(endpoint_sig)
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                import json as _json
                _json.dump(cached_obj, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to write cache file %s: %s", cache_path, e)

        return cached_obj


    def _load_csv_rows(self, csv_path: Path) -> List[Dict[str, Any]]:
        if not csv_path.exists():
            return []
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                return [dict(r) for r in reader]
        except Exception as e:
            logger.warning("Failed to read CSV %s: %s", csv_path, e)
            return []

    def _is_success_code_value(self, v: Any) -> bool:
        try:
            s = str(v).strip().lower()
            if s.endswith("xx"):
                return s.startswith("2")  # "2xx"
            num = int(s)
            return 200 <= num < 300
        except Exception:
            return False

    def _pick_first_2xx_row(self, rows: List[Dict[str, Any]]) -> TypingOptional[Dict[str, Any]]:
        if not rows:
            return None
        # Tên cột theo generator: "expected_status_code"
        candidates = ("expected_status_code", "expected_code", "expectedCode", "expected-status", "expectedStatus")
        for row in rows:
            val = None
            for k in candidates:
                if k in row and row[k] not in (None, ""):
                    val = row[k]
                    break
            if val is not None and self._is_success_code_value(val):
                return row
        return None

    def _parse_data_cell(self, row: Dict[str, Any]) -> TypingOptional[dict]:
        """
        Parse cột 'data' (JSON string) thành dict; nếu không phải dict thì bọc lại {"data": ...}.
        """
        if not row or "data" not in row or row["data"] in (None, ""):
            return None
        try:
            obj = json.loads(row["data"])
            if isinstance(obj, dict):
                return obj
            return {"data": obj}
        except Exception as e:
            logger.warning("Invalid JSON in 'data' cell: %s ; err=%s", row.get("data"), e)
            return None
    
    def _get_data_file_basename(self, method: str, path: str, part: str) -> str:
        """
        Chuẩn: f"{convert_path_fn(path)}_{operationId}_{part}"
        KHÔNG kèm '.csv'
        """
        op_id = self._get_operation_id(method, path)
        endpoint_id = f"{self.convert_path_fn(path)}_{op_id}"
        return f"{endpoint_id}_{part}"
    def convert_path_fn(self, path):
        """Convert path to function name format."""
        return path.replace('/', '_').replace('{', '').replace('}', '')

    def get_executable_data_for_endpoint(self, endpoint_sig: str) -> Dict[str, Any]:
        """
        Trả về:
            {
            "parameters": dict|None,
            "requestBody": dict|None
            }

        Nguồn: CSV do generator tạo, lấy dòng đầu tiên có expected_status_code thuộc 2xx.
        Nếu không tìm thấy dữ liệu hợp lệ → raise RuntimeError.
        """
        method, path = self._split_endpoint_sig(endpoint_sig)
        csv_dir = self.csv_dir

        # --- Build tên file ---
        param_name = self._get_data_file_basename(method, path, "param") + ".csv"
        body_name = self._get_data_file_basename(method, path, "body") + ".csv"

        param_csv = csv_dir / param_name
        body_csv = csv_dir / body_name

        logger.info("Trying to load test data CSV for endpoint %s", endpoint_sig)
        logger.info("  Param CSV: %s", param_csv)
        logger.info("  Body  CSV: %s", body_csv)

        # --- Đọc CSV ---
        p_rows = self._load_csv_rows(param_csv)
        b_rows = self._load_csv_rows(body_csv)

        # --- Chọn dòng 2xx ---
        p_row_2xx = self._pick_first_2xx_row(p_rows)
        b_row_2xx = self._pick_first_2xx_row(b_rows)

        parameters = self._parse_data_cell(p_row_2xx) if p_row_2xx else None
        request_body = self._parse_data_cell(b_row_2xx) if b_row_2xx else None

        # --- Nếu không có bất kỳ dữ liệu nào hợp lệ → QUĂNG LỖI ---
        if parameters is None and request_body is None:
            msg = (
                f"No executable test data found for endpoint '{endpoint_sig}'. "
                f"Tried files:\n  - {param_csv}\n  - {body_csv}\n"
                f"Make sure the CSV exists and has at least one row with a 2xx expected status code."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        return {"parameters": parameters, "requestBody": request_body}


    def get_data_for_endpoint(self, endpoint_sig: str):
        """
        Lấy dữ liệu upstream cho một endpoint:
          1) Ưu tiên lấy từ in-memory cache (artifacts.cache).
          2) Nếu chưa có, thử đọc file <odg_dir>/cache/<endpoint>-response_cache.json.
          3) Nếu vẫn chưa có, gọi call_api_to_get_data_for_ep() (stub hiện tại).
             Nếu có data, ghi lại vào cả in-memory lẫn file cache.

        Trả về: JSON-serializable object hoặc None nếu không có.
        """
        # 1) in-memory cache (nếu load_artifacts() đã gọi)
        if self.cache and isinstance(self.cache, list):
            for entry in self.cache:
                if entry.endpoint == endpoint_sig:
                    logger.info("Found in-memory cache for %s", endpoint_sig)
                    return entry.cache

        # 2) file cache
        logger.info("No in-memory cache for %s, checking file cache...", endpoint_sig)
        cache_path = self._cache_file_for_endpoint(endpoint_sig)
        logger.info("Cache file path: %s", cache_path)
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # đồng bộ vào in-memory cache
                if self.cache is not None:
                    new_entry = EndpointCache(endpoint=endpoint_sig, cache=data)
                    self.cache.append(new_entry)
                logger.info("Loaded file cache for %s", endpoint_sig)
                return data
            except Exception as e:
                logger.warning("Failed to read cache file %s: %s", cache_path, e)
        logger.info("No file cache found for %s", endpoint_sig)
        try:
            # 3) gọi API thật
            logger.info("No cache found for %s, calling API...", endpoint_sig)
            data = self.call_api_to_get_data_for_ep(endpoint_sig)
        except Exception as e:
            logger.warning("call_api_to_get_data_for_ep(%s) raised: %s", endpoint_sig, e)
            data = None

        # Nếu có data, ghi lại cache
        if data is not None:
            # update in-memory
            if self.cache is not None:
                new_entry = EndpointCache(endpoint=endpoint_sig, cache=data)
                self.cache.append(new_entry)
            # update file
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("Failed to write cache file %s: %s", cache_path, e)

        return data
    def _minify(self, obj: Any) -> str:
        """
        json.dumps dạng minify. Nếu obj không phải JSON-serializable, chuyển sang string trước.
        """
        try:
            return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            try:
                return json.dumps(str(obj), ensure_ascii=False, separators=(",", ":"))
            except Exception:
                return "{}"
    def _pick_cached_object(self, cache_entry: Any) -> TypingOptional[dict]:
        """
        Lấy 1 object đại diện (dict) từ cache entry (có thể là dict/list/str...).
        - Nếu là list: tìm phần tử đầu tiên là dict
        - Nếu là dict: dùng luôn
        - Nếu kiểu khác: bỏ qua (chưa hỗ trợ)
        """
        if isinstance(cache_entry, dict):
            return cache_entry
        if isinstance(cache_entry, list):
            for item in cache_entry:
                if isinstance(item, dict):
                    return item
        return None
    def get_endpoints_dependency_data(self, endpoint_sig: str) -> DependencyContext:
        """
        Lấy context (schemas + upstream blocks) để cung cấp cho prompt của một endpoint cụ thể.

        Parameters
        ----------
        endpoint_sig : str
            Chữ ký endpoint, định dạng: "<method>-<path>".
            Ví dụ: "get-/api/v1/Bills/{billId}/Stages/{stageId}/Publications"

        Returns
        -------
        DependencyContext
            - schemas: List[str]
                Danh sách schema mà endpoint này phụ thuộc (lấy từ
                endpoint_schema_dependencies nếu có, hoặc dùng heuristic từ path).
            - blocks: List[DependencyBlock]
                Danh sách tối giản các mẫu dữ liệu upstream (mỗi block gắn với một schema),
                định dạng:
                DependencyBlock(
                    endpoint="<producer-endpoint-sig hoặc '(cached)'>",
                    schema="<SchemaName hoặc None>",
                    json="<chuỗi JSON minified cho 1 object đại diện>"
                )

        Notes
        -----
        - Hàm này là entry point dùng cho LLM prompt builder.
        - Phiên bản tối thiểu dưới đây chỉ dựng khung đầu vào/đầu ra:
        * Nếu chưa có implement đầy đủ, sẽ trả về context rỗng nhưng đúng format.
        * Bạn có thể thay thế phần 'TODO' bằng logic thật (ensure upstream, cache, compact).
        """
        # Lấy danh sách schemas cho endpoint (nếu có trong artifacts), fallback heuristic.
        schemas = self._schemas_for_endpoint(endpoint_sig)
        blocks: List[DependencyBlock] = []
        producer_endpoints = self._producer_endpoints_for(endpoint_sig)
        if not producer_endpoints:
            print(f"No producer endpoints found for {endpoint_sig}. Returning empty DependencyContext.")
            return DependencyContext(schemas=schemas, blocks=[])
        else:
            for pe in producer_endpoints:
                data = self.get_data_for_endpoint(pe)
                json_str = self._minify(self._pick_cached_object(data) or data or {})
                pe_schemas = self._schemas_for_endpoint(pe)
                schema_name = pe_schemas[0] if pe_schemas else None
                blocks.append(DependencyBlock(endpoint=pe, schema=schema_name, json=json_str))
            return DependencyContext(schemas=schemas, blocks=blocks)
    def _split_endpoint_sig(self, endpoint_sig: str) -> tuple[str, str]:
        """'get-/a/b/{id}' -> ('get', '/a/b/{id}')"""
        method = endpoint_sig.split("-")[0].lower()
        path = "-".join(endpoint_sig.split("-")[1:])
        if not path.startswith("/"):
            path = "/" + path
        return method, path
    def _get_operation_id(self, method: str, path: str) -> str:
        """
        Lấy operationId từ self.swagger_spec; fallback METHOD.upper()
        (Bạn cần gán self.swagger_spec = load_swagger(...))
        """
        try:
            return self.swagger_spec["paths"][path][method]["operationId"]
        except Exception:
            return method.upper()
# Sử dụng cách 1 (raw string) là cách phổ biến và dễ đọc nhất
def read_swagger_data(file_path):
    with open(file_path, 'r', encoding="utf-8") as file:
        return json.load(file)
