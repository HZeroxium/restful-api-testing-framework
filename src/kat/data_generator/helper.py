
import json
from pathlib import Path

from kat.data_generator.models import LoadedArtifacts



def load_artifacts(odg_path) -> LoadedArtifacts:
        """
        Đọc các JSON file kể trên. Thiếu file → trả default rỗng (không raise).
        Trả về một LoadedArtifacts đã chuẩn hoá.
        """

        operation_sequences = _read_json(odg_path / "operation_sequences.json", default={})
        topolist = _read_json(odg_path / "topolist.json", default=[])
        endpoint_schema_dependencies = _read_json(odg_path / "endpoint_schema_dependencies.json", default={})
        endpoints_belong_to_schemas = _read_json(odg_path / "endpoints_belong_to_schemas.json", default={})
        # Chuẩn hoá kiểu dữ liệu tối thiểu
        if not isinstance(operation_sequences, dict):
            operation_sequences = {}
        if not isinstance(topolist, list):
            topolist = []
        if not isinstance(endpoint_schema_dependencies, dict):
            endpoint_schema_dependencies = {}
        if not isinstance(endpoints_belong_to_schemas, dict):
            endpoints_belong_to_schemas = {}

        artifacts = LoadedArtifacts(
            operation_sequences=operation_sequences,
            topolist=topolist,
            endpoint_schema_dependencies=endpoint_schema_dependencies,
            endpoints_belong_to_schemas=endpoints_belong_to_schemas,
        )
        return artifacts



def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return default