# data_for_endpoints shape:
# {
#   "params": { "<method-path>": {...} },
#   "requestBody": { "<method-path>": {...} }
# }

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import requests

import logging

from sequence_runner.test_data_runner import get_first_2xx_executable_data_for_endpoint
logger = logging.getLogger(__name__)
class ApiDataFetcher:
    """
    Provide:
      - swagger_spec: full OpenAPI/Swagger dict
      - headers: optional default headers
      - data_for_endpoints:
          {
            "params":       { "<method-path>": {...}, ... },
            "requestBody":  { "<method-path>": {...}, ... }
          }

    Example:
      fetcher = ApiDataFetcher(
          swagger_spec=my_spec,
          headers={"Authorization": "Bearer ..."},
          data_for_endpoints={
              "params": {"get-/pets/{id}": {"id": 1}},
              "requestBody": {"post-/pets": {"name": "Fido"}}
          }
      )
    """

    # ------------------------------ lifecycle ------------------------------
    def __init__(
        self,
        swagger_spec: dict,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None,
        csv_dir: Optional[Path] = None,
    ) -> None:
        self.swagger_spec = swagger_spec or {}
        self.headers = headers
        # Expected keys: "params", "requestBody" (both optional)
        self.session = session or requests.Session()
        self.csv_dir = csv_dir

    # ------------------------------ public API ------------------------------
    def call_api_to_get_data_for_ep(self, endpoint_sig: str, dep_values: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Build a minimal request from swagger + CSV, optionally inject dep_values,
        call the API, and return a compact cache-ready object.
        """
        exec_data = get_first_2xx_executable_data_for_endpoint(
            endpoint_sig,
            self.swagger_spec,
            csv_dir=self.csv_dir,
        )
        if not exec_data or (exec_data.get("parameters") is None and exec_data.get("requestBody") is None):
            logging.warning("No executable data found for %s", endpoint_sig)
            return None

        method, raw_path = self._split_endpoint_sig(endpoint_sig)
        base_url = self._get_base_url()
        if not base_url:
            logging.error("Base URL missing in swagger spec; cannot call %s", endpoint_sig)
            return None

        path_params, query_params, header_params, cookie_params, json_body = \
            self._build_minimal_request_parts(endpoint_sig, exec_data)

        # Inject dependency values
        if dep_values:
            for k, v in dep_values.items():
                if path_params is not None and k in path_params:
                    path_params[k] = v
                    continue
                if isinstance(json_body, dict) and k in json_body:
                    json_body[k] = v
                    continue
                if query_params is None:
                    query_params = {}
                if k not in query_params or query_params[k] in (None, ""):
                    query_params[k] = v

        # Optional: prune body to required
        if json_body and isinstance(json_body, dict):
            body_schema = self._get_request_body_schema(raw_path, method)
            if body_schema:
                json_body = self._prune_body_to_required(json_body, body_schema)

        final_path = self._apply_path_params(raw_path, path_params or {})
        url = f"{base_url}{final_path}"

        logging.info("➡️  Fetching %s %s", method.upper(), url)
        logging.info("    Path params: %s", path_params)

        try:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                params=query_params or None,
                json=json_body if method.upper() in ("POST", "PUT", "PATCH") else None,
                headers=header_params or None,
                cookies=cookie_params or None,
                timeout=30,
            )
            logging.info("    Response status: %d", resp.status_code)
        except Exception as e:
            raise Exception(f"API call failed for {endpoint_sig}: {e}") from e

        try:
            content = resp.json()
            if isinstance(content, (dict, list)):
                content = self.trim_response_to_singleton(endpoint_sig, content)
        except ValueError:
            content = resp.text

        ok = 200 <= (resp.status_code or 0) < 300
        return {
            "status": resp.status_code,
            "body": content,
            "ok": ok,
            "request": {
                "method": method.upper(),
                "url": url,
                "params": query_params or {},
                "path_params": path_params or {},
                "headers": header_params or {},
                "cookies": cookie_params or {},
                "json": json_body if method.upper() in ("POST", "PUT", "PATCH") else None,
            },
        }





    # ----------------------------- swagger helpers ---------------------------
    def _split_endpoint_sig(self, endpoint_sig: str) -> Tuple[str, str]:
        """'get-/a/b/{id}' -> ('get', '/a/b/{id}')"""
        method = endpoint_sig.split("-")[0].lower()
        path = "-".join(endpoint_sig.split("-")[1:])
        if not path.startswith("/"):
            path = "/" + path
        return method, path

    def _get_base_url(self) -> str:
        """
        Get base URL from swagger spec:
          - OpenAPI 3.x: spec["servers"][0]["url"]
          - Swagger 2.0: schemes[0]://host + basePath
        """
        spec = self.swagger_spec or {}
        servers = spec.get("servers")
        if isinstance(servers, list) and servers:
            url = (servers[0].get("url") or "").strip()
            return url.rstrip("/")
        host = spec.get("host")
        base_path = spec.get("basePath", "") or ""
        schemes = spec.get("schemes", []) or ["http"]
        if host:
            scheme = schemes[0] if schemes else "http"
            return f"{scheme}://{host}{base_path}".rstrip("/")
        return ""

    def _apply_path_params(self, path: str, path_params: Dict[str, Any]) -> str:
        out = path
        for k, v in (path_params or {}).items():
            out = out.replace("{" + k + "}", str(v))
        return out

    def _merged_params(self, path: str, method: str):
        """Path-level params + op-level params (op override)."""
        path_item = (self.swagger_spec.get('paths', {}) or {}).get(path, {}) or {}
        op_obj    = (path_item.get(method.lower(), {}) or {})
        merged = {}
        for p in (path_item.get('parameters', []) or []) + (op_obj.get('parameters', []) or []):
            key = (p.get('name'), p.get('in'))
            merged[key] = p
        return list(merged.values())

    def _build_minimal_request_parts(self, endpoint_sig: str, exec_data: Dict[str, Any]):
        method, raw_path = self._split_endpoint_sig(endpoint_sig)
        params_spec   = self._merged_params(raw_path, method)
        path_params   = {}
        query_params  = {}
        header_params = dict(self.headers)
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

        header_params = {k: v for k, v in header_params.items() if v is not None}

        json_body = None
        if exec_data.get('requestBody') is not None:
            json_body = exec_data['requestBody']

        return path_params, query_params, header_params, cookie_params, json_body

    # ------------------------- body schema + pruning --------------------------
    def _get_request_body_schema(self, path: str, method: str):
        """Resolve requestBody schema object (dereferenced)."""
        op = (self.swagger_spec.get('paths', {}) or {}).get(path, {}) \
            .get(method.lower(), {}) or {}
        rb = (op.get('requestBody') or {})
        if not rb:
            return None
        content = rb.get('content') or {}
        for mt in ['application/json', 'application/*+json']:
            if mt in content:
                schema = content[mt].get('schema') or {}
                break
        else:
            if content:
                schema = next(iter(content.values())).get('schema', {}) or {}
            else:
                schema = rb.get('schema', {}) or {}
        ref = self._find_object_with_key(schema, '$ref')
        return self._get_ref(self.swagger_spec, ref['$ref']) if ref else schema

    def _prune_body_to_required(self, body: dict, schema: dict):
        """Return a copy of body keeping only required fields (recursively)."""
        if not isinstance(body, dict) or not isinstance(schema, dict):
            return body
        required = set(schema.get('required') or [])
        props    = schema.get('properties') or {}
        minimal  = {}
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

    # --------------------------- response trimming ---------------------------
    def trim_response_to_singleton(self, endpoint_sig: str, data: Any) -> Any:
        schema = self.get_json_response_schema(endpoint_sig)
        if not schema:
            return data
        return self._trim_by_schema(data, schema)

    def get_json_response_schema(self, endpoint_sig: str) -> Optional[dict]:
        method, path = self._split_endpoint_sig(endpoint_sig)
        return self._get_response_schema_core(method, path)

    def _get_response_schema_core(self, method: str, path: str) -> Optional[dict]:
        try:
            op = (self.swagger_spec.get('paths', {}) or {}).get(path, {}) \
                    .get(method.lower(), {}) or {}
            responses = op.get('responses') or {}
            _, resp_obj = self._collect_first_2xx_resp(responses)
            if not resp_obj:
                return None
            schema = self._preferred_json_response(resp_obj)
            if not schema:
                return None
            return self._deref(schema)
        except Exception:
            return None

    def _collect_first_2xx_resp(self, responses: dict) -> Tuple[Optional[str], Optional[dict]]:
        if not isinstance(responses, dict):
            return (None, None)
        if '200' in responses:
            return ('200', responses['200'])
        for code, obj in responses.items():
            try:
                c = int(code)
                if 200 <= c < 300:
                    return (code, obj)
            except Exception:
                continue
        return (None, None)

    def _preferred_json_response(self, resp_obj: dict) -> Optional[dict]:
        if not isinstance(resp_obj, dict):
            return None
        content = resp_obj.get('content') or {}
        if 'application/json' in content:
            return content['application/json'].get('schema')
        for mt, val in content.items():
            if isinstance(mt, str) and ('json' in mt or mt.endswith('+json')):
                return (val or {}).get('schema')
        return resp_obj.get('schema')  # Swagger 2.0

    def _trim_by_schema(self, data: Any, schema: dict) -> Any:
        if not isinstance(schema, dict):
            return data
        schema = self._deref(schema)
        stype = schema.get('type')
        for comb in ("oneOf", "anyOf", "allOf"):
            if comb in schema and isinstance(schema[comb], list) and schema[comb]:
                return self._trim_by_schema(data, self._deref(schema[comb][0]))
        if stype == 'array':
            items_schema = self._deref(schema.get('items') or {})
            if isinstance(data, list) and data:
                return [self._trim_by_schema(data[0], items_schema)]
            return []
        if stype == 'object':
            if not isinstance(data, dict):
                return data
            props = schema.get('properties') or {}
            addl  = schema.get('additionalProperties', None)
            out = {}
            for k, v in data.items():
                if k in props:
                    out[k] = self._trim_by_schema(v, self._deref(props[k]))
                elif isinstance(addl, dict):
                    out[k] = self._trim_by_schema(v, self._deref(addl))
                else:
                    out[k] = v
            return out
        return data

    # --------------------------- tiny utils ---------------------------
    def _deref(self, schema: dict) -> dict:
        if not isinstance(schema, dict):
            return schema
        ref = schema.get('$ref')
        if not ref:
            return schema
        try:
            sub = ref.lstrip('#/').split('/')
            cur = self.swagger_spec
            for k in sub:
                cur = cur[k]
            return cur if isinstance(cur, dict) else schema
        except Exception:
            return schema

    def _get_ref(self, spec: dict, ref: str):
        sub = ref[2:].split('/')
        schema = spec
        for e in sub:
            schema = schema.get(e, {})
        return schema

    def _find_object_with_key(self, d: Any, key: str) -> Optional[dict]:
        """Shallow DFS to find a dict containing `key`."""
        if isinstance(d, dict):
            if key in d:
                return d
            for v in d.values():
                res = self._find_object_with_key(v, key)
                if res:
                    return res
        elif isinstance(d, list):
            for it in d:
                res = self._find_object_with_key(it, key)
                if res:
                    return res
        return None
