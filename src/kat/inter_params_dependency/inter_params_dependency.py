from kat.utils.llm.gpt.gpt import GPTChatCompletion
from kat.document_parser.document_parser import extract_endpoints, get_swagger_spec, write_anything_to_file
import logging
import json
import subprocess

from kat.utils.swagger_utils.swagger_utils import get_endpoint_params
VIOLATE_INTER_PARAM_CONTEXT = r'''{org_context}
To violate the inter-parameter dependency, you can try to to change the values of parameters to make it violate the dependency, or even remove one of the parameters in the dependency declared.'''
INTER_PARAM_CONTEXT = r'''Additional context to be used for detecting inter-parameter dependencies:
P/S: Note that all the fields of data items are now must be filled with values, and also the values must be valid.
{context}'''
DETECT_INTER_PARAM_DEPENDENCIES_PROMPT = r'''Given parameters' definition of a REST APIs, each parameter has a description and it may indicate a relationship to another parameter. Your responsibility is to detect all inter parameter dependencies based on descriptions.

The below is parameters and their descriptions of a REST API:
{request_data}

STRICTLY FOLLOW these rules:
1. Parameters have inter-parameter dependencies, meaning that the usage of one parameter can affect the behavior or applicability of another parameter.
2. Only infer inter-parameter dependencies from the description of parameters, if a parameter does not have a description, it does not have any inter-parameter dependencies.

Now, please list all inter-parameter dependencies that satisfy all of these rules above. If no dependency is detected, please leave it with "No dependencies detected".'''

GENERATE_INTER_PARAM_DEPENDENCY_VALIDATION_FUNC = r'''
Given parameters' definition of a REST API, each parameter has a description and it may indicate a relationship to another parameter. Your responsibility is to detect all inter parameter dependencies based on descriptions.

The below is parameters and their descriptions of a REST API:
{request_data}

The below is the dependencies you have detected:
{context}

Based on these inter-parameter dependencies, write a Python function to validate a request data item to determine if the data item satisfies these dependencies or not. The input to this function is a JSON object representing request data, and the output is either True (if the dependencies are satisfied) or False (if the dependencies are not satisfied). Use try-except for each dependency checker to ignore all errors when validating a data item. If an error occurs skip that dependency (does not return here) and continue checking another dependency.

NOTE: If a rule implies that a parameter is required (do not overlook it to ensure the request is valid), please include a check for that parameter, which should encompass checking for its existence and verifying the validity of its value.

Follow the boilerplate below to generate validation function:
def validate_request_data(request_data_item):
    try:
        # Check dependency 1
        # Return False if the data item does not satisfy dependency 1
    except:
        pass  # Skip this dependency if an error occurs

    try:
        # Check dependency 2
    except:
        pass

    # ... (continue checking other dependencies)
    return True

Only respond your general validation function. Please do not explain anything.
'''

class InterParamsDependencyTool:
    def __init__(self, swagger_spec):
        self.swagger_spec = swagger_spec
        self.filtered_endpoint_param_w_descr = self._filter_params_w_descr()

    def _filter_params_w_descr(self):
        filtered_endpoint_param_w_descr = {}
        endpoint_param_w_descr = get_endpoint_params(self.swagger_spec, get_description=True)

        for endpoint in endpoint_param_w_descr:
            filtered_endpoint_param_w_descr[endpoint] = {}
            if endpoint_param_w_descr.get(endpoint, {}).get("parameters"):
                filtered_endpoint_param_w_descr[endpoint]["parameters"] = {
                    param: value for param, value in endpoint_param_w_descr[endpoint]["parameters"].items()
                    if "description" in value
                }
            if isinstance(endpoint_param_w_descr.get(endpoint, {}).get("requestBody"), dict):
                filtered_endpoint_param_w_descr[endpoint]["requestBody"] = {
                    param: value for param, value in endpoint_param_w_descr[endpoint]["requestBody"].items()
                    if "description" in value
                }
            else:
                logging.warning(f"Request body of {endpoint} is not a dictionary")
                filtered_endpoint_param_w_descr[endpoint]["requestBody"] = {}
        return filtered_endpoint_param_w_descr

    def get_inter_param_constraints(self, endpoint: str, part: str = "all") -> str:
        if part not in ["param", "body", "all"]:
            raise ValueError("Argument 'part' must be one of: 'param', 'body', 'all'")

        if endpoint not in self.filtered_endpoint_param_w_descr:
            return ""

        request_data_dict = {}
        if part in ['param', 'all'] and self.filtered_endpoint_param_w_descr[endpoint].get("parameters"):
            request_data_dict["parameters"] = self.filtered_endpoint_param_w_descr[endpoint]["parameters"]

        if part in ['body', 'all'] and self.filtered_endpoint_param_w_descr[endpoint].get("requestBody"):
            request_data_dict["requestBody"] = self.filtered_endpoint_param_w_descr[endpoint]["requestBody"]

        if not request_data_dict:
            return ""

        request_data = {endpoint: request_data_dict}
        prompt = DETECT_INTER_PARAM_DEPENDENCIES_PROMPT.format(request_data=json.dumps(request_data))

        response = GPTChatCompletion(prompt, system="", temperature=0.0, max_tokens=1024)
        return "" if response.startswith("No dependencies") else response

    def get_inter_param_validation_script(self, endpoint: str, part: str = "all", constraints="") -> str:
        if not constraints or endpoint not in self.filtered_endpoint_param_w_descr:
            return ""

        request_data_dict = {}
        if part in ['param', 'all'] and self.filtered_endpoint_param_w_descr[endpoint].get("parameters"):
            request_data_dict["parameters"] = self.filtered_endpoint_param_w_descr[endpoint]["parameters"]

        if part in ['body', 'all'] and self.filtered_endpoint_param_w_descr[endpoint].get("requestBody"):
            request_data_dict["requestBody"] = self.filtered_endpoint_param_w_descr[endpoint]["requestBody"]

        if not request_data_dict:
            return ""

        request_data = {endpoint: request_data_dict}
        prompt = GENERATE_INTER_PARAM_DEPENDENCY_VALIDATION_FUNC.format(
            request_data=json.dumps(request_data),
            context=constraints
        )

        validation_script = GPTChatCompletion(prompt, system="", temperature=0.0)
        validation_script += "\n\nprint(validate_request_data({request_data_item}))"
        return validation_script

    def inter_param_data_items_filter(self, json_data_list, validation_script, filter_valid=True):
        invalid_rows = []
        for i, json_data in enumerate(json_data_list):
            try:
                print(json.dumps(json_data, indent=2))
                script = validation_script.format(request_data_item=json_data)
                output = subprocess.check_output(["python", "-c", script], stderr=subprocess.STDOUT, universal_newlines=True)
                print(f"Row {i}: {output}")
                if (filter_valid and output.strip() == "False") or (not filter_valid and output.strip() == "True"):
                    invalid_rows.append(i)
            except Exception as e:
                print("[INFO] Execute validation script exception: ", e)
                pass

        for i in reversed(invalid_rows):
            del json_data_list[i]

        return json_data_list
import os

if __name__ == "__main__":
    spec_name = "Canada Holidays"
    path_input = f"Dataset/{spec_name}/openapi.json"
    path_output = f"TestData/{spec_name}/inter_params_dependency/endpoints.json"

    # ✅ Nếu output đã tồn tại → Bỏ qua xử lý
    if os.path.exists(path_output):
        print(f"[SKIPPED] Output already exists at: {path_output}")
    else:
        swagger_spec = get_swagger_spec(path_input)
        endpoints_list = extract_endpoints(swagger_spec)
        test = InterParamsDependencyTool(swagger_spec)

        inter_param_constraints_list = []
        get_inter_param_validation_script = []

        for endpoint in endpoints_list:
            constraints = test.get_inter_param_constraints(endpoint)
            inter_param_constraints_list.append({
                "endpoint": endpoint,
                "constraints": constraints
            })
            validation_script = test.get_inter_param_validation_script(endpoint, constraints=constraints)
            get_inter_param_validation_script.append({
                "endpoint": endpoint,
                "validation_script": validation_script
            })

        output_content = {
            "filtered_endpoint_param_w_descr": test.filtered_endpoint_param_w_descr,
            "inter_param_constraints_list": inter_param_constraints_list,
            "get_inter_param_validation_script": get_inter_param_validation_script
        }

        write_anything_to_file(path_output, json.dumps(output_content, indent=2))
        print("[✓] Done and written to:", path_output)
