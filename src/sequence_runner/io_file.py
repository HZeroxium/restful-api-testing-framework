# src/sequence_runner/io_files.py
from __future__ import annotations

import csv
import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .models import Paths, TEST_CASE_DIR_NAME

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, service_name: str, base_module_file: str):
        # Ensure we always get project root regardless of where script is called from
        current_file = Path(base_module_file).resolve()
        print(current_file)
        # Navigate up to find project root (contains Dataset/, src/, etc.)
        project_root = current_file
        while project_root.parent != project_root:
            if (project_root / "Dataset").exists() and (project_root / "src").exists():
                break
            project_root = project_root.parent
        
        base_dir = project_root / TEST_CASE_DIR_NAME / service_name

        self.paths = Paths(
            base_dir=base_dir,
            test_case_dir=base_dir / "test_case_generator",
            test_data_dir=base_dir / "TestData/csv",
            topolist_path=base_dir / "ODG/topolist.json",
            output_csv_dir=base_dir / "Result",
            output_dir=(project_root / "Output" / service_name),
        )
        self.paths.output_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(self.paths.output_csv_dir, exist_ok=True)
        self.out_file_name = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + service_name
        self._csv_file =  None
        self._csv_writer = None


    # ---------- Topolist & TestCase ----------
    def load_topolist(self) -> List[str]:
        p = self.paths.topolist_path
        if not p.exists():
            logger.warning(f"Topolist not found: {p}")
            return []
        try:
            # utf-8-sig: nuốt BOM nếu có
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:
            logger.error(f"Failed to read topolist {p}: {e}")
            return []

    def find_test_case_files(self, endpoint_name: Optional[str] = None) -> List[Path]:
        d = self.paths.test_case_dir
        if not d.exists():
            logger.error(f"Test case directory not found: {d}")
            return []
        json_files = list(d.glob("*.json"))
        if endpoint_name:
            filtered = [f for f in json_files if endpoint_name in f.name]
            logger.info(f"Found {len(filtered)} test case files for endpoint filter: {endpoint_name}")
        else:
            filtered = [f for f in json_files if not f.name.startswith("simplified_swagger")]
            logger.info(f"Found {len(filtered)} test case files total")
        return sorted(filtered)

    def load_test_case(self, file: Path) -> Dict[str, Any]:
        try:
            return json.loads(file.read_text(encoding="utf-8-sig"))
        except Exception as e:
            logger.error(f"Failed to read test case {file}: {e}")
            return {}

    # ---------- CSV ----------
    def find_test_data_files(self, endpoint_identifier: str) -> Dict[str, Optional[Path]]:
        cands = {
            "param": [f"{endpoint_identifier}_param.csv", f"_{endpoint_identifier}_param.csv"],
            "body":  [f"{endpoint_identifier}_body.csv",  f"_{endpoint_identifier}_body.csv"],
            "any":   [f"{endpoint_identifier}.csv",       f"_{endpoint_identifier}.csv"],
        }
        found: Dict[str, Optional[Path]] = {"param": None, "body": None}
        for kind, names in cands.items():
            for name in names:
                p = self.paths.test_data_dir / name
                if p.exists():
                    if kind == "any":
                        found["param"] = p
                    else:
                        found[kind] = p
                    break
        if not found["param"] and not found["body"]:
            logger.info(f"No CSV found for endpoint identifier '{endpoint_identifier}' in {self.paths.test_data_dir}")
        return found

    def load_csv_rows(self, csv_file: Optional[Path]) -> List[Dict[str, Any]]:
        if not csv_file:
            return []
        try:
            with csv_file.open("r", encoding="utf-8-sig", newline="") as fp:
                return list(csv.DictReader(fp))
        except Exception as e:
            logger.error(f"Error loading test data from {csv_file}: {e}")
            return []

    # ---------- Output ----------
    def open_csv_output(self, service_name: str):
        out_path = self.paths.output_csv_dir / f"{self.out_file_name}.csv"
        self._csv_file = out_path.open("w", newline="", encoding="utf-8")
        headers = [
            "test_case_id","step_number","endpoint","method",
            "test_data_row","request_params","request_body","final_url",
            "response_status","expected_status","execution_time","status",
        ]
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=headers)
        self._csv_writer.writeheader()
        logger.info(f"CSV output will be saved to: {out_path}")

    def write_csv_row(self, row: Dict[str, Any]):
        if not self._csv_writer:
            logger.warning("CSV writer not initialized. Call open_csv_output() first.")
            return
        self._csv_writer.writerow(row)

    def save_target_response(self, test_case_id: str, data_row_idx: int, payload: Dict[str, Any]):
        case_dir = self.paths.output_dir / f"{test_case_id}_response"
        case_dir.mkdir(parents=True, exist_ok=True)
        fp = case_dir / f"row_{data_row_idx}_target_response.json"
        try:
            fp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write target response {fp}: {e}")

    def close(self):
        try:
            if self._csv_file:
                self._csv_file.close()
        finally:
            self._csv_file = None
            self._csv_writer = None
