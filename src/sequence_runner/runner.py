# src/sequence_runner/runner.py
from __future__ import annotations

# add near other imports
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
from .validator import extract_expected_status, is_status_match
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

        # Dependency service (warm cache)
        self.dep = DependencyService()

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
        base_params = step.query_parameters
        base_body = step.request_body
        path_vars = step.path_variables

        if step_responses is None:
            step_responses = []
        resolved_params = dict(base_params or {})
        resolved_body = dict(base_body or {})

        # 1) Resolve explicit data dependencies FIRST (inject values for downstream use)
        try:
            if getattr(step, "data_dependencies", None):
                resolved_params, resolved_body = self.dep.resolve_dependencies(
                    resolved_params,
                    resolved_body,
                    step.data_dependencies,
                    current_step=current_step,
                    step_responses=step_responses or [],
                )
        except Exception as e:
            self.logger.warning(f"Dependency resolution warning on step {current_step}: {e}")

        # 2) Merge test data (param/body) over resolved values
        csv_path_vars = {}
        if test_data_row:
            data_for = "params" if method in ("GET", "DELETE") else "body"
            # NOTE: merge_test_data returns (params, body, csv_path_vars, _not_used)
            merged = merge_test_data(
                resolved_params, resolved_body, test_data_row, endpoint, path_vars, data_for=data_for
            )
            if isinstance(merged, (tuple, list)) and len(merged) >= 3:
                resolved_params, resolved_body, csv_path_vars = merged[0], merged[1], merged[2]

        # 3) Prepare endpoint & path vars
        cleaned = clean_endpoint(endpoint)
        all_path_vars = dict(path_vars)  # base
        # Priority 1: CSV path vars
        for k, v in csv_path_vars.items():
            if f"{{{k}}}" in cleaned and v is not None:
                all_path_vars[k] = v
        # Priority 2: dependency/merged values, only if used in path
        for k, v in resolved_params.items():
            if f"{{{k}}}" in cleaned and (k not in all_path_vars or all_path_vars[k] is None):
                all_path_vars[k] = v
        for k, v in resolved_body.items():
            if isinstance(v, (str, int)) and f"{{{k}}}" in cleaned and (k not in all_path_vars or all_path_vars[k] is None):
                all_path_vars[k] = v

        # 3b) Fallback for other missing required path vars (simple defaults)
        req_vars = set(required_path_vars(cleaned))
        missing_vars = [v for v in req_vars if v not in all_path_vars or all_path_vars[v] is None]
        if missing_vars:
            for v in missing_vars:
                all_path_vars[v] = "1" if ("id" in v.lower() or v.lower().endswith("id")) else "default"

        # 3c) Remove path variables from query params
        final_params = dict(resolved_params)
        for var in list(all_path_vars.keys()):
            if var in final_params:
                del final_params[var]

        # 3d) Substitute path vars → endpoint
        final_endpoint, leftover = substitute_path_vars(cleaned, all_path_vars)
        # Best-effort: if still leftover (rare), try generic fill then substitute again
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

            # 6b) Feed successful responses into dependency cache for later steps/rows
            try:
                if isinstance(resp_json, (dict, list)):
                    # cache by normalized key, e.g. 'get__pet_id' (safe-ish)
                    cache_key = f"{method.lower()}_{final_endpoint}".replace("/", "_").strip("_")
                    if hasattr(self.dep, "global_dependency_cache"):
                        self.dep.global_dependency_cache[cache_key] = resp_json

                    # opportunistically cache extracted IDs
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

        # --- Dependency warm-up for this test case ---
        # Load persisted cache and preload producer endpoints (GET) for required dependencies
        self._load_dep_cache()
        if not self.skip_preload:
            try:
                dep_endpoints, dep_map = self.dep.auto_discover_dependencies([test_case])
                if dep_endpoints:
                    self.logger.info(f"🌱 Preloading dependencies: {len(dep_endpoints)} producer endpoint(s)")
                self.dep.preload_dependencies(
                    base_url=self.base_url,
                    http=self.http,
                    dependency_endpoints=dep_endpoints,
                    dependency_mappings=dep_map,
                )
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

        if files["param"]:
            self.logger.info(
                f"📄 Param CSV: {files['param'].name} -> {len(param_tr_rows)} rows "
                f"(strategy='{getattr(self, 'sampling_strategy', 'random_quota')}', "
                f"want_2xx={getattr(self, 'want_2xx', 10)}, want_4xx={getattr(self, 'want_4xx', 10)})"
            )
        if files["body"]:
            self.logger.info(
                f"📄 Body  CSV: {files['body'].name}  -> {len(body_tr_rows)} rows "
                f"(strategy='{getattr(self, 'sampling_strategy', 'random_quota')}', "
                f"want_2xx={getattr(self, 'want_2xx', 10)}, want_4xx={getattr(self, 'want_4xx', 10)})"
            )

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

        # sort theo topolist nếu có
        topolist = self.file.load_topolist()
        if topolist:
            def sort_key(file_path: Path):
                filename = file_path.stem
                for i, endpoint in enumerate(topolist):
                    if "-" in endpoint:
                        method, path = endpoint.split("-", 1)
                        path_pattern = path.replace("/", "_").replace("{", "").replace("}", "_")
                        patterns = [
                            f"{path_pattern}",
                            f"{method.lower()}{path_pattern}",
                            f"{path_pattern}{method}",
                            f"{path_pattern}{method.title()}",
                        ]
                        for p in patterns:
                            if p in filename:
                                return i
                return len(topolist)

            self.logger.info("📋 Sorting test cases by topolist order...")
            test_case_files.sort(key=sort_key)

        for test_case_file in test_case_files:
            try:
                if self.run_test_case(test_case_file):
                    pass
            except Exception as e:
                self.logger.error(f"Error running test case {test_case_file.name}: {e}")

        return out_file_name

    # ------------------------------------------------------------------
    def close(self):
        self.file.close()
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
