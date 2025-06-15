from kat.utils.swagger_utils.swagger_utils import find_object_with_key, get_ref
def get_successful_responses(self, endpoint):
    method = endpoint.split("-")[0]
    path = "-".join(endpoint.split("-")[1:])
    responses = self.swagger_spec["paths"][path][method]["responses"]

    response_schemas = []
    for response_code in responses:
        if response_code.startswith("2"):
            schema_ref = find_object_with_key(responses[response_code], "$ref")
            if schema_ref is not None:
                response_schemas.append(get_ref(self.swagger_spec, schema_ref["$ref"]))
    return response_schemas

def get_failed_responses(self, endpoint):
    method = endpoint.split("-")[0]
    path = "-".join(endpoint.split("-")[1:])
    responses = self.swagger_spec["paths"][path][method]["responses"]
    response_schemas = []
    for response_code in responses:
        if not response_code.startswith("2"):
            schema_ref = find_object_with_key(responses[response_code], "$ref")
            if schema_ref is not None:
                response_schemas.append(get_ref(self.swagger_spec, schema_ref["$ref"]))
    return response_schemas

def add_response_validation(self, test_script, endpoint):
    success_responses = self.get_successful_responses(endpoint)
    failure_responses = self.get_failed_responses(endpoint)
        
    if not success_responses and not failure_responses:
        return test_script
    
    # remove all $ref keys from the schema
    def remove_ref_keys(data):
        if isinstance(data, dict):
            return {key: remove_ref_keys(value) for key, value in data.items() if key != "$ref"}
        elif isinstance(data, list):
            return [remove_ref_keys(item) for item in data]
        else:
            return data
        
    test_script += "\n\n"
    for i in range(len(success_responses)):
        success_responses[i] = remove_ref_keys(success_responses[i])
        success_responses[i]["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        test_script += "def schema_" + str(i+1) + " = \n'''\n" + json.dumps(success_responses[i], indent=2) + "\n'''\n"
        
    for i in range(len(failure_responses)):
        failure_responses[i] = remove_ref_keys(failure_responses[i])
        failure_responses[i]["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        test_script += "def schema_" + str(i+len(success_responses)+1) + " = \n'''\n" + json.dumps(failure_responses[i], indent=2) + "\n'''\n"
    
    test_script += "\n"
    for i in range(len(success_responses)+len(failure_responses)):
        test_script += "\ntry {\n"
        test_script += f"\tWS.validateJsonAgainstSchema(latest_response[1], schema_{i+1})\n\treturn"
        test_script += "\n} catch (AssertionError e) {\n\tprintln(e)\n}"
    
    test_script += "\n"
    test_script += "assert false"

    return test_script
        