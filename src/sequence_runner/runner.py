# src/sequence_runner/runner.py
from __future__ import annotations

from sequence_runner.helper import extract_expected_status, is_status_match
from sequence_runner.models import StepModel, DependencyResolveValue
from .test_data_runner import TestDataRunner, TestRow
import json
from .logging_setup import setup_logging
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from .http_client import HttpClient
from .io_file import FileService
from .data_merge import merge_test_data
from .dependency import DependencyService  # your implementation with preload_endpoints_dependency(...)
from .url_builder import clean_endpoint, required_path_vars, substitute_path_vars, build_urls
from .parser import parse_test_case_core_from_dict


class SequenceRunner:
    def __init__(
        self,
        service_name: str,
        base_url: str,
        token: Optional[str] = None,
        endpoint: List[str] | None = None,
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
        self.headers = headers or {}
        self.http = HttpClient(token=token, default_headers=self.headers)

        # swagger for helpers (if needed by other utils)
        self.swagger_spec = self.file.get_swagger_spec_dict()

        # Use your strict dependency preloader (no in-run global caches here)
        self.dep = DependencyService(
            fileService=self.file,
            swagger_spec=self.swagger_spec,
            headers=self.headers,
        )

    # -------------------------------
    # helpers
    # -------------------------------
    def _extract_reason_from_row(self, row: Dict[str, Any]) -> str:
        if "param" in row and isinstance(row["param"], dict):
            reason = row["param"].get("reason", "")
            if reason:
                return reason
        if "body" in row and isinstance(row["body"], dict):
            reason = row["body"].get("reason", "")
            if reason:
                return reason
        return row.get("reason", "")

    def _testrow_to_obj(self, tr: Optional[TestRow]) -> Dict[str, Any]:
        if not tr:
            return {}
        try:
            obj = json.loads(tr.data_json) if tr.data_json else {}
        except Exception:
            obj = {}
        if isinstance(obj, dict):
            obj.setdefault("reason", tr.reason)
            obj.setdefault("expected_status_code", tr.expected_status_code)
        return obj

    def _pick_injections_for_step(
        self,
        step: StepModel,
        dep_result: Optional[DependencyResolveValue],
    ) -> Dict[str, Any]:
        """
        Map strictly-extracted dependency values to this consumer step.
        Your DependencyResolveValueData uses 'source_field_name' to mean the consumer's field name.
        We'll pick the first value from list_value deterministically.
        """
        if not dep_result or dep_result.endpoint_sig != step.endpoint:
            return {}
        inject: Dict[str, Any] = {}
        for fd in dep_result.field_dependency_data or []:
            name = fd.source_field_name  # consumer field name
            vals = fd.list_value or []
            if vals:
                inject[name] = vals[0]
        return inject

    # ------------------------------------------------------------------
    # Core request executor (deps injected by caller)
    # ------------------------------------------------------------------
    def _execute_request(
        self,
        step: StepModel,
        test_data_row: Optional[Dict[str, Any]],
        injections: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        endpoint = step.endpoint
        method = step.method.upper()
        base_params = step.query_parameters or {}
        base_body = step.request_body or {}
        path_vars = dict(step.path_variables or {})

        # Start with base
        resolved_params = dict(base_params)
        resolved_body: Dict[str, Any] = dict(base_body)

        # Inject dependency values first (highest precedence before CSV for path vars)
        injections = injections or {}
        cleaned = clean_endpoint(endpoint)

        def _apply_injection(k: str, v: Any):
            if f"{{{k}}}" in cleaned:
                path_vars[k] = v  # path takes priority
            else:
                if method in ("GET", "DELETE"):
                    resolved_params[k] = v
                else:
                    resolved_body[k] = v

        for k, v in injections.items():
            if v is not None:
                _apply_injection(k, v)

        # Merge CSV over the current resolved params/body
        csv_path_vars: Dict[str, Any] = {}
        if test_data_row:
            data_for = "params" if method in ("GET", "DELETE") else "body"
            merged = merge_test_data(
                resolved_params, resolved_body, test_data_row, endpoint, path_vars, data_for=data_for
            )
            resolved_params, resolved_body, csv_path_vars, _ = merged

        # CSV path vars fill remaining blanks (do not override already-set path vars)
        for k, v in csv_path_vars.items():
            if f"{{{k}}}" in cleaned and (k not in path_vars or path_vars[k] is None):
                path_vars[k] = v

        # Remove path vars from query params
        final_params = dict(resolved_params)
        for var in list(path_vars.keys()):
            if var in final_params:
                del final_params[var]

        # Substitute path vars
        final_endpoint, leftover = substitute_path_vars(cleaned, path_vars)
        if leftover:
            # last-resort defaults to keep request shape valid
            for v in leftover:
                if v not in path_vars or path_vars[v] is None:
                    path_vars[v] = "1" if ("id" in v.lower() or v.lower().endswith("id")) else "default"
            final_endpoint, _ = substitute_path_vars(cleaned, path_vars)

        # Build URLs
        base_with_path, full_with_query, final_params = build_urls(self.base_url, final_endpoint, final_params)

        # Prepare request kwargs
        req_kwargs: Dict[str, Any] = {"timeout": 30}
        if method in ("GET", "DELETE"):
            req_kwargs["params"] = final_params
        else:
            req_kwargs["json"] = resolved_body
            if final_params:
                req_kwargs["params"] = final_params

        # Execute HTTP
        start = time.time()
        try:
            resp = self.http.request(method, base_with_path, **req_kwargs)
            elapsed = time.time() - start
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text

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

    def _get_test_rows_from_path(self, path: Optional[Path]) -> List[TestRow]:
        if not path:
            return []
        try:
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

        # Load + parse
        test_case_dict = self.file.load_test_case(test_case_file)
        test_case = parse_test_case_core_from_dict(test_case_dict)
        test_case_id = test_case_file.stem
        target_endpoint = test_case.endpoint
        self.logger.info(f"🎯 Target endpoint: {target_endpoint}")

        steps: List[StepModel] = test_case.steps or []
        if not steps:
            self.logger.warning(f"No steps found in test case: {test_case_id}")
            return is_pass

        # Preload only what's needed for the FINAL consumer (strict; your service does it)
        dep_result: Optional[DependencyResolveValue] = None
        if not self.skip_preload:
            try:
                dep_result = self.dep.preload_endpoints_dependency(steps=steps, step_responses=[])
                self.debug_dependency_result(dep_result)

                self.logger.info("🌱 Preloaded dependencies for final consumer")
                
            except Exception as e:
                self.logger.warning(f"Dependency preloading warning: {e}")

        # Locate CSVs (compat with your identifiers)
        endpoint_identifier = (
            test_case_id.replace("_0_1", "").replace("_1_1", "").replace("_2_1", "")
        )
        files = self.file.find_test_data_files(endpoint_identifier)

        param_tr_rows = self._get_test_rows_from_path(files["param"]) if files["param"] else []
        body_tr_rows  = self._get_test_rows_from_path(files["body"])  if files["body"]  else []

        # Combine param/body rows by index (like before)
        if not param_tr_rows and not body_tr_rows:
            test_data_rows: List[Dict[str, Any]] = [{}]
            self.logger.info("🧪 No test data found, will run 1 time with empty data")
        else:
            max_len = max(len(param_tr_rows), len(body_tr_rows))
            test_data_rows = []
            for i in range(max_len):
                test_data_rows.append(
                    {
                        "param": self._testrow_to_obj(param_tr_rows[i] if i < len(param_tr_rows) else None),
                        "body":  self._testrow_to_obj(body_tr_rows[i]  if i < len(body_tr_rows)  else None),
                    }
                )
            self.logger.info(f"🧪 Will run {len(test_data_rows)} times (combine param/body rows by index)")

        # Output CSV init
        out_file_name = self.file.open_csv_output(self.service_name)

        # Iterate rows
        for row_idx, row in enumerate(test_data_rows, start=1):
            self.logger.info(f"Running with test data row {row_idx}/{len(test_data_rows)}")
            expected_status = extract_expected_status(row)
            self.logger.info(f"  🎯 Expected status: {expected_status}")

            for step_idx, step in enumerate(steps):
                is_target_step = (step.endpoint == target_endpoint)
                injections = self._pick_injections_for_step(step, dep_result) if is_target_step else {}

                result = self._execute_request(step, row, injections=injections)

                # Non-target dependency steps: log and continue, no assert
                if not is_target_step:
                    self.logger.info(
                        f"  🔄 Step {step_idx+1}: {step.method} {step.endpoint} "
                        f"-> {result['status_code']} (dependency - skip assert)"
                    )
                    continue

                # Target: assert + persist artifacts
                actual_status = result["status_code"] or 0
                is_pass = is_status_match(actual_status, expected_status)

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
                        "injections": injections,
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

                # Only one target step—break after asserting
                break

        return out_file_name
    def run_all(self):
        """Discover, strictly topologically sort, and execute all test cases."""
        self.logger.info(f"Starting test execution for service: {self.service_name}")

        test_case_files = self.file.find_test_case_files(self.endpoint_filter)
        if not test_case_files:
            self.logger.error("No test case files found!")
            return None

        # Load topological order (list of endpoint strings)
        topolist = self.file.load_topolist() or []
        topo_index = {ep.strip(): i for i, ep in enumerate(topolist)}

        def _endpoint_of(p: Path) -> str:
            try:
                d = self.file.load_test_case(p)
                case = parse_test_case_core_from_dict(d)
                return (case.endpoint or "").strip()
            except Exception:
                return ""

        # Decorate with sortable keys: (index in topolist, original order, endpoint, path)
        decorated = []
        for seq_idx, p in enumerate(test_case_files):
            ep = _endpoint_of(p)
            idx_in_topo = topo_index.get(ep, len(topolist) + 1)  # unknown endpoints go last
            decorated.append((idx_in_topo, seq_idx, ep, p))

        # Sort strictly by topolist order, then stable by discovery order
        decorated.sort(key=lambda t: (t[0], t[1]))
        ordered_files = [p for (_, _, _, p) in decorated]

        # Log the final execution order (by endpoint when possible)
        self.logger.info("📋 Final execution order (following topolist.json):")
        for _, _, ep, p in decorated:
            self.logger.info(f"  - {ep or p.name}")

        # Run in order; keep the first non-empty CSV name returned by run_test_case
        out_file_name: Optional[str] = None
        for test_case_file in ordered_files:
            try:
                res = self.run_test_case(test_case_file)
                if res and not out_file_name:
                    out_file_name = res
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
    def debug_dependency_result(self, dep_result: Optional[DependencyResolveValue], file_name: str = "dependency_debug.json") -> None:
        """
        Write detailed dependency resolution output to a JSON file under the output directory.

        Args:
            dep_result: The DependencyResolveValue returned from preload_endpoints_dependency.
            file_name:  Optional override for debug file name.
        """
        try:
            if not dep_result:
                self.logger.warning("No dependency result to debug-dump.")
                return

            # Serialize the DependencyResolveValue dataclass
            def serialize(obj):
                if hasattr(obj, "__dataclass_fields__"):
                    return {k: serialize(v) for k, v in obj.__dict__.items()}
                elif isinstance(obj, list):
                    return [serialize(v) for v in obj]
                elif isinstance(obj, dict):
                    return {k: serialize(v) for k, v in obj.items()}
                else:
                    return obj

            data = serialize(dep_result)
            out_path = self.file.paths.output_dir / file_name
            out_path.parent.mkdir(parents=True, exist_ok=True)

            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

            self.logger.info(f"🧩 Dependency debug file saved: {out_path}")
        except Exception as e:
            self.logger.error(f"Failed to write dependency debug file: {e}")
