# src/sequence_runner/dependency.py
from __future__ import annotations
import json, logging, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import yaml
import logging
from .get_endpoint_data import ApiDataFetcher
from .helper import _read_json
from .io_file import FileService
from .models import StepModel

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
        self.index_path = self.cache_dir / "_endpoint_sig_cache_response.json"
        self.csv_dir = self.fileService.paths.test_data_dir
        


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
        file_name = endpoint_sig
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
    ) -> None:
        """
        Preload dependency source endpoints and save their responses as
        individual JSON files in the cache_dir.

        Each endpoint's cache file is named:
            <endpoint_sig>.json
        Example:
            get-_projects.json
            get-_projects_{id}_repository_branches.json
        """
        needed_sources: Dict[int, str] = {}
        for step in steps:
            deps = getattr(step, "data_dependencies", None) or {}
            if not deps:
                continue
            for dep_info in deps.values():
                if isinstance(dep_info, dict) and "from_step" in dep_info:
                    src_idx = dep_info["from_step"] - 1
                    if 0 <= src_idx < len(steps):
                        needed_sources[src_idx] = steps[src_idx].endpoint  # de-dup by index

        # 2) Loop through each dependency source
        for src_idx, endpoint_sig in needed_sources.items():
            try:
                cache_path = self.cache_dir / f"{endpoint_sig}.json"

                # Skip if already cached
                if cache_path.exists():
                    logging.info("🔹 Skipping cached endpoint %s", endpoint_sig)
                    continue

                # Prefer step response (if already executed)
                if 0 <= src_idx < len(step_responses) and step_responses[src_idx] is not None:
                    self._write_json(cache_path, step_responses[src_idx])
                    logger.info("✅ Cached endpoint %s from step response -> %s", endpoint_sig, cache_path.name)
                    continue
                # Prepare to fetch
                apiDataFetcher = ApiDataFetcher(
                    swagger_spec=self.swagger_spec,
                    headers=self.headers,
                    csv_dir= Path(self.csv_dir)
                )
                # Fetch via ApiDataFetcher
                try:
                    res = apiDataFetcher.call_api_to_get_data_for_ep(endpoint_sig)
                except Exception as ex:
                    logger.warning("Fetcher failed for %s: %s", endpoint_sig, ex)
                    logging.debug("Error details:", exc_info=True)
                    continue

                if res and res.get("ok"):
                    self._write_json(cache_path, res.get("body"))
                    logger.info("✅ Cached endpoint %s -> %s", endpoint_sig, cache_path.name)
                else:
                    logger.warning("⚠️ Failed to cache endpoint %s (bad response)", endpoint_sig)
                    logging.error("Error details:", res)

            except Exception as ex:
                logger.warning("Error while preloading %s (step %d): %s", endpoint_sig, src_idx + 1, ex)


