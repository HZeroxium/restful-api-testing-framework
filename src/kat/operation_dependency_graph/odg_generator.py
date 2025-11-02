import pyvis.network as net
import time
import networkx as nx
import copy

import json
import os
import re

from kat.directory_config.directory_config import get_odg_working_dir, get_output_dir
from kat.operation_dependency_graph.graph_utils.graph_analyzer import Analyzer
from kat.operation_dependency_graph.odg_heuristic import heuristically_generate_dependencies
from kat.operation_dependency_graph.odg_prompting import *
from difflib import SequenceMatcher

from kat.document_parser.document_parser import extract_endpoints
from kat.utils.llm.gpt.gpt import GPTChatCompletion
from kat.utils.swagger_utils.swagger_utils import get_endpoint_params, get_endpoints_belong_to_schemas, get_simplified_schema

# Config create resource endpoints, POST or both POST and GET
class Config():
    def __init__(self, more_create_resource_endpoint=[]) -> None:
        self.create_resource_endpoints = ["post", "get"]
        if more_create_resource_endpoint:
            self.create_resource_endpoints = more_create_resource_endpoint

# Handling GPT's response, in cases the response is not in the correct format
def standardize_string(string):
    string = string.strip()
    string = string.replace('"', "")
    return string

# Extract endpoint-schema dependencies from GPT's response
def extract_relevant_schemas(response):
    pattern = r'(\w+): (\w+ -> \w+)'

    matches = re.findall(pattern, response)

    result = {}
    for match in matches:
        schema_info = {}
        schema_name, schema_details = match
        if schema_details == "None" or schema_details == "Not Found":
            continue
        else:
            schema_details = schema_details.strip()
            param_pairs = schema_details.split(", ")
            for pair in param_pairs:
                params = pair.split(" -> ")
                if len(params) == 2:
                    endpoint_param, schema_param = params
                    endpoint_param = standardize_string(endpoint_param)
                    schema_param = standardize_string(schema_param)
                    schema_info[endpoint_param] = schema_param
                else:
                    print(f"Error: {pair}")
        result[schema_name] = schema_info
    return result

'''
Find create-resource endpints from a set of ones that belong to a cluster
+ Input: set of endpoints
+ Ouput: create-resource endpoints
'''

def find_common_prefix(strings):
    common_prefix = os.path.commonprefix(strings)
    return common_prefix

def remove_path_variables(string):
    pattern = r'\{.*?\}'
    result = re.sub(pattern, '', string)
    return result

def preprocess_string(s):
    s = s.lower()
    s = re.sub(r"[_]", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def levenshtein_ratio(s1, s2):
    return SequenceMatcher(None, s1, s2).ratio()

class ODGGenerator():
    def __init__(self, swagger_spec, service_name) -> None:
        self.swagger_spec = swagger_spec
        self.service_name = service_name
        self.initialize()
    
    def initialize(self):
        self.endpoint_dependencies = [] # Main output
        self.endpoint_schema_dependencies = {} # Endpoints that need to identify its schema dependencies (Prompt-based)
        self.schema_dependencies = {} # Schemas that need to identified its prerequisite schemas (need to created before) (Prompt-based)
        self.endpoints_belong_to_schemas = {} # Find success response schemas (return 2xx status code) of API endpoints, not recursive (Algorithmic-based)

        self.input_token_count = 0
        self.output_token_count = 0
        self.working_directory = get_odg_working_dir(self.service_name)
        self.simplified_swagger = get_endpoint_params(self.swagger_spec, get_not_required_params=False, get_description=True)
        
        self.simplified_schemas = get_simplified_schema(self.swagger_spec)
        self.path_common_prefix = find_common_prefix(list(self.swagger_spec["paths"].keys()))
        

        with open(self.working_directory + "simplified_swagger_required_params_only.json", "w") as file:
            json.dump(self.simplified_swagger, file, indent=2)

    def prepare_working_directory(self):
        os.makedirs(self.working_directory, exist_ok=True)
    def find_endpoints_creating_resource(self, endpoints_in_schema, config=Config()):
        endpoint_creating_resource = []
        independent_endpoint_creating_resource = []
        for endpoint in endpoints_in_schema:
            method = endpoint.split("-")[0]
            if method in config.create_resource_endpoints:
                endpoint_creating_resource.append(endpoint)
                
                if not self.endpoint_schema_dependencies.get(endpoint, []):
                    independent_endpoint_creating_resource.append(endpoint)
                    
        if independent_endpoint_creating_resource:
            return independent_endpoint_creating_resource
        return endpoint_creating_resource 
    '''
    GPT_generate_schema_dependencies
        Each schema needs to find its prerequisite schemas, that need to be created before.
        Object: Available schemas in self.endpoints_belong_to_schemas (success response schemas)
        Output: self.schema_dependencies # dict
    '''    
    def GPT_generate_schema_dependencies(self):
        """
        Prompt GPT to generate schema dependencies

        Returns
        -------
        dict
            self.schema_dependencies. Key: schema name, value: list of schema names that need to be created before
        """
        base_prompt = SCHEMA_SCHEMA_DEPENDENCY_PROMPT

        schema_list = list(self.simplified_schemas.keys())
        schema_dependencies = {}
        for schema in schema_list:
            if schema not in schema_dependencies:
                schema_dependencies[schema] = []
            
            # find uncoverred dependency schemas
            all_spec_schemas = set(schema_list)
            coverred_schema_set = set(schema_dependencies[schema])
            uncoverred_schema_list = list(all_spec_schemas - coverred_schema_set)
            
            # divide schemas into groups within 5 schemas for each one
            schema_groups = [uncoverred_schema_list[i:i+5] for i in range(0, len(uncoverred_schema_list), 5)]
            
            for schemas in schema_groups:
                simplified_schemas = {schema_i: self.simplified_schemas[schema_i] for schema_i in schemas}
                prompt = base_prompt.format(specific_schema=f"{schema}:\n{self.simplified_schemas[schema]}", simplified_schemas=simplified_schemas)
                
                self.input_token_count += len(prompt)
                response = GPTChatCompletion(prompt, system="", temperature=0.0)
                with open(self.working_directory + " debug " + f"schema_dependency.txt", "a") as file:
                    file.write(f"Prompt for {schema}:\n{prompt}\n")
                    file.write(f"Response for {schema}:\n{response}\n")
                if response:
                    self.output_token_count += len(response)
            
                respond_schemas = response.split("\n")
                respond_schemas = [schema_dependency.strip() for schema_dependency in respond_schemas if schema_dependency.strip() in self.simplified_schemas and schema_dependency.strip() != schema]
                
                # update schema-schema dependency dictionary
                schema_dependencies[schema].extend(respond_schemas)
                for res_schema in respond_schemas:
                    if res_schema not in schema_dependencies:
                        schema_dependencies[res_schema] = [schema]
                    elif schema not in schema_dependencies[res_schema]:
                        schema_dependencies[res_schema].append(schema)

        return schema_dependencies 

    def analyze_schema_structure(self, schema_name, schema_data, prefix=""):
        """
        Analyze schema structure to find all possible field paths including nested ones
        Returns a list of possible field paths like ['id', 'name', 'items.id', 'items.name', 'items.categories.id']
        """
        field_paths = []
        
        if not isinstance(schema_data, dict):
            return field_paths
            
        for field_name, field_info in schema_data.items():
            current_path = f"{prefix}.{field_name}" if prefix else field_name
            field_paths.append(current_path)
            
            # If this field references an array of objects, analyze the nested structure
            if isinstance(field_info, dict):
                if field_info.get('type') == 'array' and 'items' in field_info:
                    # Array of objects - analyze the item structure
                    items_schema = field_info['items']
                    if isinstance(items_schema, dict) and 'properties' in items_schema:
                        nested_paths = self.analyze_schema_structure(f"{schema_name}_{field_name}", items_schema['properties'], current_path)
                        field_paths.extend(nested_paths)
                elif 'properties' in field_info:
                    # Nested object - analyze its properties
                    nested_paths = self.analyze_schema_structure(f"{schema_name}_{field_name}", field_info['properties'], current_path)
                    field_paths.extend(nested_paths)
            elif isinstance(field_info, str) and field_info.startswith('#/components/schemas/'):
                # Reference to another schema - we could resolve this but keeping it simple for now
                field_paths.append(f"{current_path}.id")  # Common pattern
                
        return field_paths


    def enhance_schema_context_with_paths(self, schema_name, schema_data):
        """
        Enhance schema context by adding possible nested paths
        """
        try:
            if schema_name not in self.simplified_schemas:
                return f"{schema_name}: {schema_data}"
                
            # Get original schema from swagger to analyze full structure
            original_schema = self.swagger_spec.get('components', {}).get('schemas', {}).get(schema_name, {})
            
            if original_schema and 'properties' in original_schema:
                possible_paths = self.analyze_schema_structure(schema_name, original_schema['properties'])
            else:
                possible_paths = []
            
            enhanced_context = f"{schema_name}: {schema_data}"
            if possible_paths:
                paths_with_id = [path for path in possible_paths if path.endswith('.id') or path == 'id']
                if paths_with_id:
                    enhanced_context += f"\n  Available nested ID paths: {', '.join(paths_with_id)}"
                    
            return enhanced_context
            
        except Exception as e:
            print(f"[DEBUG] Error enhancing schema context for {schema_name}: {e}")
            return f"{schema_name}: {schema_data}"

    '''
    GPT_infer_endpoint_schema_dependencies
        Each endpoint needs to be find its schema dependencies by mapping parameter names
        Object: 
            + Endpoints: have required parameters
            + Schemas: Available schemas in self.endpoints_belong_to_schemas (success response schemas)
        Output: self.endpoint_schema_dependencies # dict
    '''
    def GPT_infer_endpoint_schema_dependencies(self):
        base_prompt = OPERATION_SCHEMA_DEPENDENCY
        
        endpoint_parameters = {}
        for endpoint in self.simplified_swagger:
            if "parameters" not in self.simplified_swagger[endpoint]:
                continue
            endpoint_parameters[endpoint] = {}
            
            if "summary" in self.simplified_swagger[endpoint]:
                endpoint_parameters[endpoint]['summary'] = self.simplified_swagger[endpoint]['summary']
            endpoint_parameters[endpoint]['parameters'] = self.simplified_swagger[endpoint]["parameters"]
    
        endpoint_schema_dependencies = {}
        for endpoint in endpoint_parameters:
            endpoint_schema_dependencies[endpoint] = {}
            specific_endpoint_params = f"{endpoint}: {endpoint_parameters[endpoint]}"
            
            ranked_schemas = self.get_best_mathching_schema(endpoint)
            
            no_of_input_params = len(self.simplified_swagger[endpoint]["parameters"])
            if 2*no_of_input_params > 5 and 2*no_of_input_params < len(ranked_schemas):
                ranked_schemas = ranked_schemas[:2*no_of_input_params]
            else:
                ranked_schemas = ranked_schemas[:5]
            
            number_of_schemas_in_group = 5
            schema_groups = [list(ranked_schemas)[i:i+number_of_schemas_in_group] for i in range(0, len(ranked_schemas), number_of_schemas_in_group)]
                
            # Generate descriptions of the endpoint's parameters
            prompt = GET_PARAM_DESCRIPTION_PROMPT.format(specific_endpoint_params=specific_endpoint_params)
            parameter_description = GPTChatCompletion(prompt, system="", temperature=0.0)
            if parameter_description:
                self.input_token_count += len(prompt)
                self.output_token_count += len(parameter_description)
                parameter_description = f"\nThe following provides more detailed descriptions of the endpoint's parameters:\n{parameter_description}"
            else:
                parameter_description = ""
            
            for schemas in schema_groups:
                # Create context about schema
                schema_context = ""
                for schema in schemas:
                    schema_context += f"\n{schema}: {self.simplified_schemas[schema]}"
                
                prompt = base_prompt.format(specific_endpoint_params=specific_endpoint_params, parameter_description=parameter_description, simplified_schemas=schema_context)
                
                response = GPTChatCompletion(prompt, system="", temperature=0.0)
                if response:
                    self.input_token_count += len(prompt)
                    self.output_token_count += len(response)
            
                    endpoint_schema_dependencies[endpoint].update(extract_relevant_schemas(response))

        return endpoint_schema_dependencies
    
    '''
        Check if an endpoint has schema dependency or not?
            If exists a schema dependency, the endpoint will be available in self.endpoint_schema_dependencies dict
    '''
    def has_schema_dependency(self, endpoint):
        if endpoint not in self.endpoint_schema_dependencies:
            return False
        if not self.endpoint_schema_dependencies[endpoint]:
            return False
        return True

    '''
        Check if a dependency establishment is valid or not
        We need to discuss this function further!
    '''
    '''
        Check if a dependency establishment is valid or not
        We need to discuss this function further!
    '''
    def is_valid_dependency(self, preceeding_endpoint, endpoint):
        if preceeding_endpoint == endpoint:
            return False
        
        # Tách phương thức và đường dẫn
        try:
            pre_method, pre_path = preceeding_endpoint.split("-", 1)
            cur_method, cur_path = endpoint.split("-", 1)
        except ValueError:
            return False # Xử lý các endpoint có tên không hợp lệ

        # SỬA LỖI: Chặn logic ngược "con" -> "cha"
        # Ví dụ: producer "post-/projects/{id}/branches" (con)
        #         consumer "post-/projects" (cha)
        # Đường dẫn của con (/projects/{id}/branches) BẮT ĐẦU BẰNG đường dẫn của cha (/projects)
        if pre_path.startswith(cur_path) and pre_path != cur_path:
            return False

        # chặn GET-/X -> POST-/X (Logic cũ của bạn)
        if pre_method == "get" and cur_method == "post":
            u = pre_path.split("/{")[0]
            v = cur_path.split("/{")[0]
            if u == v:
                return False
        
        return True

    
    '''
        Find relevant schemas of an schema from self.schema_dependencies dict
        Relevants: Dependent schemas of this one and schemas that depends on this one
    '''
    def find_relevant_schemas_of_schema(self, schema_name):
        relevant_schema = []
        if schema_name in self.schema_dependencies:
            relevant_schema.extend(self.schema_dependencies[schema_name])

        for schema in self.schema_dependencies:
            if schema_name in self.schema_dependencies[schema]:
                relevant_schema.append(schema)

        return relevant_schema
    
    '''
        Main function generates endpoint dependencies
    '''
    def generate_endpoint_dependencies(self):
            self.endpoints_belong_to_schemas = get_endpoints_belong_to_schemas(self.swagger_spec)
            self.endpoint_schema_dependencies = self.GPT_infer_endpoint_schema_dependencies()
            # self.schema_dependencies = self.GPT_generate_schema_dependencies()
            
            # Generate endpoint dependencies
            endpoints = extract_endpoints(self.swagger_spec)
            for endpoint in endpoints:
                # If the endpoint does not have any required parameters, skip it
                if "parameters" not in self.simplified_swagger[endpoint]:
                    continue
                
                # Get the endpoint's required parameters
                parameters = list(self.simplified_swagger[endpoint]["parameters"].keys())
                
                # If the endpoint does not have any schema dependencies, skip it. Sometimes, it has required parameters but does not have any dependencies. We can discuss further.
                if self.has_schema_dependency(endpoint):
                    # Get schema dependencies of the endpoint
                    schema_dependencies_of_endpoint = copy.deepcopy(self.endpoint_schema_dependencies[endpoint])
                    name_schema_dependencies_of_endpoint = list(schema_dependencies_of_endpoint.keys())
                    
                    # Config valid create resource endpoints
                    config_create_source_endpoint = Config()
                    
                    visited_schemas = []
                    print(f"Schemas to find dependencies: {name_schema_dependencies_of_endpoint}")
                    for schema_name in self.endpoint_schema_dependencies[endpoint]:
                        visited_schemas.append(schema_name)
                        print(f"Visited schemas: {visited_schemas}")
                        parameter_dependencies = list(schema_dependencies_of_endpoint[schema_name].keys())
                        print(f"Parameters need to be retrieved from schema {schema_name}: {parameter_dependencies}")
                        for param in parameter_dependencies:
                            found_dependency = False
                            if param in parameters:
                                if schema_name in self.endpoints_belong_to_schemas:
                                    print(f"Find dependencies at schema {schema_name}")
                                    dependency_candidates = self.endpoints_belong_to_schemas[schema_name]
                                    create_resource_endpoints = self.find_endpoints_creating_resource(dependency_candidates, config=config_create_source_endpoint)

                                    if create_resource_endpoints:
                                        print(f"Found dependency candidates: {create_resource_endpoints}")
                                        print(f"Accepted dependency candidates:")
                                        for preceeding_endpoint in create_resource_endpoints:
                                            if self.is_valid_dependency(preceeding_endpoint, endpoint) and (preceeding_endpoint, endpoint) not in self.endpoint_dependencies:
                                                self.endpoint_dependencies.append((preceeding_endpoint, endpoint))
                                                found_dependency = True
                            else:
                                print(f"Parameter {param} does not exist in {endpoint}")
                            
                            if found_dependency:
                                parameters.remove(param)
                                parameter_dependencies.remove(param)
                        if not parameter_dependencies:
                            name_schema_dependencies_of_endpoint.remove(schema_name)
                    
                    
                #     # If there are still parameters left, we need to find dependencies through the schema dependencies
                #     while parameters:
                #         print(f"Parameters are leaving: {parameters}")
                #         schema_schema_dependencies_of_endpoint = []
                #         for schema in name_schema_dependencies_of_endpoint:
                #             if schema in self.schema_dependencies:
                #                 schema_schema_dependencies_of_endpoint.extend(self.schema_dependencies[schema])
                #         schema_schema_dependencies_of_endpoint = list(set(schema_schema_dependencies_of_endpoint) - set(visited_schemas))
                        
                #         print(f"Found dependencies via schema dependencies: {schema_schema_dependencies_of_endpoint}")
                #         if not schema_schema_dependencies_of_endpoint:
                #             break
                        
                #         for schema_name in schema_schema_dependencies_of_endpoint:
                #             visited_schemas.append(schema_name)
                #             found_dependency = False
                #             if schema_name not in self.endpoints_belong_to_schemas:
                #                 continue
                #             create_resource_endpoints = find_endpoints_which_create_resource(self.endpoints_belong_to_schemas[schema_name], config=config_create_source_endpoint)
                #             if create_resource_endpoints:
                #                 for dep_endpoint in create_resource_endpoints:
                #                     if self.is_valid_dependency(endpoint, dep_endpoint) and (dep_endpoint, endpoint) not in self.endpoint_dependencies:
                #                         self.endpoint_dependencies.append((dep_endpoint, endpoint))
                    
                #     if parameters:
                #         print(f"Parameters left a dependency: {parameters}")                  
                # else:
                #     print(f"Can not find schema dependency for {endpoint}")
                    
            # Write documents to Tests dir
            with open(f"{self.working_directory}" + "endpoint_dependencies.txt" , 'w') as file:
                for item in self.endpoint_dependencies:
                    line = f"{item[0]}, {item[1]}\n"
                    file.write(line)
                    
            endpoints_belong_to_schemas_path = self.working_directory + "endpoints_belong_to_schemas.json"
            with open(endpoints_belong_to_schemas_path, "w") as f:
                json.dump(self.endpoints_belong_to_schemas, f, indent=2)
            with open(self.working_directory + "endpoints_belong_to_schemas.json", "w") as f:
                json.dump(self.endpoints_belong_to_schemas, f, indent=2)
                
            # schema_dependencies_path = self.save_dir + "schema_dependencies.json"
            # with open(schema_dependencies_path, "w") as f:
            #     json.dump(self.schema_dependencies, f, indent=2)          
            # print(f"{'-'*20}\nSchema-dependencies saved to {schema_dependencies_path}\n{'-'*20}")
                
            endpoint_schema_dependencies_path = self.working_directory + "endpoint_schema_dependencies.json"
            with open(endpoint_schema_dependencies_path, "w") as f:
                json.dump(self.endpoint_schema_dependencies, f, indent=2)
            with open(self.working_directory + "endpoint_schema_dependencies.json", "w") as f:
                json.dump(self.endpoint_schema_dependencies, f, indent=2)
                
            # Token counts
            self.input_token_count = round(self.input_token_count/4)
            self.output_token_count = round(self.output_token_count/4)
        
    def get_best_mathching_schema(self, operation):
        if "parameters" not in self.simplified_swagger[operation]:
            return []

        similarity_score_array = [0]*len(self.simplified_schemas)
        
        endpoint = "-".join(operation.split('-')[1:])
        endpoint = endpoint.replace(self.path_common_prefix, "")
        endpoint = remove_path_variables(endpoint)
        endpoint = preprocess_string(endpoint)
        
        schema_list = list(self.simplified_schemas.keys())
        for p in self.simplified_swagger[operation]["parameters"]:
            base_str = f"{p}_{endpoint}"
            for schema_i, schema in enumerate(schema_list):
                schema_name = schema.lower()
                similarity_score_array[schema_i] += max([levenshtein_ratio(base_str, f"{schema_field}_{schema_name}") for schema_field in self.simplified_schemas[schema]]+[0])
        
        sort_object = sorted(zip(similarity_score_array, schema_list), reverse=True)
        _, sorted_schemas = zip(*sort_object)
        return list(sorted_schemas)
    def save_graph_to_test_dir(self, GPT_ODG, heuristic_ODG):
        save_dir = self.working_directory
        os.makedirs(save_dir, exist_ok=True)  # Đảm bảo thư mục tồn tại
        # Save the graph to a file (GraphML format)
        nx.write_graphml(GPT_ODG, save_dir + "GPT_ODG.graphml")
        print("GTP_ODG saved to", save_dir + "GPT_ODG.graphml")
        nx.write_graphml(heuristic_ODG, save_dir + "heuristic_ODG.graphml")
        print("Heuristic ODG saved to", save_dir + "heuristic_ODG.graphml")    

        ODG_pyvis = net.Network(height="600px", width="100%", bgcolor="white", font_color="black", notebook=True, directed=True, neighborhood_highlight=True)
        ODG_pyvis.barnes_hut(gravity=-8000, central_gravity=1.5, spring_length=200, spring_strength=0.05)
        
        for node in GPT_ODG.nodes:
            ODG_pyvis.add_node(node, label=node, title=node)
        for edge in GPT_ODG.edges:
            ODG_pyvis.add_edge(edge[0], edge[1], title=edge[0] + " -> " + edge[1])
        for node in heuristic_ODG.nodes:
            ODG_pyvis.add_node(node, label=node, title=node)
        for edge in heuristic_ODG.edges:
            ODG_pyvis.add_edge(edge[0], edge[1], title=edge[0] + " -> " + edge[1])    
        
        ODG_pyvis.show(save_dir+"ODG.html")
    def build_complete_graph_from(self):
        GPT_ODG_path = self.working_directory + "GPT_ODG.graphml"
        heuristic_ODG_path = self.working_directory + "heuristic_ODG.graphml"
        
        heuristic_ODG_analyzer = Analyzer(self.service_name, self.working_directory)
        heuristic_ODG_analyzer.load_graphml(heuristic_ODG_path)
        heuristic_ODG_analyzer.analyze()
        heuristic_ODG_analyzer.get_operation_sequences_dict()
        
        GPT_ODG_analyzer = Analyzer(self.service_name, self.working_directory)
        GPT_ODG_analyzer.load_graphml(GPT_ODG_path)
        GPT_ODG_analyzer.analyze()
        GPT_ODG_analyzer.get_operation_sequences_dict()
        
        # Join the two graphs
        joint_graph = nx.compose(heuristic_ODG_analyzer.graph, GPT_ODG_analyzer.graph)
        # If it is not a DAG, then we need to remove some edges
        if not nx.is_directed_acyclic_graph(joint_graph):
            print("[WARN] Phát hiện chu trình (cycle) trong đồ thị. Đang cố gắng phá vỡ...")
            
            # Liên tục tìm và phá vỡ chu trình cho đến khi đồ thị là DAG
            while not nx.is_directed_acyclic_graph(joint_graph):
                try:
                    # Tìm một chu trình
                    cycle = nx.find_cycle(joint_graph)
                    if not cycle:
                        break  # Đã trở thành DAG
                    
                    # Lấy cạnh đầu tiên trong chu trình (ví dụ: (A, B))
                    edge_to_remove = cycle[0] 
                    u, v = edge_to_remove[0], edge_to_remove[1]
                    
                    print(f"[FIX] Xóa cạnh {u} -> {v} để phá vỡ chu trình.")
                    joint_graph.remove_edge(u, v)
                
                except nx.NetworkXNoCycle:
                    # Không còn chu trình nào
                    break 
        
        assert nx.is_directed_acyclic_graph(joint_graph)
        
        # write joint graph to graphml file
        nx.write_graphml(joint_graph, self.working_directory + "ODG.graphml")
                
        # Sort the graph with Topo sort
        joint_graph_topo_list = list(nx.topological_sort(joint_graph))
        # Write to file
        joint_graph_topo_list_file_path = self.working_directory + "topolist.json"
        
        # Reverse the delete endpoints
        for i in range(len(joint_graph_topo_list) - 1, -1, -1):
            if joint_graph_topo_list[i].startswith('delete-'):
                joint_graph_topo_list.append(joint_graph_topo_list.pop(i))
        
        with open(joint_graph_topo_list_file_path, "w") as f:
            json.dump(joint_graph_topo_list, f, indent=2)

        # Save the graph to a file (GraphML format)
        # file_path = f"Tests/{service_name}/simplified_GPT_ODG.graphml"
        # nx.write_graphml(simplified_GPT_ODG, file_path)
        # print("Simplified GPT ODG graph saved to", file_path)
        
        with open(self.working_directory + "operation_sequences_gpt.json", "w") as f:
            json.dump(GPT_ODG_analyzer.operation_sequences_dict, f, indent=2)
            
        with open(self.working_directory + "operation_sequences_heuristic.json", "w") as f:
            json.dump(heuristic_ODG_analyzer.operation_sequences_dict, f, indent=2)   

        operation_sequences = {}
        
        endpoint_list = list(set(GPT_ODG_analyzer.operation_sequences_dict.keys()) | set(heuristic_ODG_analyzer.operation_sequences_dict.keys()))
        
        for endpoint in endpoint_list:
            operation_sequences[endpoint] = []
            
            # Prioritize heuristic sequences as they follow logical API patterns
            heuristic_sequences = heuristic_ODG_analyzer.operation_sequences_dict.get(endpoint, [])
            heuristic_sequences.sort(key=len)
            
            # Add GPT sequences but filter out circular dependencies
            gpt_sequences = GPT_ODG_analyzer.operation_sequences_dict.get(endpoint, [])
            gpt_sequences.sort(key=len)
            
            # Filter out sequences that create circular dependencies
            filtered_gpt_sequences = []
            for sequence in gpt_sequences:
                if not self._has_circular_dependency(endpoint, sequence):
                    filtered_gpt_sequences.append(sequence)
            
            # Combine sequences with heuristic taking priority
            all_sequences = heuristic_sequences + filtered_gpt_sequences
            unique_sequences = []
            seen_sequences = set()

            for sequence in all_sequences:
                tuple_sequence = tuple(sequence)
                if tuple_sequence not in seen_sequences and not self._creates_logical_inconsistency(endpoint, sequence):
                    unique_sequences.append(sequence)
                    seen_sequences.add(tuple_sequence)

            if len(unique_sequences) > 2:
                operation_sequences[endpoint] = unique_sequences[:2]
            else:
                operation_sequences[endpoint] = unique_sequences
        
        with open(self.working_directory + "operation_sequences.json", "w") as f:
            json.dump(operation_sequences, f, indent=2)

        # Graph visualization
        simplified_ODG_pyvis = net.Network(height="600px", width="100%", bgcolor="white", font_color="black", notebook=True, directed=True, neighborhood_highlight=True)
        simplified_ODG_pyvis.barnes_hut(gravity=-9000, central_gravity=0.5, spring_length=180, spring_strength=0.1)
        
        endpoints = extract_endpoints(self.swagger_spec)
        for endpoint in endpoints:
            simplified_ODG_pyvis.add_node(endpoint, label=endpoint, title=endpoint)
            
        added_edges = []
        for node in operation_sequences:
            for sequence in operation_sequences[node]:
                for i in range(len(sequence)-1):
                    if (sequence[i], sequence[i+1]) not in added_edges:
                        simplified_ODG_pyvis.add_edge(sequence[i], sequence[i+1], title=sequence[i] + " -> " + sequence[i+1])
                        added_edges.append((sequence[i], sequence[i+1]))
                if (sequence[-1], node) not in added_edges:
                    simplified_ODG_pyvis.add_edge(sequence[-1], node, title=sequence[-1] + " -> " + node)
                    added_edges.append((sequence[-1], node))
        simplified_ODG_pyvis.show(self.working_directory + "ODG.html") 
        
    def generate_operation_dependency_graph(self):
        start_time = time.time()
        # Caching cho graph phase
        save_dir = self.working_directory
        gpt_graph_path = save_dir + "GPT_ODG.graphml"
        heuristic_graph_path = save_dir + "heuristic_ODG.graphml"
        odg_html_path = save_dir + "ODG.html"
        odg_graphml_path = save_dir + "ODG.graphml"
        topolist_path = save_dir + "topolist.json"
        # Disable caching for now to apply new filtering logic
        # TODO: Restore caching after logic is stable
        # if all([os.path.exists(p) for p in [gpt_graph_path, heuristic_graph_path, odg_html_path, odg_graphml_path, topolist_path]]):
        #     print("[CACHE] All graph files exist. Skipping graph generation.")
        #     return None, None
        heuristic_dependencies = heuristically_generate_dependencies(self.swagger_spec)
        heuristic_ODG = nx.DiGraph()
        heuristic_ODG.add_edges_from(heuristic_dependencies)
        self.generate_endpoint_dependencies()
        GPT_ODG = nx.DiGraph()   
        GPT_ODG.add_edges_from(self.endpoint_dependencies)
        self.save_graph_to_test_dir(GPT_ODG, heuristic_ODG)
        self.build_complete_graph_from()
        end_time = time.time()
        execution_time_seconds = end_time - start_time
        execution_time_minutes = int(execution_time_seconds // 60)
        execution_time_seconds = int(execution_time_seconds % 60)
        # For GPT's odg generation
        GPT_ODG_token_count = {
            "input_tokens": self.input_token_count,
            "output_tokens": self.output_token_count,
            "generation_time": f"{execution_time_minutes}m:{execution_time_seconds}s"
        }
        with open(self.working_directory + "odg_generation_token_count.json", "w") as f:
            json.dump(GPT_ODG_token_count, f, indent=2)
        return GPT_ODG, heuristic_ODG

    def _has_circular_dependency(self, endpoint, sequence):
        """
        Check if adding this sequence would create a circular dependency.
        """
        if not sequence:
            return False
        
        # Check if the endpoint appears in its own dependency sequence
        if endpoint in sequence:
            return True
        
        # Check for obvious circular patterns like A->B and B->A
        for i, dep_endpoint in enumerate(sequence):
            if self._would_create_cycle(endpoint, dep_endpoint):
                return True
        
        return False
    
    def _would_create_cycle(self, endpoint_a, endpoint_b):
        """
        Check if creating dependency endpoint_a -> endpoint_b would create a cycle
        based on existing known dependencies.
        """
        # Basic check: if B already depends on A, then A->B creates a cycle
        for dep_pair in self.endpoint_dependencies:
            if dep_pair[0] == endpoint_b and dep_pair[1] == endpoint_a:
                return True
        return False
    
    def _creates_logical_inconsistency(self, endpoint, sequence):
        """
        Check if the sequence creates logical inconsistencies based on REST API patterns.
        """
        if not sequence:
            return False
        
        endpoint_method = endpoint.split("-")[0]
        endpoint_path = "-".join(endpoint.split("-")[1:])
        
        for dep_endpoint in sequence:
            dep_method = dep_endpoint.split("-")[0]
            dep_path = "-".join(dep_endpoint.split("-")[1:])
            
            # Rule 1: Resource creation (POST) should not depend on operations that need the resource ID
            if endpoint_method == "post" and "{id}" not in endpoint_path:
                if "{id}" in dep_path and endpoint_path in dep_path:
                    # POST /projects should not depend on POST /projects/{id}/branches
                    return True
            
            # Rule 2: Operations requiring resource ID should depend on resource creation
            if "{id}" in endpoint_path and dep_method == "post" and "{id}" not in dep_path:
                # This is a valid dependency pattern - continue checking
                continue
                
        return False
