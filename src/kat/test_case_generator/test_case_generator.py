import argparse
import copy
import logging
import re
import sys
from typing import Dict

from kat.operation_dependency_graph.odg_generator import ODGGenerator
from .response_validation_utils import *
from kat.data_generator.data_generator import TestDataGenerator
from kat.directory_config.directory_config import get_data_dir_file, get_endpoint_schema_dependencies_file_path, get_odg_working_dir, get_operation_sequences_file_path, get_output_dir, get_root_dir, get_test_case_generator_working_dir, get_test_data_working_dir, get_topolist_file_path
from kat.document_parser.document_parser import extract_endpoints, find_path_to_target, get_delete_operation_store, get_schemas_from_spec
from kat.utils.llm.gpt.gpt import GPTChatCompletion
from kat.utils.swagger_utils.swagger_utils import add_test_object_to_swagger, get_endpoint_id, get_endpoint_params
from .generator_utils import *
sys.path.append('..')

import os
import openai
import shutil
import json
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

import networkx as nx
import datetime

def read_swagger_data(file_path):
    """Read and parse Swagger/OpenAPI JSON file."""
    with open(file_path, 'r', encoding="utf-8") as file:
        return json.load(file)

def get_endpoints(swagger_spec):
    """Extract all endpoints from Swagger spec."""
    endpoints = []
    for path, methods in swagger_spec['paths'].items():
        for method in methods:
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                endpoints.append(f"{method}-{path}")
    return endpoints

def get_schemas(swagger_spec):
    """Extract all schemas from Swagger spec."""
    if 'components' in swagger_spec and 'schemas' in swagger_spec['components']:
        return swagger_spec['components']['schemas']
    return {}

def get_delete_operation_store(simplified_swagger):
    """Get store of delete operations."""
    delete_ops = {}
    for endpoint, spec in simplified_swagger.items():
        if endpoint.startswith('delete-'):
            delete_ops[endpoint] = spec
    return delete_ops

def convert_path_fn(path):
    """Convert path to function name format."""
    return path.replace('/', '_').replace('{', '').replace('}', '')

def get_test_object_path(object_repo_name, operation_id, path):
    """Get test object path."""
    return f"{object_repo_name}/{operation_id}/{path}"

class ObjectRepoGenerator:
    def __init__(self, service_name, collection):
        self.service_name = service_name
        self.collection = collection
        self.object_repo_name = "API"
class TestCaseGenerator():
    def __init__(
        self, service_name, collection, 
        selected_endpoints=None, 
        save_prompts=True, 
        regenerate_test_data=False,
        data_generation_mode="all", 
        clear_test_cases=True,
        headers: Dict[str, str] = None
        ) -> None:
        self.headers = headers
        self.save_prompts = save_prompts
        self.service_name = service_name
        self.collection = collection
        self.selected_endpoints = selected_endpoints
        self.regenerate_test_data = regenerate_test_data
        self.data_generation_mode = data_generation_mode
        self.clear_test_cases = clear_test_cases
        
        self.test_script_gen_input_token_count = 0
        self.test_script_gen_output_token_count = 0
        self.number_of_test_cases_generated = 0
        
        self.test_data_gen_input_token_count = 0
        self.test_data_gen_output_token_count = 0
        self.working_directory = get_test_case_generator_working_dir(service_name)
        self.test_data_working_directory = get_test_data_working_dir(service_name)
        self.odg_dir = get_odg_working_dir(service_name)
        if not os.path.exists(get_data_dir_file(service_name)):
            print(get_data_dir_file(service_name))
            raise Exception(f"Swagger spec file for service {service_name} not found. Please put it according the path: \"Dataset/{service_name}/openapi.json\"")
        
        # Create object repository
        self.object_repository_generator = ObjectRepoGenerator(service_name, collection)        
        self.swagger_spec = add_test_object_to_swagger(read_swagger_data(get_data_dir_file(service_name)))
        self.prepare_testing_directory()

        self.prepare_odg()
        # initialize necessary simplifed swagger specs
        self.simplified_swagger = get_endpoint_params(self.swagger_spec, only_get_parameter_types=True, get_test_object=True, insert_test_data_file_link=True)
        self.simplified_swagger_param_type_only = get_endpoint_params(self.swagger_spec, only_get_parameter_types=False, get_test_object=False, insert_test_data_file_link=False)
        self.simplified_swagger_required_param_only = get_endpoint_params(self.swagger_spec, get_not_required_params=False, get_test_object=False, insert_test_data_file_link=False)
        self.simplified_swagger_no_paths = get_endpoint_params(self.swagger_spec, only_get_parameter_types=True)

        self.endpoints_spec = get_endpoints(self.swagger_spec)
        self.schemas_spec = get_schemas(self.swagger_spec)
        
        self.ODG = json.load(open(get_operation_sequences_file_path(self.service_name), "r"))
        self.endpoint_schema_dependencies = json.load(open(get_endpoint_schema_dependencies_file_path(self.service_name), "r"))
        
        self.delete_operations_store = get_delete_operation_store(self.simplified_swagger_param_type_only)
        
        # write swagger spec simplifier to file
        with open(self.working_directory+f"/simplified_swagger.json", 'w') as file:
            file.write(json.dumps(self.simplified_swagger, indent=2))
    def prepare_odg(self):
        logging.info(f"Preparing ODG for service: {self.service_name}")
        if os.path.exists(get_operation_sequences_file_path(self.service_name)) and os.path.exists(get_endpoint_schema_dependencies_file_path(self.service_name)):
            logging.info(f"ODG files already exist. Skipping ODG generation.")
            return
        odg_generator = ODGGenerator(self.swagger_spec, self.service_name)
        odg_generator.generate_operation_dependency_graph()
        logging.info(f"ODG prepared and saved.")
    def prepare_testing_directory(self):
        if self.save_prompts:
            self.root_dir = get_root_dir()
            os.makedirs(self.root_dir, exist_ok=True)
            self.output_dir = get_output_dir(self.service_name, "test_case_generator")
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Prepare directory for test cases and test data
        self.kat_clone_dir = get_output_dir(self.service_name, "")
        os.makedirs(self.kat_clone_dir, exist_ok=True)
            
        self.test_cases_path = self.working_directory
        self.test_data_path = get_test_data_working_dir(self.service_name)
        
        # Only clear test cases if explicitly requested
        if self.clear_test_cases and os.path.exists(self.test_cases_path): 
            shutil.rmtree(self.test_cases_path)
        if self.regenerate_test_data and os.path.exists(self.test_data_path): 
            shutil.rmtree(self.test_data_path)
        
        os.makedirs(self.test_cases_path, exist_ok=True)
        os.makedirs(self.test_data_path, exist_ok=True)

    def get_primary_schema_for_endpoint(self, endpoint):
        """
        Determine the primary schema returned by an endpoint dynamically.
        This method extracts resource types from endpoint paths and matches them with available schemas.
        """
        # First, try to find exact match in endpoints_belong_to_schemas
        if hasattr(self, 'endpoints_belong_to_schemas'):
            for schema, endpoints in self.endpoints_belong_to_schemas.items():
                if endpoint in endpoints:
                    return schema
        
        # Dynamic schema matching based on endpoint path analysis
        if hasattr(self, 'endpoint_schema_dependencies') and endpoint in self.endpoint_schema_dependencies:
            available_schemas = list(self.endpoint_schema_dependencies[endpoint].keys())
            if available_schemas:
                # Try to match endpoint path with schema names
                best_match = self._find_best_schema_match(endpoint, available_schemas)
                if best_match:
                    return best_match
                # If no good match, return first available
                return available_schemas[0]
        
        # Fallback: analyze all available schemas and find best match
        if hasattr(self, 'endpoint_schema_dependencies') and self.endpoint_schema_dependencies:
            all_schemas = set()
            for ep_deps in self.endpoint_schema_dependencies.values():
                all_schemas.update(ep_deps.keys())
            if all_schemas:
                best_match = self._find_best_schema_match(endpoint, list(all_schemas))
                if best_match:
                    return best_match
                return list(all_schemas)[0]
        
        # Final fallback: try to infer from schemas_spec
        if hasattr(self, 'schemas_spec') and self.schemas_spec:
            best_match = self._find_best_schema_match(endpoint, list(self.schemas_spec.keys()))
            if best_match:
                return best_match
            return list(self.schemas_spec.keys())[0]
        
        return None

    def _find_best_schema_match(self, endpoint, available_schemas):
        """
        Find the best matching schema for an endpoint by analyzing path components.
        Uses fuzzy matching to handle various naming conventions.
        """
        import re
        from difflib import SequenceMatcher
        
        # Extract resource names from endpoint path
        # Remove method prefix and path parameters
        clean_path = endpoint.lower()
        if '-' in clean_path:
            clean_path = clean_path.split('-', 1)[1]  # Remove method prefix like 'get-'
        
        # Remove path parameters like {billId}, {stageId}
        clean_path = re.sub(r'\{[^}]+\}', '', clean_path)
        
        # Extract path segments
        path_segments = [seg for seg in clean_path.split('/') if seg and seg not in ['api', 'v1', 'v2']]
        
        best_schema = None
        best_score = 0
        
        for schema in available_schemas:
            schema_lower = schema.lower()
            score = 0
            
            # Try exact matches first
            for segment in path_segments:
                if segment == schema_lower:
                    score += 10  # High score for exact match
                elif segment.rstrip('s') == schema_lower.rstrip('s'):  # Handle plurals
                    score += 8
                elif schema_lower in segment or segment in schema_lower:
                    score += 5
            
            # Use fuzzy matching for partial matches
            for segment in path_segments:
                similarity = SequenceMatcher(None, segment, schema_lower).ratio()
                if similarity > 0.6:  # 60% similarity threshold
                    score += similarity * 3
            
            # Prefer schemas that contain resource-like words
            if any(word in schema_lower for word in path_segments):
                score += 2
            
            if score > best_score:
                best_score = score
                best_schema = schema
        
        # Only return if we have a reasonable match
        return best_schema if best_score > 1 else None

    def _extract_path_variables(self, endpoint):
        """Extract path variables from endpoint like {billId}, {stageId}"""
        import re
        return re.findall(r'\{(\w+)\}', endpoint)

    def _create_fallback_dependencies(self, step, sequence, step_index):
        """
        Create fallback dependencies for path variables when schema dependencies are not available.
        This analyzes the sequence and tries to infer dependencies based on common patterns.
        """
        path_vars = self._extract_path_variables(step["endpoint"])
        if not path_vars:
            return step
        
        # Analyze previous steps to find potential data sources
        for var in path_vars:
            if var not in step["data_dependencies"]:
                # Try to find dependency from previous steps
                dependency_found = False
                
                for prev_step_idx in range(step_index - 1, -1, -1):
                    prev_step = sequence[prev_step_idx]
                    prev_endpoint = prev_step if isinstance(prev_step, str) else prev_step.get("endpoint", "")
                    
                    # Common patterns for ID dependencies
                    potential_sources = self._infer_id_source_field(var, prev_endpoint)
                    
                    if potential_sources:
                        step["data_dependencies"][var] = {
                            "from_step": prev_step_idx + 1,
                            "field_mappings": {
                                var: potential_sources[0]  # Use first/best match
                            }
                        }
                        dependency_found = True
                        break
                
                if not dependency_found:
                    # Mark as not-sure for runtime resolution
                    step["path_variables"][var] = "%not-sure%"
        
        return step

    def _infer_id_source_field(self, path_var, source_endpoint):
        """
        Infer what field in the source endpoint response might contain the needed ID.
        Returns list of potential field names ordered by likelihood.
        """
        var_lower = path_var.lower()
        potential_fields = []
        
        # Direct mapping: billId -> id, billId -> billId
        potential_fields.append("id")  # Most common
        potential_fields.append(path_var)  # Direct match
        
        # Handle composite IDs like billStageId
        if var_lower.endswith('id'):
            base_name = var_lower[:-2]  # Remove 'id' suffix
            potential_fields.extend([base_name + "Id", base_name + "_id"])
        
        # Analyze source endpoint to understand what it returns
        source_lower = source_endpoint.lower()
        
        # If source returns list of items, likely has 'id' field
        if not any('{' in source_endpoint for _ in ['{}']):  # No path params = list endpoint
            potential_fields.insert(0, "id")  # Prioritize 'id' for list endpoints
        
        # Pattern matching based on endpoint paths
        if 'bill' in var_lower and 'bill' in source_lower:
            potential_fields.extend(["billId", "bill_id"])
        
        if 'stage' in var_lower and 'stage' in source_lower:
            potential_fields.extend(["stageId", "stage_id"])
        
        return list(dict.fromkeys(potential_fields))  # Remove duplicates while preserving order

    def generate_test_case_name(self, endpoint, index_of_sequence=None):
        endpoint_id = get_endpoint_id(self.swagger_spec, endpoint)
        test_case_name = endpoint_id
        
        if index_of_sequence is not None:
            test_case_name += f"_{index_of_sequence}"
        
        i = 1
        unique_test_case_name = test_case_name
        while True:
            unique_test_case_name = f"{test_case_name}_{i}"
            if not os.path.exists(f"{self.test_cases_path}/{unique_test_case_name}.json"):
                break
            i += 1  
        return unique_test_case_name

    def create_test_case_json(self, endpoint, index_of_sequence, test_case_data, to_cover_4xx=False):
        if test_case_data is None:
            return
        
        test_case_name = self.generate_test_case_name(endpoint, index_of_sequence)
        if to_cover_4xx:
            test_case_name += "_404"
            
        test_case = {
            "test_case": {
                "id": test_case_name,
                "name": test_case_name,
                "description": f"Test case for endpoint {endpoint}",
                "endpoint": endpoint,
                "sequence_index": index_of_sequence,
                "expected_status_code": "4xx" if to_cover_4xx else "2xx",
                "steps": test_case_data["steps"],
                "test_data": test_case_data["test_data"]
            }
        }
        
        with open(f"{self.test_cases_path}/{test_case_name}.json", "w") as file:
            json.dump(test_case, file, indent=2)
            
        self.number_of_test_cases_generated += 1

    def generate_individual_endpoint_test_case(self, endpoint, in_sequence=False):
        endpoint_id = get_endpoint_id(self.swagger_spec, endpoint)
        test_case_data = {
            "steps": [],
            "test_data": {
                "body_data": {"data": []},
                "parameter_data": {"data": []}
            }
        }
        
        # Add step for the endpoint
        step = {
            "step_number": 1,
            "endpoint": endpoint,
            "method": endpoint.split("-")[0].upper(),
            "path_variables": {},
            "query_parameters": {},
            "request_body": {},
            "response_validation": {
                "status_code": "2xx",
                "body_validation": {}
            }
        }
        
        # Add parameters
        if 'parameters' in self.simplified_swagger[endpoint]:
            for param, type in self.simplified_swagger[endpoint]['parameters'].items():
                if type == "PATH VARIABLE":
                    step["path_variables"][param] = None
                else:
                    step["query_parameters"][param] = None
                    
        # Add request body
        if 'requestBody' in self.simplified_swagger[endpoint]:
            step["request_body"] = self.simplified_swagger[endpoint]['requestBody']
            
        test_case_data["steps"].append(step)
        
        return test_case_data

    def generate_test_case_core(self, sequence):
        test_case_data = self.generate_individual_endpoint_test_case(endpoint=sequence[0], in_sequence=True)
        
        has_meaningful_dependencies = False
        
        for i in range(1, len(sequence)):
            endpoint = sequence[i]
            endpoint_id = get_endpoint_id(self.swagger_spec, endpoint)
            
            step = {
                "step_number": i + 1,
                "endpoint": endpoint,
                "method": endpoint.split("-")[0].upper(),
                "path_variables": {},
                "query_parameters": {},
                "request_body": {},
                "response_validation": {
                    "status_code": "2xx",
                    "body_validation": {}
                },
                "data_dependencies": {}
            }
            
            # Add parameters
            if 'parameters' in self.simplified_swagger[endpoint]:
                for param, type in self.simplified_swagger[endpoint]['parameters'].items():
                    if type == "PATH VARIABLE":
                        step["path_variables"][param] = None
                    else:
                        step["query_parameters"][param] = None
                        
            # Add request body
            if 'requestBody' in self.simplified_swagger[endpoint]:
                step["request_body"] = self.simplified_swagger[endpoint]['requestBody']
                
            # Add data dependencies - try schema mapping first, then fallback to pattern-based
            schema_dependencies = self.endpoint_schema_dependencies.get(endpoint, {})
            dependencies_added = False
            
            if schema_dependencies:
                # Determine which schema to use based on the previous step's endpoint
                previous_endpoint = sequence[i-1]
                selected_schema = self.get_primary_schema_for_endpoint(previous_endpoint)
                
                # Only add dependency if the selected schema exists and uses simple mapping
                if selected_schema and selected_schema in schema_dependencies:
                    for target_param, source_param in schema_dependencies[selected_schema].items():
                        # Only use simple direct mappings (no dot notation)
                        if '.' not in source_param:
                            step["data_dependencies"][target_param] = {
                                "from_step": i,
                                "field_mappings": {
                                    target_param: source_param
                                }
                            }
                            has_meaningful_dependencies = True
                            dependencies_added = True
            
            # If no schema dependencies were added, try fallback pattern-based dependencies
            if not dependencies_added:
                step = self._create_fallback_dependencies(step, sequence, i)
                if step["data_dependencies"]:
                    has_meaningful_dependencies = True
                    
            test_case_data["steps"].append(step)
        
            
        return test_case_data

    def get_staging_endpoints(self):
        if self.selected_endpoints:
            endpoints = self.selected_endpoints
        else:
            endpoints = get_endpoints(self.swagger_spec)
        
        topo_sorted_endpoint_list = json.load(open(get_topolist_file_path(self.service_name), "r"))
        index_dict = {element: index for index, element in enumerate(topo_sorted_endpoint_list)}
        sorted_staging_endpoint_list = sorted(endpoints, key=lambda x: index_dict.get(x, -1))
        
        not_in_topo_sorted = [x for x in sorted_staging_endpoint_list if x not in index_dict]

        sorted_staging_endpoint_list = [x for x in sorted_staging_endpoint_list if x in index_dict]
        sorted_staging_endpoint_list = not_in_topo_sorted + sorted_staging_endpoint_list
        return sorted_staging_endpoint_list
        
    def generate_test_data(self, endpoints):
        data_generator = TestDataGenerator(swagger_spec=self.swagger_spec, service_name=self.service_name, collection=self.collection, selected_endpoints=endpoints, generation_mode=self.data_generation_mode,
                                           working_directory=self.test_data_working_directory, headers=self.headers)
        data_generator.filter_params_w_descr()
        data_generator.generateData()
        
        self.test_data_gen_input_token_count = data_generator.input_token_count
        self.test_data_gen_output_token_count = data_generator.output_token_count
    def get_endpoints(self):
        return self.endpoints_spec
    def generate_test_cases(self):
        """Only generate test cases. Return endpoints that need test data."""
        staging_endpoints = self.get_staging_endpoints()
        endpoints_needed_generate_data = copy.deepcopy(staging_endpoints)

        for endpoint in staging_endpoints:
            print(f"{'-'*20}Generate test cases for endpoint {endpoint}{'-'*20}")
            sequences = []
            if endpoint in self.ODG:
                sequences = self.ODG[endpoint]

            if len(sequences) > 2:
                sequences = sequences[:2]

            if sequences != []:
                for i in range(len(sequences)):
                    if sequences[i] == []:
                        continue
                    unit_sequence = sequences[i] + [endpoint]
                    endpoints_needed_generate_data += unit_sequence

                    print(f"Sequence {i+1}: {unit_sequence}")
                    test_case_data = self.generate_test_case_core(sequence=unit_sequence)

                    if test_case_data is not None:
                        self.create_test_case_json(
                            endpoint=endpoint,
                            index_of_sequence=i+1,
                            test_case_data=test_case_data
                        )
                    else:
                        print(f"[SKIP] Skipped creating test case for sequence {unit_sequence}")
            else:
                single_endpoint_test_case = self.generate_individual_endpoint_test_case(endpoint, in_sequence=False)
                self.create_test_case_json(
                    endpoint=endpoint, index_of_sequence=0, test_case_data=single_endpoint_test_case
                )

        endpoints_needed_generate_data = list(set(endpoints_needed_generate_data))
        return endpoints_needed_generate_data

    def generate_test_data_for(self, endpoints):
        """Only generate test data for provided endpoints."""
        if not endpoints:
            print("[WARN] No endpoints provided for test data generation.")
            return

        data_generator = TestDataGenerator(
            swagger_spec=self.swagger_spec,
            service_name=self.service_name,
            collection=self.collection,
            selected_endpoints=endpoints,
            generation_mode=self.data_generation_mode,
            working_directory=self.test_data_working_directory,
            odg_dir = self.odg_dir,
            headers=self.headers
        )
        data_generator.filter_params_w_descr()
        data_generator.generateData()

        self.test_data_gen_input_token_count = data_generator.input_token_count
        self.test_data_gen_output_token_count = data_generator.output_token_count
    def run(self):
        """Backward-compatible: generate test cases, then (maybe) test data."""
        endpoints_needed_generate_data = self.generate_test_cases()

        # Giữ hành vi cũ: chỉ generate test data nếu cần/được yêu cầu
        if self.regenerate_test_data or not os.path.exists(self.test_data_path) or os.listdir(self.test_data_path) == []:
            self.generate_test_data_for(endpoints_needed_generate_data)

        # Token count for GPT's test script generation
        self.test_script_gen_input_token_count = round(self.test_script_gen_input_token_count / 4)
        self.test_script_gen_output_token_count = round(self.test_script_gen_output_token_count / 4)

        print("Test cases generated successfully!")