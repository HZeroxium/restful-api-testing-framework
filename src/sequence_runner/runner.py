# src/sequence_runner/runner.py
from __future__ import annotations

# add near other imports
from sequence_runner.helper import extract_expected_status, is_status_match
from sequence_runner.models import StepModel
from .test_data_runner import TestDataRunner, TestRow
import json
from .logging_setup import setup_logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .http_client import HttpClient
from .io_file import FileService
from .data_merge import merge_test_data
from .dependency import DependencyService  # NOTE: removed NOT_SURE import
from .url_builder import clean_endpoint, required_path_vars, substitute_path_vars, build_urls
from .parser import parse_test_case_core_from_dict, parse_all_from_files
import datetime


class SequenceRunner:
    def __init__(
        self,
        service_name: str,
        base_url: str,
        token: Optional[str] = None,
        endpoint: list[str] = None,
        skip_preload: bool = False,
        base_module_file: str = __file__,
        out_file_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        sampling_strategy: Literal["random", "all"] = "all",
        want_2xx: int = 10,
        want_4xx: int = 10,
        seed: Optional[int] = 42,
    ):
        self.sampling_strategy = sampling_strategy
        self.want_2xx = want_2xx
        self.want_4xx = want_4xx
        self.seed = seed
        self.skip_preload = skip_preload

        self.file = FileService(service_name, base_module_file, out_file_name)
        self.logger = setup_logging(log_file=self.file.get_log_path())
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.endpoint_filter = endpoint
        self.headers = headers
        self.http = HttpClient(token=token, default_headers=self.headers)
        self.response_cache: Dict[str, Any] = {}
        self.swagger_spec = self.file.get_swagger_spec_dict()
        # Dependency service (warm cache)
        self.dep = DependencyService(fileService= self.file, swagger_spec=self.swagger_spec)

        # CSV output
        # self.file.open_csv_output(service_name)

    # -------------------------------
    # Dependency cache persistence
    # -------------------------------
    def _dep_cache_path(self) -> Path:
        return self.file.paths.output_dir / "dependency_cache.json"

    def _load_dep_cache(self) -> None:
        """Load persisted dependency cache (ids + responses) if available."""
        try:
            p = self._dep_cache_path()
            if p.exists():
                payload = json.loads(p.read_text(encoding="utf-8"))
                # seed resolver’s caches
                responses = payload.get("responses", {}) or {}
                ids = payload.get("ids", {}) or {}
                if hasattr(self.dep, "global_dependency_cache"):
                    self.dep.global_dependency_cache.update(responses)
                if hasattr(self.dep, "available_ids_cache"):
                    for k, v in ids.items():
                        try:
                            cur = self.dep.available_ids_cache.get(k) or []
                            # extend unique
                            existing = set(cur)
                            cur.extend([x for x in v if x not in existing])
                            self.dep.available_ids_cache[k] = cur
                        except Exception:
                            pass
                self.logger.info(
                    f"🔁 Loaded dependency cache: "
                    f"{len(responses)} response buckets, "
                    f"{sum(len(v) for v in ids.values()) if isinstance(ids, dict) else 0} IDs"
                )
        except Exception as e:
            self.logger.warning(f"Failed to load dependency cache: {e}")

    def _save_dep_cache(self) -> None:
        """Persist dependency cache to disk for next runs."""
        try:
            p = self._dep_cache_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "responses": getattr(self.dep, "global_dependency_cache", {}),
                "ids": getattr(self.dep, "available_ids_cache", {}),
            }
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.logger.info(f"💾 Saved dependency cache to {p}")
        except Exception as e:
            self.logger.warning(f"Failed to save dependency cache: {e}")

    def _extract_reason_from_row(self, row: Dict[str, Any]) -> str:
        """Extract reason from nested test data row structure"""
        # Try to get reason from param data first
        if "param" in row and isinstance(row["param"], dict):
            reason = row["param"].get("reason", "")
            if reason:
                return reason

        # Try to get reason from body data
        if "body" in row and isinstance(row["body"], dict):
            reason = row["body"].get("reason", "")
            if reason:
                return reason

        # Fallback to top-level reason (for backward compatibility)
        return row.get("reason", "")

    # ------------------------------------------------------------------
    # Single step executor (handles deps, merge, URL, request)
    # ------------------------------------------------------------------
    def execute_request(
    self,
    step: StepModel,
    test_data_row: Optional[Dict[str, Any]] = None,
    current_step: int = 1,
    step_responses: List[Optional[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        endpoint = step.endpoint
        method = step.method.upper()
        base_params = step.query_parameters or {}
        path_vars = step.path_variables

        if step_responses is None:
            step_responses = []

        # Start from query params; start body EMPTY (do NOT use step.request_body)
        resolved_params = dict(base_params)
        resolved_body: Dict[str, Any] = {}

        # 1) Resolve explicit dependencies FIRST
        try:
            if getattr(step, "data_dependencies", None):
                resolved_params, resolved_body = self.dep.resolve_dependencies(
                    resolved_params,
                    resolved_body,
                    step.data_dependencies,
                    current_step=current_step,
                    step_responses=step_responses or [],
                )
            deps_params, deps_body = dict(resolved_params), dict(resolved_body)
            print("Resolved dependencies:", deps_params, deps_body) 
        except Exception as e:
            raise Exception(f"Dependency resolution failed at step {current_step} ({method} {endpoint}): {e}")

        # 2) Merge CSV data (param/body) over resolved values
        csv_path_vars = {}
        if test_data_row:
            data_for = "params" if method in ("GET", "DELETE") else "body"
            merged = merge_test_data(
                resolved_params, resolved_body, test_data_row, endpoint, path_vars, data_for=data_for
            )
            if isinstance(merged, (tuple, list)) and len(merged) >= 3:
                resolved_params, resolved_body, csv_path_vars = merged[0], merged[1], merged[2]
        # 3) Prepare endpoint & path vars
        cleaned = clean_endpoint(endpoint)
        all_path_vars = dict(path_vars)  # base

        def set_if_needed(dst: dict, k: str, v: Any):
            if v is None:
                return
            if k not in dst or dst[k] in (None, ""):
                dst[k] = v

        # 3a) Prefer values discovered via deps (before CSV overrides)
        for k, v in (deps_params or {}).items():
            if f"{{{k}}}" in cleaned:
                set_if_needed(all_path_vars, k, v)
        for k, v in (deps_body or {}).items():
            if isinstance(v, (str, int)) and f"{{{k}}}" in cleaned:
                set_if_needed(all_path_vars, k, v)
        # 3b) Then use merged params/body (may include CSV)
        for k, v in (resolved_params or {}).items():
            if f"{{{k}}}" in cleaned:
                set_if_needed(all_path_vars, k, v)
        for k, v in (resolved_body or {}).items():
            if isinstance(v, (str, int)) and f"{{{k}}}" in cleaned:
                set_if_needed(all_path_vars, k, v)
        # 3c) Finally, CSV-provided path vars (fill blanks only)
        for k, v in (csv_path_vars or {}).items():
            if f"{{{k}}}" in cleaned:
                set_if_needed(all_path_vars, k, v)

        # Remove path variables from query params
        final_params = dict(resolved_params)
        for var in list(all_path_vars.keys()):
            if var in final_params:
                del final_params[var]

        # Substitute path vars → endpoint
        final_endpoint, leftover = substitute_path_vars(cleaned, all_path_vars)
        if leftover:
            for v in leftover:
                if v not in all_path_vars or all_path_vars[v] is None:
                    all_path_vars[v] = "1" if ("id" in v.lower() or v.lower().endswith("id")) else "default"
            final_endpoint, leftover = substitute_path_vars(cleaned, all_path_vars)

        # 4) Build URLs
        base_with_path, full_with_query, final_params = build_urls(self.base_url, final_endpoint, final_params)

        # Debug log
        self.logger.info("  🔗 URL Construction:")
        self.logger.info(f"    Original endpoint: {cleaned}")
        self.logger.info(f"    Final endpoint:    {final_endpoint}")
        self.logger.info(f"    Base URL:          {base_with_path}")
        self.logger.info(f"    Full URL + query:  {full_with_query}")
        if all_path_vars:
            self.logger.info(f"    Path variables:    {all_path_vars}")
        if final_params:
            self.logger.info(f"    Query parameters:  {final_params}")

        # 5) Prepare request kwargs
        req_kwargs: Dict[str, Any] = {"timeout": 30}
        if method in ("GET", "DELETE"):
            req_kwargs["params"] = final_params
        else:
            # Body is ONLY deps + CSV (no step.request_body leakage)
            req_kwargs["json"] = resolved_body
            if final_params:
                req_kwargs["params"] = final_params

        # 6) Execute HTTP
        start = time.time()
        try:
            resp = self.http.request(method, base_with_path, **req_kwargs)
            elapsed = time.time() - start
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text

            # Cache responses & opportunistic IDs for later steps
            try:
                if isinstance(resp_json, (dict, list)):
                    cache_key = f"{method.lower()}_{final_endpoint}".replace("/", "_").strip("_")
                    if hasattr(self.dep, "global_dependency_cache"):
                        self.dep.global_dependency_cache[cache_key] = resp_json

                    if hasattr(self.dep, "extract_ids_from_response"):
                        ids = self.dep.extract_ids_from_response(resp_json)
                        if ids and hasattr(self.dep, "available_ids_cache"):
                            for likely in ["id", "petId", "userId", "orderId", "categoryId", "tagId"]:
                                bucket = self.dep.available_ids_cache.get(likely, [])
                                for val in ids:
                                    if val not in bucket:
                                        bucket.append(val)
                                self.dep.available_ids_cache[likely] = bucket
            except Exception:
                pass

            return {
                "url": full_with_query,
                "status_code": resp.status_code,
                "response": resp_json,
                "execution_time": elapsed,
                "success": resp.status_code < 400,
                "error": None,
                "merged_params": final_params,
                "merged_body": resolved_body,
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "url": full_with_query,
                "status_code": None,
                "response": None,
                "execution_time": elapsed,
                "success": False,
                "error": str(e),
                "merged_params": final_params,
                "merged_body": resolved_body,
            }

    def get_test_rows_from_path(self, path: Optional[Path]) -> List[TestRow]:
        if not path:
            return []
        try:
            # TestDataRunner returns List[TestRow]
            tdr = TestDataRunner(path, seed=self.seed)
            if self.sampling_strategy == "all":
                return tdr.select_all()
            else:
                return tdr.select_random_quota(self.want_2xx, self.want_4xx, allow_less=True)
        except Exception as e:
            self.logger.error(f"Failed to load CSV {path}: {e}")
            return []

    # ------------------------------------------------------------------
    # Run a single test case file
    # ------------------------------------------------------------------
    def run_test_case(self, test_case_file: Path) -> bool:
        self.logger.info(f"Running test case: {test_case_file.name}")
        is_pass = False

        # Load and parse test case using models
        test_case_dict = self.file.load_test_case(test_case_file)
        test_case = parse_test_case_core_from_dict(test_case_dict)
        test_case_id = test_case_file.stem
        target_endpoint = test_case.endpoint
        self.logger.info(f"🎯 Target endpoint: {target_endpoint}")

        steps: List[StepModel] = test_case.steps
        if not steps:
            self.logger.warning(f"No steps found in test case: {test_case_id}")
            return is_pass

        if not self.skip_preload:
            try:
                # We have not executed any step yet in this test case, so pass an empty list
                self.dep.preload_endpoints_dependency(steps, step_responses=[])
                self.logger.info("🌱 Preloaded dependency source endpoints to cache dir")
            except Exception as e:
                self.logger.warning(f"Dependency preloading warning: {e}")

        # CSV locate by endpoint_identifier (compat rules)
        endpoint_identifier = (
            test_case_id.replace("_0_1", "").replace("_1_1", "").replace("_2_1", "")
        )
        files = self.file.find_test_data_files(endpoint_identifier)

        # --- NEW: load TestRow lists (per-side) via TestDataRunner
        param_tr_rows: List[TestRow] = self.get_test_rows_from_path(files["param"]) if files["param"] else []
        body_tr_rows: List[TestRow] = self.get_test_rows_from_path(files["body"]) if files["body"] else []


        # Convert TestRow → side dict your pipeline expects
        def _testrow_to_obj(tr: Optional[TestRow]) -> Dict[str, Any]:
            if not tr:
                return {}
            try:
                obj = json.loads(tr.data_json) if tr.data_json else {}
            except Exception:
                obj = {}
            if isinstance(obj, dict):
                # ensure keys needed by extract_expected_status(...)
                obj.setdefault("reason", tr.reason)
                obj.setdefault("expected_status_code", tr.expected_status_code)
            return obj

        # Build combined rows (index-wise)
        if not param_tr_rows and not body_tr_rows:
            test_data_rows: List[Dict[str, Any]] = [{}]
            self.logger.info("🧪 No test data found, will run 1 time with empty data")
        else:
            max_len = max(len(param_tr_rows), len(body_tr_rows))
            test_data_rows = []
            for i in range(max_len):
                test_data_rows.append(
                    {
                        "param": _testrow_to_obj(param_tr_rows[i] if i < len(param_tr_rows) else None),
                        "body": _testrow_to_obj(body_tr_rows[i] if i < len(body_tr_rows) else None),
                    }
                )
            self.logger.info(
                f"🧪 Will run {len(test_data_rows)} times "
                f"(combine param/body rows by index; strategy='{getattr(self, 'sampling_strategy', 'random_quota')}')"
            )

        # Iterate rows
        for row_idx, row in enumerate(test_data_rows, start=1):
            self.logger.info(f"Running with test data row {row_idx}/{len(test_data_rows)}")
            expected_status = extract_expected_status(row)
            self.logger.info(f"  🎯 Expected status extracted: {expected_status}")

            step_responses: List[Optional[Dict[str, Any]]] = []

            for step_idx, step in enumerate(steps):
                step_endpoint = step.endpoint
                is_target_step = (step_endpoint == target_endpoint)

                result = self.execute_request(step, row, step_idx + 1, step_responses)

                # Push response for dependency resolution (keep shape)
                if result["success"] and result["response"] is not None:
                    step_responses.append(result["response"])
                else:
                    step_responses.append(None)

                # Dependency step: no assert, just continue
                if not is_target_step:
                    self.logger.info(
                        f"  🔄 Step {step_idx+1}: {step.method} {step_endpoint} "
                        f"-> {result['status_code']} (dependency - skip assert)"
                    )
                    continue

                # Target step: assert & log
                actual_status = result["status_code"] or 0
                is_pass = is_status_match(actual_status, expected_status)

                # Save target response JSON
                payload = {
                    "test_case_id": test_case_id,
                    "target_endpoint": target_endpoint,
                    "step_number": step_idx + 1,
                    "data_row": row_idx,
                    "request": {
                        "url": result.get("url", ""),
                        "method": step.method,
                        "endpoint": step.endpoint,
                        "base_query_parameters": step.query_parameters,
                        "merged_query_parameters": result.get("merged_params", {}),
                        "base_request_body": step.request_body,
                        "merged_request_body": result.get("merged_body", {}),
                        "test_data_used": row,
                    },
                    "response": {
                        "status_code": result["status_code"],
                        "body": result["response"],
                        "execution_time": f"{result['execution_time']:.3f}s",
                        "success": result["success"],
                        "error": result.get("error"),
                    },
                    "validation": {
                        "expected_status": expected_status,
                        "actual_status": actual_status,
                        "status_match": is_pass,
                        "test_result": "PASS" if is_pass else "FAIL",
                    },
                }
                self.file.save_target_response(test_case_id, row_idx, payload)

                # CSV row
                self.file.write_csv_row(
                    {
                        "test_case_id": test_case_id,
                        "step_number": step_idx + 1,
                        "endpoint": step.endpoint,
                        "method": step.method,
                        "test_data_row": row_idx,
                        "reason": self._extract_reason_from_row(row),
                        "request_params": json.dumps(result.get("merged_params", {})),
                        "request_body": json.dumps(result.get("merged_body", {})),
                        "final_url": result.get("url", ""),
                        "response_status": result["status_code"],
                        "expected_status": expected_status,
                        "execution_time": f"{result['execution_time']:.3f}s",
                        "status": "PASS" if is_pass else "FAIL",
                    }
                )

                status_emoji = "✅" if is_pass else "❌"
                expected_info = f"(expected: {expected_status})" if expected_status != "2xx" else ""
                self.logger.info(
                    f"  {status_emoji} 🎯 TARGET: {step.method} {step.endpoint} "
                    f"-> {result['status_code']} {expected_info} ({result['execution_time']:.3f}s)"
                )
                if not is_pass and result.get("error"):
                    self.logger.error(f"    Error: {result.get('error')}")
                if not is_pass and result["response"]:
                    try:
                        self.logger.error(f"    Response: {json.dumps(result['response'], indent=2)}")
                    except Exception:
                        self.logger.error(f"    Response: {result['response']}")

                time.sleep(0.1)

        # Persist dependency cache for next test cases / runs
        self._save_dep_cache()

        return is_pass

    # ------------------------------------------------------------------
    # Run all test cases
    # ------------------------------------------------------------------
    def run_all(self):
        self.logger.info(f"Starting test execution for service: {self.service_name}")
        test_case_files = self.file.find_test_case_files(self.endpoint_filter)
        if not test_case_files:
            self.logger.error("No test case files found!")
            return

        out_file_name = self.file.open_csv_output(self.service_name)

        # ---- exact, canonical sort using the endpoint inside each JSON ----
        topolist = self.file.load_topolist() or []
        topo_index = {ep.strip(): i for i, ep in enumerate(topolist)}

        def _endpoint_of(p: Path) -> str:
            try:
                d = self.file.load_test_case(p)
                case = parse_test_case_core_from_dict(d)
                return (case.endpoint or "").strip()
            except Exception:
                return ""

        # build sortable list
        decorated = []
        for seq_idx, p in enumerate(test_case_files):
            ep = _endpoint_of(p)
            idx_in_topo = topo_index.get(ep, len(topolist) + 1)  # unmatched go last
            decorated.append((idx_in_topo, seq_idx, ep, p))

        # sort strictly by topolist order
        decorated.sort(key=lambda t: (t[0], t[1]))
        ordered_files = [p for (_, _, _, p) in decorated]

        # log final order for confirmation
        self.logger.info("📋 Final execution order (following topolist.json):")
        for p in ordered_files:
            self.logger.info(f"  - {_endpoint_of(p) or p.name}")

        # run in sorted order
        for test_case_file in ordered_files:
            print(f"Running test case file: {test_case_file}")
            try:
                if self.run_test_case(test_case_file):
                    pass
            except Exception as e:
                self.logger.error(f"Error running test case {test_case_file.name}: {e}")

        return out_file_name


    def _split_body_into_form_and_files(body: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, tuple]]:
        """
        Turn a body dict into (form_fields, files) suitable for:
        requests.post(..., data=form_fields, files=files)

        File detection rules:
        - key name looks file-ish (avatar, file, image, upload, attachment), OR
        - value starts with "file:" prefix, e.g., "file:/path/to/logo.png"
        - value is a string that points to an existing file on disk
        """
        if not isinstance(body, dict):
            return {}, {}

        form_fields: Dict[str, Any] = {}
        files: Dict[str, tuple] = {}

        for k, v in body.items():
            # Only strings can be local paths or file: URIs
            if isinstance(v, str):
                has_file_prefix = v.startswith("file:")
                path_str = v[5:] if has_file_prefix else v
                p = Path(path_str)

                if has_file_prefix or (p.exists() and p.is_file()):
                    if p.exists() and p.is_file():
                        # (filename, fileobj)
                        files[k] = (p.name, p.open("rb"))
                    else:
                        # Not a real path; leave as plain form value
                        form_fields[k] = v
                    continue

            # default: treat as normal form value (requests will str() as needed)
            form_fields[k] = "" if v is None else v

        return form_fields, files
    # ------------------------------------------------------------------
    def close(self):
        self.file.close()
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
# src/sequence_runner/dependency.py (or wherever the runner plans steps)
