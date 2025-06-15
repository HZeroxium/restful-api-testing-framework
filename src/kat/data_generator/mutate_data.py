

import copy
import random

from kat.utils.swagger_utils.swagger_utils import find_object_with_key, get_ref


class DataMutator:
    @staticmethod
    def _mutate(data):
        """
        Mutation utility function
        """
        if isinstance(data, dict) or isinstance(data, list):
            return data
        
        if isinstance(data, str):
            return ""

        elif isinstance(data, int):
            # lst = [-1, 1e7, -1e7 + 1]
            lst = [-1, -1e7 + 1]
            return random.choice(lst)

        elif isinstance(data, float):
            # lst = [-1.0, float(1e9), -float(1e9), float(1e-9), -float(1e-9)]
            lst = [-1.0, -float(1e9), -float(1e-9)]
            return random.choice(lst)
        
        else:
            # Warning
            print("Warning: cannot mutate data of type", type(data))
            return data
    @staticmethod
    def mutate(data_item):
        """
        Mutate the data item to get invalid data
        """
        if isinstance(data_item, dict):
            for key, value in data_item.items():
                data_item[key] = DataMutator._mutate(value)
                DataMutator.mutate(data_item[key])
        elif isinstance(data_item, list):
            for i, item in enumerate(data_item):
                data_item[i] = DataMutator._mutate(item)
                DataMutator.mutate(data_item[i])

        return data_item 
    @staticmethod
    def mutate_wrong_dtype(swagger_spec, endpoint_data, true_data, for_request_body=False):
        """
        Mutate the true data to get wrong data type.
        The result consists len(true_data)*2 - 1 data items, based on true_data.
        """

        mutated_data = []

        if for_request_body == False:
            # Get param
            param = endpoint_data.get('definition', {}).get('parameters', [])
            if param == {}: return mutated_data

            # Step 1. Wrong 1 field each
            for p in param:
                data = copy.deepcopy(true_data)
                if not p.get('schema', {}).get('type', None): continue
                
                # Handle nested data structure - modify data["data"] if it exists
                target_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
                
                if p['schema']['type'] == 'string':
                    target_data[p['name']] = 123456789
                elif p['schema']['type'] == 'integer':
                    target_data[p['name']] = "123456"
                elif p['schema']['type'] == 'number':
                    target_data[p['name']] = "123456"
                elif p['schema']['type'] == 'boolean':
                    target_data[p['name']] = "123456"
                elif p['schema']['type'] == 'array':
                    target_data[p['name']] = "123456"
                elif p['schema']['type'] == 'object':
                    target_data[p['name']] = "123456"
                mutated_data.append(data)

            # Step 2. Wrong from 2 to n-1 fields each
            for j in range(2, len(param)+1):
                data = copy.deepcopy(true_data)
                # Handle nested data structure - modify data["data"] if it exists
                target_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
                
                # Randomly choose k fields to be wrong
                random.shuffle(param)
                for k in range(j):
                    if not param[k].get('schema', {}).get('type', None): continue
                    if param[k]['schema']['type'] == 'string':
                        target_data[param[k]['name']] = 123456789
                    elif param[k]['schema']['type'] == 'integer':
                        target_data[param[k]['name']] = "123456"
                    elif param[k]['schema']['type'] == 'number':
                        target_data[param[k]['name']] = "123456"
                    elif param[k]['schema']['type'] == 'boolean':
                        target_data[param[k]['name']] = "123456"
                    elif param[k]['schema']['type'] == 'array':
                        target_data[param[k]['name']] = "123456"
                    elif param[k]['schema']['type'] == 'object':
                        target_data[param[k]['name']] = "123456"
                mutated_data.append(data) 
        else:
            # mutate for request body
            # Get request body specification
            request_body = endpoint_data.get('definition', {}).get('requestBody', {})
            if request_body == {}: return mutated_data
            
            # Get request body schema
            request_body_schema_ref = find_object_with_key(request_body, "$ref")
            if request_body_schema_ref is None: return mutated_data
            request_body_schema = get_ref(swagger_spec, request_body_schema_ref["$ref"])
            if request_body_schema is None: return mutated_data
            
            properties = request_body_schema.get("properties", {})
            if properties == {}: return mutated_data
            
            property_names = list(properties.keys())
            
            # Step 1. Wrong 1 field each
            for p in properties.keys():
                data = copy.deepcopy(true_data)
                if 'type' not in properties[p]: continue
                
                # Handle nested data structure - modify data["data"] if it exists
                target_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
                
                if properties[p]['type'] == 'string':
                    target_data[p] = 123456789
                elif properties[p]['type'] == 'integer':
                    target_data[p] = "123456"
                elif properties[p]['type'] == 'number':
                    target_data[p] = "123456"
                elif properties[p]['type'] == 'boolean':
                    target_data[p] = "123456"
                elif properties[p]['type'] == 'array':
                    target_data[p] = "123456"
                elif properties[p]['type'] == 'object':
                    target_data[p] = "123456"
                mutated_data.append(data)

            # Step 2. Wrong from 2 to n-1 fields each
            for j in range(2, len(property_names)+1):
                data = copy.deepcopy(true_data)
                # Randomly choose k fields to be wrong
                random.shuffle(property_names)
                for k in range(j):
                    if 'type' not in properties[property_names[k]]: continue
                    if properties[property_names[k]]['type'] == 'string':
                        data[property_names[k]] = 123456789
        return mutated_data
    @staticmethod
    def ignore_optional_param_combination(swagger_spec,swagger_spec_required_fields, base_item, endpoint, for_request_body=False):
        """
        Mutate the true data to get missing optinal fields.
        The result consists len(required_true_data)*2 - 1 data items, based on true_data.
        """      
        if isinstance(base_item, list):
            base_item = base_item[0]
        if not isinstance(base_item, dict):
            return []
          
        data_items = []
        
        endpoint_required_fields = swagger_spec_required_fields[endpoint]

        param = list(base_item.keys())
        if param == []: return data_items
        
        required_fields = []
        optional_fields = []
        
        required_fields_spec = None
        if for_request_body:
            required_fields_spec = endpoint_required_fields.get("requestBody", None)
        else:
            required_fields_spec = endpoint_required_fields.get("parameters", None)
            
        if required_fields_spec is not None:
            required_fields = list(required_fields_spec.keys())
        
        optional_fields = [field for field in param if field not in required_fields]

        # Step 1. Miss 1 required field each
        for p in optional_fields:
            data = copy.deepcopy(base_item)
            # Handle nested data structure - modify data["data"] if it exists
            target_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
            target_data[p] = None
            data_items.append(data)
                    
        # Step 2. Miss from 2 to n-1 optional fields each
        for j in range(2, len(optional_fields)+1):
            data = copy.deepcopy(base_item)
            # Handle nested data structure - modify data["data"] if it exists
            target_data = data.get("data", data) if isinstance(data.get("data"), dict) else data
            # Randomly choose k required fields to miss
            random.shuffle(optional_fields)
            for k in range(j):
                target_data[optional_fields[k]] = None
            data_items.append(data)
            
        data_items.reverse()
        
        return data_items