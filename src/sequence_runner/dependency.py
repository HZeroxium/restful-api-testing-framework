# src/sequence_runner/dependency.py
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from .http_client import HttpClient
from .models import TestCaseCore, StepModel

logger = logging.getLogger(__name__)


class DependencyService:
    def __init__(self):
        # cache json trả về từ các endpoint preload hoặc step trước
        self.global_dependency_cache: Dict[str, Any] = {}
        # KHÔNG hard-code key nào: key được sinh động theo dep_key, path var...
        self.available_ids_cache: Dict[str, List[str]] = defaultdict(list)

    def resolve_dependencies(
        self,
        params: Dict[str, Any],
        body: Dict[str, Any],
        data_dependencies: Dict[str, Any],
        current_step: int,
        step_responses: List[Optional[Dict]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        def _is_scalar(x: Any) -> bool:
            return isinstance(x, (str, int, float, bool))

        resolved_params = dict(params or {})
        resolved_body = dict(body or {})

        if not data_dependencies:
            return resolved_params, resolved_body

        for dep_key, dep_info in (data_dependencies or {}).items():
            if not isinstance(dep_info, dict):
                logger.warning(f"⚠️ Dependency '{dep_key}' must be an object; got {type(dep_info).__name__}")
                continue

            from_step = dep_info.get("from_step", None)
            if not isinstance(from_step, int) or from_step <= 0:
                logger.warning(f"⚠️ Dependency '{dep_key}' is missing a valid 'from_step' (1-based).")
                continue

            idx = from_step - 1
            if idx < 0 or idx >= len(step_responses):
                logger.warning(f"⚠️ Step[{from_step}] response not available for dependency '{dep_key}'.")
                continue

            source_resp = step_responses[idx]
            if source_resp is None:
                logger.warning(f"⚠️ Step[{from_step}] returned no JSON body; cannot resolve '{dep_key}'.")
                continue

            field_mappings = dep_info.get("field_mappings") or {}

            if field_mappings:
                # Map EXACT theo chỉ định
                for target_field, source_path in field_mappings.items():
                    extracted = self.extract_from_response(source_resp, str(source_path or "").strip())
                    if _is_scalar(extracted):
                        resolved_params[target_field] = str(extracted) if not isinstance(extracted, str) else extracted
                        logger.info(f"✅ Resolved: {target_field} <- {source_path}")
                    else:
                        logger.warning(f"❌ Cannot resolve '{target_field}' from path '{source_path}' (non-scalar/absent).")
            else:
                # Không có field_mappings → thử lấy trực tiếp theo dep_key như một path
                extracted = self.extract_from_response(source_resp, str(dep_key or "").strip())
                if _is_scalar(extracted):
                    resolved_params[dep_key] = str(extracted) if not isinstance(extracted, str) else extracted
                    logger.info(f"✅ Resolved: {dep_key} (direct)")
                else:
                    logger.warning(f"❌ Cannot resolve '{dep_key}' directly (non-scalar/absent).")

        return resolved_params, resolved_body


    # ---------- helpers ----------
    def extract_from_response(self, response_data: Any, path: str) -> Any:
        if not path:
            return response_data
        current = response_data
        if isinstance(current, list) and current:
            current = current[0]
        for key in path.split("."):
            if key == "":
                continue
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, list) and current:
                current = current[0]
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            else:
                return None
        return current

    

    def _cache_parameter_value(self, param_name: str, value: str):
        if value not in self.available_ids_cache[param_name]:
            self.available_ids_cache[param_name].append(value)

    def _extract_id_from_response(self, response_data: dict, param_name: str) -> Optional[str]:
        if param_name in response_data:
            return str(response_data[param_name])
        for key, value in response_data.items():
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    if param_name in first:
                        return str(first[param_name])
                    for id_key in ("id", "Id", "ID"):
                        if id_key in first:
                            p_root = param_name.lower().rstrip("id")
                            k_root = key.lower().rstrip("s")
                            if (
                                p_root == k_root
                                or p_root.startswith(k_root)
                                or k_root.startswith(p_root)
                                or key.lower() in {"items", "data", "results", "list", "records"}
                                or (len(p_root) >= 3 and len(k_root) >= 3 and p_root[:3] == k_root[:3])
                            ):
                                return str(first[id_key])
            elif isinstance(value, dict):
                nested = self._extract_id_from_response(value, param_name)
                if nested:
                    return nested
        return None

    # ---------- preload ----------
    def extract_ids_from_response(self, response_data: Any) -> List[str]:
        ids: List[str] = []
        
        if isinstance(response_data, list):
            for it in response_data:
                if isinstance(it, dict) and "id" in it:
                    ids.append(str(it["id"]))
        elif isinstance(response_data, dict):
            for key in ["data", "items", "results", "holidays", "provinces", "brands", "categories", "products"]:
                if key in response_data and isinstance(response_data[key], list):
                    for it in response_data[key]:
                        if isinstance(it, dict) and "id" in it:
                            ids.append(str(it["id"]))
                    break
            if not ids and "id" in response_data:
                ids.append(str(response_data["id"]))
        return ids

    def convert_endpoint_to_url(self, base_url: str, endpoint: str) -> str:
        if "-" in endpoint and endpoint.split("-")[0].upper() in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
            clean = endpoint.split("-", 1)[1]
        else:
            clean = endpoint
        url = f"{base_url}{clean}"
        return re.sub(r"/\{[^}]+\}$", "", url)

    def auto_discover_dependencies(self, test_cases: List[TestCaseCore]) -> Tuple[set, Dict[str, str]]:
        dependency_endpoints: set = set()
        dependency_mappings: Dict[str, str] = {}
        for test_case in test_cases:
            steps = test_case.steps
            for step in steps:
                deps = step.data_dependencies
                if not deps: 
                    continue
                for dep_key, dep_info in deps.items():
                    if isinstance(dep_info, dict) and "from_step" in dep_info:
                        from_idx = dep_info["from_step"] - 1
                        if 0 <= from_idx < len(steps):
                            src_ep = steps[from_idx].endpoint
                            if src_ep:
                                dependency_endpoints.add(src_ep)
                                dependency_mappings[dep_key] = src_ep
        return dependency_endpoints, dependency_mappings

    def preload_dependencies(
        self,
        base_url: str,
        http: HttpClient,
        dependency_endpoints: set,
        dependency_mappings: Dict[str, str],
    ):
        if not dependency_endpoints:
            logger.info("🔍 No dependencies found in test cases")
            return

        logger.info(f"🔍 Found {len(dependency_endpoints)} dependency endpoints: {list(dependency_endpoints)}")
        total = len(dependency_endpoints)
        for i, ep in enumerate(dependency_endpoints, start=1):
            try:
                url = self.convert_endpoint_to_url(base_url, ep)
                logger.info(f"📡 Preloading ({i}/{total}): {ep} -> {url}")
                start = time.time()
                resp = http.request("GET", url, timeout=10)
                elapsed = time.time() - start
                logger.info(f"    ⏱️  Response time: {elapsed:.2f}s")

                if resp.status_code == 200:
                    data = resp.json()
                    cache_key = ep.replace("get-", "").replace("/", "_").strip("_")
                    self.global_dependency_cache[cache_key] = data

                    ids = self.extract_ids_from_response(data)
                    if ids:
                        for dep_key, src_ep in dependency_mappings.items():
                            if src_ep == ep:
                                self.available_ids_cache[dep_key] = ids[:]  # clone list
                                logger.info(f"    📋 Cached {len(ids)} IDs for {dep_key} (ex: {ids[:3]})")

                    logger.info(f"    ✅ Success ({resp.status_code})")
                else:
                    logger.warning(f"    ❌ Failed ({resp.status_code}): {resp.text[:120]}")
            except Exception as e:
                logger.warning(f"    ❌ Error: {str(e)[:160]}")

        logger.info(f"✅ Preloading complete: {len(self.global_dependency_cache)} endpoints cached")
