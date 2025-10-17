import csv
import logging
import os
import sys
import shutil
import uuid
import random
from io import StringIO
import pandas as pd
import numpy as np
import json
import copy

from kat.data_generator.data_endpoint_dependency import DataEndpointDependency

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
                 working_directory: str = None):
        
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
        
        
        
        odg_dir = r"C:\Users\Admin\Desktop\NCKH\restful-api-testing-framework\database\Bill\ODG"
        
        self.dep = DataEndpointDependency(odg_dir=odg_dir, swagger_spec=swagger_spec)
        self.dep.load_artifacts()
        
        
        # Init root directory
        if not os.path.exists(self.root_dir):
            print(f"[INFO] Creating root directory at {self.root_dir}...")
            os.makedirs(self.root_dir)
            os.makedirs(f"{self.root_dir}/csv")
        else:
            # Delete all files in the directory
            print(f"[INFO] Emptying root directory at {self.root_dir}...")
            shutil.rmtree(self.root_dir)
            os.makedirs(self.root_dir)
            os.makedirs(f"{self.root_dir}/csv")
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
        response = GPTChatCompletion(prompt, system="", temperature=0.0)
        if response:
            self.input_token_count += len(prompt)
            self.output_token_count += len(response)
        return response

    def write_test_data_file(self, new_data: list, data_filename: str, expected_status_code: str, default_reason: str = "") -> None:
        if new_data is None:
            return
        try:
            csv_file_path: str = f"{self.root_dir}/csv/{data_filename}.csv"

            def _row(idx: int, item: dict):
                payload = copy.deepcopy(item) if isinstance(item, dict) else {"data": item}
                reason = ""
                if isinstance(payload, dict):
                    reason = payload.pop("__reason", default_reason) or default_reason
                return {
                    "index": str(idx),
                    "data": json.dumps(payload),
                    "expected_status_code": expected_status_code,
                    "reason": humanize_reason(reason),
                }

            header = ["index", "data", "expected_status_code", "reason"]

            if os.path.exists(csv_file_path):
                with open(csv_file_path, "r+", newline="", encoding="utf-8") as f:
                    # tìm last_index
                    try:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        last_index = int(rows[-1]["index"]) if rows else 0
                    except Exception:
                        last_index = 0
                    f.seek(0, os.SEEK_END)
                    writer = csv.DictWriter(f, fieldnames=header)
                    if f.tell() == 0:
                        writer.writeheader()
                    for i, item in enumerate(new_data):
                        writer.writerow(_row(last_index + i + 1, item))
            else:
                with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    for i, item in enumerate(new_data):
                        writer.writerow(_row(i + 1, item))
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
            llm_expected_code = str(item.get("expected_code", "2xx")).lower()
            reason = item.get("reason", "")

            # Chuẩn hoá payload
            payload = copy.deepcopy(data_payload)
            if not isinstance(payload, dict):
                payload = {"data": payload}
            # Giữ nguyên reason của LLM, KHÔNG thêm [CORRECTED ...]
            payload["__reason"] = reason

            # Phân loại THEO LLM (không theo validator)
            # Hỗ trợ các biến thể: "2xx", "200", "201", ...
            if llm_expected_code.startswith("2"):
                valid_2xx.append(payload)
            else:
                invalid_4xx.append(payload)
                
        return valid_2xx, invalid_4xx
    def _normalize_llm_items(self, items, fallback_source: str):
        """
        Accepts a list returned by parse_jsonl_response().
        Each item may be either:
        - {"data": {...}, "reason": "...", "source": "llm_success|llm_violation"}
        - OR (legacy) a plain dict of payload fields (no wrapper)
        Returns a list of dict payloads, each with __reason embedded.
        """
        if not items:
            return items
        out = []
        for x in items:
            # Case 1: new wrapped shape with "data"
            if isinstance(x, dict) and "data" in x and isinstance(x["data"], dict):
                payload = copy.deepcopy(x["data"])
                src = (x.get("source") or fallback_source or "").strip()
                why = (x.get("reason") or "").strip()
                # combine into __reason
                tag = src if src else "llm"
                if why:
                    payload["__reason"] = f"{tag}: {why}"
                else:
                    payload["__reason"] = tag
                out.append(payload)
            # Case 2: legacy plain payload (no wrapper)
            elif isinstance(x, dict):
                payload = copy.deepcopy(x)
                # No reason from LLM → mark with fallback
                payload.setdefault("__reason", f"{fallback_source or 'llm'}")
                out.append(payload)
            else:
                # For non-dict, wrap as {"data":..., "__reason":...}
                out.append({"data": x, "__reason": f"{fallback_source or 'llm'}"})
        return out

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

    def create_test_data_file_from_swagger(self) -> None:
        amount_instruction = "containing 5 data items,"
        # amount_instruction = ""
        
        if self.selected_endpoints:
            endpoints = self.selected_endpoints
        else:
            endpoints = extract_endpoints(self.swagger_spec)
        
        for endpoint in endpoints:
            param_data_2xx = []
            param_data_4xx = []
            body_data_2xx = []
            body_data_4xx = []
            
            print("Generating data for endpoint:", endpoint, "...")
            # Step 0. Get the method and path from the endpoint string
            method: str = endpoint.split('-')[0]
            path: str = '-'.join(endpoint.split('-')[1:])

            if LOGGED:
                print(f"{endpoint=} -> {method=} {path=}")

            # Step 1. Create the base prompt's smaller parts
            endpoint_data = get_endpoint_data(self.swagger_spec, endpoint)
            
            # Step 2. Generate data in JSON format
            if "parameters" in endpoint_data.get('definition', {}):
                lprint(f"{'*'*100}\nGenerating data for parameters of endpoint: {endpoint}...\n{'*'*100}")
                endpoint_data_parameter_only = copy.deepcopy(endpoint_data)
                if "responses" in endpoint_data_parameter_only:
                    del endpoint_data_parameter_only["responses"]
                if "requestBody" in endpoint_data_parameter_only['definition']:
                    del endpoint_data_parameter_only['definition']['requestBody']
                
                ref_data = ""
                ref_paths = get_all_reference_schema_path_in_endpoint_object(self.swagger_spec, endpoint_data_parameter_only)
                
                for ref_path in ref_paths:
                    path_list = ref_path.split('/')[1:]
                    schema_spec = get_object_from_path(self.swagger_spec, path_list)
                    if schema_spec is not None:
                        ref_data += f"\n\n{ref_path}:\n"
                        ref_data += json.dumps(schema_spec)
                
                # Context about inter-parameter dependency
                param_inter_param_constraints = self.get_inter_param_constraints(endpoint, part="param")
                param_validation_script = ""
                param_inter_param_prompt_context = ""
                param_violate_inter_param_prompt_context = ""
                
                if param_inter_param_constraints == "":
                    print(f"The parameters of endpoint {endpoint} do not have any inter-parameter dependency")
                else:
                    param_validation_script = self.get_inter_param_validation_script(endpoint, part="param", constraints=param_inter_param_constraints)
                    param_inter_param_prompt_context = INTER_PARAM_CONTEXT.format(context=param_inter_param_constraints)
                    param_violate_inter_param_prompt_context = VIOLATE_INTER_PARAM_CONTEXT.format(org_context=param_inter_param_constraints)
                
                if self.generation_mode in ["all", "2xx"]:
                    prompt_2xx        = GET_DATASET_PROMPT.format(
                        amount_instruction = amount_instruction,
                        additional_context=param_inter_param_prompt_context,
                        part="PARAMETERS",
                        additional_instruction=INSTRUCT_SUCCESS.format(part="PARAMETERS"),
                        endpoint_data=json.dumps(endpoint_data_parameter_only),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                    )
                    data_2xx_raw = self.generate_data_items(prompt_2xx)
                    # Validate and correct LLM output
                    if data_2xx_raw:
                        valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(data_2xx_raw, endpoint, "param")
                        
                        # Add valid data to 2xx collection
                        param_data_2xx += valid_2xx
                        
                        # Add invalid data that LLM wrongly classified as 2xx to 4xx collection
                        if invalid_4xx:
                            param_data_4xx += invalid_4xx
                        
                        # Ignore optional combination (only for actually valid data)
                        if valid_2xx:
                            extra = DataMutator.ignore_optional_param_combination(self.swagger_spec, self.swagger_spec_required_fields, valid_2xx[0], endpoint)
                            if extra:
                                # tag riêng cho biết là bản mở rộng từ logic khung
                                extra = self._with_reason(extra, "llm_success_ignore_optional")
                                param_data_2xx += extra


                if self.generation_mode in ["all", "4xx"]:
                    prompt_constraint_violation = GET_DATASET_PROMPT.format(
                        amount_instruction = amount_instruction,
                        additional_context=param_violate_inter_param_prompt_context,
                        part="PARAMETERS",
                        additional_instruction=INSTRUCTION_CONSTRAINT_VIOLATION,
                        endpoint_data=json.dumps(endpoint_data_parameter_only),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                    )
                    data_constraintviolation_raw = self.generate_data_items(prompt_constraint_violation)
                    if data_constraintviolation_raw:
                        # Validate and correct LLM output 
                        valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(data_constraintviolation_raw, endpoint, "param")
                        
                        # Add invalid data to 4xx collection
                        param_data_4xx += invalid_4xx
                        
                        # Add valid data that LLM wrongly classified as 4xx to 2xx collection
                        if valid_2xx:
                            param_data_2xx += valid_2xx


                # Filter data items by the validation script                 
                if param_validation_script: 
                    self.save_val_script(self.get_data_file_path_name(path, method, part="param"), param_validation_script)                        
                    
                    if self.generation_mode in ["all", "2xx"]:
                        param_data_2xx = self.inter_param_dependency_tool.inter_param_data_items_filter(json_data_list=param_data_2xx, validation_script=param_validation_script, filter_valid=True)
                    
                    if self.generation_mode in ["all", "4xx"]:
                        param_data_4xx = self.inter_param_dependency_tool.inter_param_data_items_filter(json_data_list=param_data_4xx, validation_script=param_validation_script, filter_valid=False)
                
                if self.generation_mode in ["all", "4xx"]:
                    # Generate data for only 4xx status code by using mutation
                    if not self.enabled_mutation:
                        params: list = endpoint_data.get('definition', {}).get('parameters', [])
                        if len(params) != 0:
                            # Get 1 row of valid data for parameters using GPT model
                            param_1_item = None
                            if param_data_2xx:
                                param_1_item = param_data_2xx[0]
                            else:
                                new_1_item_data = DataGeneratorUtils.parse_jsonl_response(
                                    self.get_data_from_gpt(GET_DATASET_PROMPT.format(                            
                                        amount_instruction="containing 1 data item,",
                                        additional_context=param_inter_param_prompt_context,
                                        part="PARAMETERS",
                                        additional_instruction=INSTRUCT_SUCCESS,
                                        endpoint_data=json.dumps(endpoint_data_parameter_only),
                                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                                )))
                                if new_1_item_data:
                                    param_1_item = new_1_item_data[0]
                
                            if param_1_item is not None:
                                # Loop into each parameter and mutate the value
                                try:
                                    # 404
                                    base_data_item = copy.deepcopy(param_1_item)
                                    param_404_data = DataMutator.mutate(base_data_item)
                                    
                                    if param_404_data:
                                        param_data_4xx += [param_404_data]

                                    # Missing required
                                    mutated_data = self.mutate_missing_required(endpoint, copy.deepcopy(base_data_item))
                                    # Wrong dtype  
                                    mutated_data += DataMutator.mutate_wrong_dtype(swagger_spec=self.swagger_spec,endpoint_data= endpoint_data_parameter_only, true_data= copy.deepcopy(base_data_item))
                                    # Write to file
                                    if mutated_data:
                                        param_data_4xx += mutated_data
                                    # self.create_test_data_file(mutated_data, 
                                    #                         self.get_data_file_path_name(path, method, part="param"), expected_status_code="4xx")
                                except Exception as e:
                                    lprint("[INFO] Error when trying to mutate parameters: ", e)
                                    pass
                            else:
                                print("[INFO] Param 1-item data is None, skip mutation")


            if "requestBody" in endpoint_data.get("definition", {}) and endpoint_data.get("definition", {}).get("requestBody", {}) is not None:
                lprint(f"{'*'*100}\nGenerating data for request body of endpoint: {endpoint}...\n{'*'*100}")
                endpoint_data_request_body_only = copy.deepcopy(endpoint_data)
                if "responses" in endpoint_data_request_body_only:
                    del endpoint_data_request_body_only["responses"]
                if "parameters" in endpoint_data_request_body_only['definition']:
                    del endpoint_data_request_body_only['definition']['parameters']
                
                ref_data = ""
                ref_paths = get_all_reference_schema_path_in_endpoint_object(self.swagger_spec, 
                                                         endpoint_data_request_body_only)
                
                for ref_path in ref_paths:
                    path_list = ref_path.split('/')[1:]
                    schema_spec = get_object_from_path(self.swagger_spec, path_list)
                    if schema_spec is not None: 
                        ref_data += f"\n\n{ref_path}:\n"
                        ref_data += json.dumps(schema_spec)

                # Context about inter-parameter dependency
                body_inter_param_constraints = self.get_inter_param_constraints(endpoint, part="body")
                body_validation_script = ""
                body_inter_param_prompt_context = ""
                body_violate_inter_param_prompt_context = ""
                
                if body_inter_param_constraints == "":
                    print(f"The body of endpoint {endpoint} do not have any inter-parameter dependency")
                else:
                    body_validation_script = self.get_inter_param_validation_script(endpoint, part="body", constraints=body_inter_param_constraints)
                    body_inter_param_prompt_context = INTER_PARAM_CONTEXT.format(context=body_inter_param_constraints)
                    body_violate_inter_param_prompt_context = VIOLATE_INTER_PARAM_CONTEXT.format(org_context=body_inter_param_constraints)
                            
                if self.generation_mode in ["all", "2xx"]:
                    prompt_2xx        = GET_DATASET_PROMPT.format(
                        amount_instruction = amount_instruction,
                        additional_context=body_inter_param_prompt_context,
                        part="REQUEST BODY",
                        additional_instruction=INSTRUCT_SUCCESS.format(part="REQUEST BODY"),
                        endpoint_data=json.dumps(endpoint_data_request_body_only),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                    )
                    data_2xx_raw = self.generate_data_items(prompt_2xx, enc=False)
                    if data_2xx_raw:
                        # Validate and correct LLM output
                        valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(data_2xx_raw, endpoint, "body")
                        
                        # Add valid data to 2xx collection
                        body_data_2xx += valid_2xx
                        
                        # Add invalid data that LLM wrongly classified as 2xx to 4xx collection
                        if invalid_4xx:
                            body_data_4xx += invalid_4xx
                        
                        # Ignore optional combination (only for actually valid data)
                        if valid_2xx:
                            extra = DataMutator.ignore_optional_param_combination(self.swagger_spec, self.swagger_spec_required_fields, valid_2xx[0], endpoint, for_request_body=True)
                            if extra:
                                extra = self._with_reason(extra, "llm_success_ignore_optional")
                                body_data_2xx += extra

                if self.generation_mode in ["all", "4xx"]:
                    prompt_constraintviolation = GET_DATASET_PROMPT.format(
                        amount_instruction = amount_instruction,
                        additional_context=body_violate_inter_param_prompt_context,
                        part="REQUEST BODY",
                        additional_instruction=INSTRUCTION_CONSTRAINT_VIOLATION,
                        endpoint_data=json.dumps(endpoint_data_request_body_only),
                        ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                    )
                    data_constraintviolation_raw = self.generate_data_items(prompt_constraintviolation, enc=False)
                    if data_constraintviolation_raw:
                        # Validate and correct LLM output
                        valid_2xx, invalid_4xx = self._validate_and_correct_expected_code(data_constraintviolation_raw, endpoint, "body")
                        
                        # Add invalid data to 4xx collection
                        body_data_4xx += invalid_4xx
                        
                        # Add valid data that LLM wrongly classified as 4xx to 2xx collection
                        if valid_2xx:
                            body_data_2xx += valid_2xx

                # Filter data items by the validation script
                if body_validation_script:                    
                    self.save_val_script(self.get_data_file_path_name(path, method, part="body"), body_validation_script)
                    
                    if self.generation_mode in ['all', '2xx']:
                        body_data_2xx = self.inter_param_dependency_tool.inter_param_data_items_filter(body_data_2xx, body_validation_script, filter_valid=True)
                    
                    if self.generation_mode in ['all', '4xx']:
                        body_data_4xx = self.inter_param_dependency_tool.inter_param_data_items_filter(body_data_4xx, body_validation_script, filter_valid=False)
                
                if self.generation_mode in ["all", "4xx"]:
                    if not self.enabled_mutation:
                        
                    # Generate data for only 4xx status code by using mutation
                        if 'requestBody' in self.simplified_swagger_spec[endpoint] and \
                            self.simplified_swagger_spec[endpoint]['requestBody'] is not None and \
                            self.simplified_swagger_spec[endpoint]['requestBody'] != "":
                            
                            body_1_item = None
                            if body_data_2xx:
                                body_1_item = body_data_2xx[0]
                            else:
                                new_1_item_data = self.generate_data_items(GET_DATASET_PROMPT.format(
                                    amount_instruction="containing 1 data item,",
                                    additional_context=body_inter_param_prompt_context,
                                    part="REQUEST BODY",
                                    additional_instruction=INSTRUCT_SUCCESS,
                                    endpoint_data=json.dumps(endpoint_data_request_body_only),
                                    ref_data=f"\nReferenced schemas:\n{ref_data}" if ref_data != "" else "",
                                ), enc=False)
                                if new_1_item_data:
                                    body_1_item = new_1_item_data[0]
                            
                            if body_1_item is not None:
                                base_data_item = copy.deepcopy(body_1_item)
                                ### Mutated by heuristic
                                mutated_data = []
                                # Missing required
                                mutated_data = self.mutate_missing_required(endpoint, copy.deepcopy(base_data_item), for_request_body=True)
                                # Wrong dtype
                                # mutated_data += DataMutator.mutate_wrong_dtype(swagger_spec=self.swagger_spec,endpoint_data= endpoint_data_request_body_only, true_data= copy.deepcopy(base_data_item))
                                
                                if mutated_data:
                                    body_data_4xx += mutated_data
            
            # Balance data items at parameter and request body
            param_data_2xx, body_data_2xx = DataGeneratorUtils.balancing_test_data_item(param_data_2xx, body_data_2xx)
            param_data_4xx, body_data_4xx = DataGeneratorUtils.balancing_test_data_item(param_data_4xx, body_data_4xx)

            if param_data_2xx:
                self.write_test_data_file(param_data_2xx, self.get_data_file_path_name(path, method, part="param"), expected_status_code="2xx")
            if param_data_4xx:
                self.write_test_data_file(param_data_4xx, self.get_data_file_path_name(path, method, part="param"), expected_status_code="4xx")
            if body_data_2xx:
                self.write_test_data_file(body_data_2xx, self.get_data_file_path_name(path, method, part="body"), expected_status_code="2xx")
            if body_data_4xx:
                self.write_test_data_file(body_data_4xx, self.get_data_file_path_name(path, method, part="body"), expected_status_code="4xx")

        # Token count for GPT's test data generation
        self.input_token_count = round(self.input_token_count/4)
        self.output_token_count = round(self.output_token_count/4)
                
###################### Add method to handle inter parameter dependencies ###############################

########################################################################################################

    def create_data(): 

