import json
from collections import defaultdict
import sys
from typing import List
from kat.utils.swagger_utils.swagger_utils import find_object_with_key

orders = []
q = []

def get_ref(spec, ref):
    sub = ref[2:].split('/')
    schema = spec
    for e in sub:
        schema = schema.get(e, {})
    return schema


def list_all_param_names(spec, d: dict, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    if d is None:
        return []

    if '$ref' in d:
        ref = d['$ref']
        if ref in visited_refs:
            return []  # Prevent infinite recursion for circular references
        visited_refs.add(ref)
        return list_all_param_names(spec, get_ref(spec, ref), visited_refs)

    if d.get('type') == 'object':
        res = list(d.get('properties', {}).keys())
        for val in d.get('properties', {}).values():
            res += list_all_param_names(spec, val, visited_refs)
        return res
    elif d.get('type') == 'array':
        return list_all_param_names(spec, d.get('items', {}), visited_refs)
    elif 'name' in d:
        return [d.get('name')]
    else:
        return []

class Operation():
    def __repr__(self) -> str:
        return f"{self.method}-{self.endpoint}"

    def __init__(self, method, endpoint, swagger):
        self.method = method
        self.endpoint = endpoint
        self.swagger = swagger
        self.parse_input()
        self.parse_output()

    def __hash__(self) -> int:
        return hash(f"{self.method} {self.endpoint}")

    def __eq__(self, __value: object) -> bool:
        if type(self) != type(__value):
            return False
        return self.method == __value.method and self.endpoint == __value.endpoint
    
    def __lt__(self,  __value: object) -> bool:
        return True
    
    def parse_input(self):
        parameters_specification = self.swagger.get('paths', {}) \
            .get(self.endpoint, {}) \
            .get(self.method, {}) \
            .get("parameters", [])
            
        request_body_specification = self.swagger.get('paths', {}) \
            .get(self.endpoint, {}) \
            .get(self.method, {}) \
            .get("requestBody", {})    
        
        self.input_params = []
        for p in parameters_specification:
            self.input_params += list_all_param_names(self.swagger, p)
        
        if request_body_specification:
            ref_obj = find_object_with_key(request_body_specification, "$ref")
            if ref_obj:
                self.input_params += list_all_param_names(self.swagger, ref_obj)
            else:
                self.input_params += list_all_param_names(self.swagger, request_body_specification)

        self.input_params = list(set(e for e in self.input_params if e is not None))

    def parse_output(self):
        responses_specification = self.swagger.get('paths', {}) \
            .get(self.endpoint, {}) \
            .get(self.method, {}) \
            .get("responses", {})
        self.output_params = []
        for status_code in responses_specification.keys():
            if not status_code.isdigit():
                continue
            if int(status_code) < 200 or 300 <= int(status_code):
                continue
            spec = responses_specification.get(status_code, {})
            if spec:
                ref_obj = find_object_with_key(spec, "$ref")
                if ref_obj:
                    self.output_params += list_all_param_names(self.swagger, ref_obj)   
            
            self.output_params += list_all_param_names(self.swagger, spec)
        self.output_params = list(set(e for e in self.output_params if not e is None))      


def has_connection(u, v):
    if u.method == "delete":
        return False
    
    if u.endpoint == v.endpoint:
        if ["post", "get", "put", "delete"].index(u.method) > ["post", "get", "put", "delete"].index(v.method):
            return False
        for i in u.output_params:
            for j in v.input_params:
                if i == j:
                    return True
                
    elif v.endpoint.startswith(u.endpoint):
        for i in u.output_params:
            for j in v.input_params:
                if i == j:
                    return True
    return False

def find_operation(method, endpoint):
    for o in operations:
        if o.method == method and o.endpoint == endpoint:
            return o
    return None


def find_min_weight():
    w = []
    for u in operations:
        if is_visited[u]:
            continue
        for v in edges[u]:
            if is_visited[v]:
                continue
            
            w.append((len(set(u.output_params) & set(v.input_params)), u, v))
    w = sorted(w)
    _, u, v = w[0]
    return u, v

def heuristically_generate_dependencies(swagger):
    global operations
    global in_degrees
    global edges
    global is_visited

    operations = []

    for endpoint in swagger.get('paths').keys():
        for method in swagger.get('paths').get(endpoint).keys():
            if method not in ["get", "post", "put", "delete"]:
                continue
            operations.append(Operation(method, endpoint, swagger))
    
    dependencies = []
    
    for u in operations:
        for v in operations:
            if u == v:
                continue
            if has_connection(u, v):
                dependencies.append((str(u), str(v)))
            
    return dependencies

