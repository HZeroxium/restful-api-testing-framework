# config/prompts/script_generation.py

"""
Prompts used for script generation in the RBCTest framework.
"""

INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API's response, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the API response.

Below is the attribute's description:
- "{attribute}": "{description}"

Below is the API response's schema:
{response_schema_specification}

Now, help to generate a Python script to verify the attribute "{attribute}" in the API response. Follow these rules below:

Rules:
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. 
- Format your answer as shown in the backtick block below.
```python
def verify_latest_response(latest_response):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```
- No explanation is needed.
"""

INSIDE_RESPONSEBODY_SCRIPT_CONFIRM_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API's response, your responsibility is to confirm whether the provided Python script can verify these constraints through the API response. 
This is the attribute's description:
- "{attribute}": "{description}"

This is the API response's schema:
{response_schema_specification}

This is the generated Python script to verify the attribute "{attribute}" in the API response:
```python
{generated_verification_script}
```

Task 1: Confirm whether the provided Python script can verify the constraints of the attribute "{attribute}" in the API response.
If the script is correct, please type "yes". Incorrect, please type "no".


Task 2: If the script is incorrect, please provide a revised Python script to verify the constraints of the attribute "{attribute}" in the API response.
In your code, no need to fix the latest_response variable, just focus on the verification flow.
Do not repeat the old script.
Format your answer as shown in the backtick block below.
```python
// import section

def verify_latest_response(latest_response):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```

"""

RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT = """Given a description implying constraints, rules, or limitations of an input parameter in a REST API, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the REST API's response.

Below is the input parameter's description:
- "{parameter}": "{parameter_description}"


Below is the API response's schema:
{response_schema_specification}

Below is the corresponding attribute of the provided input parameter in the API response:
{attribute_information}

Now, based on the provided request information, input parameter, and the corresponding attribute in the API response,
help generate a Python script to verify the '{attribute}' attribute in the API response against the constraints of the input parameter '{parameter}'. 
Follow the rules below:

Rules:
- The input parameter can be null or not exist in the request_info dictionary.
- The attribute in the latest_response may not exist or be null.
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute {parameter}.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- 'request_info' is a dictionary containing the information of the request to the API. for example {{"created[gt]": "1715605373"}}
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. The script should be formatted within triple backticks as shown below: 
```python
def verify_latest_response(latest_response, request_info):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```
- No explanation is needed."""

RESPONSEBODY_PARAM_SCRIPT_CONFIRM_PROMPT = """Given a description implying constraints, rules, or limitations of an input parameter in a REST API, your responsibility is to confirm whether the provided Python script can verify these constraints through the REST API's response.

Below is the input parameter's description:
- "{parameter}": "{parameter_description}"

Below is the API response's schema:
{response_schema_specification}

Below is the corresponding attribute of the provided input parameter in the API response:
{attribute_information}

This is the generated Python script to verify the '{attribute}' attribute in the API response against the constraints of the input parameter '{parameter}':

```python
{generated_verification_script}
```

Task 1: Confirm whether the provided Python script can verify the constraints of the attribute "{attribute}" in the API response.
If the script is correct, please type "yes". Incorrect, please type "no".

Task 2: If the script is incorrect, please provide a revised Python script to verify the constraints of the attribute "{attribute}" in the API response.
In your code, no need to fix the latest_response variable, just focus on the verification flow.
Do not repeat the old script.
Check those rules below:
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- 'request_info' is a dictionary containing the information of the request to the API. for example {{"created[gt]": "1715605373"}}
- Remember to cast the request_info values to the appropriate data type before comparing them with the response attribute.
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. The script should be formatted within triple backticks as shown below: 

Format your answer as shown in the backtick block below.
```python
// import section

def verify_latest_response(latest_response, request_info):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).

```
"""
