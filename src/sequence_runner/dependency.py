# src/sequence_runner/dependency.py
from __future__ import annotations
import json, logging, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

import yaml
import logging
from .get_endpoint_data import ApiDataFetcher
from .helper import _read_json
from .io_file import FileService
from .models import DataDependencies, DependencyResolveValue, DependencyResolveValueData, FieldDependency, StepModel

logger = logging.getLogger(__name__)

class DependencyService:
    def __init__(
        self,
        fileService: FileService,
        swagger_spec: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        # in-memory pools (kept tiny)
        self.available_ids_cache: Dict[str, List[str]] = defaultdict(list)

        self.fileService = fileService
        self.swagger_spec = swagger_spec or {}
        self.headers = headers or {}
        # file-backed cache
        self.cache_dir = self.fileService.paths.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir = self.fileService.paths.test_data_dir
    def _cache_file(self, endpoint_sig: str) -> Path:
        return self.cache_dir / f"{self.get_cache_name_from_endpoint_sig(endpoint_sig)}.json"
    
    def _load_cached_body(self, endpoint_sig: str) -> Any:
        fp = self._cache_file(endpoint_sig)
        if not fp.exists():
            return None
        try:
            with fp.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    @staticmethod
    def get_cache_name_from_endpoint_sig(endpoint_sig: str) -> str:
        """
        Convert endpoint signature into a filesystem-safe filename.
        Example:
            get-/projects/{id}/members → get-_projects_{id}_members.json
        """
        sanitized = endpoint_sig.replace("/", "_").replace("{", "").replace("}", "")
        sanitized = sanitized.replace("?", "_").replace(":", "_").replace("\\", "_")
        sanitized = sanitized.replace(" ", "_")
        return sanitized

    @staticmethod
    def _write_json(path: Path, obj: Any) -> None:
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            logger.warning("Failed writing %s: %s", path, ex)
    def _save_cached_response(self, endpoint_sig: str, data: Any) -> None:
        if data is None:
            return
        file_name = f"{self.get_cache_name_from_endpoint_sig(endpoint_sig)}.json"
        fpath = self.cache_dir / file_name
        self._write_json(fpath, data)

        idx = _read_json(self.index_path) or {}
        idx[endpoint_sig] = {
            "file": file_name,
            "saved_at": datetime.now(timezone.utc).isoformat()
        }
        self._write_json(self.index_path, idx)

        # opportunistic id indexing
    def _has_disk_cache(self, endpoint_sig: str) -> bool:
        idx = _read_json(self.index_path)
        meta = (idx or {}).get(endpoint_sig)
        if not meta:
            return False
        f = self.cache_dir / meta.get("file", "")
        return f.exists()
    def preload_endpoints_dependency(
        self,
        steps: List[StepModel],
        step_responses: List[Optional[Dict[str, Any]]],
    ):
        """
        Preload only the producer endpoints needed by the FINAL consumer step,
        then resolve and return a single DependencyResolveValue for that final endpoint.

        - No heuristics, no global side-effects.
        - Strictly extracts values using declared source_field_name paths.
        """
        # --- guard ---
        if not steps:
            return None

        # Final consumer endpoint
        final_consumer = steps[-1].endpoint

        # Build dependencies (for all), then pick only final consumer
        deps_by_consumer = build_data_dependencies(steps)
        consumer_dep = next((d for d in deps_by_consumer if d.endpoint_sig == final_consumer), None)

        # If the final step has no declared dependencies, we don't need to preload anything.
        if not consumer_dep:
            return DependencyResolveValue(endpoint_sig=final_consumer, field_dependency_data=[])

        # Collect the exact producer endpoints needed for the final consumer, preserving first occurrence per step
        # (keyed by producer step index to avoid duplicates)
        producers: Dict[int, str] = {}
        for fd in consumer_dep.field_dependencies:
            src_idx = fd.from_step - 1
            if 0 <= src_idx < len(steps):
                producers.setdefault(src_idx, steps[src_idx].endpoint)

        # Preload each producer
        for src_idx, endpoint_sig in producers.items():
            try:
                cache_path = self._cache_file(endpoint_sig)

                # 1) skip if cached already
                if cache_path.exists():
                    logger.info("🔹 Skipping cached endpoint %s (already cached)", endpoint_sig)
                    continue

                # 2) prefer in-run step response if present
                if 0 <= src_idx < len(step_responses) and step_responses[src_idx] is not None:
                    self._write_json(cache_path, step_responses[src_idx])
                    logger.info("✅ Cached endpoint %s from step response -> %s", endpoint_sig, cache_path.name)
                    continue

                # 3) if this producer itself is also a consumer of earlier producers,
                #    inject only strictly-declared values from already-cached upstream bodies.
                injections: Dict[str, Any] = {}
                inner_consumer_dep = next((d for d in deps_by_consumer if d.endpoint_sig == endpoint_sig), None)
                if inner_consumer_dep:
                    for inner_fd in inner_consumer_dep.field_dependencies:
                        upstream_body = self._load_cached_body(inner_fd.from_endpoint)
                        if upstream_body is None:
                            continue
                        vals = self._extract_many_from_body(upstream_body, inner_fd.source_field_name)
                        if vals:
                            # choose first value deterministically (no randomness, no assumptions)
                            injections[inner_fd.depend_field_name] = vals[0]

                # 4) call API to fetch the producer data and cache the body
                apiDataFetcher = ApiDataFetcher(
                    swagger_spec=self.swagger_spec,
                    headers=self.headers,
                    csv_dir=Path(self.csv_dir),
                )

                try:
                    res = apiDataFetcher.call_api_to_get_data_for_ep(endpoint_sig, dep_values=injections or None)
                except Exception as ex:
                    logger.warning("Fetcher failed for %s: %s", endpoint_sig, ex)
                    logger.debug("Error details:", exc_info=True)
                    continue

                if res and res.get("ok"):
                    self._write_json(cache_path, res.get("body"))
                    logger.info("✅ Cached endpoint %s -> %s", endpoint_sig, cache_path.name)
                else:
                    logger.warning("⚠️ Failed to cache endpoint %s (bad response)", endpoint_sig)
                    logger.error("Error details: %s", res)

            except Exception as ex:
                logger.warning("Error while preloading %s (step %d): %s", endpoint_sig, src_idx + 1, ex)

        # --- Resolve values for the FINAL consumer only (strict extraction) ---
        field_datas: List[DependencyResolveValueData] = []
        for fd in consumer_dep.field_dependencies:
            producer_body = self._load_cached_body(fd.from_endpoint)
            values = _extract_many_from_body(producer_body, fd.source_field_name) if producer_body is not None else []
            field_datas.append(
                DependencyResolveValueData(
                    source_field_name=fd.depend_field_name,  # name at consumer
                    list_value=values,                       # strictly extracted by path
                )
            )

        return DependencyResolveValue(
            endpoint_sig=final_consumer,
            field_dependency_data=field_datas,
        )


def build_data_dependencies(steps: List[StepModel]) -> List[DataDependencies]:
    """
    Build a list of DataDependencies from the given StepModel list.

    Each DataDependencies represents one consumer step (that has data_dependencies),
    and contains FieldDependency items describing how each field depends on earlier steps.
    """
    result: List[DataDependencies] = []

    for consumer_idx, consumer in enumerate(steps):
        deps: Dict[str, Any] = getattr(consumer, "data_dependencies", None) or {}
        if not isinstance(deps, dict) or not deps:
            continue

        field_deps: List[FieldDependency] = []

        for depend_field_name, dep_info in deps.items():
            if not isinstance(dep_info, dict):
                continue

            from_step = dep_info.get("from_step")
            if not isinstance(from_step, int):
                continue

            producer_idx = from_step - 1
            if not (0 <= producer_idx < len(steps)):
                continue

            from_endpoint = steps[producer_idx].endpoint
            field_mappings = dep_info.get("field_mappings", {}) or {}

            # Determine source field name
            if depend_field_name in field_mappings and field_mappings[depend_field_name]:
                source_field = field_mappings[depend_field_name]
            elif len(field_mappings) == 1:
                source_field = next(iter(field_mappings.values()))
            else:
                source_field = depend_field_name  

            field_deps.append(
                FieldDependency(
                    source_field_name=source_field,
                    from_step=from_step,
                    from_endpoint=from_endpoint,
                    depend_field_name=depend_field_name
                )
            )

        if field_deps:
            result.append(
                DataDependencies(
                    step_index=consumer_idx,
                    endpoint_sig=consumer.endpoint,
                    field_dependencies=field_deps
                )
            )

    return result


@staticmethod
def _extract_from_response(resp: Any, path: str) -> Any:
    """Very light JSON-path-ish extractor: supports 'a.b' or top-level 'a'."""
    if resp is None or not path:
        return None
    cur = resp
    # if list, prefer first element
    if isinstance(cur, list) and cur:
        cur = cur[0]
    for key in str(path).split("."):
        if key == "":
            continue
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list) and key.isdigit():
            i = int(key)
            if 0 <= i < len(cur):
                cur = cur[i]
            else:
                return None
        else:
            return None
    return cur
@staticmethod
def _extract_many_from_body(body: Any, field_path: str) -> List[Any]:
    """
    Trả về danh sách giá trị cho field_path.
    - body là list[dict]: lấy theo path cho từng phần tử, gom lại
    - body là dict: trả về 1 phần tử (nếu có)
    - hỗ trợ path 'a.b' và chỉ số list 'items.0.id'
    - khử trùng lặp (giữ thứ tự)
    """
    import json as _json

    def _one(obj: Any, path: str) -> Any:
        cur = obj
        for key in str(path).split("."):
            if not key:
                continue
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            elif isinstance(cur, list) and key.isdigit():
                i = int(key)
                if 0 <= i < len(cur):
                    cur = cur[i]
                else:
                    return None
            else:
                return None
        return cur

    out: List[Any] = []
    if isinstance(body, list):
        for item in body:
            if isinstance(item, (dict, list)):
                v = _one(item, field_path)
                if v is not None:
                    out.append(v)
    elif isinstance(body, (dict, list)):
        v = _one(body, field_path)
        if v is not None:
            out.append(v)

    # de-dup, keep order (works for scalars and JSON-serializable structs)
    seen = set()
    uniq: List[Any] = []
    for v in out:
        key = _json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    return uniq