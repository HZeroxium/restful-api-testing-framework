# config/template/execution.py

"""
Templates used for executing scripts in the RBCTest framework.
"""

# Template for executing a verification script against a response body
EXECUTION_SCRIPT = """\
{generated_verification_script}

import json
latest_response = json.loads(open("{file_path}",).read())
status = verify_latest_response(latest_response)
print(status)
"""

# Template for executing a verification script against a request and response body
INPUT_PARAM_EXECUTION_SCRIPT = """\
{generated_verification_script}

import json

def pre_check(json, key):
    if isinstance(json, dict):
        for k, v in json.items():
            if k == key:
                return True
            if pre_check(v, key):
                return True
    elif isinstance(json, list):
        for item in json:
            if pre_check(item, key):
                return True
    return False


latest_response = json.loads(open("{api_response}", encoding="utf-8").read())
request_info = json.loads(open("{request_info}", encoding="utf-8").read())

if not pre_check(request_info, "{request_param}") or not pre_check(latest_response, "{field_name}"):
    status = 0
else:
    status = verify_latest_response(latest_response, request_info)
print(status)
"""

# Template for script generator execution
GENERATOR_EXECUTION_SCRIPT = """\
{generated_verification_script}

import json
latest_response = json.loads('''{api_response}''')
status = verify_latest_response(latest_response)
print(status)
"""

# Template for script generator with input parameters
GENERATOR_INPUT_PARAM_EXECUTION_SCRIPT = """\
{generated_verification_script}

import json


latest_response = json.loads('''{api_response}''')
request_info = json.loads('''{request_info}''')
status = verify_latest_response(latest_response, request_info)
print(status)
"""
