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
NOT_SURE = "%not-sure%"


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
        import random

        resolved_params = params.copy()
        resolved_body = body.copy()

        if not data_dependencies:
            return resolved_params, resolved_body

        for dep_key, dep_info in (data_dependencies or {}).items():
            if not (isinstance(dep_info, dict) and "from_step" in dep_info):
                continue

            from_step = dep_info["from_step"]
            field_mappings = dep_info.get("field_mappings", {}) or {}

            # chọn nguồn dữ liệu
            prev_response = None
            for cache_key, cached_data in self.global_dependency_cache.items():
                if any(token in cache_key.lower() for token in dep_key.lower().split("_")):
                    prev_response = cached_data
                    logger.info(f"  📋 Using global cached '{cache_key}' for dep '{dep_key}'")
                    break

            if not prev_response:
                idx = (from_step - 1)
                if 0 <= idx < len(step_responses) and step_responses[idx]:
                    prev_response = step_responses[idx]
                    logger.info(f"  📋 Using step[{from_step}] response for dep '{dep_key}'")

            if not prev_response and self.global_dependency_cache:
                any_key = next(iter(self.global_dependency_cache.keys()))
                prev_response = self.global_dependency_cache[any_key]
                logger.info(f"  📋 Using fallback cached '{any_key}' for dep '{dep_key}'")

            if not prev_response:
                logger.warning("❌ No cached data available for dependency resolution")
                continue

            if field_mappings:
                for target_field, source_field in field_mappings.items():
                    value = None

                    # nếu đã có list id cache cho target_field thì ưu tiên
                    if self.available_ids_cache.get(target_field):
                        value = random.choice(self.available_ids_cache[target_field])
                        logger.info(f"🎲 Random selected {target_field} = {value}")
                    else:
                        # cố gắng lấy theo 'source_field' (JSON path nhẹ)
                        extracted = self.extract_from_response(prev_response, source_field)

                        # nếu extract trả về list/dict, cố gắng đoán id
                        value = self._guess_scalar_from_any(extracted)
                        if value is None:
                            # fallback: quét nhẹ toàn response để tìm field phù hợp
                            if isinstance(prev_response, dict):
                                for _, v in prev_response.items():
                                    if isinstance(v, (list, dict)):
                                        value = self._guess_scalar_from_any(
                                            self.extract_from_response(v, source_field)
                                        )
                                        if value is not None:
                                            break

                    if value is not None:
                        resolved_params[target_field] = value
                        logger.info(f"✅ Resolved dependency: {target_field} = {value}")
                    else:
                        logger.warning(f"❌ Failed to resolve dependency: {target_field} from {source_field}")
            else:
                # không có field_mappings -> thử lấy trực tiếp theo dep_key
                if self.available_ids_cache.get(dep_key):
                    value = random.choice(self.available_ids_cache[dep_key])
                    resolved_params[dep_key] = value
                    logger.info(f"🎲 Random selected {dep_key} = {value}")
                else:
                    value = self.extract_from_response(prev_response, dep_key)
                    value = self._guess_scalar_from_any(value)
                    if value is not None:
                        resolved_params[dep_key] = value
                        logger.info(f"✅ Resolved dependency: {dep_key} = {value}")

        return resolved_params, resolved_body

    def resolve_not_sure_parameter(self, param_name: str, step_responses: List[Optional[Dict]]) -> Optional[str]:
        if self.available_ids_cache.get(param_name):
            return self.available_ids_cache[param_name][0]

        for resp in step_responses:
            if not isinstance(resp, dict):
                continue
            # direct
            if param_name in resp:
                val = str(resp[param_name])
                self._cache_parameter_value(param_name, val)
                return val
            # heuristic đào sâu
            val = self._extract_id_from_response(resp, param_name)
            if val:
                self._cache_parameter_value(param_name, val)
                return val
        return None

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

    def _guess_scalar_from_any(self, obj: Any) -> Optional[str]:
        """Thử rút ra 1 scalar (ưu tiên 'id') từ obj (dict/list/scalar)."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return str(obj)
        if isinstance(obj, dict):
            if "id" in obj:
                return str(obj["id"])
            # nếu chỉ có 1 key -> lấy luôn
            if len(obj) == 1:
                k, v = next(iter(obj.items()))
                return str(v) if not isinstance(v, (dict, list)) else None
            return None
        if isinstance(obj, list) and obj:
            first = obj[0]
            if isinstance(first, dict):
                if "id" in first:
                    return str(first["id"])
            elif isinstance(first, (str, int, float, bool)):
                return str(first)
        return None

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
