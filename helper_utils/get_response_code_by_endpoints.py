import json
import os
from typing import Dict, List

############################
# Helpers
############################

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}

def convert_path_fn(path: str) -> str:
    """
    Turn a swagger path into a safe identifier:
    '/pet/{petId}/upload' -> '_pet_petId_upload'
    (Kept for compatibility; not used in the flat output.)
    """
    return (
        path.replace("/", "_")
            .replace("{", "")
            .replace("}", "")
            .replace("-", "_")
            or "_"
    )

def get_endpoint_id(swagger_spec: dict, endpoint: str) -> str:
    """
    Original signature rule (kept for compatibility/other uses).
    endpoint is 'method-/path/...'
    """
    method = endpoint.split("-")[0]
    path = "-".join(endpoint.split("-")[1:])
    endpoint_spec = swagger_spec["paths"][path][method]
    operation_id = endpoint_spec.get("operationId", method.upper())
    unique_name = f"{convert_path_fn(path)}_{operation_id}"
    return unique_name

def _is_numeric_status(k: str) -> bool:
    return k.isdigit() and len(k) == 3

def _classify(code: str) -> str:
    if not code.isdigit():
        return "other"
    n = int(code)
    if   200 <= n <= 299: return "2xx"
    elif 300 <= n <= 399: return "3xx"
    elif 400 <= n <= 499: return "4xx"
    elif 500 <= n <= 599: return "5xx"
    else:                 return "other"

def _collect_from_spec_flat(swagger_spec: dict) -> Dict[str, dict]:
    """
    Extract response codes from a single swagger/openapi spec.
    Returns a dict keyed by 'method-/path', with only status_codes and by_class.
    """
    out: Dict[str, dict] = {}
    paths = swagger_spec.get("paths", {}) or {}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op_obj in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op_obj, dict):
                continue

            responses = (op_obj.get("responses") or {})
            codes: List[str] = []
            for k in responses.keys():
                if _is_numeric_status(k):
                    codes.append(k)
                # If you also want "default"/vendor keys, uncomment:
                # else:
                #     codes.append(k)

            uniq_codes = sorted(set(codes), key=lambda x: int(x) if x.isdigit() else x)

            by_class = {"2xx": [], "3xx": [], "4xx": [], "5xx": [], "other": []}
            for c in uniq_codes:
                by_class[_classify(c)].append(c)

            endpoint_sig = f"{method}-{path}"
            out[endpoint_sig] = {
                "status_codes": uniq_codes,
                "by_class": by_class,
            }
    return out

############################
# Public API
############################

def collect_response_codes_from_dir(spec_dir: str) -> Dict[str, dict]:
    """
    Scan a directory for swagger/openapi json files (e.g., 'openapi.json'),
    parse them, and merge all endpoints into a single flat dict keyed by 'method-/path'.
    If multiple files define the same endpoint, later files override earlier ones.
    """
    results: Dict[str, dict] = {}

    for fname in os.listdir(spec_dir):
        if not fname.lower().endswith(".json"):
            continue
        fpath = os.path.join(spec_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                spec = json.load(f)
        except Exception:
            continue  # skip unreadable files

        # Basic sanity check it's an OpenAPI/Swagger doc
        if not isinstance(spec, dict) or "paths" not in spec:
            continue

        per_file = _collect_from_spec_flat(spec)
        results.update(per_file)

    return results

############################
# Optional: write to file
############################

def write_response_codes(spec_dir: str, out_json: str) -> Dict[str, dict]:
    data = collect_response_codes_from_dir(spec_dir)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


if __name__ == "__main__":
    services = ["Pet Store"]  # or: ["Bill", "GitLab Branch", ...]
    for service in services:
        spec_dir = r"/Users/npt/Documents/NCKH/restful-api-testing-framework/Database/{}/specs".format(service)
        out_json = r"/Users/npt/Documents/NCKH/restful-api-testing-framework/Database/{}/response_code/response_codes_normalized.json".format(service)
        write_response_codes(spec_dir, out_json)
