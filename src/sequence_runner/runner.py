# src/sequence_runner/runner.py
from __future__ import annotations

import json
from .logging_setup import setup_logging
import re   
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .http_client import HttpClient
from .io_file import FileService
from .validator import extract_expected_status, is_status_match
from .data_merge import merge_test_data
from .dependency import DependencyService, NOT_SURE
from .url_builder import clean_endpoint, required_path_vars, substitute_path_vars, build_urls
from .models import TestCaseCore, DataRow, InjectedDataset, TestCaseWithDataset, StepModel
from .parser import parse_test_case_core_from_dict, parse_all_from_files
import datetime
logger = setup_logging()


class SequenceRunner:
    def __init__(
        self,
        service_name: str,
        base_url: str,
        token: Optional[str] = None,
        endpoint: Optional[str] = None,
        skip_preload: bool = False,
        base_module_file: str = __file__,
    ):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.endpoint_filter = endpoint
        self.file = FileService(service_name , base_module_file)
        self.http = HttpClient(token=token)
        self.dep = DependencyService()
        self.response_cache: Dict[str, Any] = {}

        # CSV output
        # self.file.open_csv_output(service_name)

        # Auto-discover & preload dependencies (optional)
        if not skip_preload:
            # Load test cases using models
            test_cases = []
            for f in self.file.find_test_case_files(self.endpoint_filter):
                doc = self.file.load_test_case(f)
                try:
                    test_case = parse_test_case_core_from_dict(doc)
                    test_cases.append(test_case)
                except Exception as e:
                    logger.warning(f"Failed to parse test case {f}: {e}")
            
            eps, mappings = self.dep.auto_discover_dependencies(test_cases)
            self.dep.preload_dependencies(self.base_url, self.http, eps, mappings)

    # ------------------------------------------------------------------
    # Single step executor (handles deps, merge, not-sure, URL, request)
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
        data_deps = step.data_dependencies

        if step_responses is None:
            step_responses = []

        # 1) Resolve data dependencies
        resolved_params, resolved_body = self.dep.resolve_dependencies(
            base_params, base_body, data_deps, current_step, step_responses
        )

        # 2) Merge test data
        csv_path_vars, not_sure_params = {}, {}
        if test_data_row:
            data_for = "params" if method in ("GET", "DELETE") else "body"
            resolved_params, resolved_body, csv_path_vars, not_sure_params = merge_test_data(
                resolved_params, resolved_body, test_data_row, endpoint, path_vars, data_for=data_for
            )

        # 3) Prepare endpoint & path vars
        cleaned = clean_endpoint(endpoint)
        all_path_vars = dict(path_vars)  # base
        # Priority 1: CSV path vars
        for k, v in csv_path_vars.items():
            if f"{{{k}}}" in cleaned and v is not None:
                all_path_vars[k] = v
        # Priority 2: dependency values, only if used in path
        for k, v in resolved_params.items():
            if f"{{{k}}}" in cleaned and (k not in all_path_vars or all_path_vars[k] is None):
                all_path_vars[k] = v

        # 3a) Resolve %not-sure% (only for vars marked not-sure)
        for var in not_sure_params:
            if var not in all_path_vars or all_path_vars[var] in (None, NOT_SURE):
                val = self.dep.resolve_not_sure_parameter(var, step_responses)
                if val is not None:
                    all_path_vars[var] = val

        # 3b) Skip row if any required not-sure param remains unresolved
        req_vars = set(required_path_vars(cleaned))
        unresolved_not_sure = [
            v for v in req_vars if (v in not_sure_params) and (v not in all_path_vars or all_path_vars[v] in (None, NOT_SURE))
        ]
        if unresolved_not_sure:
            reason = f"Unresolved %not-sure% parameter(s): {', '.join(unresolved_not_sure)}"
            logger.error(f"🚫 Skip calling HTTP: {reason}")
            return {
                "url": f"{self.base_url}{cleaned}",
                "status_code": None,
                "response": None,
                "execution_time": 0.0,
                "success": False,
                "error": reason,
                "merged_params": {},
                "merged_body": {},
                "skipped": True,
            }

        # 3c) Fallback for other missing required path vars
        missing_vars = [v for v in req_vars if v not in all_path_vars or all_path_vars[v] is None]
        if missing_vars:
            for v in missing_vars:
                # ưu tiên cache id động nếu có (theo key var)
                if self.dep.available_ids_cache.get(v):
                    all_path_vars[v] = self.dep.available_ids_cache[v][0]
                else:
                    # generic fallback: id-like -> '1', else 'default'
                    all_path_vars[v] = "1" if ("id" in v.lower() or v.lower().endswith("id")) else "default"

        # 3d) Remove path variables from query params
        final_params = dict(resolved_params)
        for var in list(all_path_vars.keys()):
            if var in final_params:
                del final_params[var]

        # 3e) Substitute path vars → endpoint
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
        logger.info("  🔗 URL Construction:")
        logger.info(f"    Original endpoint: {cleaned}")
        logger.info(f"    Final endpoint:    {final_endpoint}")
        logger.info(f"    Base URL:          {base_with_path}")
        logger.info(f"    Full URL + query:  {full_with_query}")
        if all_path_vars:
            logger.info(f"    Path variables:    {all_path_vars}")
        if final_params:
            logger.info(f"    Query parameters:  {final_params}")

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

            # Cache response data for later deps
            if resp.status_code < 400:
                cache_key = f"{method}_{final_endpoint}"
                self.response_cache[cache_key] = resp_json

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

    # ------------------------------------------------------------------
    # Run a single test case file
    # ------------------------------------------------------------------
    def run_test_case(self, test_case_file: Path) -> bool:
        logger.info(f"Running test case: {test_case_file.name}")
        is_pass = False

        # Load and parse test case using models
        test_case_dict = self.file.load_test_case(test_case_file)
        test_case = parse_test_case_core_from_dict(test_case_dict)
        test_case_id = test_case_file.stem
        target_endpoint = test_case.endpoint
        logger.info(f"🎯 Target endpoint: {target_endpoint}")

        steps: List[StepModel] = test_case.steps
        if not steps:
            logger.warning(f"No steps found in test case: {test_case_id}")
            return is_pass

        # CSV locate by endpoint_identifier (compat rules)
        endpoint_identifier = (
            test_case_id.replace("_0_1", "").replace("_1_1", "").replace("_2_1", "")
        )
        files = self.file.find_test_data_files(endpoint_identifier)
        param_rows = self.file.load_csv_rows(files["param"]) if files["param"] else []
        body_rows = self.file.load_csv_rows(files["body"]) if files["body"] else []

        if files["param"]:
            logger.info(f"📄 Param CSV: {files['param'].name} -> {len(param_rows)} rows")
        if files["body"]:
            logger.info(f"📄 Body  CSV: {files['body'].name}  -> {len(body_rows)} rows")

        if not param_rows and not body_rows:
            test_data_rows: List[Dict[str, Any]] = [{}]
            logger.info("🧪 No test data found, will run 1 time with empty data")
        else:
            max_len = max(len(param_rows), len(body_rows))
            test_data_rows = []
            for i in range(max_len):
                test_data_rows.append(
                    {
                        "param": param_rows[i] if i < len(param_rows) else {},
                        "body": body_rows[i] if i < len(body_rows) else {},
                    }
                )
            logger.info(f"🧪 Will run {len(test_data_rows)} times (combine param/body rows by index)")

        # Iterate rows
        for row_idx, row in enumerate(test_data_rows, start=1):
            logger.info(f"Running with test data row {row_idx}/{len(test_data_rows)}")
            expected_status = extract_expected_status(row)
            logger.info(f"  🎯 Expected status extracted: {expected_status}")

            step_responses: List[Optional[Dict[str, Any]]] = []
            skip_row = False

            for step_idx, step in enumerate(steps):
                step_endpoint = step.endpoint
                is_target_step = (step_endpoint == target_endpoint)

                result = self.execute_request(step, row, step_idx + 1, step_responses)

                # If skip because unresolved %not-sure% → log CSV error once and skip whole row
                if result.get("skipped"):
                    self.file.write_csv_row(
                        {
                            "test_case_id": test_case_id,
                            "step_number": step_idx + 1,
                            "endpoint": step.endpoint,
                            "method": step.method,
                            "test_data_row": row_idx,
                            "request_params": json.dumps(result.get("merged_params", {})),
                            "request_body": json.dumps(result.get("merged_body", {})),
                            "final_url": result.get("url", ""),
                            "response_status": None,
                            "expected_status": expected_status,
                            "execution_time": f"{result.get('execution_time', 0.0):.3f}s",
                            "status": "ERROR(%not-sure%)",
                        }
                    )
                    logger.error(f"  ❌ ERROR(%not-sure%): {result.get('error')}")
                    skip_row = True
                    break

                # Push response for dependency resolution
                if result["success"] and result["response"] is not None:
                    step_responses.append(result["response"])
                else:
                    step_responses.append(None)

                # Dependency step: no assert, just continue
                if not is_target_step:
                    logger.info(
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
                logger.info(
                    f"  {status_emoji} 🎯 TARGET: {step.method} {step.endpoint} "
                    f"-> {result['status_code']} {expected_info} ({result['execution_time']:.3f}s)"
                )
                if not is_pass and result.get("error"):
                    logger.error(f"    Error: {result.get('error')}")
                if not is_pass and result["response"]:
                    logger.error(f"    Response: {json.dumps(result['response'], indent=2)}")

                time.sleep(0.1)

            if skip_row:
                # chuyển ngay sang row kế tiếp
                continue

        return is_pass

    # ------------------------------------------------------------------
    # Run all test cases
    # ------------------------------------------------------------------
    def run_all(self):
        logger.info(f"Starting test execution for service: {self.service_name}")
        test_case_files = self.file.find_test_case_files(self.endpoint_filter)
        if not test_case_files:
            logger.error("No test case files found!")
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

            logger.info("📋 Sorting test cases by topolist order...")
            test_case_files.sort(key=sort_key)

        
        for test_case_file in test_case_files:
            try:
                if self.run_test_case(test_case_file):
                    pass
            except Exception as e:
                logger.error(f"Error running test case {test_case_file.name}: {e}")

        return out_file_name
    # ------------------------------------------------------------------
    def close(self):
        self.file.close()
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
