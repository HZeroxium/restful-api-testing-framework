import os
import json
import importlib.util
from kat.directory_config.directory_config import get_output_dir, get_test_data_working_dir

class TestCaseConverter:
    def __init__(self, service_name):
        self.service_name = service_name
        self.test_cases_dir = get_output_dir(service_name, "test_cases")
        self.validation_scripts_dir = "Validation scripts"
        self.test_data_dir = get_test_data_working_dir(service_name)

    def convert_test_case(self, test_case_file):
        """Convert a single test case JSON to Python test script"""
        with open(test_case_file, 'r') as f:
            test_case = json.load(f)

        test_case_data = test_case['test_case']
        test_name = test_case_data['id']
        steps = test_case_data['steps']
        
        # Create Python test script content
        script_content = f"""import pytest
import requests
import json
import os
from pathlib import Path

# Load test data
def load_test_data():
    test_data_dir = Path("{self.test_data_dir}")
    body_data = {{}}
    param_data = {{}}
    
    # Load body data if exists
    body_data_file = test_data_dir / "body_data.json"
    if body_data_file.exists():
        with open(body_data_file, 'r') as f:
            body_data = json.load(f)
            
    # Load parameter data if exists
    param_data_file = test_data_dir / "parameter_data.json"
    if param_data_file.exists():
        with open(param_data_file, 'r') as f:
            param_data = json.load(f)
            
    return body_data, param_data

def test_{test_name}():
    body_data, param_data = load_test_data()
    
"""
        # Add test steps
        for step in steps:
            endpoint = step['endpoint']
            method = step['method']
            path_vars = step['path_variables']
            query_params = step['query_parameters']
            request_body = step['request_body']
            response_validation = step['response_validation']
            
            # Add request
            script_content += f"""
    # Step {step['step_number']}: {endpoint}
    url = "http://localhost:8000{endpoint.split('-')[1]}"
    
    # Prepare path variables
    path_vars = {path_vars}
    for var, value in path_vars.items():
        if value is not None:
            url = url.replace(f"{{{var}}}", str(value))
            
    # Prepare query parameters
    params = {query_params}
    params = {{k: v for k, v in params.items() if v is not None}}
    
    # Prepare request body
    body = {request_body}
    
    # Make request
    response = requests.{method.lower()}(url, params=params, json=body)
    
    # Validate response
    assert response.status_code in range(200, 300)  # 2xx status code
"""
            
            # Add response validation if exists
            if response_validation.get('body_validation'):
                script_content += """
    # Validate response body
    response_data = response.json()
"""
                for field, validation in response_validation['body_validation'].items():
                    script_content += f"    assert '{field}' in response_data\n"

        # Write test script to file
        output_file = os.path.join(self.validation_scripts_dir, f"{test_name}.py")
        with open(output_file, 'w') as f:
            f.write(script_content)

    def convert_all_test_cases(self):
        """Convert all test cases in the test cases directory"""
        for file in os.listdir(self.test_cases_dir):
            if file.endswith('.json'):
                test_case_file = os.path.join(self.test_cases_dir, file)
                self.convert_test_case(test_case_file)

if __name__ == '__main__':
    converter = TestCaseConverter("Canada Holidays")
    converter.convert_all_test_cases() 