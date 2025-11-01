import argparse
import copy
import logging
import re
import sys
from typing import Dict

from kat.operation_dependency_graph.odg_generator import ODGGenerator
from shared_config import get_endpoint_schema_dependencies_file_path, get_odg_working_dir, get_operation_sequences_file_path, get_output_dir, get_root_dir, get_test_case_generator_working_dir, get_test_data_working_dir, get_spec_file, get_topolist_file_path
from .response_validation_utils import *
from kat.data_generator.data_generator import TestDataGenerator

from kat.document_parser.document_parser import (
get_delete_operation_store,
)
from kat.utils.llm.gpt.gpt import GPTChatCompletion
from kat.utils.swagger_utils.swagger_utils import (
    add_test_object_to_swagger,
    get_endpoint_id,
    get_endpoint_params,
)
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


def convert_path_fn(path):
    """Convert path to function name format."""
    return path.replace('/', '_').replace('{', '').replace('}', '')


class ObjectRepoGenerator:
    def __init__(self, service_name, collection):
        self.service_name = service_name
        self.collection = collection
        self.object_repo_name = "API"


class TestCaseGenerator():
    def __init__(
        self,
        service_name,
        collection,
        selected_endpoints=None,
        save_prompts=True,
        regenerate_test_data=False,
        data_generation_mode="all",
        clear_test_cases=False,
        working_directory=None,
        headers: Dict[str, str] = None,
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

        if not os.path.exists(get_spec_file(service_name)):
            print(get_spec_file(service_name))
            raise Exception(
                f"Service '{service_name}' not found in {get_spec_file(service_name)}. Please register the service first."
            )

        # Create object repository
        self.object_repository_generator = ObjectRepoGenerator(service_name, collection)
        self.swagger_spec = add_test_object_to_swagger(read_swagger_data(get_spec_file(service_name)))

        self.prepare_testing_directory()
        self.prepare_odg()

        # initialize necessary simplified swagger specs
        self.simplified_swagger = get_endpoint_params(
            self.swagger_spec,
            only_get_parameter_types=True,
            get_test_object=True,
            insert_test_data_file_link=True,
        )
        self.simplified_swagger_param_type_only = get_endpoint_params(
            self.swagger_spec,
            only_get_parameter_types=False,
            get_test_object=False,
            insert_test_data_file_link=False,
        )
        self.simplified_swagger_required_param_only = get_endpoint_params(
            self.swagger_spec,
            get_not_required_params=False,
            get_test_object=False,
            insert_test_data_file_link=False,
        )
        self.simplified_swagger_no_paths = get_endpoint_params(
            self.swagger_spec,
            only_get_parameter_types=True,
        )

        self.endpoints_spec = get_endpoints(self.swagger_spec)
        self.schemas_spec = get_schemas(self.swagger_spec)

        self.ODG = json.load(open(get_operation_sequences_file_path(self.service_name), "r"))
        self.endpoint_schema_dependencies = json.load(open(get_endpoint_schema_dependencies_file_path(self.service_name), "r"))

        self.delete_operations_store = get_delete_operation_store(self.simplified_swagger_param_type_only)

        # write swagger spec simplifier to file
        with open(self.working_directory + f"/simplified_swagger.json", 'w') as file:
            file.write(json.dumps(self.simplified_swagger, indent=2))

    def prepare_odg(self):
        logging.info(f"Preparing ODG for service: {self.service_name}")
        if os.path.exists(get_operation_sequences_file_path(self.service_name)) and os.path.exists(
            get_endpoint_schema_dependencies_file_path(self.service_name)
        ):
            logging.info("ODG files already exist. Skipping ODG generation.")
            return
        odg_generator = ODGGenerator(self.swagger_spec, self.service_name)
        odg_generator.generate_operation_dependency_graph()
        logging.info("ODG prepared and saved.")

    def prepare_testing_directory(self):
        if self.save_prompts:
            self.root_dir = get_root_dir()
            os.makedirs(self.root_dir, exist_ok=True)
            self.output_dir = get_output_dir(self.service_name, "test_cases")
            os.makedirs(self.output_dir, exist_ok=True)

        # Prepare directory for test cases and test data
        self.kat_clone_dir = get_output_dir(self.service_name, "")
        os.makedirs(self.kat_clone_dir, exist_ok=True)

        self.test_cases_path = self.working_directory
        self.test_data_path = get_test_data_working_dir(self.service_name)

        # Only clear test cases if explicitly requested
        if self.clear_test_cases and os.path.exists(self.test_cases_path):
            shutil.rmtree(self.test_cases_path)
            shutil.rmtree(self.odg_dir)
        if self.regenerate_test_data and os.path.exists(self.test_data_path):
            shutil.rmtree(self.test_data_path)

        os.makedirs(self.test_cases_path, exist_ok=True)
        os.makedirs(self.test_data_path, exist_ok=True)

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
                "test_data": test_case_data["test_data"],
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
                "parameter_data": {"data": []},
            },
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
                "body_validation": {},
            },
        }

        # Add parameters
        if 'parameters' in self.simplified_swagger[endpoint]:
            for param, type_ in self.simplified_swagger[endpoint]['parameters'].items():
                if type_ == "PATH VARIABLE":
                    step["path_variables"][param] = None
                else:
                    step["query_parameters"][param] = None

        # Add request body
        if 'requestBody' in self.simplified_swagger[endpoint]:
            step["request_body"] = self.simplified_swagger[endpoint]['requestBody']

        test_case_data["steps"].append(step)
        return test_case_data

    def _simple_schema_dependency_mapping(self, endpoint: str, prev_step_number: int, prev_endpoint: str):
        """
        Original-style, strict mapping:
        - Only use endpoint_schema_dependencies[endpoint][schema] where source field is a simple top-level name (no dots).
        - Build per-target field dependency pointing to the *previous* step.
        - No heuristics, no 'not-sure' placeholders.
        Returns: Dict[target_param, dependency_obj]
        """
        deps_for_endpoint = self.endpoint_schema_dependencies.get(endpoint, {})
        if not deps_for_endpoint:
            return {}

        # Flatten: {target_param: source_field}
        flat: Dict[str, str] = {}
        for _schema, mappings in deps_for_endpoint.items():
            for target_param, source_param in (mappings or {}).items():
                if isinstance(source_param, str) and '.' not in source_param:
                    flat[target_param] = source_param  # keep last wins if duplicated

        if not flat:
            return {}

        result = {}
        for target_param, source_param in flat.items():
            result[target_param] = {
                "from_step": prev_step_number,
                "from_endpoint": prev_endpoint,
                "field_mappings": {
                    target_param: source_param
                }
            }
        return result

    def generate_test_case_core(self, sequence):
        """
        Build steps for a sequence using *only* explicit endpoint_schema_dependencies.
        No guessing, no fallback. If we can't map, we simply don't add a dependency.
        """
        test_case_data = self.generate_individual_endpoint_test_case(endpoint=sequence[0], in_sequence=True)

        for i in range(1, len(sequence)):
            endpoint = sequence[i]
            prev_endpoint = sequence[i - 1]

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

            # Parameters
            if 'parameters' in self.simplified_swagger[endpoint]:
                for param, type_ in self.simplified_swagger[endpoint]['parameters'].items():
                    if type_ == "PATH VARIABLE":
                        step["path_variables"][param] = None
                    else:
                        step["query_parameters"][param] = None

            # Request body
            if 'requestBody' in self.simplified_swagger[endpoint]:
                step["request_body"] = self.simplified_swagger[endpoint]["requestBody"]

            # Dependencies: STRICT explicit mapping only
            # We always reference the *previous* step for simplicity (original style tied retrieval to latest response_i).
            simple_map = self._simple_schema_dependency_mapping(
                endpoint=endpoint,
                prev_step_number=i,          # previous step number (1-based)
                prev_endpoint=prev_endpoint  # previous endpoint sig
            )
            if simple_map:
                step["data_dependencies"] = simple_map

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
        data_generator = TestDataGenerator(
            swagger_spec=self.swagger_spec,
            service_name=self.service_name,
            collection=self.collection,
            selected_endpoints=endpoints,
            generation_mode=self.data_generation_mode,
            working_directory=self.test_data_working_directory,
            headers=self.headers,
        )
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
                            index_of_sequence=i + 1,
                            test_case_data=test_case_data,
                        )
                    else:
                        print(f"[SKIP] Skipped creating test case for sequence {unit_sequence}")
            else:
                single_endpoint_test_case = self.generate_individual_endpoint_test_case(endpoint, in_sequence=False)
                self.create_test_case_json(
                    endpoint=endpoint,
                    index_of_sequence=0,
                    test_case_data=single_endpoint_test_case,
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
            odg_dir=self.odg_dir,
            headers=self.headers,
        )
        data_generator.filter_params_w_descr()
        data_generator.generateData()

        self.test_data_gen_input_token_count = data_generator.input_token_count
        self.test_data_gen_output_token_count = data_generator.output_token_count

    def run(self):
        """Backward-compatible: generate test cases, then (maybe) test data."""
        endpoints_needed_generate_data = self.generate_test_cases()

        # Keep behavior: only generate test data if needed/asked
        if self.regenerate_test_data or not os.path.exists(self.test_data_path) or os.listdir(self.test_data_path) == []:
            self.generate_test_data_for(endpoints_needed_generate_data)

        # Token count for GPT's test script generation
        self.test_script_gen_input_token_count = round(self.test_script_gen_input_token_count / 4)
        self.test_script_gen_output_token_count = round(self.test_script_gen_output_token_count / 4)

        print("Test cases generated successfully!")
