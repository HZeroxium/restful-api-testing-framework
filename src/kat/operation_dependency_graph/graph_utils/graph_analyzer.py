import networkx as nx
import json
import copy
import heapq
from queue import PriorityQueue


def is_post_operation(operation):
    return operation.split("-")[0] == "post"

def list_exists_in_list_of_lists(target_list, list_of_lists):
    return any(target_list == sub_list for sub_list in list_of_lists)

def is_valid_sequence(sequence):
    return len(sequence) == len(list(set(sequence)))

def ranking_operation_sequences(sequences):
    min_length_post = float('inf')
    min_length_get = float('inf')
    min_length_post_sequences = []
    min_length_get_sequences = []

    for sequence in sequences:
        length = len(sequence)
        first_operation = sequence[0] if length > 0 else None

        if is_post_operation(first_operation):
            if length < min_length_post:
                min_length_post = length
                min_length_post_sequences = [sequence]
            elif length == min_length_post:
                min_length_post_sequences.append(sequence)
        else:
            if length < min_length_get:
                min_length_get = length
                min_length_get_sequences = [sequence]
            elif length == min_length_get:
                min_length_get_sequences.append(sequence)

    if min_length_post_sequences:
        return min_length_post_sequences
    else:
        return min_length_get_sequences

def find_shortest_sequences(sequences):
    if not sequences:
        return []

    shortest_length = min(len(seq) for seq in sequences)
    shortest_sequences = [seq for seq in sequences if len(seq) == shortest_length]

    return shortest_sequences

def BFS_search_paths(G, target_node):
    all_paths = []
    
    root_nodes = [node for node in G.nodes if len(list(G.predecessors(node))) == 0]

    for root_node in root_nodes:
        queue = [(root_node, [root_node])]  # Queue holds node and its path
        while queue:
            current_node, path = queue.pop(0)
            if current_node == target_node:
                all_paths.append(path)
            neighbors = list(G.neighbors(current_node))
            for neighbor in neighbors:
                if neighbor not in path:
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))
    return all_paths

class Analyzer:
    def __init__(self, service_name, save_dir):
        self.graph = None   
        self.simplifed_graph = {}
        self.service_name = service_name
        self.save_dir = save_dir

        self.endpoint_schema_dependencies = json.load(open(self.save_dir + "endpoint_schema_dependencies.json", "r"))
        self.endpoints_belong_to_schemas = json.load(open(self.save_dir + "endpoints_belong_to_schemas.json", "r"))
        
    def load_graphml(self, file_path):
        self.graph = nx.read_graphml(file_path)
        if self.graph is None:
            raise Exception("Failed to load graph from {}".format(file_path))
        else:
            print("Loaded graph from {}".format(file_path))
            # print(self.graph.nodes)
    
    def load_graphjs(self, file_path):
        with open(file_path, "r") as f:
            graph = json.load(f)
            self.graph = nx.node_link_graph(graph)
        if self.graph is None:
            raise Exception("Failed to load graph from {}".format(file_path))
        else:
            print("Loaded graph from {}".format(file_path))
            # print(self.graph.nodes)

    def load_graph(self, graph):
        if graph is not None:
            self.graph = graph
        
    def analyze(self):    
        self.odg = {}
        
        for node in self.graph.nodes:
            self.odg[node] = list(self.graph.predecessors(node))
            
        return self.odg
    
    # def operation_sequences(self, operation, visited=None):
    #     if visited is None:
    #         visited = set()

    #     if operation in visited:
    #         return []

    #     visited.add(operation)
    #     sequences = []

    #     for node in self.odg[operation]:
    #         next_sequences = self.operation_sequences(node, visited)
            
    #         if not next_sequences:
    #             sequences.append([node])
    #         else:
    #             for sequence in next_sequences:
    #                 sequences.append(sequence + [node])

    #     visited.remove(operation)
    #     return sequences


    def operation_sequences(self, operation):
        # Find root nodes to start BFS
        if operation not in self.odg or not self.odg[operation]:
            return []
        
        start_nodes = copy.deepcopy(self.odg[operation])

        # Priority queue to store sequences by their length (shortest first)
        pq = PriorityQueue()
        # Initialize the queue with root nodes
        for node in start_nodes:
            pq.put((1, [node]))  # (sequence length, sequence)

        # List to store the top n sequences
        #___Configuration___
        n = 2
        #___________________
        
        top_sequences = []

        while not pq.empty() and len(top_sequences) < n:
            seq_len, sequence = pq.get()
            last_node = sequence[-1]

            # If the last node has no further dependencies, skip
            if last_node not in self.odg or not self.odg[last_node]:
                sequence.reverse()
                top_sequences.append(sequence)
                continue

            # Expand the sequence with the dependencies of the last node
            for next_node in self.odg[last_node]:
                if next_node not in sequence:  # Avoid cycles
                    new_sequence = sequence + [next_node]
                    pq.put((seq_len + 1, new_sequence))

        # Sort the sequences by their length before returning
        top_sequences.sort(key=len)
        return top_sequences

    def build_simplifer_graph(self, sequences):
        for sequence in sequences:
            for i in range(len(sequence) - 1):
                if sequence[i] == sequence[i+1]:
                    continue
                if sequence[i] not in self.simplifed_graph:
                    self.simplifed_graph[sequence[i]] = [sequence[i+1]]
                elif sequence[i+1] not in self.simplifed_graph[sequence[i]]:
                    self.simplifed_graph[sequence[i]].append(sequence[i+1])
    
    def get_operation_sequences_dict(self):
        self.operation_sequences_dict = {}
        for operation in self.odg.keys():
            sequences = self.operation_sequences(operation)
            self.operation_sequences_dict[operation] = sequences
                    
    def optimizing_operation_sequences(self, operation, sequences):
        if operation not in self.endpoint_schema_dependencies:
            print(f"Cannot find {operation} in endpoint_schema_dependencies")
            return sequences

        optimized_sequences = {}
        for schema in self.endpoint_schema_dependencies[operation]:
            optimized_sequences[schema] = []

        for sequence in sequences:
            # ignore invalid sequences, that is, sequences containing duplicate operations
            if list(set(sequence)) != sequence:
                continue
            for op in sequence:
                for schema in optimized_sequences:
                    if schema not in self.endpoints_belong_to_schemas:
                        continue
                    if op in self.endpoints_belong_to_schemas[schema] and not list_exists_in_list_of_lists(sequence, optimized_sequences[schema]):
                        optimized_sequences[schema].append(sequence)

        complete_sequences = []
        for sequence in sequences:
            if all(list_exists_in_list_of_lists(sequence, optimized_sequences[schema]) for schema in optimized_sequences):
                complete_sequences.append(sequence)
                
        if complete_sequences:
            # after_ranking_sequences = ranking_operation_sequences(complete_sequences)
            # return after_ranking_sequences
            return sorted(complete_sequences, key=len)
        else:
            covering_sequences = []
            for schema in optimized_sequences:
                covering_sequences += optimized_sequences[schema]
            return sorted(covering_sequences, key=len)

    # def query_optimized_sequences(self, operation):
    #     return self.optimized_sequences[operation] if operation in self.optimized_sequences else []

    def to_graph(self):
        edges = []
        for key in self.simplifed_graph.keys():
            for value in self.simplifed_graph[key]:
                edges.append((key,value))
        simplified_ODG = nx.DiGraph()
        simplified_ODG.add_edges_from(edges)
        return simplified_ODG
    # chưa cần sử dụng
    # def verifying_simplifying_graph(self, swagger_spec):
    #     endpoints = extract_endpoints(swagger_spec)
    #     for endpoint in endpoints:
    #         try:
    #             method = endpoint.split("-")[0]
    #             path = "-".join(endpoint.split("-")[1:])
    #         except:
    #             st.error("Cannot analyze endpoint: {}, please review it manually".format(endpoint))
    #             continue
    #         if endpoint not in self.odg.keys():
    #             st.error("GPT missed endpoint: {} in ODG".format(endpoint))
    #             continue
    #         sequences = self.operation_sequences(endpoint)
    #         if not sequences:
    #             endpoint_swagger_infor = swagger_spec['paths'][path][method]
    #             # convert endpoint_swagger_infor to string
    #             endpoint_swagger_infor = json.dumps(endpoint_swagger_infor)
    #             if 'parameters' in endpoint_swagger_infor and '''"in": "path"''' in endpoint_swagger_infor:
    #                 st.error("[Dependency is missed] Operation: {}".format(endpoint))
    #         else:
    #             valid_sequences = []
    #             for sequence in sequences:
                    
    #                 if endpoint in sequence:
    #                     st.error("[There exists an invalid sequence] Operation: {} | Sequence: {}".format(endpoint, sequence))
    #                     continue
                    
    #                 first_operation = sequence[0]
    #                 try:
    #                     method = first_operation.split("-")[0]
    #                     path = "-".join(first_operation.split("-")[1:])
    #                 except:
    #                     st.error("Cannot analyze endpoint: {}, please review it manually".format(endpoint))
    #                     continue
                    
    #                 endpoint_swagger_infor = swagger_spec['paths'][path][method]
    #                 # convert endpoint_swagger_infor to string
    #                 endpoint_swagger_infor = json.dumps(endpoint_swagger_infor)
    #                 if 'parameters' in endpoint_swagger_infor and '''"in": "path"''' in endpoint_swagger_infor:
    #                     st.error("[There exists an invalid sequence] Operation: {} | Sequence: {}".format(endpoint, sequence))
    #                     continue
                
    #                 valid_sequences.append(sequence)
                    
    #             if not valid_sequences:
    #                 st.error("[No valid sequence is found] Operation: {}".format(endpoint))
                    
