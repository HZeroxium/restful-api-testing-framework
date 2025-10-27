import csv
import logging
import os
from pathlib import Path
import sys
import shutil
from typing import Any, Dict, List
import uuid
import random
from io import StringIO
import pandas as pd
import numpy as np
import json
import copy

from kat.data_generator.data_endpoint_dependency import DataEndpointDependency
from kat.data_generator.helper import load_artifacts
from kat.data_generator.models import DependencyContext, LineDataBase, SingleEndpointDetailedResult

# Setup logger
logger = logging.getLogger(__name__)

from .data_generator_utils import DataGeneratorUtils, collect_merged_parameters, humanize_reason
from .data_generator_prompt import GET_DATASET_PROMPT, INSTRUCT_SUCCESS, INSTRUCTION_CONSTRAINT_VIOLATION
from .data_validator import DataValidator
from .mutate_data import DataMutator
from kat.document_parser.document_parser import extract_endpoints, get_all_reference_schema_path_in_endpoint_object, get_endpoint_data, get_object_from_path
from kat.inter_params_dependency.inter_params_dependency import INTER_PARAM_CONTEXT, VIOLATE_INTER_PARAM_CONTEXT, InterParamsDependencyTool
import openai
from kat.utils.swagger_utils.swagger_utils import convert_path_fn
import os, shutil
import argparse

from dotenv import load_dotenv
from kat.utils.llm.gpt.gpt import GPTChatCompletion
from kat.utils.swagger_utils.swagger_utils import find_object_with_key, get_endpoint_id, get_endpoint_params, get_ref, get_required_fields
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY') 

############## Logging #######################
LOGGED = True
def lprint(*x): 
    if LOGGED: print(*x)
def jprint(x):
    if LOGGED: print(json.dumps(x))
##############################################

##############################################
# DATA_GENERATOR_SYSTEM_PROMPT = "You are acting as a data generator for the user. The user will provide the API endpoint Swagger Specification and referenced schemas for your better understanding of the endpoint that they will have to test. The data will be generated based on real-world data as much as possible following the referenced schemas."

##############################################
    
class TestDataGenerator:
    def __init__(self, 
                 swagger_spec: dict, 
                 service_name: str,
                 collection: str,
                 selected_endpoints: list = None,
                 generation_mode: str = "all",
                 working_directory: str = None,
                 odg_dir: str = None,
                 headers: Dict[str, str] = None):
        self.headers = headers
        self.odg_dir = odg_dir
        self.enabled_mutation = False
        self.swagger_spec: dict = swagger_spec
        self.service_name: str = service_name
        self.collection = collection
        self.root_dir: str = working_directory
        self.generation_mode = generation_mode
        self.filtered_endpoint_param_w_descr: dict = {}
        self.selected_endpoints = selected_endpoints
        self.simplified_swagger_spec = get_endpoint_params(self.swagger_spec)
        self.swagger_spec_required_fields = get_required_fields(self.swagger_spec)
        self.input_token_count = 0
        self.output_token_count = 0
        self.mutation_resource = None
        self.inter_param_dependency_tool = InterParamsDependencyTool(self.swagger_spec)
        self.filter_params_w_descr             = self.inter_param_dependency_tool._filter_params_w_descr
        self.get_inter_param_constraints       = self.inter_param_dependency_tool.get_inter_param_constraints
        self.get_inter_param_validation_script = self.inter_param_dependency_tool.get_inter_param_validation_script
        self.odg_dir: Path = Path(odg_dir)


        self.path_operation_sequences: Path = self.odg_dir / "operation_sequences.json"
        self.path_topolist: Path = self.odg_dir / "topolist.json"
        self.path_endpoint_schema_dependencies: Path = self.odg_dir / "endpoint_schema_dependencies.json"
        self.path_endpoints_belong_to_schemas: Path = self.odg_dir / "endpoints_belong_to_schemas.json"
        self.artifacts = load_artifacts(odg_path=self.odg_dir)

        # Init root directory
        # Init root directory (SAFE)
        self.root_dir: str = working_directory
        self.csv_dir = os.path.join(self.root_dir, "csv")
        self.dataEndpointDependency = DataEndpointDependency(headers=self.headers,odg_dir=self.odg_dir, swagger_spec=swagger_spec, artifacts=self.artifacts, csv_dir=self.csv_dir)

        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)

    def get_data_file_path_name(self, path: str, method: str, part: str) -> str:
        """
        Get the name of the data file for the endpoint.
        P/S: Without the extension.

        Args:
            path (str): the path of the endpoint
            method (str): the method of the endpoint
            part (str): "body" or "param"
        Returns:
            str: the name of the data file
        """
        try:
            operation_id = self.swagger_spec['paths'][path][method]['operationId']
        except:
            operation_id = method.upper()

        endpoint_id = "{}_{}".format(
            convert_path_fn(path), 
            operation_id)

        return f"{endpoint_id}_{part}"
          
    def get_actual_successful_response(self):
        """
        đơn giản là nó lấy các file có code 200 trong thư mục mutation_resource
        và lưu vào actual_success_responses 
        ví dụ:
        post_user_create_1.json → { code: 200, text: '{"username": "a", "age": 20}' }

        post_user_create_2.json → { code: 404, text: '{"error": "not found"}' }

        post_user_create_3.json → { code: 200, text: '{"username": "b", "age": "twenty"}' }
        get_actual_successful_response() sẽ:
        Lấy ra file 1 và 3 vì có code == 200

        Gán self.actual_success_responses["post-/user/create"] = [{...}, {...}]
        với list các status code === 200
        """
        if self.mutation_resource is None:
            return None
        
        self.actual_success_responses = {}
        
        endpoints = extract_endpoints(self.swagger_spec)
        for endpoint in endpoints:
            self.actual_success_responses[endpoint] = []
            endpoint_id = get_endpoint_id(self.swagger_spec, endpoint)
            
            for filename in os.listdir(self.mutation_resource):
                if endpoint_id in filename:
                    response = json.load(open(os.path.join(self.mutation_resource, filename), 'r'))
                    if response['code'] == 200:
                        self.actual_success_responses[endpoint].append(json.loads(response['text']))
                        

    def get_data_file_path_name(self, path: str, method: str, part: str) -> str:
        """
        Get the name of the data file for the endpoint.
        P/S: Without the extension.

        Args:
            path (str): the path of the endpoint
            method (str): the method of the endpoint
            part (str): "body" or "param"
        Returns:
            str: the name of the data file
        """
        try:
            operation_id = self.swagger_spec['paths'][path][method]['operationId']
        except:
            operation_id = method.upper()

        endpoint_id = "{}_{}".format(
            convert_path_fn(path), 
            operation_id)

        return f"{endpoint_id}_{part}"
    
    
        
    def get_data_from_gpt(self, prompt: str) -> str:
        response = GPTChatCompletion(prompt, system="", temperature=0.2)
        if response:
            self.input_token_count += len(prompt)
            self.output_token_count += len(response)
        return response

    def write_test_data_file(
        self,
        new_data: list,
        data_filename: str,
        expected_status_code: str,
        default_reason: str = "",
    ) -> None:
        if not new_data:
            return
        try:
            csv_file_path: str = os.path.join(self.csv_dir, f"{data_filename}.csv")

            def _row(idx: int, item: dict):
                payload = copy.deepcopy(item) if isinstance(item, dict) else {"data": item}
                reason = ""
                if isinstance(payload, dict):
                    reason = payload.pop("__reason", default_reason) or default_reason
                return {
                    "index": str(idx),
                    "data": json.dumps(payload, ensure_ascii=False),
                    "expected_status_code": expected_status_code,
                    "reason": humanize_reason(reason),
                }

            header = ["index", "data", "expected_status_code", "reason"]

            # if file exists, read last index, else create with header
            last_index = 0
            if os.path.exists(csv_file_path):
                with open(csv_file_path, "r", newline="", encoding="utf-8") as fr:
                    try:
                        reader = csv.DictReader(fr)
                        rows = list(reader)
                        if rows:
                            last_index = int(rows[-1].get("index", "0")) or 0
                    except Exception:
                        # corrupted/empty? rewrite header fresh
                        last_index = 0

                f = open(csv_file_path, "a", newline="", encoding="utf-8")
                writer = csv.DictWriter(f, fieldnames=header)
            else:
                f = open(csv_file_path, "w", newline="", encoding="utf-8")
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()

            with f:
                for i, item in enumerate(new_data, start=1):
                    writer.writerow(_row(last_index + i, item))

        except Exception as e:
            raise RuntimeError(f"Error when trying to create data file:\n{e}")

    def _with_reason(self, items, reason: str):
        if not items:
            return items
        out = []
        for x in items:
            if isinstance(x, dict):
                y = copy.deepcopy(x)
                y.setdefault("__reason", reason)
                out.append(y)
            else:
                out.append({"data": x, "__reason": reason})
        return out

    def save_val_script(self, filepath: str, content: str):
        if not os.path.exists(self.root_dir+f"/Validation Scripts"):
            os.makedirs(self.root_dir+f"/Validation Scripts")

        with open(self.root_dir+f"/Validation Scripts/{filepath}.py", 'w') as f:
            f.write(content)
            
    
    def _validate_and_correct_expected_code(self, items, endpoint, part="param"):
        if not items:
            return [], []
            
        valid_2xx = []
        invalid_4xx = []
        
        for item in items:
            if not isinstance(item, dict):
                continue

            data_payload = item.get("data", {})
            llm_expected_code = str(item.get("expected_code", "")).strip().lower()
            reason = item.get("reason", "")
            payload = copy.deepcopy(data_payload) if isinstance(data_payload, dict) else {"data": data_payload}
            payload["__reason"] = reason

            # --- FIX: be more tolerant ---
            if not llm_expected_code:
                llm_expected_code = "2xx"
            if llm_expected_code.startswith("2") or llm_expected_code in ["ok", "success"]:
                valid_2xx.append(payload)
            else:
                invalid_4xx.append(payload)
        
        # --- Optional logging to debug ---
        if not valid_2xx:
            logger.warning(f"[WARN] No 2xx items detected for {endpoint} ({part})")
        return valid_2xx, invalid_4xx

    def get_path_parameter_names(self, endpoint):
        """Get list of path parameter names for an endpoint"""
        try:
            from ..document_parser.document_parser import get_endpoint_data
            endpoint_data = get_endpoint_data(self.swagger_spec, endpoint)
            path_params = []
            
            if 'parameters' in endpoint_data.get('definition', {}):
                for param in endpoint_data['definition']['parameters']:
                    if param.get('in') == 'path':
                        path_params.append(param.get('name'))
            
            return path_params
        except Exception as e:
            logger.warning(f"Could not get path parameters for {endpoint}: {e}")
            return []

    def mutate_missing_required(self, endpoint, true_data, for_request_body=False):
        if isinstance(true_data, list):
            true_data = true_data[0]
        if not isinstance(true_data, dict):
            return []

        mutated_data = []
        endpoint_required_fields = self.swagger_spec_required_fields[endpoint]

        param = list(true_data.keys())
        if param == []:
            return mutated_data
        
        # Get path parameter names to exclude from mutation
        path_param_names = self.get_path_parameter_names(endpoint)

        required_fields = []
        required_fields_spec = None
        if for_request_body:
            required_fields_spec = endpoint_required_fields.get("requestBody", None)
        else:
            required_fields_spec = endpoint_required_fields.get("parameters", None)

        if required_fields_spec is not None:
            required_fields = list(required_fields_spec.keys())

        # Filter out path parameters from required fields mutation
        # Path parameters should NEVER be mutated to None as they're always required
        required_fields_to_mutate = [p for p in required_fields if p not in path_param_names]
        
        if path_param_names:
            logger.info(f"Excluding path parameters from mutation: {path_param_names}")
        
        # Miss 1 field (excluding path parameters)
        for p in required_fields_to_mutate:
            data = copy.deepcopy(true_data)
            
            target = data.get("data", data) if isinstance(data.get("data"), dict) else data
            target[p] = None
            if isinstance(data, dict):
                data["__reason"] = f"mutate_missing_required: set {p}=None"
            else:
                data = {"data": data, "__reason": f"mutate_missing_required: set {p}=None"}
            mutated_data.append(data)

        # Miss nhiều field (excluding path parameters)
        for j in range(2, len(required_fields_to_mutate)+1):
            data = copy.deepcopy(true_data)
            target = data.get("data", data) if isinstance(data.get("data"), dict) else data
            dropped = []
            random.shuffle(required_fields_to_mutate)
            for k in range(j):
                if k < len(required_fields_to_mutate):  # Safety check
                    target[required_fields_to_mutate[k]] = None
                    dropped.append(required_fields_to_mutate[k])
            if dropped:  # Only add if we actually dropped some fields
                if isinstance(data, dict):
                    data["__reason"] = f"mutate_missing_required: set {', '.join(dropped)}=None"
                else:
                    data = {"data": data, "__reason": f"mutate_missing_required: set {', '.join(dropped)}=None"}
                mutated_data.append(data)

        mutated_data.reverse()
        return mutated_data


    
    def get_valid_actual_success_response(self, endpoint):
        if self.mutation_resource is None:
            return None
        
        if self.actual_success_responses[endpoint] == []:
            return None
        
        if "requestBody" not in self.simplified_swagger_spec[endpoint] or\
            self.simplified_swagger_spec[endpoint]["requestBody"] is None or\
            self.simplified_swagger_spec[endpoint]["requestBody"] == "":
             return None
         
        def find_dict(lst):
            if lst == [] or lst is None:
                return None

            for item in lst:
                if isinstance(item, dict):
                    return item
                elif isinstance(item, list):
                    # Recursively search within nested lists
                    result = find_dict(item)
                    if result:
                        return result
            return None
        
        for response in self.actual_success_responses[endpoint]:
            if isinstance(response, dict):
                if DataValidator.is_valid_response_schema(self.simplified_swagger_spec[endpoint]["requestBody"], response):
                    return response
            if isinstance(response, list):
                for item in response:
                    dict_item = find_dict(item)
                    if dict_item:
                        if DataValidator.is_valid_response_schema(self.simplified_swagger_spec[endpoint]["requestBody"], dict_item):
                            return dict_item
        return None
    
    
    def generate_data_items(self, prompt, enc=True):
        """_summary_

        Args:
            prompt (_type_): _description_

        Returns:
            _type_: _description_
        """
        i = 3
        while True:
            i -= 1
            data = DataGeneratorUtils.parse_jsonl_response(self.get_data_from_gpt(prompt),enc=enc)

            if data is not None:
                return data
            if i == 0:
                break
        return None
###################### Add method to handle inter parameter dependencies ###############################



    def create_test_data_for_endpoint_and_parse(
        self,
        endpoint_sig: str,
        dependency_block: DependencyContext = None,
        amount_items: int = 10
    ) -> SingleEndpointDetailedResult:
        """
        Sinh test data cho 1 endpoint *không ghi file*, trả về SingleEndpointDetailedResult
        gồm 4 list (param/body × 2xx/4xx) dưới dạng LineDataBase.
        """

        # ---------- helpers ----------
        def _as_line_list(payloads: List[Dict[str, Any]], expected_code: str) -> List[LineDataBase]:
            """
            Convert list payload dicts (may contain '__reason') -> List[LineDataBase]
            expected_code: '2xx' hoặc '4xx'
            """
            out: List[LineDataBase] = []
            idx = 1
            for p in (payloads or []):
                if not isinstance(p, dict):
                    continue
                # tách reason & data
                data = {k: v for k, v in p.items() if k != "__reason"}
                reason = p.get("__reason")
                out.append(LineDataBase(index=idx, expected_code=expected_code, reason=reason, data=data, raw_json=None))
                idx += 1
            return out

        def _merge_ctx(base: str, extra: str) -> str:
            return f"{base}\n\n{extra}" if base and extra else (base or extra)

        # --- NEW: make reasons consistent with the bucket (2xx/4xx) ---
        def _reconcile_reasons(payloads: List[Dict[str, Any]], bucket: str, default_reason: str = None) -> List[Dict[str, Any]]:
            """
            Ensure every payload in `payloads` has __reason aligned to `bucket`.
            If reason is missing or contradicts the bucket, overwrite with a sane default.
            """
            if not payloads:
                return payloads
            bucket = bucket.lower()
            want_2xx = bucket.startswith("2")
            for p in payloads:
                if not isinstance(p, dict):
                    continue
                r = (p.get("__reason") or p.get("reason") or "").strip()
                rl = r.lower()
                if want_2xx:
                    bad = (not r) or ("violate" in rl) or ("invalid" in rl) or ("error" in rl) or ("4xx" in rl)
                    if bad:
                        p["__reason"] = default_reason or "All provided fields satisfy the spec (2xx)."
                    else:
                        p["__reason"] = r
                else:
                    bad = (not r) or ("valid" in rl and "invalid" not in rl) or ("2xx" in rl)
                    if bad:
                        p["__reason"] = default_reason or "One or more fields deliberately violate the spec (4xx)."
                    else:
                        p["__reason"] = r
            return payloads

        # --- NEW: apply a short tag to a list of payloads (kept in __reason) ---
        def _tag_reason(payloads: List[Dict[str, Any]], tag: str) -> List[Dict[str, Any]]:
            if not payloads:
                return payloads
            for p in payloads:
                if isinstance(p, dict):
                    base = (p.get("__reason") or "").strip()
                    p["__reason"] = f"{tag}" + (f": {base}" if base else "")
            return payloads

        # --- NEW: ensure a payload has a reason; if absent, set fallback ---
        def _ensure_reason(p: Dict[str, Any], fallback: str) -> Dict[str, Any]:
            if isinstance(p, dict) and not (p.get("__reason") or p.get("reason")):
                p["__reason"] = fallback
            return p

        # ---------- chuẩn bị ----------
        try:
            method: str = endpoint_sig.split("-")[0]
            path: str = "-".join(endpoint_sig.split("-")[1:])
        except Exception as e:
            raise ValueError(f"Invalid endpoint_sig '{endpoint_sig}': {e}")

        endpoint_data = get_endpoint_data(self.swagger_spec, endpoint_sig)
        if not endpoint_data:
            raise RuntimeError(f"Cannot find endpoint data for: {endpoint_sig}")

        amount_instruction = f"containing {amount_items} data items,"
        # build ref_data cho prompt
        ref_data = ""
        try:
            ref_paths = get_all_reference_schema_path_in_endpoint_object(self.swagger_spec, copy.deepcopy(endpoint_data))
            for ref_path in ref_paths:
                path_list = ref_path.split('/')[1:]
                schema_spec = get_object_from_path(self.swagger_spec, path_list)
                if schema_spec is not None:
                    ref_data += f"\n\n{ref_path}:\n{json.dumps(schema_spec, ensure_ascii=False)}"
        except Exception:
            pass

        # kết quả in-memory
        param_data_2xx: list = []
        param_data_4xx: list = []
        body_data_2xx: list = []
        body_data_4xx: list = []

        # =========================
        # 1) PARAMETERS
        # =========================
        params = (endpoint_data.get("definition", {}) or {}).get("parameters") or []

        if params:
            ep_param_only = copy.deepcopy(endpoint_data)
            ep_param_only.pop("responses", None)
            ep_param_only["definition"].pop("requestBody", None)

            constraints_param = self.get_inter_param_constraints(endpoint_sig, part="param")
            inter_ctx = ""
            violate_ctx = ""
            param_validation_script = ""
            if constraints_param:
                param_validation_script = self.get_inter_param_validation_script(endpoint_sig, part="param", constraints=constraints_param)
                inter_ctx = INTER_PARAM_CONTEXT.format(context=constraints_param)
                violate_ctx = VIOLATE_INTER_PARAM_CONTEXT.format(org_context=constraints_param)

            # 2xx
            prompt_p2 = GET_DATASET_PROMPT.format(
                amount_instruction=amount_instruction,
                additional_context=_merge_ctx(inter_ctx, dependency_block),
                part="PARAMETERS",
                additional_instruction=INSTRUCT_SUCCESS.format(part="PARAMETERS"),
                endpoint_data=json.dumps(ep_param_only, ensure_ascii=False),
                ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
            )

            p2_raw = self.generate_data_items(prompt_p2)
            if p2_raw:
                # normalize/tags before validation split
                p2_raw = _tag_reason(p2_raw, "llm_success")
                valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(p2_raw, endpoint_sig, "param")
                # reconcile reasons with their actual buckets
                param_data_2xx += _reconcile_reasons(valid_2xx, "2xx")
                param_data_4xx += _reconcile_reasons(invalid_4xx, "4xx")

                if valid_2xx:
                    extra = DataMutator.ignore_optional_param_combination(
                        self.swagger_spec, self.swagger_spec_required_fields, valid_2xx[0], endpoint_sig
                    )
                    if extra:
                        extra = _tag_reason(extra, "llm_success_ignore_optional")
                        param_data_2xx += _reconcile_reasons(extra, "2xx", default_reason="Optional parameters omitted while staying valid (2xx).")

            # 4xx
            prompt_p4 = GET_DATASET_PROMPT.format(
                amount_instruction=amount_instruction,
                additional_context=_merge_ctx(violate_ctx, dependency_block),
                part="PARAMETERS",
                additional_instruction=INSTRUCTION_CONSTRAINT_VIOLATION,
                endpoint_data=json.dumps(ep_param_only, ensure_ascii=False),
                ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
            )
            p4_raw = self.generate_data_items(prompt_p4)
            if p4_raw:
                p4_raw = _tag_reason(p4_raw, "llm_violation")
                valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(p4_raw, endpoint_sig, "param")
                param_data_4xx += _reconcile_reasons(invalid_4xx, "4xx")
                param_data_2xx += _reconcile_reasons(valid_2xx, "2xx")

            # validation script filter
            if param_validation_script:
                if param_data_2xx:
                    param_data_2xx = self.inter_param_dependency_tool.inter_param_data_items_filter(
                        param_data_2xx, param_validation_script, filter_valid=True
                    )
                if param_data_4xx:
                    param_data_4xx = self.inter_param_dependency_tool.inter_param_data_items_filter(
                        param_data_4xx, param_validation_script, filter_valid=False
                    )

            # mutation bồi 4xx
            try:
                base_1 = param_data_2xx[0] if param_data_2xx else None
                if not base_1:
                    one_raw = self.generate_data_items(GET_DATASET_PROMPT.format(
                        amount_instruction="containing 1 data item,",
                        additional_context=_merge_ctx(inter_ctx, dependency_block),
                        part="PARAMETERS",
                        additional_instruction=INSTRUCT_SUCCESS,
                        endpoint_data=json.dumps(ep_param_only, ensure_ascii=False),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
                    ))
                    if one_raw:
                        base_1 = one_raw[0]
                        _ensure_reason(base_1, "seed sample for mutations")

                if base_1:
                    # heuristic/out-of-range mutation
                    mutated_404 = DataMutator.mutate(copy.deepcopy(base_1))
                    if mutated_404:
                        _ensure_reason(mutated_404, "heuristic_mutation: out-of-range/invalid primitives")
                        param_data_4xx.append(mutated_404)

                    # missing-required + wrong dtype
                    mutated = self.mutate_missing_required(endpoint_sig, copy.deepcopy(base_1))
                    mutated = [ _ensure_reason(m, "missing_required: at least one required field omitted") for m in (mutated or []) ]

                    mutated += DataMutator.mutate_wrong_dtype(
                        swagger_spec=self.swagger_spec, endpoint_data=ep_param_only, true_data=copy.deepcopy(base_1)
                    ) or []
                    mutated = [ _ensure_reason(m, "mutate_wrong_dtype: set wrong data types") for m in mutated ]

                    if mutated:
                        param_data_4xx += mutated
            except Exception as e:
                logger.info(f"[PARAM] Mutation error: {e}")

        # =========================
        # 2) REQUEST BODY
        # =========================
        if "requestBody" in endpoint_data.get("definition", {}) and endpoint_data["definition"]["requestBody"] is not None:
            ep_body_only = copy.deepcopy(endpoint_data)
            ep_body_only.pop("responses", None)
            ep_body_only["definition"].pop("parameters", None)

            constraints_body = self.get_inter_param_constraints(endpoint_sig, part="body")
            inter_ctx_b = ""
            violate_ctx_b = ""
            body_validation_script = ""
            if constraints_body:
                body_validation_script = self.get_inter_param_validation_script(endpoint_sig, part="body", constraints=constraints_body)
                inter_ctx_b = INTER_PARAM_CONTEXT.format(context=constraints_body)
                violate_ctx_b = VIOLATE_INTER_PARAM_CONTEXT.format(org_context=constraints_body)

            # 2xx
            prompt_b2 = GET_DATASET_PROMPT.format(
                amount_instruction=amount_instruction,
                additional_context=_merge_ctx(inter_ctx_b, dependency_block),
                part="REQUEST BODY",
                additional_instruction=INSTRUCT_SUCCESS.format(part="REQUEST BODY"),
                endpoint_data=json.dumps(ep_body_only, ensure_ascii=False),
                ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
            )
            b2_raw = self.generate_data_items(prompt_b2, enc=False)
            if b2_raw:
                b2_raw = _tag_reason(b2_raw, "llm_success")
                valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(b2_raw, endpoint_sig, "body")
                body_data_2xx += _reconcile_reasons(valid_2xx, "2xx")
                body_data_4xx += _reconcile_reasons(invalid_4xx, "4xx")
                if valid_2xx:
                    extra = DataMutator.ignore_optional_param_combination(
                        self.swagger_spec, self.swagger_spec_required_fields, valid_2xx[0], endpoint_sig, for_request_body=True
                    )
                    if extra:
                        extra = _tag_reason(extra, "llm_success_ignore_optional")
                        body_data_2xx += _reconcile_reasons(extra, "2xx", default_reason="Optional fields omitted while staying valid (2xx).")

            # 4xx
            prompt_b4 = GET_DATASET_PROMPT.format(
                amount_instruction=amount_instruction,
                additional_context=_merge_ctx(violate_ctx_b, dependency_block),
                part="REQUEST BODY",
                additional_instruction=INSTRUCTION_CONSTRAINT_VIOLATION,
                endpoint_data=json.dumps(ep_body_only, ensure_ascii=False),
                ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
            )
            b4_raw = self.generate_data_items(prompt_b4, enc=False)
            if b4_raw:
                b4_raw = _tag_reason(b4_raw, "llm_violation")
                valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(b4_raw, endpoint_sig, "body")
                body_data_4xx += _reconcile_reasons(invalid_4xx, "4xx")
                body_data_2xx += _reconcile_reasons(valid_2xx, "2xx")

            # # validation script filter
            if body_validation_script:
                if body_data_2xx:
                    body_data_2xx = self.inter_param_dependency_tool.inter_param_data_items_filter(
                        body_data_2xx, body_validation_script, filter_valid=True
                    )
                if body_data_4xx:
                    body_data_4xx = self.inter_param_dependency_tool.inter_param_data_items_filter(
                        body_data_4xx, body_validation_script, filter_valid=False
                    )

            # mutation bồi 4xx
            try:
                base_1 = body_data_2xx[0] if body_data_2xx else None
                if not base_1:
                    one_raw = self.generate_data_items(GET_DATASET_PROMPT.format(
                        amount_instruction="containing 1 data item,",
                        additional_context=_merge_ctx(inter_ctx_b, dependency_block),
                        part="REQUEST BODY",
                        additional_instruction=INSTRUCT_SUCCESS,
                        endpoint_data=json.dumps(ep_body_only, ensure_ascii=False),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data else "",
                    ), enc=False)
                    if one_raw:
                        base_1 = one_raw[0]
                        _ensure_reason(base_1, "seed sample for mutations")

                if base_1:
                    mutated = self.mutate_missing_required(endpoint_sig, copy.deepcopy(base_1), for_request_body=True) or []
                    mutated = [ _ensure_reason(m, "missing_required: at least one required field omitted") for m in mutated ]

                    # mở nếu muốn thêm wrong dtype cho body:
                    # wd = DataMutator.mutate_wrong_dtype(self.swagger_spec, ep_body_only, copy.deepcopy(base_1)) or []
                    # wd = [ _ensure_reason(m, "mutate_wrong_dtype: set wrong data types") for m in wd ]
                    # mutated += wd

                    if mutated:
                        body_data_4xx += mutated
            except Exception as e:
                logger.info(f"[BODY] Mutation error: {e}")

        # =========================
        # 3) Cân bằng & convert to model (KHÔNG GHI FILE)
        # =========================
        # Final reconciliation before balancing (paranoia pass)
        param_data_2xx = _reconcile_reasons(param_data_2xx, "2xx")
        body_data_2xx  = _reconcile_reasons(body_data_2xx,  "2xx")
        param_data_4xx = _reconcile_reasons(param_data_4xx, "4xx")
        body_data_4xx  = _reconcile_reasons(body_data_4xx,  "4xx")

        param_data_2xx, body_data_2xx = DataGeneratorUtils.balancing_test_data_item(param_data_2xx, body_data_2xx)
        param_data_4xx, body_data_4xx = DataGeneratorUtils.balancing_test_data_item(param_data_4xx, body_data_4xx)

        result = SingleEndpointDetailedResult(
            endpoint=endpoint_sig,
            param_2xx=_as_line_list(param_data_2xx, "2xx"),
            param_4xx=_as_line_list(param_data_4xx, "4xx"),
            body_2xx=_as_line_list(body_data_2xx, "2xx"),
            body_4xx=_as_line_list(body_data_4xx, "4xx"),
        )
        return result

########################################################################################################
    def print_dependency_context(self,context: DependencyContext):
        print("Schemas in context:")
        for item in context.schemas:
            print(f"- {json.dumps(item)}")
        print("Blocks in context:")
    def generateData(self):
            """
            Chạy theo topo list:
            1) Lấy dependency context cho mỗi endpoint (từ DataEndpointDependency)
            2) Gọi create_test_data_for_endpoint_and_parse(...) để sinh dữ liệu (LineDataBase lists)
            3) Ghi ra 4 file CSV: param/body × 2xx/4xx
            """
            # Chọn danh sách endpoint để chạy

            try:
                topo_list = list(self.artifacts.topolist or [])
            except Exception:
                topo_list = []

            all_endpoints = extract_endpoints(self.swagger_spec)  # e.g. ["get-/a", "post-/b", ...]

            # 2) Append independent endpoints not in topo
            seen = set(topo_list)
            independent = [e for e in all_endpoints if e not in seen]
            list_endpoints =independent + topo_list 
            for ep in list_endpoints:
                logger.info(f"Independent endpoint added to run list: {ep}")
            print(f"Total endpoints to generate data: {len(list_endpoints)}")
            # raise Exception("Disabled full run for safety. Enable when needed.")
            # Helper convert LineDataBase -> dict payload (phù hợp write_test_data_file)
            def _lines_to_payloads(lines):
                out = []
                for ln in (lines or []):
                    try:
                        # LineDataBase: index, expected_code, reason, data, raw_json
                        payload = copy.deepcopy(ln.data) if isinstance(ln.data, dict) else {"data": ln.data}
                        # đưa reason vào __reason để write_test_data_file pop sang cột "reason"
                        if ln.reason:
                            payload["__reason"] = ln.reason
                        out.append(payload)
                    except Exception:
                        continue
                return out

            # Chạy từng endpoint
            summary = []
            for endpoint in list_endpoints:
                try:
                    logger.info(f"Generating data for endpoint: {endpoint}...")

                    # method/path để đặt tên file CSV
                    method: str = endpoint.split("-")[0]
                    path:   str = "-".join(endpoint.split("-")[1:])

                    # Lấy dependency context từ ODG
                    dep_ctx_obj = None
                    try:
                        dep_ctx_obj = self.dataEndpointDependency.get_endpoints_dependency_data(endpoint)
                        self.print_dependency_context(dep_ctx_obj)
                    except Exception as e:
                        logger.warning(f"[WARN] get_endpoints_dependency_data failed for {endpoint}: {e}")


                    # Gọi core generator (trả về SingleEndpointDetailedResult)
                    result = self.create_test_data_for_endpoint_and_parse(
                        endpoint_sig=endpoint,
                        dependency_block=dep_ctx_obj,
                        amount_items=5
                    )

                    # Chuyển LineDataBase -> list[dict] cho writer
                    param_2xx = _lines_to_payloads(getattr(result, "param_2xx", None))
                    param_4xx = _lines_to_payloads(getattr(result, "param_4xx", None))
                    body_2xx  = _lines_to_payloads(getattr(result, "body_2xx", None))
                    body_4xx  = _lines_to_payloads(getattr(result, "body_4xx", None))

                    # Cân bằng số lượng item giữa param/body (giữ nguyên chiến lược cũ)
                    param_2xx, body_2xx = DataGeneratorUtils.balancing_test_data_item(param_2xx, body_2xx)
                    param_4xx, body_4xx = DataGeneratorUtils.balancing_test_data_item(param_4xx, body_4xx)

                    # Ghi file CSV
                    base_param = self.get_data_file_path_name(path, method, part="param")
                    base_body  = self.get_data_file_path_name(path, method, part="body")

                    if param_2xx:
                        self.write_test_data_file(param_2xx, base_param, expected_status_code="2xx")
                    if param_4xx:
                        self.write_test_data_file(param_4xx, base_param, expected_status_code="4xx")
                    if body_2xx:
                        self.write_test_data_file(body_2xx,  base_body,  expected_status_code="2xx")
                    if body_4xx:
                        self.write_test_data_file(body_4xx,  base_body,  expected_status_code="4xx")

                    summary.append({
                        "endpoint": endpoint,
                        "param_2xx": len(param_2xx or []),
                        "param_4xx": len(param_4xx or []),
                        "body_2xx":  len(body_2xx  or []),
                        "body_4xx":  len(body_4xx  or []),
                    })
                    print(f"✓ Done {endpoint}: "
                        f"param(2xx={len(param_2xx or [])},4xx={len(param_4xx or [])}), "
                        f"body(2xx={len(body_2xx or [])},4xx={len(body_4xx or [])})")

                except Exception as e:
                    logger.error(f"[ERROR] Generate data failed for {endpoint}: {e}", exc_info=False)

            # Token count quy đổi “ước lượng” (đã có trong class)
            self.input_token_count  = round(self.input_token_count/4)
            self.output_token_count = round(self.output_token_count/4)

            # Log tổng kết ngắn
            total_rows = sum(s["param_2xx"]+s["param_4xx"]+s["body_2xx"]+s["body_4xx"] for s in summary)
            print(f"\n=== SUMMARY ===")
            print(f"Endpoints processed: {len(summary)}")
            print(f"Total CSV rows: {total_rows}")
            for s in summary:
                print(f"- {s['endpoint']}: "
                    f"param(2xx={s['param_2xx']},4xx={s['param_4xx']}), "
                    f"body(2xx={s['body_2xx']},4xx={s['body_4xx']})")

def read_swagger_data(file_path):
    with open(file_path, 'r', encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    # --- 1. Khởi tạo ---
    swagger_file = r"database/Pet Store/specs/openapi.json"

    odg_dir = r"database/Pet Store/ODG"
    work_dir = r"database/Pet Store"
    
     # --- 2. Đọc swagger_spec ---
    swagger_spec = read_swagger_data(swagger_file)
    testDataGenerator = TestDataGenerator(swagger_spec=swagger_spec,
                                          service_name="Pet Store",
                                          collection="default",
                                          generation_mode="all",
                                          working_directory=work_dir)

    testDataGenerator.generateData()